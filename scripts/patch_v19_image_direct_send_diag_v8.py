from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s = S.read_text(encoding='utf-8')

required = [
    '===== DIAGNOSTICO TEXTO v6 | OLD BASE + TEXT TAIL DELTA + DIRECT SEND =====',
    'private fun waitForTextDirectSendReadyV5(',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    'Prefs.setSpeedDiagnosticReport(this,x)',
    'private fun findAdminUltraSendNodeFast(',
]
for marker in required:
    if marker not in s:
        raise SystemExit('IMAGE DIRECT DIAG v8 wrong base / missing marker: ' + marker)

# ---------------------------------------------------------------------------
# Image diagnostic state. Kept entirely separate from td* so TEXT v6 behavior
# stays byte-for-byte equivalent on its critical path.
# ---------------------------------------------------------------------------
field_anchor = '    private var tdHeld=0L; private var tdReleased=0L\n'
if field_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: td field anchor not found')
fields = field_anchor + '''    private var idOn=false; private var idStart=0L; private var idMediaFound=0L; private var idMediaStore=0L
    private var idDecode=0L; private var idScan=0L; private var idBairro=0L; private var idBairroOcr=0L
    private var idCage=0L; private var idCageOcr=0L; private var idRoute=0L
    private var idSend=0L; private var idSendCollect=0L; private var idEditor=0L; private var idSet=0L; private var idFilled=0L
    private var idReady=0L; private var idReadyFound=0L; private var idReadyPoll=0
    private var idClicked=0L; private var idAction=0L; private var idConfirmCollect=0L; private var idConfirmPoll=0; private var idConfirmed=0L
    private var idNeighborhood=""; private var idCageText=""; private var idHeight=0
'''
s = s.replace(field_anchor, fields, 1)

# ---------------------------------------------------------------------------
# Begin the image trace at the MediaStore scan that actually found the file.
# This avoids inventing an AccessibilityEvent timestamp for image routes, which
# are detected by the 10ms MediaStore watcher.
# ---------------------------------------------------------------------------
start_anchor = '''        val media = findNewestWhatsAppImage() ?: return
        val mediaStoreMs = SystemClock.elapsedRealtime() - mediaStoreStarted

        // Reserva o arquivo antes de iniciar OCR para nenhum outro evento pegar o
'''
start_new = '''        val media = findNewestWhatsAppImage() ?: return
        val mediaStoreMs = SystemClock.elapsedRealtime() - mediaStoreStarted
        idBegin(mediaStoreStarted, SystemClock.elapsedRealtime(), mediaStoreMs, media.height)

        // Reserva o arquivo antes de iniciar OCR para nenhum outro evento pegar o
'''
if start_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: MediaStore start anchor not found')
s = s.replace(start_anchor, start_new, 1)

# Bairro-first measurements: decode/scan + OCR finish point.
bairro_anchor = '''                lastDensePriorityNeighborhood = chosen.neighborhood
                lastDensePriorityIndex = chosen.priorityIndex
                lastDensePriorityCenterY = chosen.centerY
'''
bairro_new = '''                if (idOn) {
                    idDecode = decodeMs
                    idScan = scanMs
                    idBairroOcr = bairroOcrMs
                    idBairro = SystemClock.elapsedRealtime()
                    idNeighborhood = chosen.neighborhood
                }
                lastDensePriorityNeighborhood = chosen.neighborhood
                lastDensePriorityIndex = chosen.priorityIndex
                lastDensePriorityCenterY = chosen.centerY
'''
if bairro_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: bairro anchor not found')
s = s.replace(bairro_anchor, bairro_new, 1)

# Gaiola/route-ready point for the fast dense path.
cage_anchor = '''                    val route = RouteResult(
                        neighborhood = lastDensePriorityNeighborhood,
                        cage = cage!!,
                        priorityIndex = lastDensePriorityIndex
                    )

                    if (isDuplicate(route)) {
'''
cage_new = '''                    val route = RouteResult(
                        neighborhood = lastDensePriorityNeighborhood,
                        cage = cage!!,
                        priorityIndex = lastDensePriorityIndex
                    )
                    if (idOn) {
                        idCageOcr = cageOcrMs
                        idCage = SystemClock.elapsedRealtime()
                        idRoute = idCage
                        idNeighborhood = route.neighborhood
                        idCageText = route.cage
                    }

                    if (isDuplicate(route)) {
'''
if cage_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: gaiola anchor not found')
s = s.replace(cage_anchor, cage_new, 1)

