from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s = S.read_text(encoding='utf-8')

required = [
    '===== DIAGNOSTICO TEXTO v6 | OLD BASE + TEXT TAIL DELTA + DIRECT SEND =====',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
    'val tfNewItems = tfNewItemsReverse.asReversed()',
    'private fun clickNodeOrParent(',
    'private fun waitForTextDirectSendReadyV5(',
]
for marker in required:
    if marker not in s:
        raise SystemExit('READ MORE FAST v10 wrong base / missing marker: ' + marker)

# State carried only between the first new-message event and the expanded-tree parse.
state_anchor = '    private var tdHeld=0L; private var tdReleased=0L\n'
state_insert = '''    private var tdHeld=0L; private var tdReleased=0L
    private var rmPending=false; private var rmCarry=false; private var rmUsed=false
    private var rmStarted=0L; private var rmClicked=0L; private var rmExpanded=0L
    private var rmClickMs=0L; private var rmPolls=0
    private var tdReadMoreUsed=false; private var tdReadMoreClicked=0L; private var tdReadMoreExpanded=0L
    private var tdReadMoreClickMs=0L; private var tdReadMorePolls=0
'''
if state_anchor not in s:
    raise SystemExit('READ MORE FAST v10 state anchor not found')
s = s.replace(state_anchor, state_insert, 1)

# While waiting for the bubble to expand, ignore the accessibility-event storm.
# This preserves the original event timestamp and avoids parsing the truncated tree.
event_old = '''        if (processing) return
        if (!analyzeScheduled) tdCandidate = SystemClock.elapsedRealtime()
        scheduleAnalyze(12L)
'''
event_new = '''        if (processing) return
        if (rmPending) return
        if (!analyzeScheduled) {
            tdCandidate = SystemClock.elapsedRealtime()
            if (!rmCarry) {
                rmUsed=false; rmStarted=0L; rmClicked=0L; rmExpanded=0L; rmClickMs=0L; rmPolls=0
            }
        }
        scheduleAnalyze(12L)
'''
if event_old not in s:
    raise SystemExit('READ MORE FAST v10 event anchor not found')
s = s.replace(event_old, event_new, 1)

# Fast lookup by accessibility text. We still require the node to overlap the vertical
# band of the NEW tail items, so an old "Ler mais" higher in the chat is not clicked.
helper_anchor = '    private fun waitForTextDirectSendReadyV5(\n'
helper = r'''    private fun findNewestReadMoreV10(
        root: AccessibilityNodeInfo,
        newItems: List<NodeItem>
    ): AccessibilityNodeInfo? {
        if (newItems.isEmpty()) return null

        val validRects = newItems.map { it.rect }.filter { !it.isEmpty }
        if (validRects.isEmpty()) return null
        val newTop = validRects.minOf { it.top }
        val newBottom = validRects.maxOf { it.bottom }
        val h = resources.displayMetrics.heightPixels
        val extraBelow = maxOf(180, (h * 0.08f).toInt())

        var best: AccessibilityNodeInfo? = null
        var bestBottom = Int.MIN_VALUE
        val queries = arrayOf("Ler mais", "Read more")

        for (query in queries) {
            val nodes = try {
                root.findAccessibilityNodeInfosByText(query)
            } catch (_: Throwable) {
                emptyList<AccessibilityNodeInfo>()
            }

            for (node in nodes) {
                val rect = Rect()
                node.getBoundsInScreen(rect)
                if (rect.isEmpty) continue
                if (rect.bottom < newTop) continue
                if (rect.top > newBottom + extraBelow) continue

                val merged = buildString {
                    node.text?.toString()?.let { append(it) }
                    node.contentDescription?.toString()?.let {
                        if (isNotEmpty()) append(' ')
                        append(it)
                    }
                }
                val n = RouteParser.normalize(merged)
                val isReadMore = n == "ler mais" || n == "read more" || n.endsWith(" ler mais") || n.endsWith(" read more")
                if (!isReadMore) continue

                if (rect.bottom > bestBottom) {
                    bestBottom = rect.bottom
                    best = node
                }
            }
        }
        return best
    }

    private fun waitForReadMoreExpansionV10(
        clickedNode: AccessibilityNodeInfo,
        startedAt: Long,
        poll: Int
    ) {
        val pollDelayMs = 4L
        val maxPolls = 45
        var stillReadMore = false

        try {
            if (clickedNode.refresh()) {
                val merged = buildString {
                    clickedNode.text?.toString()?.let { append(it) }
                    clickedNode.contentDescription?.toString()?.let {
                        if (isNotEmpty()) append(' ')
                        append(it)
                    }
                }
                val n = RouteParser.normalize(merged)
                stillReadMore = n == "ler mais" || n == "read more" || n.endsWith(" ler mais") || n.endsWith(" read more")
            }
        } catch (_: Throwable) {
            stillReadMore = false
        }

        if (!stillReadMore || poll >= maxPolls) {
            rmExpanded = SystemClock.elapsedRealtime()
            rmPolls = poll
            rmPending = false
            rmCarry = true
            // Parse immediately from the expanded tree; no fixed 100/200ms sleep.
            handler.post { analyzeCurrentWindow() }
            return
        }

        handler.postDelayed(
            { waitForReadMoreExpansionV10(clickedNode, startedAt, poll + 1) },
            pollDelayMs
        )
    }

'''
if helper_anchor not in s:
    raise SystemExit('READ MORE FAST v10 helper anchor not found')
