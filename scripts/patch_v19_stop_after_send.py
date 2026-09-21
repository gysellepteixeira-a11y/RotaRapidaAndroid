from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
activity_path = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")
layout_path = Path("app/src/main/res/layout/activity_main.xml")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")
a = activity_path.read_text(encoding="utf-8")
xml = layout_path.read_text(encoding="utf-8")

# v0.19 STOP
# - Depois que uma rota e REALMENTE enviada, o APK fica desarmado e nao procura
#   nenhuma outra rota, mesmo depois dos 20 avisos.
# - So volta a procurar quando a pessoa toca em PROCURAR NOVAMENTE no app.
# - Mantem a rota pendente da v0.19-final: se a rota ja foi encontrada mas o grupo
#   configurado nao esta aberto na hora do envio, ela fica guardada e e enviada
#   automaticamente quando o grupo correto abrir.

# -----------------------------------------------------------------------------
# PREFS: estado armado/desarmado + pedido de prime ao rearmar.
# -----------------------------------------------------------------------------
if 'KEY_SEARCH_ARMED' not in prefs:
    prefs = prefs.replace(
        '    private const val KEY_LAST_MESSAGE = "last_message"\n',
        '    private const val KEY_LAST_MESSAGE = "last_message"\n'
        '    private const val KEY_SEARCH_ARMED = "search_armed"\n'
        '    private const val KEY_NEEDS_PRIME = "needs_prime"\n',
        1
    )

    insert_anchor = '''    fun setLastMessage(context: Context, value: String) {
        prefs(context).edit().putString(KEY_LAST_MESSAGE, value).apply()
    }
'''
    extra = '''    fun setLastMessage(context: Context, value: String) {
        prefs(context).edit().putString(KEY_LAST_MESSAGE, value).apply()
    }

    fun searchArmed(context: Context): Boolean =
        prefs(context).getBoolean(KEY_SEARCH_ARMED, true)

    fun setSearchArmed(context: Context, value: Boolean) {
        prefs(context).edit().putBoolean(KEY_SEARCH_ARMED, value).apply()
    }

    fun needsPrime(context: Context): Boolean =
        prefs(context).getBoolean(KEY_NEEDS_PRIME, false)

    fun setNeedsPrime(context: Context, value: Boolean) {
        prefs(context).edit().putBoolean(KEY_NEEDS_PRIME, value).apply()
    }
'''
    if insert_anchor not in prefs:
        raise SystemExit('patch_v19_stop: setLastMessage nao encontrado em Prefs')
    prefs = prefs.replace(insert_anchor, extra, 1)

prefs_path.write_text(prefs, encoding="utf-8")

# -----------------------------------------------------------------------------
# UI: botao explicito PROCURAR NOVAMENTE.
# -----------------------------------------------------------------------------
if 'buttonSearchAgain' not in xml:
    anchor = '''        <Button
            android:id="@+id/buttonAccessibility"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="12dp"
            android:text="Abrir Acessibilidade do Android" />
'''
    button = anchor + '''
        <Button
            android:id="@+id/buttonSearchAgain"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="12dp"
            android:text="PROCURAR NOVAMENTE" />
'''
    if anchor not in xml:
        raise SystemExit('patch_v19_stop: botao Acessibilidade nao encontrado no layout')
    xml = xml.replace(anchor, button, 1)
layout_path.write_text(xml, encoding="utf-8")

if 'buttonSearchAgain' not in a:
    anchor = '        val accessibility = findViewById<Button>(R.id.buttonAccessibility)\n'
    if anchor not in a:
        raise SystemExit('patch_v19_stop: accessibility button nao encontrado em MainActivity')
    a = a.replace(
        anchor,
        anchor + '        val searchAgain = findViewById<Button>(R.id.buttonSearchAgain)\n',
        1
    )

    listener_anchor = '''        accessibility.setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
'''
    listener = listener_anchor + '''

        searchAgain.setOnClickListener {
            Prefs.setSearchArmed(this, true)
            Prefs.setNeedsPrime(this, true)
            Prefs.setStatus(
                this,
                "Procurar novamente ativado. Abra o grupo configurado; a partir da tela atual, vou aguardar uma NOVA rota."
            )
        }
'''
    if listener_anchor not in a:
        raise SystemExit('patch_v19_stop: listener accessibility nao encontrado')
    a = a.replace(listener_anchor, listener, 1)