# Any image fallback that eventually reaches sendRouteInCurrentChat still gets a
# route-ready timestamp here. TEXT has idOn=false and pays only one branch.
send_entry_anchor = '''    private fun sendRouteInCurrentChat(route: RouteResult) {
        if(tdOn && tdSend==0L) tdSend=SystemClock.elapsedRealtime()
'''
send_entry_new = '''    private fun sendRouteInCurrentChat(route: RouteResult) {
        if(tdOn && tdSend==0L) tdSend=SystemClock.elapsedRealtime()
        if (idOn) {
            val now = SystemClock.elapsedRealtime()
            if (idRoute == 0L) idRoute = now
            if (idSend == 0L) idSend = now
            if (idNeighborhood.isBlank()) idNeighborhood = route.neighborhood
            if (idCageText.isBlank()) idCageText = route.cage
        }
'''
if send_entry_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: send entry anchor not found')
s = s.replace(send_entry_anchor, send_entry_new, 1)

# Initial send tree/editor collection timing.
collect_anchor = '''        val tdSc = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val items = collectNodeItems(root)
        if(tdOn && tdSc>0L) tdSendCollect += SystemClock.elapsedRealtime()-tdSc

        val editor = findMessageEditor(items)
        if(tdOn && editor!=null && tdEditor==0L) tdEditor=SystemClock.elapsedRealtime()
'''
collect_new = '''        val tdSc = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val idSc = if(idOn) SystemClock.elapsedRealtime() else 0L
        val items = collectNodeItems(root)
        if(tdOn && tdSc>0L) tdSendCollect += SystemClock.elapsedRealtime()-tdSc
        if(idOn && idSc>0L) idSendCollect += SystemClock.elapsedRealtime()-idSc

        val editor = findMessageEditor(items)
        if(tdOn && editor!=null && tdEditor==0L) tdEditor=SystemClock.elapsedRealtime()
        if(idOn && editor!=null && idEditor==0L) idEditor=SystemClock.elapsedRealtime()
'''
if collect_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: send collect anchor not found')
s = s.replace(collect_anchor, collect_new, 1)

# ACTION_SET_TEXT timing.
set_anchor = '''        val tdSs = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val setOk = editor.node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        )
        if(tdOn && tdSs>0L){ tdSet += SystemClock.elapsedRealtime()-tdSs; if(setOk) tdFilled=SystemClock.elapsedRealtime() }
'''
set_new = '''        val tdSs = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val idSs = if(idOn) SystemClock.elapsedRealtime() else 0L
        val setOk = editor.node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        )
        if(tdOn && tdSs>0L){ tdSet += SystemClock.elapsedRealtime()-tdSs; if(setOk) tdFilled=SystemClock.elapsedRealtime() }
        if(idOn && idSs>0L){ idSet += SystemClock.elapsedRealtime()-idSs; if(setOk) idFilled=SystemClock.elapsedRealtime() }
'''
if set_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: setText anchor not found')
s = s.replace(set_anchor, set_new, 1)

