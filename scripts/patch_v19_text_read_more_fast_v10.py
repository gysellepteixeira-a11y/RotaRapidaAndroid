from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s = S.read_text(encoding='utf-8')

required = [
    '===== DIAGNOSTICO TEXTO v6 | OLD BASE + TEXT TAIL DELTA + DIRECT SEND =====',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
    'val tfNewItems = tfNewItemsReverse.asReversed()',
    'private fun clickNodeOrParent(',
    'private fun waitForTextDirectSendReadyV5(',
    'appendLine("RESUMO")',
]
for marker in required:
    if marker not in s:
        raise SystemExit('READ MORE FAST v10 wrong base / missing marker: ' + marker)

# Estado temporario entre o primeiro evento da mensagem truncada e a arvore expandida.
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

# Enquanto o balao expande, ignora a tempestade de eventos do WhatsApp.
# Preserva o timestamp do primeiro evento para medir o custo real do Ler mais.
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

# Procura direta por Ler mais/Read more, restrita a faixa vertical dos itens NOVOS.
# Assim nao clica em Ler mais antigo que ficou mais acima na conversa.
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
                val isReadMore =
                    n == "ler mais" || n == "read more" ||
                    n.endsWith(" ler mais") || n.endsWith(" read more")
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
                stillReadMore =
                    n == "ler mais" || n == "read more" ||
                    n.endsWith(" ler mais") || n.endsWith(" read more")
            }
        } catch (_: Throwable) {
            stillReadMore = false
        }

        if (!stillReadMore || poll >= maxPolls) {
            rmExpanded = SystemClock.elapsedRealtime()
            rmPolls = poll
            rmPending = false
            rmCarry = true
            // Sem espera fixa: rele a arvore assim que o no Ler mais some/muda.
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

# O TAIL v6 ja isolou a cauda da mensagem nova. Antes de chamar o parser,
# expande Ler mais apenas se ele estiver nessa mesma cauda.
hot_anchor = '''        val tfNewItems = tfNewItemsReverse.asReversed()

        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.
'''
hot_insert = '''        val tfNewItems = tfNewItemsReverse.asReversed()

        // READ MORE FAST v10: nunca escolhe prioridade usando balao novo truncado.
        // Mensagens sem Ler mais seguem direto para o parser v6.
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
                // Se existe Ler mais mas o WhatsApp recusou o clique, nao manda uma
                // prioridade potencialmente incompleta. Tenta reler logo depois.
                handler.postDelayed({ analyzeCurrentWindow() }, 20L)
                return
            }
        }

        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.
'''
if hot_anchor not in s:
    raise SystemExit('READ MORE FAST v10 hot anchor not found')
s = s.replace(hot_anchor, hot_insert, 1)

# Leva os tempos do Ler mais para o diagnostico da rota antes de limpar o estado.
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

header_old = '===== DIAGNOSTICO TEXTO v6 | OLD BASE + TEXT TAIL DELTA + DIRECT SEND ====='
header_new = '===== DIAGNOSTICO TEXTO v10 | TEXT v6 + READ MORE FAST + DIRECT SEND ====='
s = s.replace(header_old, header_new, 1)

# O compile-fix usa appendLine(). Acrescenta o custo do Ler mais sem mexer nos
# demais timestamps da v6.
report_anchor = '''            appendLine("[${tdA(tdCollectDone)}] Arvore inicial coletada | collect=${tdCollect}ms")
            appendLine("[${tdA(tdRoute)}] Rota: ${route.neighborhood} -> ${route.cage} | parser=${tdParse}ms | newItems=$tdNewItems")
'''
report_replacement = '''            appendLine("[${tdA(tdCollectDone)}] Arvore inicial coletada | collect=${tdCollect}ms")
            if(tdReadMoreUsed){
                appendLine("[${tdA(tdReadMoreClicked)}] Ler mais clicado | action=${tdReadMoreClickMs}ms")
                appendLine("[${tdA(tdReadMoreExpanded)}] Conteudo expandido | click->expand=${tdD(tdReadMoreClicked,tdReadMoreExpanded)} | polls=$tdReadMorePolls")
            }
            appendLine("[${tdA(tdRoute)}] Rota: ${route.neighborhood} -> ${route.cage} | parser=${tdParse}ms | newItems=$tdNewItems")
'''
if report_anchor not in s:
    raise SystemExit('READ MORE FAST v10 appendLine report anchor not found')
s = s.replace(report_anchor, report_replacement, 1)

summary_anchor = '''            appendLine("evento->confirm=${tdD(tdEvent,tdConfirmed)}")
            append("collectTotal=${tdCollect+tdSendCollect+tdReadyCollect+tdClickCollect+tdConfirmCollect}ms | statusWrites=${tdStatusTexto+tdStatusEnvio+tdStatusReady}ms")
'''
summary_replacement = '''            appendLine("evento->confirm=${tdD(tdEvent,tdConfirmed)}")
            if(tdReadMoreUsed) appendLine("readMore=${tdD(tdReadMoreClicked,tdReadMoreExpanded)} | readMoreAction=${tdReadMoreClickMs}ms | readMorePolls=$tdReadMorePolls")
            append("collectTotal=${tdCollect+tdSendCollect+tdReadyCollect+tdClickCollect+tdConfirmCollect}ms | statusWrites=${tdStatusTexto+tdStatusEnvio+tdStatusReady}ms")
'''
if summary_anchor not in s:
    raise SystemExit('READ MORE FAST v10 appendLine summary anchor not found')
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
