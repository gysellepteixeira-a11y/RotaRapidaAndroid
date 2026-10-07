from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
P=Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
A=Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")
L=Path("app/src/main/res/layout/activity_main.xml")

s=S.read_text(encoding="utf-8")
p=P.read_text(encoding="utf-8")
a=A.read_text(encoding="utf-8")
x=L.read_text(encoding="utf-8")

required=[
    'private fun updateFloatingToggleAppearanceV52()',
    'private fun toggleBotFromFloatingV52()',
    'floatingPrefsListenerV52',
    'Prefs.setSearchArmed(this,true)',
    'Prefs.setSearchArmed(this,false)',
]
for m in required:
    if m not in s:
        raise SystemExit("v54 wrong service base: "+m)

# PREFS: persistent visibility of the floating overlay. Default=true.
if 'KEY_FLOATING_OVERLAY_ENABLED' not in p:
    key_anchor='    private const val KEY_STATUS = "status"\n'
    if key_anchor not in p:
        raise SystemExit("v54 prefs key anchor missing")
    p=p.replace(
        key_anchor,
        key_anchor+'    private const val KEY_FLOATING_OVERLAY_ENABLED = "floating_overlay_enabled"\n',
        1
    )

    end=p.rfind('\n}')
    if end<0:
        raise SystemExit("v54 prefs end missing")
    helper='''

    fun floatingOverlayEnabled(context: Context): Boolean =
        prefs(context).getBoolean(KEY_FLOATING_OVERLAY_ENABLED, true)

    fun setFloatingOverlayEnabled(context: Context, value: Boolean) {
        prefs(context).edit().putBoolean(KEY_FLOATING_OVERLAY_ENABLED, value).apply()
    }
'''
    p=p[:end]+helper+p[end:]

# APP UI: switch to show/hide floating button.
if 'switchFloatingOverlay' not in x:
    anchor='''        <androidx.appcompat.widget.SwitchCompat
            android:id="@+id/switchEnabled"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="16dp"
            android:text="Automação ativa" />
'''
    insert=anchor+'''
        <androidx.appcompat.widget.SwitchCompat
            android:id="@+id/switchFloatingOverlay"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="10dp"
            android:text="Mostrar botão flutuante" />
'''
    if anchor not in x:
        raise SystemExit("v54 layout switchEnabled anchor missing")
    x=x.replace(anchor,insert,1)

if 'switchFloatingOverlay' not in a:
    anchor='''        val enabled = findViewById<SwitchCompat>(R.id.switchEnabled)
'''
    if anchor not in a:
        raise SystemExit("v54 MainActivity enabled anchor missing")
    a=a.replace(
        anchor,
        anchor+'        val floatingOverlay = findViewById<SwitchCompat>(R.id.switchFloatingOverlay)\n',
        1
    )

    anchor='''        enabled.isChecked = Prefs.isEnabled(this)
'''
    if anchor not in a:
        raise SystemExit("v54 MainActivity checked anchor missing")
    a=a.replace(
        anchor,
        anchor+'        floatingOverlay.isChecked = Prefs.floatingOverlayEnabled(this)\n',
        1
    )

    listener_anchor='''        enabled.setOnCheckedChangeListener { _, checked ->
            Prefs.setEnabled(this, checked)
            Prefs.setStatus(
                this,
                when {
                    checked ->
                        "Automação ligada. Abra qualquer grupo no WhatsApp."
                    else ->
                        "Automação desligada."
                }
            )
        }
'''
    listener_new=listener_anchor+'''

        floatingOverlay.setOnCheckedChangeListener { _, checked ->
            Prefs.setFloatingOverlayEnabled(this, checked)
            Prefs.setStatus(
                this,
                if (checked)
                    "Botão flutuante ativado."
                else
                    "Botão flutuante ocultado."
            )
        }
'''
    if listener_anchor not in a:
        raise SystemExit("v54 MainActivity listener anchor missing")
    a=a.replace(listener_anchor,listener_new,1)