# Direct named Enviar/Send for IMAGE. Same 4ms strategy as TEXT v5, with old
# SEND READY preserved as fallback if WhatsApp does not expose the named node.
current_editor_anchor = '    private fun currentEditorText(items: List<NodeItem>): String {\n'
if current_editor_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: currentEditorText anchor not found')
helper = r'''    private fun waitForImageDirectSendReadyV8(
        route: RouteResult,
        startedAt: Long,
        poll: Int,
        editorRect: Rect
    ) {
        if (!processing || !idOn) return
        if (idReady == 0L) idReady = startedAt

        val pollDelayMs = 4L
        val maxPolls = 70
        val root = rootInActiveWindow
        if (root == null) {
            if (poll < maxPolls) {
                handler.postDelayed(
                    { waitForImageDirectSendReadyV8(route, startedAt, poll + 1, editorRect) },
                    pollDelayMs
                )
            } else {
                waitForSendButtonReady(route, startedAt, 0)
            }
            return
        }

        val sendNode = findAdminUltraSendNodeFast(root, editorRect)
        if (sendNode != null) {
            idReadyFound = SystemClock.elapsedRealtime()
            idReadyPoll = poll
            speedDiagnosticSendAttempts = 1
            speedDiagnosticSendMethod = "IMAGE_DIRECT_V8"

            if (clickNodeOrParent(sendNode)) {
                handler.postDelayed({ verifySendResult(route, 0, 0) }, 8L)
                return
            }

            // No accepted click yet; safe to use the original single-attempt fallback.
            tryClickSend(route, 0)
            return
        }

        if (poll < maxPolls) {
            handler.postDelayed(
                { waitForImageDirectSendReadyV8(route, startedAt, poll + 1, editorRect) },
                pollDelayMs
            )
            return
        }

        waitForSendButtonReady(route, startedAt, 0)
    }

'''
s = s.replace(current_editor_anchor, helper + current_editor_anchor, 1)

# Change only the non-text branch: v6 TEXT DIRECT remains untouched; image now
# goes direct, while any unrelated path keeps the old delayed SEND READY.
postfill_anchor = '''        if (tdOn) {
            waitForTextDirectSendReadyV5(
                route,
                SystemClock.elapsedRealtime(),
                0,
                Rect(editor.rect)
            )
        } else {
            handler.postDelayed(
                {
                    waitForSendButtonReady(
                        route,
                        SystemClock.elapsedRealtime(),
                        0
                    )
                },
                SEND_BUTTON_DELAY_MS
            )
        }
'''
postfill_new = '''        if (tdOn) {
            waitForTextDirectSendReadyV5(
                route,
                SystemClock.elapsedRealtime(),
                0,
                Rect(editor.rect)
            )
        } else if (idOn) {
            waitForImageDirectSendReadyV8(
                route,
                SystemClock.elapsedRealtime(),
                0,
                Rect(editor.rect)
            )
        } else {
            handler.postDelayed(
                {
                    waitForSendButtonReady(
                        route,
                        SystemClock.elapsedRealtime(),
                        0
                    )
                },
                SEND_BUTTON_DELAY_MS
            )
        }
'''
if postfill_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: post-fill branch anchor not found')
s = s.replace(postfill_anchor, postfill_new, 1)

# Record accepted ACTION_CLICK regardless of whether the image used normal direct
# send or ADMIN direct while a group was locked. td* instrumentation remains as-is.
click_start_anchor = '''    private fun clickNodeOrParent(start: AccessibilityNodeInfo): Boolean {
        val t=if(tdOn) SystemClock.elapsedRealtime() else 0L
'''
click_start_new = '''    private fun clickNodeOrParent(start: AccessibilityNodeInfo): Boolean {
        val t=if(tdOn) SystemClock.elapsedRealtime() else 0L
        val idClickStart=if(idOn) SystemClock.elapsedRealtime() else 0L
'''
if click_start_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: click helper start anchor not found')
s = s.replace(click_start_anchor, click_start_new, 1)

click_success_anchor = '''                if(tdOn && t>0L){ tdAction += SystemClock.elapsedRealtime()-t; if(tdClicked==0L) tdClicked=SystemClock.elapsedRealtime() }
                return true
'''
click_success_new = '''                if(tdOn && t>0L){ tdAction += SystemClock.elapsedRealtime()-t; if(tdClicked==0L) tdClicked=SystemClock.elapsedRealtime() }
                if(idOn && idClickStart>0L){ idAction += SystemClock.elapsedRealtime()-idClickStart; if(idClicked==0L) idClicked=SystemClock.elapsedRealtime() }
                return true
'''
if click_success_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: click success anchor not found')
s = s.replace(click_success_anchor, click_success_new, 1)