s = s.replace(helper_anchor, helper + helper_anchor, 1)

# v6 has already isolated the newest text tail. Before giving that tail to the parser,
# expand only a Read-more node that belongs to the same vertical band.
hot_anchor = '''        val tfNewItems = tfNewItemsReverse.asReversed()

        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.
'''
hot_insert = '''        val tfNewItems = tfNewItemsReverse.asReversed()

        // READ MORE FAST v10: never choose a priority from a truncated newest bubble.
        // No cost beyond one direct text lookup when the newest tail exists; normal
        // messages continue straight to the v6 parser.
        if (primed && Prefs.searchArmed(this) && tfNewItems.isNotEmpty() && !rmPending && !rmCarry) {
            val readMoreNode = findNewestReadMoreV10(root, tfNewItems)
            if (readMoreNode != null) {
                val started = SystemClock.elapsedRealtime()
                val ok = clickNodeOrParent(readMoreNode)
                val afterClick = SystemClock.elapsedRealtime()
                if (ok) {
                    rmUsed = true
                    rmPending = true
                    rmCarry = true
                    rmStarted = started
                    rmClicked = afterClick
                    rmClickMs = afterClick - started
                    rmExpanded = 0L
                    rmPolls = 0
                    waitForReadMoreExpansionV10(readMoreNode, started, 0)
                    return
                }
                // Safety over speed: if WhatsApp exposes Ler mais but refuses the click,
                // do not send from a potentially truncated priority list. Retry shortly.
                handler.postDelayed({ analyzeCurrentWindow() }, 20L)
                return
            }
        }

        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.
'''
if hot_anchor not in s:
    raise SystemExit('READ MORE FAST v10 hot anchor not found')
s = s.replace(hot_anchor, hot_insert, 1)

