from pathlib import Path
import sys

S = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
if not S.exists():
    sys.exit(f"Erro: {S} nao encontrado.")

s = S.read_text(encoding="utf-8").replace("\r\n", "\n")
balance_before = s.count("{") - s.count("}")

for req in [
    "private fun findMessageEditorFastV48(",
    "private fun trySendPendingRouteIfChatOpen(): Boolean {",
    "private fun findAdminUltraSendNodeFast(",
    "private fun waitForAdminUltraSendReady(",
]:
    if req not in s:
        sys.exit(f"Erro V69: pre-requisito ausente no codigo pos-V68: {req}")

# 1. Estado de telemetria + helper leve para detectar o editor no grupo fechado
pending_anchor = "    private fun trySendPendingRouteIfChatOpen(): Boolean {\n"
pending_helper = '''    private var adminUltraUsedV69: Boolean = false
    private var adminUltraCycleStartAtV69: Long = 0L
    private var adminUltraEditorLookupMsV69: Long = -1L
    private var adminUltraEditorSourceV69: String = "--"
    private var adminUltraFillMsV69: Long = -1L
    private var adminUltraSendSourceV69: String = "--"
    private var adminUltraReadyMsV69: Long = -1L
    private var adminUltraPollsV69: Int = -1
    private var adminUltraClickActionMsV69: Long = -1L
    private var adminUltraTotalMsV69: Long = -1L

    private fun findPendingEditorFastV69(root: AccessibilityNodeInfo): EditorFastHitV48? {
        val lowerLimit = (resources.displayMetrics.heightPixels * 0.50f).toInt()
        val viewIds = arrayOf("com.whatsapp:id/entry", "com.whatsapp.w4b:id/entry")
        for (viewId in viewIds) {
            val nodes: List<AccessibilityNodeInfo> = try {
                root.findAccessibilityNodeInfosByViewId(viewId) ?: emptyList()
            } catch (_: Throwable) {
                emptyList()
            }
            for (node in nodes) {
                val editable = try {
                    node.isEditable || node.className?.toString() == "android.widget.EditText"
                } catch (_: Throwable) {
                    false
                }
                if (!editable) continue
                val visible = try { node.isVisibleToUser } catch (_: Throwable) { true }
                if (!visible) continue
                val rect = Rect()
                try { node.getBoundsInScreen(rect) } catch (_: Throwable) {}
                if (!rect.isEmpty && rect.bottom >= lowerLimit) {
                    adminUltraEditorSourceV69 = "id"
                    return EditorFastHitV48(node, rect, 1)
                }
            }
        }
        val fast = findMessageEditorFastV48(root)
        if (fast != null) {
            adminUltraEditorSourceV69 = "bfs(${fast.visited})"
            return fast
        }
        return null
    }

'''
if "private fun findPendingEditorFastV69(" not in s:
    s = s.replace(pending_anchor, pending_helper + pending_anchor, 1)

# 2. Substituicao cirurgica da busca do editor e medicao de setText em trySendPendingRouteIfChatOpen
p_start = s.find(pending_anchor)
p_end = s.find("    private fun sendRouteInCurrentChat(", p_start)
if p_start < 0 or p_end < 0:
    sys.exit("Erro V69: limites de trySendPendingRouteIfChatOpen nao encontrados.")

pending_block = s[p_start:p_end]
old_lookup = '''        val root = rootInActiveWindow ?: return false
        val items = collectNodeItems(root)
        val editor = findMessageEditor(items) ?: return false

        val releasedAt = SystemClock.elapsedRealtime()'''
new_lookup = '''        val root = rootInActiveWindow ?: return false
        val lookupStartedAtV69 = SystemClock.elapsedRealtime()
        val editor = findPendingEditorFastV69(root) ?: return false

        val releasedAt = SystemClock.elapsedRealtime()
        adminUltraUsedV69 = true
        adminUltraCycleStartAtV69 = lookupStartedAtV69
        adminUltraEditorLookupMsV69 = releasedAt - lookupStartedAtV69
        adminUltraFillMsV69 = -1L
        adminUltraSendSourceV69 = "--"
        adminUltraReadyMsV69 = -1L
        adminUltraPollsV69 = -1
        adminUltraClickActionMsV69 = -1L
        adminUltraTotalMsV69 = -1L'''