click_final_anchor = '''        if(tdOn && t>0L){ tdAction += SystemClock.elapsedRealtime()-t; if(ok && tdClicked==0L) tdClicked=SystemClock.elapsedRealtime() }
        return ok
'''
click_final_new = '''        if(tdOn && t>0L){ tdAction += SystemClock.elapsedRealtime()-t; if(ok && tdClicked==0L) tdClicked=SystemClock.elapsedRealtime() }
        if(idOn && idClickStart>0L){ idAction += SystemClock.elapsedRealtime()-idClickStart; if(ok && idClicked==0L) idClicked=SystemClock.elapsedRealtime() }
        return ok
'''
if click_final_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: click final anchor not found')
s = s.replace(click_final_anchor, click_final_new, 1)

# Confirmation collection timing. This is after the click and therefore does not
# affect the race, but lets the report match the TEXT diagnostic detail.
confirm_anchor = '''        val tdFc = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val items = collectNodeItems(root)
        if(tdOn && tdFc>0L){ tdConfirmCollect += SystemClock.elapsedRealtime()-tdFc; tdConfirmPoll=poll }
        val editor = findMessageEditor(items)

        // Se o editor existe e a mensagem sumiu, o primeiro ACTION_CLICK enviou.
        if (editor != null && !messageStillInEditor(items)) {
            markSent(route)
'''
confirm_new = '''        val tdFc = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val idFc = if(idOn) SystemClock.elapsedRealtime() else 0L
        val items = collectNodeItems(root)
        if(tdOn && tdFc>0L){ tdConfirmCollect += SystemClock.elapsedRealtime()-tdFc; tdConfirmPoll=poll }
        if(idOn && idFc>0L){ idConfirmCollect += SystemClock.elapsedRealtime()-idFc; idConfirmPoll=poll }
        val editor = findMessageEditor(items)

        // Se o editor existe e a mensagem sumiu, o primeiro ACTION_CLICK enviou.
        if (editor != null && !messageStillInEditor(items)) {
            if(idOn && idConfirmed==0L) idConfirmed=SystemClock.elapsedRealtime()
            markSent(route)
'''
if confirm_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: confirm anchor not found')
s = s.replace(confirm_anchor, confirm_new, 1)

# Reset a failed image trace so it can never leak into a later text route.
failure_anchor = '''    private fun finishFileOnlyFailure(message: String) {
        processing = false
        Prefs.setStatus(this, message)
'''
failure_new = '''    private fun finishFileOnlyFailure(message: String) {
        processing = false
        Prefs.setStatus(this, message)
        idOn = false
'''
if failure_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: failure anchor not found')
s = s.replace(failure_anchor, failure_new, 1)