# Copy Read-more timing into the route diagnostic before clearing the carry state.
tdbegin_old = '''    private fun tdBegin(e:Long,a:Long,cd:Long,c:Long,pa:Long,ro:Long,ni:Int){
        tdOn=true; tdEvent=e; tdAnalyze=a; tdCollectDone=cd; tdCollect=c; tdParse=pa; tdRoute=ro; tdNewItems=ni
'''
tdbegin_new = '''    private fun tdBegin(e:Long,a:Long,cd:Long,c:Long,pa:Long,ro:Long,ni:Int){
        tdReadMoreUsed=rmUsed; tdReadMoreClicked=rmClicked; tdReadMoreExpanded=rmExpanded; tdReadMoreClickMs=rmClickMs; tdReadMorePolls=rmPolls
        rmPending=false; rmCarry=false; rmUsed=false; rmStarted=0L; rmClicked=0L; rmExpanded=0L; rmClickMs=0L; rmPolls=0
        tdOn=true; tdEvent=e; tdAnalyze=a; tdCollectDone=cd; tdCollect=c; tdParse=pa; tdRoute=ro; tdNewItems=ni
'''
if tdbegin_old not in s:
    raise SystemExit('READ MORE FAST v10 tdBegin anchor not found')
s = s.replace(tdbegin_old, tdbegin_new, 1)

# Add explicit timing lines to the text diagnostic and update its header.
header_old = '===== DIAGNOSTICO TEXTO v6 | OLD BASE + TEXT TAIL DELTA + DIRECT SEND ====='
header_new = '===== DIAGNOSTICO TEXTO v10 | TEXT v6 + READ MORE FAST + DIRECT SEND ====='
s = s.replace(header_old, header_new, 1)

report_anchor = '''            append("[${tdA(tdCollectDone)}] Arvore inicial coletada | collect=${tdCollect}ms\\n")
            append("[${tdA(tdRoute)}] Rota: ${route.neighborhood} -> ${route.cage} | parser=${tdParse}ms | newItems=$tdNewItems\\n")
'''
report_replacement = '''            append("[${tdA(tdCollectDone)}] Arvore inicial coletada | collect=${tdCollect}ms\\n")
            if(tdReadMoreUsed){
                append("[${tdA(tdReadMoreClicked)}] Ler mais clicado | action=${tdReadMoreClickMs}ms\\n")
                append("[${tdA(tdReadMoreExpanded)}] Conteudo expandido | click->expand=${tdD(tdReadMoreClicked,tdReadMoreExpanded)} | polls=$tdReadMorePolls\\n")
            }
            append("[${tdA(tdRoute)}] Rota: ${route.neighborhood} -> ${route.cage} | parser=${tdParse}ms | newItems=$tdNewItems\\n")
'''
if report_anchor not in s:
    raise SystemExit('READ MORE FAST v10 report anchor not found')
s = s.replace(report_anchor, report_replacement, 1)

summary_anchor = '''            append("evento->confirm=${tdD(tdEvent,tdConfirmed)}\\n")
            append("collectTotal=${tdCollect+tdSendCollect+tdReadyCollect+tdClickCollect+tdConfirmCollect}ms | statusWrites=${tdStatusTexto+tdStatusEnvio+tdStatusReady}ms")
'''
summary_replacement = '''            append("evento->confirm=${tdD(tdEvent,tdConfirmed)}\\n")
            if(tdReadMoreUsed) append("readMore=${tdD(tdReadMoreClicked,tdReadMoreExpanded)} | readMoreAction=${tdReadMoreClickMs}ms | readMorePolls=$tdReadMorePolls\\n")
            append("collectTotal=${tdCollect+tdSendCollect+tdReadyCollect+tdClickCollect+tdConfirmCollect}ms | statusWrites=${tdStatusTexto+tdStatusEnvio+tdStatusReady}ms")
'''
if summary_anchor not in s:
    raise SystemExit('READ MORE FAST v10 summary anchor not found')
s = s.replace(summary_anchor, summary_replacement, 1)

for marker in [
    header_new,
    'private fun findNewestReadMoreV10(',
    'private fun waitForReadMoreExpansionV10(',
    'Ler mais clicado',
    'readMoreAction=',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
]:
    if marker not in s:
        raise SystemExit('READ MORE FAST v10 verification failed: ' + marker)

S.write_text(s, encoding='utf-8')
print('READ MORE FAST v10 applied: newest truncated text bubble expands before v6 parser; TEXT direct and IMAGE v9 preserved')
