from pathlib import Path
S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
P=Path('app/src/main/java/com/gy/rotarapida/Prefs.kt')
s=S.read_text(); p=P.read_text()

def r(old,new,n=1):
    global s
    c=s.count(old)
    if c < n: raise SystemExit(f'missing anchor {old[:60]!r} count={c}')
    s=s.replace(old,new,n)

# Must be the old MEDIA10 + ADMIN DIRECT base, never the newer experiments.
for x in ['private const val DIRECT_MEDIASTORE_WATCH_MS = 10L','private const val PENDING_ROUTE_SEND_WATCH_MS = 10L','private fun findAdminUltraSendNodeFast(']:
    if x not in s: raise SystemExit('wrong base: '+x)
if 'MEDIA10 STATUSLEAN ADMIN ULTRA DIRECT FAST' not in p: raise SystemExit('wrong Prefs base')
if 'TEXT DIRECT:' in s or 'CLEAN STATE' in s or 'CLEAR DIAG' in s: raise SystemExit('not old base')

# RAM timestamps only. No diagnostic persistence before confirmation.
r('    private var speedDiagnosticSendMethod = "nenhum"\n','''    private var speedDiagnosticSendMethod = "nenhum"
    private var tdCandidate=0L; private var tdOn=false; private var tdEvent=0L
    private var tdAnalyze=0L; private var tdCollectDone=0L; private var tdCollect=0L; private var tdParse=0L; private var tdRoute=0L
    private var tdStatusTexto=0L; private var tdStatusTextoDone=0L
    private var tdSend=0L; private var tdSendCollect=0L; private var tdEditor=0L; private var tdSet=0L; private var tdFilled=0L
    private var tdStatusEnvio=0L; private var tdStatusEnvioDone=0L
    private var tdReady=0L; private var tdReadyCollect=0L; private var tdReadyFound=0L; private var tdReadyPoll=0
    private var tdStatusReady=0L; private var tdStatusReadyDone=0L
    private var tdClick=0L; private var tdClickCollect=0L; private var tdCandidateSend=0L; private var tdAction=0L; private var tdClicked=0L
    private var tdConfirmCollect=0L; private var tdConfirmPoll=0; private var tdConfirmed=0L; private var tdNewItems=0
    private var tdHeld=0L; private var tdReleased=0L
''')

# First WhatsApp event that schedules this analyze batch.
r('''        if (processing) return
        scheduleAnalyze(12L)
''','''        if (processing) return
        if (!analyzeScheduled) tdCandidate = SystemClock.elapsedRealtime()
        scheduleAnalyze(12L)
''')

# Initial tree collection.
r('''    private fun analyzeCurrentWindow() {
        if (processing || !Prefs.isEnabled(this)) return

        val root = rootInActiveWindow ?: return
        val items = collectNodeItems(root)
''','''    private fun analyzeCurrentWindow() {
        if (processing || !Prefs.isEnabled(this)) return

        val tdAnalyzeLocal = SystemClock.elapsedRealtime()
        val root = rootInActiveWindow ?: return
        val tdCollectStart = SystemClock.elapsedRealtime()
        val items = collectNodeItems(root)
        val tdCollectDoneLocal = SystemClock.elapsedRealtime()
        val tdCollectLocal = tdCollectDoneLocal - tdCollectStart
''')

