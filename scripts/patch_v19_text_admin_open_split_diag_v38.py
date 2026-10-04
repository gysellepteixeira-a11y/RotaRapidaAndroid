from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v37 | TEXT v6 + ADMIN CLOSED READ FIX + ASCII NORMALIZE FAST + LOCAL ANCHOR PROOF + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v38 | TEXT v6 + ADMIN OPEN SPLIT DIAG + ADMIN CLOSED READ FIX + ASCII NORMALIZE FAST + LOCAL ANCHOR PROOF + READ MORE v21 + DIRECT SEND ====='

required=[
    old_header,
    'private const val PENDING_ROUTE_SEND_WATCH_MS = 10L',
    'private val pendingRouteSendWatchRunnable = object : Runnable',
    'private fun trySendPendingRouteIfChatOpen(): Boolean {',
    'private fun findAdminUltraSendNodeFast(',
    'private var tdHeld=0L; private var tdReleased=0L',
    'collectTotal=${tdCollect+tdSendCollect+tdReadyCollect+tdClickCollect+tdConfirmCollect}ms',
]
for m in required:
    if m not in s:
        raise SystemExit('ADMIN OPEN SPLIT DIAG v38 wrong base: '+m)

# RAM-only counters. No extra Prefs writes are added before confirmation.
state_anchor='    private var tdHeld=0L; private var tdReleased=0L\n'
state_insert=state_anchor+'''    private var tdV38PendingCaller="NONE"; private var tdV38PendingSource="NONE"
    private var tdV38PendingCollectMs=0L; private var tdV38EditorLookupMs=0L; private var tdV38SetTextMs=0L
    private var tdV38ReadyCalls=0; private var tdV38EnviarQueryUs=0L; private var tdV38SendQueryUs=0L; private var tdV38QueryCandidates=0
'''
s=s.replace(state_anchor,state_insert,1)

# Reset together with the existing text diagnostic state.
reset_anchor='''        tdCandidateSend=0;tdAction=0;tdClicked=0;tdConfirmCollect=0;tdConfirmPoll=0;tdConfirmed=0;tdHeld=0;tdReleased=0
'''
reset_new=reset_anchor+'''        tdV38PendingSource="NONE";tdV38PendingCollectMs=0;tdV38EditorLookupMs=0;tdV38SetTextMs=0
        tdV38ReadyCalls=0;tdV38EnviarQueryUs=0;tdV38SendQueryUs=0;tdV38QueryCandidates=0
'''
if reset_anchor not in s:
    raise SystemExit('v38 tdBegin reset anchor not found')
s=s.replace(reset_anchor,reset_new,1)

# Mark calls originating from the 10ms watcher. Any successful pending send that
# does not carry WATCH therefore came from the accessibility-event path.
watch_sig='    private val pendingRouteSendWatchRunnable = object : Runnable {'
ws=s.find(watch_sig)
we=s.find('\n    override fun onServiceConnected()',ws)
if ws<0 or we<0:
    raise SystemExit('v38 watcher block not found')
wb=s[ws:we]
old_watch_call='''                    trySendPendingRouteIfChatOpen()
'''
new_watch_call='''                    tdV38PendingCaller="WATCH"
                    try {
                        trySendPendingRouteIfChatOpen()
                    } finally {
                        tdV38PendingCaller="NONE"
                    }
'''
if old_watch_call not in wb:
    raise SystemExit('v38 watcher call not found')
wb=wb.replace(old_watch_call,new_watch_call,1)
s=s[:ws]+wb+s[we:]

# Successful admin-open attempt: split full-tree collection, editor lookup, and
# ACTION_SET_TEXT. Failed closed-state polls are intentionally not accumulated.
ps=s.find('    private fun trySendPendingRouteIfChatOpen(): Boolean {')
pe=s.find('    private fun sendRouteInCurrentChat(route: RouteResult) {',ps)
if ps<0 or pe<0:
    raise SystemExit('v38 pending function block not found')
pb=s[ps:pe]
old_pending='''        val root = rootInActiveWindow ?: return false
        val items = collectNodeItems(root)
        val editor = findMessageEditor(items) ?: return false

        val releasedAt = SystemClock.elapsedRealtime()
'''
new_pending='''        val root = rootInActiveWindow ?: return false
        val v38CollectStart = SystemClock.elapsedRealtime()
        val items = collectNodeItems(root)
        val v38CollectMs = SystemClock.elapsedRealtime() - v38CollectStart
        val v38EditorStart = SystemClock.elapsedRealtime()
        val editor = findMessageEditor(items)
        val v38EditorMs = SystemClock.elapsedRealtime() - v38EditorStart
        if (editor == null) return false

        tdV38PendingSource = if(tdV38PendingCaller=="WATCH") "WATCH" else "EVENT"
        tdV38PendingCollectMs = v38CollectMs
        tdV38EditorLookupMs = v38EditorMs
        val releasedAt = SystemClock.elapsedRealtime()
'''
if old_pending not in pb:
    raise SystemExit('v38 pending collect/editor anchor not found')
