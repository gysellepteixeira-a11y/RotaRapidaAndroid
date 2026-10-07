from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

required=[
    '===== DIAGNOSTICO IMAGEM v19 | V48 EDITOR FAST PATH + V47 CLEAN FAST =====',
    'private var pendingRoute',
    'override fun onServiceConnected() {',
    'override fun onDestroy() {',
    'Prefs.isEnabled(this)',
]
for m in required:
    if m not in s:
        raise SystemExit("v52 wrong base: "+m)

connect_anchor='''    override fun onServiceConnected() {
        super.onServiceConnected()
'''
if connect_anchor not in s:
    raise SystemExit("v52 onServiceConnected anchor missing")

overlay=r'''    // v52: botao flutuante via TYPE_ACCESSIBILITY_OVERLAY.
    // Nao exige permissao de "aparecer sobre outros apps": usa o proprio
    // AccessibilityService. Nao cria polling novo; so reage a toque/arraste
    // e a mudancas do SharedPreferences "enabled".
    private var floatingToggleV52: android.widget.TextView? = null
    private var floatingParamsV52: android.view.WindowManager.LayoutParams? = null
    private var floatingWindowManagerV52: android.view.WindowManager? = null

    private val floatingPrefsV52 by lazy {
        getSharedPreferences("rota_rapida", android.content.Context.MODE_PRIVATE)
    }

    private val floatingPrefsListenerV52 =
        android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
            if (key == "enabled") {
                handler.post { updateFloatingToggleAppearanceV52() }
            }
        }

    private fun dpV52(value:Int):Int =
        (value * resources.displayMetrics.density + 0.5f).toInt()

    private fun floatingBackgroundV52(enabled:Boolean):android.graphics.drawable.GradientDrawable {
        return android.graphics.drawable.GradientDrawable().apply {
            shape=android.graphics.drawable.GradientDrawable.OVAL
            setColor(
                if(enabled)
                    android.graphics.Color.argb(225,46,125,50)
                else
                    android.graphics.Color.argb(210,75,75,75)
            )
            setStroke(dpV52(2),android.graphics.Color.argb(230,255,255,255))
        }
    }

    private fun updateFloatingToggleAppearanceV52(){
        val button=floatingToggleV52 ?: return
        val enabled=Prefs.isEnabled(this)
        button.text=if(enabled) "ON" else "OFF"
        button.contentDescription=
            if(enabled) "Rota Rapida ligada. Toque para desligar."
            else "Rota Rapida desligada. Toque para ligar."
        button.background=floatingBackgroundV52(enabled)
    }

    private fun toggleBotFromFloatingV52(){
        val next=!Prefs.isEnabled(this)
        Prefs.setEnabled(this,next)

        if(next){
            primed=false
            Prefs.setStatus(
                this,
                if(Prefs.groupName(this).isBlank())
                    "Automacao ligada pelo botao flutuante, mas falta configurar o grupo."
                else
                    "Automacao ligada pelo botao flutuante."
            )
            handler.postDelayed({
                if(Prefs.isEnabled(this)) primeCurrentScreen()
            },80L)
        }else{
            // Para imediatamente novos trabalhos e invalida rota pendente.
            // Callbacks ja postados continuam seguros porque os caminhos criticos
            // checam processing/enabled antes de prosseguir.
            processing=false
            pendingRoute=null
            analyzeScheduled=false
            Prefs.setStatus(this,"Automacao desligada pelo botao flutuante.")
        }

        updateFloatingToggleAppearanceV52()
    }

    private fun showFloatingToggleV52(){
        if(floatingToggleV52!=null)return

        val wm=getSystemService(android.content.Context.WINDOW_SERVICE)
            as? android.view.WindowManager ?: return
        floatingWindowManagerV52=wm

        val size=dpV52(48)
        val metrics=resources.displayMetrics
        val defaultX=(metrics.widthPixels-size-dpV52(10)).coerceAtLeast(0)
        val defaultY=(metrics.heightPixels/3).coerceAtLeast(0)

        val params=android.view.WindowManager.LayoutParams(
            size,
            size,
            android.view.WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            android.view.WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                android.view.WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            android.graphics.PixelFormat.TRANSLUCENT
        ).apply{
            gravity=android.view.Gravity.TOP or android.view.Gravity.START
            x=floatingPrefsV52.getInt("floating_x_v52",defaultX)
            y=floatingPrefsV52.getInt("floating_y_v52",defaultY)
        }
        floatingParamsV52=params

        val button=android.widget.TextView(this).apply{
            gravity=android.view.Gravity.CENTER
            setTextColor(android.graphics.Color.WHITE)
            setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP,10f)
            typeface=android.graphics.Typeface.DEFAULT_BOLD
            elevation=dpV52(6).toFloat()
            includeFontPadding=false
            setPadding(0,0,0,0)
        }
        floatingToggleV52=button
        updateFloatingToggleAppearanceV52()

        var downRawX=0f
        var downRawY=0f
        var startX=0
        var startY=0
        var dragged=false
        val dragThreshold=dpV52(6)

        button.setOnTouchListener { _, event ->
            when(event.actionMasked){
                android.view.MotionEvent.ACTION_DOWN -> {
                    downRawX=event.rawX
                    downRawY=event.rawY
                    startX=params.x
                    startY=params.y
                    dragged=false
                    true
                }
                android.view.MotionEvent.ACTION_MOVE -> {
                    val dx=(event.rawX-downRawX).toInt()
                    val dy=(event.rawY-downRawY).toInt()
                    if(!dragged && (kotlin.math.abs(dx)>dragThreshold || kotlin.math.abs(dy)>dragThreshold)){
                        dragged=true
                    }
                    if(dragged){
                        val maxX=(resources.displayMetrics.widthPixels-size).coerceAtLeast(0)
                        val maxY=(resources.displayMetrics.heightPixels-size).coerceAtLeast(0)
                        params.x=(startX+dx).coerceIn(0,maxX)
                        params.y=(startY+dy).coerceIn(0,maxY)
                        try{wm.updateViewLayout(button,params)}catch(_:Throwable){}
                    }
                    true
                }
                android.view.MotionEvent.ACTION_UP -> {
                    if(dragged){
                        floatingPrefsV52.edit()
                            .putInt("floating_x_v52",params.x)
                            .putInt("floating_y_v52",params.y)
                            .apply()
                    }else{
                        toggleBotFromFloatingV52()
                    }
                    true
                }
                android.view.MotionEvent.ACTION_CANCEL -> true
                else -> false
            }
        }

        try{
            wm.addView(button,params)
        }catch(_:Throwable){
            floatingToggleV52=null
            floatingParamsV52=null
            floatingWindowManagerV52=null
        }
    }

    private fun removeFloatingToggleV52(){
        val button=floatingToggleV52
        val wm=floatingWindowManagerV52
        if(button!=null && wm!=null){
            try{wm.removeView(button)}catch(_:Throwable){}
        }
        floatingToggleV52=null
        floatingParamsV52=null
        floatingWindowManagerV52=null
    }

'''
s=s.replace(connect_anchor,overlay+connect_anchor,1)