# SERVICE listener: react to enabled, search_armed, and overlay visibility.
old='''    private val floatingPrefsListenerV52 =
        android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
            if (key == "enabled") {
                handler.post { updateFloatingToggleAppearanceV52() }
            }
        }
'''
new='''    private val floatingPrefsListenerV52 =
        android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
            when(key){
                "enabled", "search_armed" ->
                    handler.post { updateFloatingToggleAppearanceV52() }
                "floating_overlay_enabled" ->
                    handler.post {
                        if(Prefs.floatingOverlayEnabled(this))
                            showFloatingToggleV52()
                        else
                            removeFloatingToggleV52()
                    }
            }
        }
'''
if old not in s:
    raise SystemExit("v54 prefs listener anchor missing")
s=s.replace(old,new,1)

# Appearance reflects ACTIVE SEARCH, not merely service enabled.
old='''    private fun updateFloatingToggleAppearanceV52(){
        val button=floatingToggleV52 ?: return
        val enabled=Prefs.isEnabled(this)
        button.text=if(enabled) "ON" else "OFF"
        button.contentDescription=
            if(enabled) "Rota Rapida ligada. Toque para desligar."
            else "Rota Rapida desligada. Toque para ligar."
        button.background=floatingBackgroundV52(enabled)
    }
'''
new='''    private fun updateFloatingToggleAppearanceV52(){
        val button=floatingToggleV52 ?: return
        val activeSearch=Prefs.isEnabled(this) && Prefs.searchArmed(this)
        button.text=if(activeSearch) "ON" else "OFF"
        button.contentDescription=
            if(activeSearch)
                "Rota Rapida procurando rota. Toque para parar."
            else
                "Rota Rapida parada. Toque para procurar novamente."
        button.background=floatingBackgroundV52(activeSearch)
    }
'''
if old not in s:
    raise SystemExit("v54 appearance block missing")
s=s.replace(old,new,1)

# Button semantics: green(active) -> stop; gray -> rearm and search.
start=s.find('    private fun toggleBotFromFloatingV52(){')
end=s.find('    private fun showFloatingToggleV52(){',start)
if start<0 or end<0:
    raise SystemExit("v54 toggle block bounds missing")
toggle=r'''    private fun toggleBotFromFloatingV52(){
        val activeSearch=Prefs.isEnabled(this) && Prefs.searchArmed(this)

        if(activeSearch){
            Prefs.setSearchArmed(this,false)
            Prefs.setEnabled(this,false)
            processing=false
            pendingRoute=null
            analyzeScheduled=false
            Prefs.setStatus(this,"Automacao parada pelo botao flutuante.")
        }else{
            Prefs.setEnabled(this,true)
            Prefs.setSearchArmed(this,true)
            Prefs.setNeedsPrime(this,false)

            primed=false
            Prefs.setStatus(
                this,
                if(Prefs.groupName(this).isBlank())
                    "Automacao ligada pelo botao flutuante, mas falta configurar o grupo."
                else
                    "Procurar novamente ativado pelo botao flutuante."
            )
            handler.postDelayed({
                if(Prefs.isEnabled(this) && Prefs.searchArmed(this)) primeCurrentScreen()
            },80L)
        }

        updateFloatingToggleAppearanceV52()
    }

'''
s=s[:start]+toggle+s[end:]

# Service connection obeys visibility preference.
old='''        try{floatingPrefsV52.registerOnSharedPreferenceChangeListener(floatingPrefsListenerV52)}catch(_:Throwable){}
        showFloatingToggleV52()
'''
new='''        try{floatingPrefsV52.registerOnSharedPreferenceChangeListener(floatingPrefsListenerV52)}catch(_:Throwable){}
        if(Prefs.floatingOverlayEnabled(this)) showFloatingToggleV52()
'''
if old not in s:
    raise SystemExit("v54 service connect overlay anchor missing")
s=s.replace(old,new,1)

checks=[
    'Prefs.searchArmed(this)',
    '"enabled", "search_armed"',
    '"floating_overlay_enabled"',
    'Prefs.floatingOverlayEnabled(this)',
    'Rota Rapida parada. Toque para procurar novamente.',
    'switchFloatingOverlay',
]
for m in checks:
    blob=s+p+a+x
    if m not in blob:
        raise SystemExit("v54 verify failed: "+m)

S.write_text(s,encoding="utf-8")
P.write_text(p,encoding="utf-8")
A.write_text(a,encoding="utf-8")
L.write_text(x,encoding="utf-8")
print("v54 aplicado: cor segue searchArmed; cinza rearma; switch no app mostra/oculta overlay")