# Parser and route-detected point. Keep original parser unchanged.
r('''        val textRoute =
            RouteParser.parseScreenTexts(
                newItems.map {
                    ScreenText(
                        text = it.text,
                        left = it.rect.left,
                        top = it.rect.top,
                        right = it.rect.right,
                        bottom = it.rect.bottom
                    )
                },
                screenHeight
            )
                ?: RouteParser.parsePlainTexts(newItems.map { it.text })

        if (textRoute != null && !isDuplicate(textRoute)) {
            previousImageFingerprints = currentImageFingerprints
            currentStartedAt = SystemClock.elapsedRealtime()
            processing = true
            Prefs.setStatus(
                this,
                "Texto: ${textRoute.neighborhood} -> ${textRoute.cage}. Enviando..."
            )
            sendRouteInCurrentChat(textRoute)
            return
        }
''','''        val tdParseStart = SystemClock.elapsedRealtime()
        val textRoute =
            RouteParser.parseScreenTexts(
                newItems.map {
                    ScreenText(
                        text = it.text,
                        left = it.rect.left,
                        top = it.rect.top,
                        right = it.rect.right,
                        bottom = it.rect.bottom
                    )
                },
                screenHeight
            )
                ?: RouteParser.parsePlainTexts(newItems.map { it.text })
        val tdParseDone = SystemClock.elapsedRealtime()

        if (textRoute != null && !isDuplicate(textRoute)) {
            previousImageFingerprints = currentImageFingerprints
            currentStartedAt = SystemClock.elapsedRealtime()
            tdBegin(if(tdCandidate>0L) tdCandidate else tdAnalyzeLocal, tdAnalyzeLocal, tdCollectDoneLocal, tdCollectLocal, tdParseDone-tdParseStart, currentStartedAt, newItems.size)
            processing = true
            val tdSt = SystemClock.elapsedRealtime()
            Prefs.setStatus(
                this,
                "Texto: ${textRoute.neighborhood} -> ${textRoute.cage}. Enviando..."
            )
            if(tdOn){ tdStatusTexto += SystemClock.elapsedRealtime()-tdSt; tdStatusTextoDone=SystemClock.elapsedRealtime() }
            sendRouteInCurrentChat(textRoute)
            return
        }
''')

# If group is locked, flag the wait; diagnostic continues when admin releases.
r('''    private fun holdRouteUntilChatOpen(route: RouteResult, reason: String) {
        pendingRoute = route
''','''    private fun holdRouteUntilChatOpen(route: RouteResult, reason: String) {
        if(tdOn && tdHeld==0L) tdHeld=SystemClock.elapsedRealtime()
        pendingRoute = route
''')
r('''        val releasedAt = SystemClock.elapsedRealtime()
        processing = true
''','''        val releasedAt = SystemClock.elapsedRealtime()
        if(tdOn){ tdReleased=releasedAt; if(tdEditor==0L) tdEditor=releasedAt }
        processing = true
''')

# ADMIN DIRECT pending path: same timestamps, still no behavior change.
old_admin="""        val setOk = editor.node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        )

        if (!setOk) {
"""
if old_admin not in s: raise SystemExit('admin setText anchor missing')
new_admin="""        val tdAs = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val setOk = editor.node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        )
        if(tdOn && tdAs>0L){ tdSet += SystemClock.elapsedRealtime()-tdAs; if(setOk) tdFilled=SystemClock.elapsedRealtime() }

        if (!setOk) {
"""
s=s.replace(old_admin,new_admin,1)
r("""        Prefs.setStatus(
            this,
            \"ADMIN ULTRA DIRECT: liberado + preenchido em ${fillMs}ms | watch=10ms | ready=4ms\"
        )

        waitForAdminUltraSendReady(
""","""        val tdAe = if(tdOn) SystemClock.elapsedRealtime() else 0L
        Prefs.setStatus(
            this,
            \"ADMIN ULTRA DIRECT: liberado + preenchido em ${fillMs}ms | watch=10ms | ready=4ms\"
        )
        if(tdOn && tdAe>0L){ tdStatusEnvio += SystemClock.elapsedRealtime()-tdAe; tdStatusEnvioDone=SystemClock.elapsedRealtime() }

        waitForAdminUltraSendReady(
""")
r("""        if (sendNode != null) {
            val waited = SystemClock.elapsedRealtime() - startedAt
            speedDiagnosticSendAttempts = 1
            speedDiagnosticSendMethod = \"ACTION_CLICK\"

            if (clickNodeOrParent(sendNode)) {
""","""        if (sendNode != null) {
            val waited = SystemClock.elapsedRealtime() - startedAt
            speedDiagnosticSendAttempts = 1
            speedDiagnosticSendMethod = \"ACTION_CLICK\"
            if(tdOn){ if(tdReady==0L) tdReady=startedAt; tdReadyFound=SystemClock.elapsedRealtime(); tdReadyPoll=poll }

            if (clickNodeOrParent(sendNode)) {
""")

