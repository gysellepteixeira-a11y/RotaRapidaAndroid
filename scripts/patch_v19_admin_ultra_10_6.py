from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

old_watch = '        private const val PENDING_ROUTE_SEND_WATCH_MS = 120L\n'
if old_watch not in s:
    raise SystemExit('ADMIN ULTRA: watcher 120ms nao encontrado')
s = s.replace(old_watch, '        private const val PENDING_ROUTE_SEND_WATCH_MS = 10L\n', 1)

anchor = '    private fun currentEditorText(items: List<NodeItem>): String {\n'
if anchor not in s:
    raise SystemExit('ADMIN ULTRA: currentEditorText nao encontrado')

helper = r'''    private fun waitForAdminUltraSendReady(
        route: RouteResult,
        startedAt: Long,
        poll: Int,
        textSeenBefore: Boolean = false
    ) {
        if (!processing) return

        val pollDelayMs = 6L
        val maxPolls = 50
        val root = rootInActiveWindow

        if (root == null) {
            if (poll < maxPolls) {
                handler.postDelayed(
                    { waitForAdminUltraSendReady(route, startedAt, poll + 1, textSeenBefore) },
                    pollDelayMs
                )
            } else {
                holdRouteUntilChatOpen(route, "ADMIN ULTRA: perdi a janela antes do envio.")
            }
            return
        }

        val items = collectNodeItems(root)
        val editor = findMessageEditor(items)

        if (editor == null) {
            if (poll < maxPolls) {
                handler.postDelayed(
                    { waitForAdminUltraSendReady(route, startedAt, poll + 1, textSeenBefore) },
                    pollDelayMs
                )
            } else {
                holdRouteUntilChatOpen(route, "ADMIN ULTRA: campo indisponivel antes do envio.")
            }
            return
        }

        val rawText = editor.node.text?.toString().orEmpty()
        val normalizedText = RouteParser.normalize(rawText)
        val textVisible = rawText.isNotBlank() && (
            "felipe lima de castilho" in normalizedText ||
            "1347515" in normalizedText ||
            "gaiola" in normalizedText
        )
        val textSeen = textSeenBefore || textVisible

        if (textVisible && namedSendButtonReady(items, editor.rect)) {
            val waited = SystemClock.elapsedRealtime() - startedAt
            Prefs.setStatus(
                this,
                "ADMIN ULTRA READY: Enviar pronto em ${waited}ms | polls=$poll | clicando 1x..."
            )
            tryClickSend(route, 0)
            return
        }

        if (poll < maxPolls) {
            handler.postDelayed(
                { waitForAdminUltraSendReady(route, startedAt, poll + 1, textSeen) },
                pollDelayMs
            )
            return
        }

        if (textSeen || textVisible) {
            val waited = SystemClock.elapsedRealtime() - startedAt
            Prefs.setStatus(
                this,
                "ADMIN ULTRA READY: fallback em ${waited}ms | clicando 1x..."
            )
            tryClickSend(route, 0)
        } else {
            holdRouteUntilChatOpen(route, "ADMIN ULTRA: texto nao apareceu no editor.")
        }
    }

'''

if 'private fun waitForAdminUltraSendReady(' not in s:
    s = s.replace(anchor, helper + anchor, 1)

start = s.find('    private fun trySendPendingRouteIfChatOpen(): Boolean {')
end = s.find('    private fun sendRouteInCurrentChat(route: RouteResult) {', start)
if start < 0 or end < 0:
    raise SystemExit('ADMIN ULTRA: pending send nao encontrado')

new_pending = r'''    private fun trySendPendingRouteIfChatOpen(): Boolean {
        val route = pendingRoute ?: return false
        if (alertSequenceRunning || processing) return false

        val root = rootInActiveWindow ?: return false
        val items = collectNodeItems(root)
        val editor = findMessageEditor(items) ?: return false

        val releasedAt = SystemClock.elapsedRealtime()
        processing = true
        currentStartedAt = releasedAt
        speedDiagnosticSendStartedAt = releasedAt
        speedDiagnosticSendAttempts = 0
        speedDiagnosticSendMethod = "nenhum"

        val message = buildMessage(route.cage)
        val args = Bundle().apply {
            putCharSequence(
                AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                message
            )
        }

        val setOk = editor.node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        )

        if (!setOk) {
            holdRouteUntilChatOpen(route, "ADMIN ULTRA: falha ao preencher o campo.")
            return false
        }

        val fillMs = SystemClock.elapsedRealtime() - releasedAt
        Prefs.setStatus(
            this,
            "ADMIN ULTRA: liberado + preenchido em ${fillMs}ms | watch=10ms | ready=6ms"
        )

        waitForAdminUltraSendReady(
            route,
            SystemClock.elapsedRealtime(),
            0,
            false
        )
        return true
    }

'''

s = s[:start] + new_pending + s[end:]
prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND READY =====',
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND READY ADMIN ULTRA 10-6 ====='
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")
print('ADMIN ULTRA 10/6 aplicado')