pb=pb.replace(old_pending,new_pending,1)
old_set='''        val setOk = editor.node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        )

        if (!setOk) {
'''
new_set='''        val v38SetStart = SystemClock.elapsedRealtime()
        val setOk = editor.node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        )
        tdV38SetTextMs = SystemClock.elapsedRealtime() - v38SetStart

        if (!setOk) {
'''
if old_set not in pb:
    raise SystemExit('v38 pending setText anchor not found')
pb=pb.replace(old_set,new_set,1)
s=s[:ps]+pb+s[pe:]

# Direct Send search: time the Portuguese and English Accessibility text queries
# separately at microsecond resolution. Search order/criteria remain identical.
fs=s.find('    private fun findAdminUltraSendNodeFast(')
fe=s.find('    private fun verifyAdminUltraFast(',fs)
if fs<0 or fe<0:
    raise SystemExit('v38 fast send finder block not found')
fb=s[fs:fe]
body_anchor='''        val queries = arrayOf("Enviar", "Send")

        for (query in queries) {
            val nodes = try {
                root.findAccessibilityNodeInfosByText(query)
            } catch (_: Throwable) {
                emptyList<AccessibilityNodeInfo>()
            }

            for (node in nodes) {
'''
body_new='''        val queries = arrayOf("Enviar", "Send")
        if(tdOn) tdV38ReadyCalls++

        for (query in queries) {
            val v38QueryStart = SystemClock.elapsedRealtimeNanos()
            val nodes = try {
                root.findAccessibilityNodeInfosByText(query)
            } catch (_: Throwable) {
                emptyList<AccessibilityNodeInfo>()
            }
            if(tdOn){
                val v38Us=(SystemClock.elapsedRealtimeNanos()-v38QueryStart)/1000L
                if(query=="Enviar") tdV38EnviarQueryUs += v38Us else tdV38SendQueryUs += v38Us
                tdV38QueryCandidates += nodes.size
            }

            for (node in nodes) {
'''
if body_anchor not in fb:
    raise SystemExit('v38 query timing anchor not found')
fb=fb.replace(body_anchor,body_new,1)
s=s[:fs]+fb+s[fe:]

# One report line after confirmation only. Existing diagnostic already owns the
# release/filled/ready/click timestamps, so expose those deltas alongside query cost.
report_anchor='''            append("collectTotal=${tdCollect+tdSendCollect+tdReadyCollect+tdClickCollect+tdConfirmCollect}ms | statusWrites=${tdStatusTexto+tdStatusEnvio+tdStatusReady}ms")
'''
report_new='''            append("adminOpenV38=source=$tdV38PendingSource | release->filled=${tdD(tdReleased,tdFilled)} | filled->ready=${tdD(tdFilled,tdReadyFound)} | ready->click=${tdD(tdReadyFound,tdClicked)} | pendingCollect=${tdV38PendingCollectMs}ms | editorLookup=${tdV38EditorLookupMs}ms | setText=${tdV38SetTextMs}ms | readyCalls=$tdV38ReadyCalls | enviarQuery=${tdV38EnviarQueryUs}us | sendQuery=${tdV38SendQueryUs}us | candidates=$tdV38QueryCandidates | readyPoll=$tdReadyPoll | clickAction=${tdAction}ms\\n")
            append("collectTotal=${tdCollect+tdSendCollect+tdReadyCollect+tdClickCollect+tdConfirmCollect}ms | statusWrites=${tdStatusTexto+tdStatusEnvio+tdStatusReady}ms")
'''
if report_anchor not in s:
    raise SystemExit('v38 final report anchor not found')
s=s.replace(report_anchor,report_new,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'adminOpenV38=source=$tdV38PendingSource',
    'tdV38PendingSource = if(tdV38PendingCaller=="WATCH") "WATCH" else "EVENT"',
    'SystemClock.elapsedRealtimeNanos()',
    'val queries = arrayOf("Enviar", "Send")',
    'private const val PENDING_ROUTE_SEND_WATCH_MS = 10L',
    'ADMIN CLOSED READ FIX',
    'normalizeV36=$tdV36NormalizeDiag',
]:
    if m not in s:
        raise SystemExit('ADMIN OPEN SPLIT DIAG v38 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('ADMIN OPEN SPLIT DIAG v38 applied: pending collect/editor/setText + direct Enviar/Send query costs + source WATCH/EVENT; behavior unchanged')