# Standard send entry/tree/editor.
r('''    private fun sendRouteInCurrentChat(route: RouteResult) {
        if (isDuplicate(route)) {
''','''    private fun sendRouteInCurrentChat(route: RouteResult) {
        if(tdOn && tdSend==0L) tdSend=SystemClock.elapsedRealtime()
        if (isDuplicate(route)) {
''')
r('''        val items = collectNodeItems(root)

        val editor = findMessageEditor(items)
        if (editor == null) {
''','''        val tdSc = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val items = collectNodeItems(root)
        if(tdOn && tdSc>0L) tdSendCollect += SystemClock.elapsedRealtime()-tdSc

        val editor = findMessageEditor(items)
        if(tdOn && editor!=null && tdEditor==0L) tdEditor=SystemClock.elapsedRealtime()
        if (editor == null) {
''')

# Standard ACTION_SET_TEXT: by now this is the second identical occurrence; replace only the last one.
old='''        val setOk = editor.node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        )

        if (!setOk) {
'''
pos=s.rfind(old)
if pos<0: raise SystemExit('setText anchor missing')
new='''        val tdSs = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val setOk = editor.node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        )
        if(tdOn && tdSs>0L){ tdSet += SystemClock.elapsedRealtime()-tdSs; if(setOk) tdFilled=SystemClock.elapsedRealtime() }

        if (!setOk) {
'''
s=s[:pos]+new+s[pos+len(old):]

# Existing ENVIO status cost.
r('''        Prefs.setStatus(
            this,
            "ENVIO: campo preenchido em ${formatElapsedMs(fillMs)} | " +
                "aguardando clique/confirmacao do WhatsApp..."
        )

        handler.postDelayed(
''','''        val tdSe = if(tdOn) SystemClock.elapsedRealtime() else 0L
        Prefs.setStatus(
            this,
            "ENVIO: campo preenchido em ${formatElapsedMs(fillMs)} | " +
                "aguardando clique/confirmacao do WhatsApp..."
        )
        if(tdOn && tdSe>0L){ tdStatusEnvio += SystemClock.elapsedRealtime()-tdSe; tdStatusEnvioDone=SystemClock.elapsedRealtime() }

        handler.postDelayed(
''')

# SEND READY wait and tree collection.
r('''        val pollDelayMs = 12L
        val maxPolls = 25
''','''        if(tdOn && tdReady==0L) tdReady=SystemClock.elapsedRealtime()
        val pollDelayMs = 12L
        val maxPolls = 25
''')
r('''        val items = collectNodeItems(root)

        // Se a mensagem sumiu antes de qualquer clique nosso, nao tenta clicar.
''','''        val tdRc = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val items = collectNodeItems(root)
        if(tdOn && tdRc>0L){ tdReadyCollect += SystemClock.elapsedRealtime()-tdRc; tdReadyPoll=poll }

        // Se a mensagem sumiu antes de qualquer clique nosso, nao tenta clicar.
''')
r('''        if (namedSendButtonReady(items, editor.rect)) {
            val waited = SystemClock.elapsedRealtime() - startedAt
            Prefs.setStatus(
                this,
                "ENVIO READY: botao Enviar apareceu em ${waited}ms | polls=$poll | clicando 1x..."
            )
            tryClickSend(route, 0)
''','''        if (namedSendButtonReady(items, editor.rect)) {
            val waited = SystemClock.elapsedRealtime() - startedAt
            if(tdOn){ tdReadyFound=SystemClock.elapsedRealtime(); tdReadyPoll=poll }
            val tdSr = if(tdOn) SystemClock.elapsedRealtime() else 0L
            Prefs.setStatus(
                this,
                "ENVIO READY: botao Enviar apareceu em ${waited}ms | polls=$poll | clicando 1x..."
            )
            if(tdOn && tdSr>0L){ tdStatusReady += SystemClock.elapsedRealtime()-tdSr; tdStatusReadyDone=SystemClock.elapsedRealtime() }
            tryClickSend(route, 0)
''')