if old_lookup not in pending_block:
    sys.exit("Erro V69: bloco collectNodeItems dentro de trySendPendingRouteIfChatOpen nao encontrado.")
pending_block = pending_block.replace(old_lookup, new_lookup, 1)

wait_call_anchor = "        waitForAdminUltraSendReady(\n"
if pending_block.count(wait_call_anchor) != 1:
    sys.exit(f"Erro V69: chamada waitForAdminUltraSendReady inesperada (count={pending_block.count(wait_call_anchor)}).")
pending_block = pending_block.replace(
    wait_call_anchor,
    "        adminUltraFillMsV69 = SystemClock.elapsedRealtime() - releasedAt\n" + wait_call_anchor,
    1,
)

s = s[:p_start] + pending_block + s[p_end:]

# 3. Busca direta por viewId do botao Enviar + registro da fonte (id vs text)
send_start = s.find("    private fun findAdminUltraSendNodeFast(")
send_end = s.find("    private fun verifyAdminUltraFast(", send_start)
if send_start < 0 or send_end < 0:
    sys.exit("Erro V69: limites de findAdminUltraSendNodeFast nao encontrados.")

send_block = s[send_start:send_end]
text_return_anchor = "                    return node\n"
if send_block.count(text_return_anchor) != 1:
    sys.exit("Erro V69: retorno da busca textual em findAdminUltraSendNodeFast nao e unico.")
send_block = send_block.replace(
    text_return_anchor,
    '                    adminUltraSendSourceV69 = "text"\n                    return node\n',
    1,
)

queries_anchor = '        val queries = arrayOf("Enviar", "Send")\n'
send_id_fast = '''        val sendIds = arrayOf("com.whatsapp:id/send", "com.whatsapp.w4b:id/send")
        for (sendId in sendIds) {
            val idNodes: List<AccessibilityNodeInfo> = try {
                root.findAccessibilityNodeInfosByViewId(sendId) ?: emptyList()
            } catch (_: Throwable) {
                emptyList()
            }
            for (node in idNodes) {
                val visible = try { node.isVisibleToUser } catch (_: Throwable) { true }
                val enabled = try { node.isEnabled } catch (_: Throwable) { true }
                if (!visible || !enabled) continue
                val rect = Rect()
                try { node.getBoundsInScreen(rect) } catch (_: Throwable) {}
                if (rect.isEmpty) continue
                val merged = buildString {
                    node.text?.toString()?.let { append(it) }
                    node.contentDescription?.toString()?.let {
                        if (isNotEmpty()) append(' ')
                        append(it)
                    }
                }
                val n = RouteParser.normalize(merged)
                val namedSend =
                    n.isBlank() ||
                    "enviar" in n ||
                    n == "send" ||
                    "send message" in n
                if (
                    namedSend &&
                    rect.right >= (w * 0.78f).toInt() &&
                    kotlin.math.abs(rect.centerY() - editorY) <= yTolerance
                ) {
                    adminUltraSendSourceV69 = "id"
                    return node
                }
            }
        }

'''
if queries_anchor not in send_block:
    sys.exit("Erro V69: ancora queries em findAdminUltraSendNodeFast nao encontrada.")
if "com.whatsapp:id/send" not in send_block:
    send_block = send_block.replace(queries_anchor, send_id_fast + queries_anchor, 1)
s = s[:send_start] + send_block + s[send_end:]

# 4. Capturar ready, polls, click e total sem depender de Prefs.setStatus removido pela V47
w_start = s.find("    private fun waitForAdminUltraSendReady(")
w_end = s.find("\n    private fun ", w_start + 1)
if w_start < 0 or w_end < 0:
    sys.exit("Erro V69: limites de waitForAdminUltraSendReady nao encontrados.")

wait_block = s[w_start:w_end]
click_sig = "if (clickNodeOrParent(sendNode)) {"
if wait_block.count(click_sig) != 1:
    sys.exit(f"Erro V69: clickNodeOrParent(sendNode) inesperado em waitForAdminUltraSendReady (count={wait_block.count(click_sig)}).")

