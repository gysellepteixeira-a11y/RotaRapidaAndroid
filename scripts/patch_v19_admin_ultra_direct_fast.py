from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

start = s.find('    private fun waitForAdminUltraSendReady(')
end = s.find('    private fun currentEditorText(items: List<NodeItem>): String {', start)
if start < 0 or end < 0:
    raise SystemExit('ADMIN ULTRA DIRECT: helper 10/6 nao encontrado')

helper = r'''    private fun findAdminUltraSendNodeFast(
        root: AccessibilityNodeInfo,
        editorRect: Rect
    ): AccessibilityNodeInfo? {
        val w = resources.displayMetrics.widthPixels
        val h = resources.displayMetrics.heightPixels
        val editorY = editorRect.centerY()
        val yTolerance = maxOf(70, (h * 0.06f).toInt())
        val queries = arrayOf("Enviar", "Send")

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

                val merged = buildString {
                    node.text?.toString()?.let { append(it) }
                    node.contentDescription?.toString()?.let {
                        if (isNotEmpty()) append(' ')
                        append(it)
                    }
                }
                val n = RouteParser.normalize(merged)
                val namedSend =
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

        return null
    }

    private fun verifyAdminUltraFast(
        route: RouteResult,
        editorNode: AccessibilityNodeInfo,
        clickedAt: Long,
        poll: Int
    ) {
        if (!processing) return

        val pollDelayMs = 8L
        val maxFastPolls = 8

        var editableNode: AccessibilityNodeInfo? = null

        try {
            if (editorNode.refresh() && editorNode.isEditable) {
                editableNode = editorNode
            }
        } catch (_: Throwable) {
            // O WhatsApp pode recriar o editor depois do clique.
        }

        if (editableNode == null) {
            try {
                val root = rootInActiveWindow
                val focused = root?.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
                if (focused != null && focused.isEditable) {
                    editableNode = focused
                }
            } catch (_: Throwable) {
                // Cai no fallback completo abaixo.
            }
        }

        if (editableNode != null) {
            val raw = editableNode.text?.toString().orEmpty()
            if (raw.isBlank()) {
                val confirmMs = SystemClock.elapsedRealtime() - clickedAt
                Prefs.setStatus(
                    this,
                    "ADMIN ULTRA CONFIRM FAST: campo vazio em ${confirmMs}ms | polls=$poll"
                )
                markSent(route)
                return
            }
        }

        if (poll < maxFastPolls) {
            handler.postDelayed(
                { verifyAdminUltraFast(route, editorNode, clickedAt, poll + 1) },
                pollDelayMs
            )
            return
        }

        // Fallback seguro: usa a confirmacao completa existente, SEM novo clique.
        verifySendResult(route, 0, 0)
    }

    private fun waitForAdminUltraSendReady(
        route: RouteResult,
        startedAt: Long,
        poll: Int,
        editorNode: AccessibilityNodeInfo,
        editorRect: Rect
    ) {
        if (!processing) return

        val pollDelayMs = 4L
        val maxPolls = 70
        val root = rootInActiveWindow

        if (root == null) {
            if (poll < maxPolls) {
                handler.postDelayed(
                    { waitForAdminUltraSendReady(route, startedAt, poll + 1, editorNode, editorRect) },
                    pollDelayMs
                )
            } else {
                holdRouteUntilChatOpen(route, "ADMIN ULTRA DIRECT: perdi a janela antes do envio.")
            }
            return
        }

        val sendNode = findAdminUltraSendNodeFast(root, editorRect)
        if (sendNode != null) {
            val waited = SystemClock.elapsedRealtime() - startedAt
            speedDiagnosticSendAttempts = 1
            speedDiagnosticSendMethod = "ACTION_CLICK"

            if (clickNodeOrParent(sendNode)) {
                val clickedAt = SystemClock.elapsedRealtime()
                Prefs.setStatus(
                    this,
                    "ADMIN ULTRA DIRECT: Enviar pronto em ${waited}ms | polls=$poll | clique direto 1x"
                )
                handler.postDelayed(
                    { verifyAdminUltraFast(route, editorNode, clickedAt, 0) },
                    8L
                )
                return
            }

            // O no apareceu mas recusou ACTION_CLICK. Como nenhum clique foi aceito,
            // podemos usar a rotina completa existente uma unica vez com seguranca.
            tryClickSend(route, 0)
            return
        }

        if (poll < maxPolls) {
            handler.postDelayed(
                { waitForAdminUltraSendReady(route, startedAt, poll + 1, editorNode, editorRect) },
                pollDelayMs
            )
            return
        }

        // Nao achou o botao pela busca direta. Usa SEND READY completo como fallback.
        waitForSendButtonReady(route, startedAt, 0)
    }

'''

s = s[:start] + helper + s[end:]

old_call = '''        waitForAdminUltraSendReady(
            route,
            SystemClock.elapsedRealtime(),
            0,
            false
        )
'''
new_call = '''        waitForAdminUltraSendReady(
            route,
            SystemClock.elapsedRealtime(),
            0,
            editor.node,
            Rect(editor.rect)
        )
'''
if old_call not in s:
    raise SystemExit('ADMIN ULTRA DIRECT: chamada antiga 10/6 nao encontrada')
s = s.replace(old_call, new_call, 1)

s = s.replace(
    '"ADMIN ULTRA: liberado + preenchido em ${fillMs}ms | watch=10ms | ready=6ms"',
    '"ADMIN ULTRA DIRECT: liberado + preenchido em ${fillMs}ms | watch=10ms | ready=4ms"',
    1
)

prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND READY ADMIN ULTRA 10-6 =====',
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND READY ADMIN ULTRA DIRECT FAST ====='
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")
print('ADMIN ULTRA DIRECT FAST aplicado: busca direta do Enviar + confirmacao rapida sem segundo clique')