# Image report helpers inserted next to the existing tdReport/format helpers.
format_anchor = '    private fun formatElapsedMs(ms: Long): String {\n'
if format_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: formatElapsedMs anchor not found')
report_helpers = r'''    private fun idBegin(start:Long, found:Long, mediaMs:Long, height:Int){
        idOn=true; idStart=start; idMediaFound=found; idMediaStore=mediaMs; idHeight=height
        idDecode=0; idScan=0; idBairro=0; idBairroOcr=0; idCage=0; idCageOcr=0; idRoute=0
        idSend=0; idSendCollect=0; idEditor=0; idSet=0; idFilled=0; idReady=0; idReadyFound=0; idReadyPoll=0
        idClicked=0; idAction=0; idConfirmCollect=0; idConfirmPoll=0; idConfirmed=0
        idNeighborhood=""; idCageText=""
    }
    private fun idA(t:Long):String = if(t>0L && idStart>0L) "+${(t-idStart).coerceAtLeast(0L)}ms" else "--"
    private fun idD(a:Long,b:Long):String = if(a>0L && b>=a) "${b-a}ms" else "--"
    private fun idReport(route:RouteResult){
        if(!idOn) return
        if(idConfirmed==0L) idConfirmed=SystemClock.elapsedRealtime()
        val x=buildString{
            appendLine("===== DIAGNOSTICO IMAGEM v8 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND =====")
            appendLine("[+0ms] MediaStore watcher")
            appendLine("[${idA(idMediaFound)}] Imagem localizada | MediaStore=${idMediaStore}ms | h=${idHeight}px")
            if(idBairro>0L) appendLine("[${idA(idBairro)}] Bairro: $idNeighborhood | OCR=${idBairroOcr}ms | decode=${idDecode}ms | scan=${idScan}ms")
            if(idCage>0L) appendLine("[${idA(idCage)}] Gaiola: $idCageText | OCR=${idCageOcr}ms")
            appendLine("[${idA(idRoute)}] Rota pronta: ${route.neighborhood} -> ${route.cage}")
            appendLine("[${idA(idEditor)}] Editor encontrado | collectEnvio=${idSendCollect}ms")
            appendLine("[${idA(idFilled)}] Campo preenchido | setText=${idSet}ms")
            appendLine("[${idA(idReady)}] DIRECT SEND iniciou")
            appendLine("[${idA(idReadyFound)}] Enviar encontrado | polls=$idReadyPoll")
            appendLine("[${idA(idClicked)}] Clique aceito | action=${idAction}ms | metodo=$speedDiagnosticSendMethod")
            appendLine("[${idA(idConfirmed)}] Confirmado | collectConfirm=${idConfirmCollect}ms | polls=$idConfirmPoll")
            appendLine()
            appendLine("RESUMO")
            appendLine("media->rota=${idD(idMediaFound,idRoute)}")
            appendLine("bairro->gaiola=${idD(idBairro,idCage)}")
            appendLine("rota->campo=${idD(idRoute,idFilled)}")
            appendLine("campo->click=${idD(idFilled,idClicked)}")
            appendLine("click->confirm=${idD(idClicked,idConfirmed)}")
            appendLine("rota->click=${idD(idRoute,idClicked)}")
            appendLine("rota->confirm=${idD(idRoute,idConfirmed)}")
            appendLine("media->confirm=${idD(idMediaFound,idConfirmed)}")
            append("collectTotal=${idSendCollect+idConfirmCollect}ms | OCRbairro=${idBairroOcr}ms | OCRgaiola=${idCageOcr}ms")
        }
        Prefs.setSpeedDiagnosticReport(this,x)
        idOn=false
    }

'''
s = s.replace(format_anchor, report_helpers + format_anchor, 1)

# Finalize the detailed image report after the existing CONFIRMADO status. TEXT
# tdReport still executes independently when tdOn=true.
mark_anchor = '''        Prefs.setStatus(
            this,
            "CONFIRMADO: ${route.neighborhood} -> ${route.cage} | " +
                "envio=${formatElapsedMs(sendStageMs)} | tentativas=${speedDiagnosticSendAttempts} | " +
                "metodo=${speedDiagnosticSendMethod} | app=${formatElapsedMs(elapsed)}"
        )
        speedDiagnosticSendStartedAt = 0L
'''
mark_new = '''        Prefs.setStatus(
            this,
            "CONFIRMADO: ${route.neighborhood} -> ${route.cage} | " +
                "envio=${formatElapsedMs(sendStageMs)} | tentativas=${speedDiagnosticSendAttempts} | " +
                "metodo=${speedDiagnosticSendMethod} | app=${formatElapsedMs(elapsed)}"
        )
        if(idOn){
            if(idConfirmed==0L) idConfirmed=SystemClock.elapsedRealtime()
            idReport(route)
        }
        speedDiagnosticSendStartedAt = 0L
'''
if mark_anchor not in s:
    raise SystemExit('IMAGE DIRECT DIAG v8: markSent anchor not found')
s = s.replace(mark_anchor, mark_new, 1)

checks = [
    'private fun waitForImageDirectSendReadyV8(',
    'speedDiagnosticSendMethod = "IMAGE_DIRECT_V8"',
    '===== DIAGNOSTICO IMAGEM v8 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND =====',
    'else if (idOn) {\n            waitForImageDirectSendReadyV8(',
    'Prefs.setSpeedDiagnosticReport(this,x)',
    '===== DIAGNOSTICO TEXTO v6 | OLD BASE + TEXT TAIL DELTA + DIRECT SEND =====',
]
for marker in checks:
    if marker not in s:
        raise SystemExit('IMAGE DIRECT DIAG v8 verification failed: ' + marker)

S.write_text(s, encoding='utf-8')
print('IMAGE DIRECT SEND + detailed image diagnostic v8 applied; TEXT v6 preserved')