activity_path.write_text(a, encoding="utf-8")

# -----------------------------------------------------------------------------
# SERVICO: quando desarmado, nao analisa novas rotas. Rota pendente continua com
# prioridade e pode ser enviada quando o grupo abrir.
# -----------------------------------------------------------------------------
event_old = '''        if (alertSequenceRunning) return

        if (!processing && pendingRoute != null) {
            if (trySendPendingRouteIfChatOpen()) return
        }

        inspectImageHint(event)

        if (processing) return
        scheduleAnalyze(12L)
'''
event_new = '''        if (alertSequenceRunning) return

        // Uma rota que JA foi encontrada continua pendente ate conseguir enviar.
        // Isso funciona mesmo se o grupo configurado tiver sido fechado.
        if (!processing && pendingRoute != null) {
            if (trySendPendingRouteIfChatOpen()) return
        }

        // Depois de um envio confirmado, o bot fica PARADO indefinidamente.
        // So o botao PROCURAR NOVAMENTE rearma a busca.
        if (!Prefs.searchArmed(this)) return

        inspectImageHint(event)

        if (processing) return
        scheduleAnalyze(12L)
'''
if event_old not in s:
    raise SystemExit('patch_v19_stop: bloco onAccessibilityEvent da v0.19-final nao encontrado')
s = s.replace(event_old, event_new, 1)

# Quando a busca for rearmada, a primeira tela do grupo vira apenas referencia.
# Assim uma rota velha ainda visivel nao e reenviada como se fosse nova.
analyze_anchor = '''        if (!isTargetGroup(items, group)) {
            previousTexts = textSignatures(items)
            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
            primed = true
            return
        }

        val currentSignatures = textSignatures(items)
'''
analyze_new = '''        if (!isTargetGroup(items, group)) {
            previousTexts = textSignatures(items)
            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
            primed = true
            return
        }

        if (!Prefs.searchArmed(this)) return

        if (Prefs.needsPrime(this)) {
            previousTexts = textSignatures(items)
            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
            primed = true
            Prefs.setNeedsPrime(this, false)
            Prefs.setStatus(this, "Pronto. Aguardando uma NOVA rota.")
            return
        }

        val currentSignatures = textSignatures(items)
'''
if analyze_anchor not in s:
    raise SystemExit('patch_v19_stop: ancora analyzeCurrentWindow nao encontrada')
s = s.replace(analyze_anchor, analyze_new, 1)

# Assim que o envio e confirmado, desarma imediatamente. Os 20 avisos continuam,
# mas nenhuma nova rota pode ser lida durante ou depois deles.
mark_anchor = '''    private fun markSent(route: RouteResult) {
        pendingRoute = null
        lastSentSignature = "${route.priorityIndex}:${route.cage}"
'''
mark_new = '''    private fun markSent(route: RouteResult) {
        pendingRoute = null
        Prefs.setSearchArmed(this, false)
        Prefs.setNeedsPrime(this, false)
        lastSentSignature = "${route.priorityIndex}:${route.cage}"
'''
if mark_anchor not in s:
    raise SystemExit('patch_v19_stop: markSent nao encontrado')
s = s.replace(mark_anchor, mark_new, 1)

# Ao terminar os 20 avisos, nao rearma nem faz prime. Apenas informa que parou.
old_finish = '''            if (index >= ROUTE_ALERT_COUNT) {
                alertSequenceRunning = false
                Prefs.setStatus(
                    this,
                    "ENVIADO: ${route.neighborhood} -> ${route.cage} | 20 avisos concluidos."
                )
                handler.postDelayed({ primeCurrentScreen() }, 120L)
                return
            }
'''
new_finish = '''            if (index >= ROUTE_ALERT_COUNT) {
                alertSequenceRunning = false
                processing = false
                Prefs.setStatus(
                    this,
                    "ENVIADO: ${route.neighborhood} -> ${route.cage} | 20 avisos concluidos. BOT PARADO. Toque em PROCURAR NOVAMENTE para buscar outra rota."
                )
                return
            }
'''
if old_finish not in s:
    raise SystemExit('patch_v19_stop: final dos 20 avisos nao encontrado')
s = s.replace(old_finish, new_finish, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 STOP aplicado: para apos envio e so rearma pelo botao; rota pendente espera grupo abrir")