connect_new='''    override fun onServiceConnected() {
        super.onServiceConnected()
        try{floatingPrefsV52.registerOnSharedPreferenceChangeListener(floatingPrefsListenerV52)}catch(_:Throwable){}
        showFloatingToggleV52()
'''
s=s.replace(connect_anchor,connect_new,1)

destroy_anchor='''    override fun onDestroy() {
'''
destroy_new='''    override fun onDestroy() {
        try{floatingPrefsV52.unregisterOnSharedPreferenceChangeListener(floatingPrefsListenerV52)}catch(_:Throwable){}
        removeFloatingToggleV52()
'''
if destroy_anchor not in s:
    raise SystemExit("v52 onDestroy anchor missing")
s=s.replace(destroy_anchor,destroy_new,1)

checks=[
    'TYPE_ACCESSIBILITY_OVERLAY',
    'private fun toggleBotFromFloatingV52()',
    'button.text=if(enabled) "ON" else "OFF"',
    'putInt("floating_x_v52",params.x)',
    'Prefs.setEnabled(this,next)',
    'pendingRoute=null',
    'showFloatingToggleV52()',
    'removeFloatingToggleV52()',
]
for m in checks:
    if m not in s:
        raise SystemExit("v52 verify failed: "+m)

S.write_text(s,encoding="utf-8")
print("v52 FLOATING TOGGLE aplicado: ON/OFF por Accessibility Overlay, arrastavel, posicao salva, sem polling extra")