# tryClick tree and candidate.
r('''    private fun tryClickSend(route: RouteResult, attempt: Int) {
        if (!processing) return
''','''    private fun tryClickSend(route: RouteResult, attempt: Int) {
        if (!processing) return
        if(tdOn && tdClick==0L) tdClick=SystemClock.elapsedRealtime()
''')
r('''        val items = collectNodeItems(root)

        if (findMessageEditor(items) == null) {
            holdRouteUntilChatOpen(route, "A conversa foi fechada antes de concluir o envio.")
''','''        val tdCc = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val items = collectNodeItems(root)
        if(tdOn && tdCc>0L) tdClickCollect += SystemClock.elapsedRealtime()-tdCc

        if (findMessageEditor(items) == null) {
            holdRouteUntilChatOpen(route, "A conversa foi fechada antes de concluir o envio.")
''')
r('''        val candidate = findStrictSendCandidate(items, editor.rect)

        // Primeiro tenta ACTION_CLICK no proprio botao/pai.
''','''        val candidate = findStrictSendCandidate(items, editor.rect)
        if(tdOn && candidate!=null) tdCandidateSend=SystemClock.elapsedRealtime()

        // Primeiro tenta ACTION_CLICK no proprio botao/pai.
''')

# ACTION_CLICK helper timing; semantics unchanged.
r('''    private fun clickNodeOrParent(start: AccessibilityNodeInfo): Boolean {
        var current: AccessibilityNodeInfo? = start
        var depth = 0

        while (current != null && depth < 6) {
            if (current.isClickable &&
                current.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            ) {
                return true
            }

            current = current.parent
            depth++
        }

        return start.performAction(AccessibilityNodeInfo.ACTION_CLICK)
    }
''','''    private fun clickNodeOrParent(start: AccessibilityNodeInfo): Boolean {
        val t=if(tdOn) SystemClock.elapsedRealtime() else 0L
        var current: AccessibilityNodeInfo? = start
        var depth = 0
        while (current != null && depth < 6) {
            if (current.isClickable && current.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                if(tdOn && t>0L){ tdAction += SystemClock.elapsedRealtime()-t; if(tdClicked==0L) tdClicked=SystemClock.elapsedRealtime() }
                return true
            }
            current = current.parent; depth++
        }
        val ok=start.performAction(AccessibilityNodeInfo.ACTION_CLICK)
        if(tdOn && t>0L){ tdAction += SystemClock.elapsedRealtime()-t; if(ok && tdClicked==0L) tdClicked=SystemClock.elapsedRealtime() }
        return ok
    }
''')

# Confirmation tree timing.
r('''        val items = collectNodeItems(root)
        val editor = findMessageEditor(items)

        // Se o editor existe e a mensagem sumiu, o primeiro ACTION_CLICK enviou.
''','''        val tdFc = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val items = collectNodeItems(root)
        if(tdOn && tdFc>0L){ tdConfirmCollect += SystemClock.elapsedRealtime()-tdFc; tdConfirmPoll=poll }
        val editor = findMessageEditor(items)

        // Se o editor existe e a mensagem sumiu, o primeiro ACTION_CLICK enviou.
''')

# Build report only after existing CONFIRMADO status.
r('''        Prefs.setStatus(
            this,
            "CONFIRMADO: ${route.neighborhood} -> ${route.cage} | " +
                "envio=${formatElapsedMs(sendStageMs)} | tentativas=${speedDiagnosticSendAttempts} | " +
                "metodo=${speedDiagnosticSendMethod} | app=${formatElapsedMs(elapsed)}"
        )
        speedDiagnosticSendStartedAt = 0L
''','''        Prefs.setStatus(
            this,
            "CONFIRMADO: ${route.neighborhood} -> ${route.cage} | " +
                "envio=${formatElapsedMs(sendStageMs)} | tentativas=${speedDiagnosticSendAttempts} | " +
                "metodo=${speedDiagnosticSendMethod} | app=${formatElapsedMs(elapsed)}"
        )
        if(tdOn){ tdConfirmed=SystemClock.elapsedRealtime(); tdReport(route) }
        speedDiagnosticSendStartedAt = 0L
''')

