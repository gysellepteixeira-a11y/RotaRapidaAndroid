from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

required=[
    '===== DIAGNOSTICO IMAGEM v18 | V47 CLEAN FAST + V46 9 BAIRROS =====',
    'private fun sendRouteInCurrentChat(route: RouteResult) {',
    'val items = collectNodeItems(root)',
    'val editor = findMessageEditor(items)',
    'private fun findMessageEditor(items: List<NodeItem>): NodeItem? =',
]
for m in required:
    if m not in s:
        raise SystemExit("v48 wrong base: "+m)

state_old='''    private var idNeighborhood=""; private var idCageText=""; private var idHeight=0
'''
state_new='''    private var idNeighborhood=""; private var idCageText=""; private var idHeight=0
    private var idEditorFastV48=false; private var idEditorFallbackV48=false
    private var idEditorVisitedV48=0; private var idEditorLookupMsV48=0L
'''
if state_old not in s:
    raise SystemExit("v48 image diag state anchor missing")
s=s.replace(state_old,state_new,1)

send_old='''        val tdSc = if(tdOn) SystemClock.elapsedRealtime() else 0L
        val idSc = if(idOn) SystemClock.elapsedRealtime() else 0L
        val items = collectNodeItems(root)
        if(tdOn && tdSc>0L) tdSendCollect += SystemClock.elapsedRealtime()-tdSc
        if(idOn && idSc>0L) idSendCollect += SystemClock.elapsedRealtime()-idSc

        val editor = findMessageEditor(items)
        if(tdOn && editor!=null && tdEditor==0L) tdEditor=SystemClock.elapsedRealtime()
        if(idOn && editor!=null && idEditor==0L) idEditor=SystemClock.elapsedRealtime()
        if (editor == null) {
            holdRouteUntilChatOpen(route, "O campo de mensagem ainda nao apareceu.")
            return
        }
'''
send_new='''        val editorLookupStarted = SystemClock.elapsedRealtime()
        val fastEditorV48 = findMessageEditorFastV48(root)
        var editorFallbackV48 = false
        val editor = if (fastEditorV48 != null) {
            NodeItem(
                text = "",
                rect = Rect(fastEditorV48.rect),
                className = "android.widget.EditText",
                clickable = false,
                editable = true,
                node = fastEditorV48.node
            )
        } else {
            editorFallbackV48 = true
            findMessageEditor(collectNodeItems(root))
        }
        val editorLookupMs = SystemClock.elapsedRealtime() - editorLookupStarted

        if(tdOn) tdSendCollect += editorLookupMs
        if(idOn){
            idSendCollect += editorLookupMs
            idEditorFastV48 = fastEditorV48 != null
            idEditorFallbackV48 = editorFallbackV48
            idEditorVisitedV48 = fastEditorV48?.visited ?: 0
            idEditorLookupMsV48 = editorLookupMs
        }

        if(tdOn && editor!=null && tdEditor==0L) tdEditor=SystemClock.elapsedRealtime()
        if(idOn && editor!=null && idEditor==0L) idEditor=SystemClock.elapsedRealtime()
        if (editor == null) {
            holdRouteUntilChatOpen(route, "O campo de mensagem ainda nao apareceu.")
            return
        }
'''
if send_old not in s:
    raise SystemExit("v48 send collect/editor block missing")
s=s.replace(send_old,send_new,1)

helper_anchor='''    private fun findMessageEditor(items: List<NodeItem>): NodeItem? =
'''
helper='''    private data class EditorFastHitV48(
        val node: AccessibilityNodeInfo,
        val rect: Rect,
        val visited: Int
    )

    private fun findMessageEditorFastV48(root: AccessibilityNodeInfo): EditorFastHitV48? {
        val screenHeight = resources.displayMetrics.heightPixels
        val lowerLimit = (screenHeight * 0.58f).toInt()
        val queue = java.util.ArrayDeque<AccessibilityNodeInfo>()
        queue.add(root)
        var visited = 0
        var bestNode: AccessibilityNodeInfo? = null
        var bestRect: Rect? = null

        while (queue.isNotEmpty() && visited < 512) {
            val node = queue.removeFirst()
            visited++

            val editable = try { node.isEditable } catch (_: Throwable) { false }
            val isEditText = if (editable) {
                true
            } else {
                try { node.className?.toString() == "android.widget.EditText" } catch (_: Throwable) { false }
            }

            if (isEditText) {
                val rect = Rect()
                try { node.getBoundsInScreen(rect) } catch (_: Throwable) {}
                if (!rect.isEmpty && rect.bottom >= lowerLimit) {
                    // WhatsApp normalmente expoe um unico editor na parte inferior.
                    // Retorna imediatamente: evita percorrer o restante da arvore.
                    return EditorFastHitV48(node, rect, visited)
                }
                if (!rect.isEmpty && (bestRect == null || rect.bottom > bestRect!!.bottom)) {
                    bestNode = node
                    bestRect = rect
                }
            }

            val count = try { node.childCount } catch (_: Throwable) { 0 }
            for (i in 0 until count) {
                val child = try { node.getChild(i) } catch (_: Throwable) { null }
                if (child != null) queue.addLast(child)
            }
        }

        val n = bestNode
        val r = bestRect
        return if (n != null && r != null) EditorFastHitV48(n, r, visited) else null
    }

'''
if helper_anchor not in s:
    raise SystemExit("v48 helper anchor missing")
s=s.replace(helper_anchor,helper+helper_anchor,1)

begin_old='''        idNeighborhood=""; idCageText=""
'''
begin_new='''        idNeighborhood=""; idCageText=""
        idEditorFastV48=false; idEditorFallbackV48=false; idEditorVisitedV48=0; idEditorLookupMsV48=0L
'''
if begin_old not in s:
    raise SystemExit("v48 idBegin anchor missing")
s=s.replace(begin_old,begin_new,1)

report_old='''            appendLine("[${idA(idEditor)}] Editor encontrado | collectEnvio=${idSendCollect}ms")
'''
report_new='''            appendLine("[${idA(idEditor)}] Editor encontrado | collectEnvio=${idSendCollect}ms")
            appendLine("editorFastV48=hit=${idEditorFastV48} | fallback=${idEditorFallbackV48} | visited=${idEditorVisitedV48} | lookup=${idEditorLookupMsV48}ms")
'''
if report_old not in s:
    raise SystemExit("v48 image report editor anchor missing")
s=s.replace(report_old,report_new,1)

s=s.replace(
    '===== DIAGNOSTICO IMAGEM v18 | V47 CLEAN FAST + V46 9 BAIRROS =====',
    '===== DIAGNOSTICO IMAGEM v19 | V48 EDITOR FAST PATH + V47 CLEAN FAST =====',
    1
)

for m in [
    'private fun findMessageEditorFastV48(',
    'editorFastV48=hit=',
    'findMessageEditor(collectNodeItems(root))',
    'waitForImageDirectSendReadyV8(',
    'waitForTextDirectSendReadyV5(',
    '7 to "Mata da Praia"',
    '8 to "Republica"',
    '===== DIAGNOSTICO IMAGEM v19 | V48 EDITOR FAST PATH + V47 CLEAN FAST =====',
]:
    if m not in s:
        raise SystemExit("v48 verify failed: "+m)

S.write_text(s,encoding="utf-8")
print("v48 EDITOR FAST PATH applied: lightweight editable-node BFS first, full-tree fallback preserved")