idx = wait_block.find(click_sig)
line_start = wait_block.rfind("\n", 0, idx) + 1
indent = wait_block[line_start:idx]
if indent.strip():
    sys.exit(f"Erro V69: prefixo inesperado antes de clickNodeOrParent(sendNode): {indent!r}")
line_end = wait_block.find("\n", idx)
if line_end < 0:
    sys.exit("Erro V69: fim de linha de clickNodeOrParent(sendNode) nao encontrado.")

injected_before = f"{indent}val clickStartV69 = SystemClock.elapsedRealtime()\n"
injected_inside = (
    f"{indent}    val clickedAtV69 = SystemClock.elapsedRealtime()\n"
    f"{indent}    adminUltraReadyMsV69 = clickStartV69 - startedAt\n"
    f"{indent}    adminUltraPollsV69 = poll\n"
    f"{indent}    adminUltraClickActionMsV69 = clickedAtV69 - clickStartV69\n"
    f"{indent}    adminUltraTotalMsV69 = if (adminUltraCycleStartAtV69 > 0L) {{\n"
    f"{indent}        clickedAtV69 - adminUltraCycleStartAtV69\n"
    f"{indent}    }} else {{\n"
    f"{indent}        clickedAtV69 - startedAt\n"
    f"{indent}    }}\n"
)
wait_block = (
    wait_block[:line_start]
    + injected_before
    + wait_block[line_start:line_end + 1]
    + injected_inside
    + wait_block[line_end + 1:]
)
s = s[:w_start] + wait_block + s[w_end:]

# 5. Zerar contadores V69 ao iniciar um novo ciclo de diagnostico de imagem (idBegin)
reset_anchor = "        idEditorFastV48=false; idEditorFallbackV48=false; idEditorVisitedV48=0; idEditorLookupMsV48=0L\n"
reset_v69 = (
    '        adminUltraUsedV69=false; adminUltraCycleStartAtV69=0L; adminUltraEditorLookupMsV69=-1L; '
    'adminUltraEditorSourceV69="--"; adminUltraFillMsV69=-1L; adminUltraSendSourceV69="--"; '
    'adminUltraReadyMsV69=-1L; adminUltraPollsV69=-1; adminUltraClickActionMsV69=-1L; adminUltraTotalMsV69=-1L\n'
)
if reset_anchor not in s:
    sys.exit("Erro V69: ancora de reset V48 em idBegin nao encontrada.")
s = s.replace(reset_anchor, reset_anchor + reset_v69, 1)

# 6. Fixar a linha V69 GRUPO FECHADO no relatorio final logo apos V68 FOTO PRIORITARIA
v68_anchor = '            appendLine("V68 FOTO PRIORITARIA | textoIgnorado=$photoSuppressedTextV68 | $photoEvidenceV68")\n'
v69_report = '''            if (adminUltraUsedV69) {
                appendLine("V69 GRUPO FECHADO | total=${adminUltraTotalMsV69}ms | lookup=${adminUltraEditorLookupMsV69}ms(${adminUltraEditorSourceV69}) | setText=${adminUltraFillMsV69}ms | ready=${adminUltraReadyMsV69}ms(${adminUltraSendSourceV69},polls=${adminUltraPollsV69}) | click=${adminUltraClickActionMsV69}ms")
            } else {
                appendLine("V69 GRUPO FECHADO | usado=false")
            }
'''
if s.count(v68_anchor) != 1:
    sys.exit(f"Erro V69: ancora V68 FOTO PRIORITARIA inesperada (count={s.count(v68_anchor)}).")
s = s.replace(v68_anchor, v68_anchor + v69_report, 1)

# 7. Validacoes de integridade estrutural
balance_after = s.count("{") - s.count("}")
if balance_after != balance_before:
    sys.exit(f"Erro V69: saldo de chaves alterado ({balance_before} -> {balance_after}).")

for fn in [
    "fun trySendPendingRouteIfChatOpen(",
    "fun waitForAdminUltraSendReady(",
    "fun sendRouteWhenChatReady(",
]:
    cnt = s.count(fn)
    if cnt != 1:
        sys.exit(f"Erro V69: contagem inesperada para {fn}: {cnt}")

S.write_text(s, encoding="utf-8")
print("Patch V69 aplicado com sucesso (compativel com V47 clean fast + bloco V69 GRUPO FECHADO).")