# Helpers/report. Persistence happens once, after confirmation.
r('''    private fun formatElapsedMs(ms: Long): String {
''','''    private fun tdBegin(e:Long,a:Long,cd:Long,c:Long,pa:Long,ro:Long,ni:Int){
        tdOn=true; tdEvent=e; tdAnalyze=a; tdCollectDone=cd; tdCollect=c; tdParse=pa; tdRoute=ro; tdNewItems=ni
        tdStatusTexto=0;tdStatusTextoDone=0;tdSend=0;tdSendCollect=0;tdEditor=0;tdSet=0;tdFilled=0;tdStatusEnvio=0;tdStatusEnvioDone=0
        tdReady=0;tdReadyCollect=0;tdReadyFound=0;tdReadyPoll=0;tdStatusReady=0;tdStatusReadyDone=0;tdClick=0;tdClickCollect=0
        tdCandidateSend=0;tdAction=0;tdClicked=0;tdConfirmCollect=0;tdConfirmPoll=0;tdConfirmed=0;tdHeld=0;tdReleased=0
    }
    private fun tdD(a:Long,b:Long)=if(a>0&&b>=a) "${b-a}ms" else "--"
    private fun tdA(a:Long)=if(tdEvent>0&&a>=tdEvent) "+${a-tdEvent}ms" else "+--"
    private fun tdReport(route:RouteResult){
        val x=buildString{
            append("===== DIAGNOSTICO TEXTO v1 | OLD BASE =====\n")
            append("[+0ms] Evento WhatsApp\n")
            append("[${tdA(tdAnalyze)}] Analise iniciou | evento->analise=${tdD(tdEvent,tdAnalyze)}\n")
            append("[${tdA(tdCollectDone)}] Arvore inicial coletada | collect=${tdCollect}ms\n")
            append("[${tdA(tdRoute)}] Rota: ${route.neighborhood} -> ${route.cage} | parser=${tdParse}ms | newItems=$tdNewItems\n")
            append("[${tdA(tdStatusTextoDone)}] Status Texto | write=${tdStatusTexto}ms\n")
            append("[${tdA(tdEditor)}] Editor encontrado | collectEnvio=${tdSendCollect}ms\n")
            if(tdHeld>0) append("[${tdA(tdHeld)}] Rota pendente: sem editor\n")
            if(tdReleased>0) append("[${tdA(tdReleased)}] Editor/admin liberado | wait=${tdD(tdHeld,tdReleased)}\n")
            append("[${tdA(tdFilled)}] Campo preenchido | setText=${tdSet}ms\n")
            append("[${tdA(tdStatusEnvioDone)}] Status ENVIO | write=${tdStatusEnvio}ms\n")
            append("[${tdA(tdReady)}] SEND READY iniciou\n")
            append("[${tdA(tdReadyFound)}] Enviar encontrado | collectReady=${tdReadyCollect}ms | polls=$tdReadyPoll\n")
            append("[${tdA(tdStatusReadyDone)}] Status READY | write=${tdStatusReady}ms\n")
            append("[${tdA(tdCandidateSend)}] Candidato Enviar | collectClick=${tdClickCollect}ms\n")
            append("[${tdA(tdClicked)}] Clique aceito | action=${tdAction}ms | metodo=$speedDiagnosticSendMethod\n")
            append("[${tdA(tdConfirmed)}] Confirmado | collectConfirm=${tdConfirmCollect}ms | polls=$tdConfirmPoll\n\n")
            append("RESUMO\n")
            append("evento->rota=${tdD(tdEvent,tdRoute)}\nrota->campo=${tdD(tdRoute,tdFilled)}\ncampo->click=${tdD(tdFilled,tdClicked)}\n")
            append("click->confirm=${tdD(tdClicked,tdConfirmed)}\nrota->click=${tdD(tdRoute,tdClicked)}\nrota->confirm=${tdD(tdRoute,tdConfirmed)}\n")
            append("evento->confirm=${tdD(tdEvent,tdConfirmed)}\n")
            append("collectTotal=${tdCollect+tdSendCollect+tdReadyCollect+tdClickCollect+tdConfirmCollect}ms | statusWrites=${tdStatusTexto+tdStatusEnvio+tdStatusReady}ms")
        }
        Prefs.setSpeedDiagnosticReport(this,x); tdOn=false; tdCandidate=0
    }

    private fun formatElapsedMs(ms: Long): String {
''')

# Prefs direct setter used only after send confirmation.
needle='''    fun speedDiagnostic(context: Context): String =
'''
if needle not in p: raise SystemExit('Prefs anchor missing')
p=p.replace(needle,'''    fun setSpeedDiagnosticReport(context: Context, value: String) {
        prefs(context).edit().putString(KEY_SPEED_DIAGNOSTIC, value).putBoolean(KEY_SPEED_DIAGNOSTIC_ACTIVE, false).apply()
    }

'''+needle,1)

S.write_text(s);P.write_text(p)
print('OK compact text diagnostic old base')
