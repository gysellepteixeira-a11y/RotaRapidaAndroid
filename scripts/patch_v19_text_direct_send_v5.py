from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s = S.read_text(encoding='utf-8')

required = [
    '===== DIAGNOSTICO TEXTO v4 | OLD BASE + TEXT FIRST + RAW DELTA =====',
    'private fun findAdminUltraSendNodeFast(',
    'private fun waitForSendButtonReady(',
    'private var tdReady=0L',
    'private var tdClicked=0L',
    'private fun clickNodeOrParent(',
]
for marker in required:
    if marker not in s:
        raise SystemExit('TEXT DIRECT SEND v5 wrong base / missing marker: ' + marker)

anchor = '    private fun currentEditorText(items: List<NodeItem>): String {\n'
if anchor not in s:
    raise SystemExit('TEXT DIRECT SEND v5: currentEditorText anchor not found')

helper = r'''    private fun waitForTextDirectSendReadyV5(
        route: RouteResult,
        startedAt: Long,
        poll: Int,
        editorRect: Rect
    ) {
        if (!processing) return

        if (tdOn && tdReady == 0L) tdReady = startedAt

        val pollDelayMs = 4L
        val maxPolls = 70
        val root = rootInActiveWindow

        if (root == null) {
            if (poll < maxPolls) {
                handler.postDelayed(
                    { waitForTextDirectSendReadyV5(route, startedAt, poll + 1, editorRect) },
                    pollDelayMs
                )
            } else {
                // Fallback seguro e identico ao envio antigo; nenhum clique foi aceito.
                waitForSendButtonReady(route, startedAt, 0)
            }
            return
        }

        // Busca direta pelo no nomeado Enviar/Send, reutilizando o helper que ja
        // foi validado no ADMIN ULTRA DIRECT. Nao coleta a arvore inteira aqui.
        val sendNode = findAdminUltraSendNodeFast(root, editorRect)
        if (sendNode != null) {
            val foundAt = SystemClock.elapsedRealtime()
            if (tdOn) {
                tdReadyFound = foundAt
                tdReadyPoll = poll
                if (tdClick == 0L) tdClick = foundAt
                tdCandidateSend = foundAt
                // Caminho direto nao usa collectNodeItems para READY/click.
                tdReadyCollect = 0L
                tdClickCollect = 0L
            }

            speedDiagnosticSendAttempts = 1
            speedDiagnosticSendMethod = "TEXT_DIRECT_V5"

            if (clickNodeOrParent(sendNode)) {
                // clickNodeOrParent ja grava tdAction/tdClicked no diagnostico.
                // Confirmacao fica fora da corrida e nao faz nenhum segundo clique.
                handler.postDelayed(
                    { verifySendResult(route, 0, 0) },
                    8L
                )
                return
            }

            // O no apareceu mas recusou ACTION_CLICK. Como nenhum clique foi
            // aceito, pode cair na rotina antiga de uma tentativa com seguranca.
            tryClickSend(route, 0)
            return
        }

        if (poll < maxPolls) {
            handler.postDelayed(
                { waitForTextDirectSendReadyV5(route, startedAt, poll + 1, editorRect) },
                pollDelayMs
            )
            return
        }

        // WhatsApp nao expos o botao pela busca direta. Preserva compatibilidade.
        waitForSendButtonReady(route, startedAt, 0)
    }

'''

if 'private fun waitForTextDirectSendReadyV5(' not in s:
    s = s.replace(anchor, helper + anchor, 1)

old_call = '''        handler.postDelayed(
            {
                waitForSendButtonReady(
                    route,
                    SystemClock.elapsedRealtime(),
                    0
                )
            },
            SEND_BUTTON_DELAY_MS
        )
'''
new_call = '''        // TEXT DIRECT SEND v5: somente rotas de texto diagnosticadas (tdOn)
        // pulam o atraso inicial e a coleta completa de SEND READY. Imagem segue
        // exatamente pelo fluxo antigo abaixo.
        if (tdOn) {
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
if old_call not in s:
    raise SystemExit('TEXT DIRECT SEND v5: standard post-fill SEND READY call not found')
s = s.replace(old_call, new_call, 1)

old_header = '===== DIAGNOSTICO TEXTO v4 | OLD BASE + TEXT FIRST + RAW DELTA ====='
new_header = '===== DIAGNOSTICO TEXTO v5 | OLD BASE + TEXT FIRST + RAW DELTA + DIRECT SEND ====='
s = s.replace(old_header, new_header, 1)

checks = [
    'private fun waitForTextDirectSendReadyV5(',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    'if (tdOn) {\n            waitForTextDirectSendReadyV5(',
    new_header,
]
for marker in checks:
    if marker not in s:
        raise SystemExit('TEXT DIRECT SEND v5 verification failed: ' + marker)

# Safety: image flow must still contain the old SEND_BUTTON_DELAY + SEND READY call.
if 'SEND_BUTTON_DELAY_MS' not in s or 'waitForSendButtonReady(' not in s:
    raise SystemExit('TEXT DIRECT SEND v5 safety failed: image fallback missing')

S.write_text(s, encoding='utf-8')
print('TEXT DIRECT SEND v5 aplicado: texto usa busca direta Enviar 4ms; imagem e fallback antigos preservados')
