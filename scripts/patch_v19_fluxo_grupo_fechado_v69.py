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

# 1. Helper leve para detectar o editor no grupo fechado sem collectNodeItems
pending_anchor = "    private fun trySendPendingRouteIfChatOpen(): Boolean {\n"
pending_helper = '''    private var adminUltraEditorSeenAtV69: Long = 0L
    private var adminUltraEditorLookupMsV69: Long = 0L
    private var adminUltraEditorSourceV69: String = "v48"

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

# 2. Substituicao cirurgica APENAS da busca do editor dentro de trySendPendingRouteIfChatOpen
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
        adminUltraEditorSeenAtV69 = releasedAt
        adminUltraEditorLookupMsV69 = releasedAt - lookupStartedAtV69'''

if old_lookup not in pending_block:
    print("--- TRECHO REAL DE trySendPendingRouteIfChatOpen ---")
    print(pending_block[:1200])
    sys.exit("Erro V69: bloco collectNodeItems dentro de trySendPendingRouteIfChatOpen nao encontrado.")

pending_block = pending_block.replace(old_lookup, new_lookup, 1)
s = s[:p_start] + pending_block + s[p_end:]

# 3. Busca direta por viewId do botao Enviar antes da busca por texto em findAdminUltraSendNodeFast
send_start = s.find("    private fun findAdminUltraSendNodeFast(")
send_end = s.find("    private fun verifyAdminUltraFast(", send_start)
if send_start < 0 or send_end < 0:
    sys.exit("Erro V69: limites de findAdminUltraSendNodeFast nao encontrados.")

send_block = s[send_start:send_end]
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
                    return node
                }
            }
        }

'''
if queries_anchor not in send_block:
    print("--- TRECHO REAL DE findAdminUltraSendNodeFast ---")
    print(send_block[:1200])
    sys.exit("Erro V69: ancora queries em findAdminUltraSendNodeFast nao encontrada.")

if "com.whatsapp:id/send" not in send_block:
    send_block = send_block.replace(queries_anchor, send_id_fast + queries_anchor, 1)
    s = s[:send_start] + send_block + s[send_end:]

# 4. Log de latencia editor->click no clique direto do grupo fechado
old_click_log = '''                val clickedAt = SystemClock.elapsedRealtime()
                Prefs.setStatus(
                    this,
                    "ADMIN ULTRA DIRECT: Enviar pronto em ${waited}ms | polls=$poll | clique direto 1x"
                )'''
new_click_log = '''                val clickedAt = SystemClock.elapsedRealtime()
                val editorToClickMsV69 = if (adminUltraEditorSeenAtV69 > 0L) {
                    clickedAt - adminUltraEditorSeenAtV69
                } else {
                    waited
                }
                Prefs.setStatus(
                    this,
                    "ADMIN ULTRA V69: editor->click=${editorToClickMsV69}ms | ready=${waited}ms | lookup=${adminUltraEditorLookupMsV69}ms(${adminUltraEditorSourceV69}) | polls=$poll | clique direto 1x"
                )'''
if old_click_log in s:
    s = s.replace(old_click_log, new_click_log, 1)
else:
    print("Aviso V69: status ADMIN ULTRA DIRECT diferente, mantendo status existente.")

# 5. Validacoes de integridade estrutural
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
print("Patch V69 fluxo grupo fechado aplicado com sucesso (viewId + V48 fastpath + telemetria editor->click).")