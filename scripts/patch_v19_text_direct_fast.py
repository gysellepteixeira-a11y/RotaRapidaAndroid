from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

# A/B ISOLADO SOBRE MEDIA10 STATUSLEAN + ADMIN ULTRA DIRECT FAST
# - imagem nao muda
# - admin unlock nao muda
# - rota de texto tenta primeiro o payload do AccessibilityEvent
# - se o evento nao trouxer rota completa, cai no fluxo normal atual
# - quando ha editor, reutiliza o editor ja encontrado e busca Enviar direto
# - nenhum Prefs.setStatus antes do clique no caminho rapido

required = [
    'private fun findAdminUltraSendNodeFast(',
    'private fun verifyAdminUltraFast(',
    'private const val DIRECT_MEDIASTORE_WATCH_MS = 10L',
    'private const val PENDING_ROUTE_SEND_WATCH_MS = 10L',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'TEXT DIRECT FAST: dependencia ausente: {marker}')

anchor = '    private fun currentEditorText(items: List<NodeItem>): String {\n'
if anchor not in s:
    raise SystemExit('TEXT DIRECT FAST: currentEditorText nao encontrado')

helper = r'''    private fun waitForTextDirectSendReady(
        route: RouteResult,
        eventStartedAt: Long,
        fillFinishedAt: Long,
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
                    {
                        waitForTextDirectSendReady(
                            route,
                            eventStartedAt,
                            fillFinishedAt,
                            poll + 1,
                            editorNode,
                            editorRect
                        )
                    },
                    pollDelayMs
                )
            } else {
                holdRouteUntilChatOpen(
                    route,
                    "TEXT DIRECT: perdi a janela antes do botao Enviar aparecer."
                )
            }
            return
        }

        val sendNode = findAdminUltraSendNodeFast(root, editorRect)
        if (sendNode != null) {
            speedDiagnosticSendAttempts = 1

            if (clickNodeOrParent(sendNode)) {
                val clickedAt = SystemClock.elapsedRealtime()
                val eventToClick = clickedAt - eventStartedAt
                val fillToClick = clickedAt - fillFinishedAt
                speedDiagnosticSendMethod = "TEXT_DIRECT_${eventToClick}ms"

                // Log somente DEPOIS do clique para nao atrasar o envio real.
                Prefs.setStatus(
                    this,
                    "TEXT DIRECT: clique em ${eventToClick}ms desde evento | " +
                        "pos-fill=${fillToClick}ms | polls=$poll | clique direto 1x"
                )

                handler.postDelayed(
                    { verifyAdminUltraFast(route, editorNode, clickedAt, 0) },
                    8L
                )
                return
            }

            // O no apareceu mas recusou ACTION_CLICK. Nenhum clique foi aceito,
            // entao o fallback atual pode tentar uma unica vez com seguranca.
            tryClickSend(route, 0)
            return
        }

        if (poll < maxPolls) {
            handler.postDelayed(
                {
                    waitForTextDirectSendReady(
                        route,
                        eventStartedAt,
                        fillFinishedAt,
                        poll + 1,
                        editorNode,
                        editorRect
                    )
                },
                pollDelayMs
            )
            return
        }

        // WhatsApp nao expos o botao nomeado pela busca direta.
        // Mantem o SEND READY existente como fallback, sem perder compatibilidade.
        waitForSendButtonReady(route, fillFinishedAt, 0)
    }

    private fun tryTextDirectFast(event: AccessibilityEvent): Boolean {
        val eventStartedAt = SystemClock.elapsedRealtime()

        val eventTexts = ArrayList<String>(8)
        event.text?.forEach { value ->
            val text = value?.toString().orEmpty().trim()
            if (text.isNotBlank()) eventTexts.add(text)
        }

        event.contentDescription?.toString()?.trim()?.let { text ->
            if (text.isNotBlank()) eventTexts.add(text)
        }

        try {
            event.source?.text?.toString()?.trim()?.let { text ->
                if (text.isNotBlank()) eventTexts.add(text)
            }
            event.source?.contentDescription?.toString()?.trim()?.let { text ->
                if (text.isNotBlank()) eventTexts.add(text)
            }
        } catch (_: Throwable) {
            // source pode ficar stale entre o evento e a leitura; segue com event.text.
        }

        if (eventTexts.isEmpty()) return false

        val route = RouteParser.parsePlainTexts(eventTexts) ?: return false
        if (isDuplicate(route)) return true

        val root = rootInActiveWindow ?: return false
        val items = collectNodeItems(root)
        val editor = findMessageEditor(items)

        // Grupo fechado pelo admin: ja guarda a rota sem esperar os 12ms do
        // analyzeCurrentWindow. O ADMIN ULTRA DIRECT FAST existente cuidara do envio.
        if (editor == null) {
            val adminLockedNow = isAdminLockedGroup(items)
            if (!adminLockedNow && !adminLockedConversationActive) return false

            processing = true
            currentStartedAt = eventStartedAt
            speedDiagnosticSendStartedAt = eventStartedAt
            speedDiagnosticSendAttempts = 0
            speedDiagnosticSendMethod = "TEXT_DIRECT_PENDING"
            holdRouteUntilChatOpen(
                route,
                "TEXT DIRECT: rota capturada direto do evento; campo ainda nao apareceu."
            )
            return true
        }

        processing = true
        currentStartedAt = eventStartedAt
        speedDiagnosticSendStartedAt = eventStartedAt
        speedDiagnosticSendAttempts = 0
        speedDiagnosticSendMethod = "TEXT_DIRECT"
        pendingRoute = route

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
            holdRouteUntilChatOpen(
                route,
                "TEXT DIRECT: falha ao preencher; aguardando o campo ficar pronto."
            )
            return true
        }

        val fillFinishedAt = SystemClock.elapsedRealtime()
        waitForTextDirectSendReady(
            route,
            eventStartedAt,
            fillFinishedAt,
            0,
            editor.node,
            Rect(editor.rect)
        )
        return true
    }

'''

if 'private fun tryTextDirectFast(' not in s:
    s = s.replace(anchor, helper + anchor, 1)

old_tail = '''        inspectImageHint(event)

        if (processing) return
        scheduleAnalyze(12L)
'''
new_tail = '''        if (processing) return

        // A primeira tela apos PROCURAR NOVAMENTE e apenas referencia. Nao usa
        // o fast path para nao interpretar rota velha ainda visivel como nova.
        if (!Prefs.needsPrime(this) && tryTextDirectFast(event)) return

        inspectImageHint(event)
        scheduleAnalyze(12L)
'''
if old_tail not in s:
    raise SystemExit('TEXT DIRECT FAST: cauda de onAccessibilityEvent nao encontrada')
s = s.replace(old_tail, new_tail, 1)

old_header = '===== DIAGNOSTICO IMAGEM v0.19 MEDIA10 STATUSLEAN ADMIN ULTRA DIRECT FAST ====='
new_header = '===== DIAGNOSTICO IMAGEM v0.19 MEDIA10 STATUSLEAN ADMIN ULTRA DIRECT FAST TEXT DIRECT FAST ====='
if old_header not in prefs:
    raise SystemExit('TEXT DIRECT FAST: cabecalho da base atual nao encontrado')
prefs = prefs.replace(old_header, new_header, 1)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")
print('TEXT DIRECT FAST aplicado: evento -> parse -> editor reutilizado -> Enviar direto; fallback antigo preservado')
