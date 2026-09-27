from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

# TESTE ISOLADO: SEND READY
# - mantem SEND1 + polling de confirmacao ja aplicados
# - depois de ACTION_SET_TEXT, nao clica imediatamente no alvo generico da direita
# - espera o WhatsApp expor explicitamente o botao Enviar/Send na arvore
# - consulta a cada 12ms por ate ~300ms
# - quando o botao nomeado aparece, executa UMA unica tentativa real via tryClickSend
# - se o nome nunca aparecer, usa o strict candidate atual UMA unica vez no fim
# - nao altera OCR, parser, MediaStore, Bairro ou Gaiola

# Insere helper antes de currentEditorText, que fica logo apos sendRouteInCurrentChat.
anchor = '    private fun currentEditorText(items: List<NodeItem>): String {\n'
if anchor not in s:
    raise SystemExit('send wait ready: currentEditorText nao encontrado')

helper = r'''    private fun namedSendButtonReady(
        items: List<NodeItem>,
        editorRect: Rect
    ): Boolean {
        val w = resources.displayMetrics.widthPixels
        val h = resources.displayMetrics.heightPixels
        val editorY = editorRect.centerY()
        val yTolerance = maxOf(70, (h * 0.06f).toInt())

        return items.any { item ->
            val n = RouteParser.normalize(item.text)
            val namedSend =
                "enviar" in n ||
                n == "send" ||
                "send message" in n

            namedSend &&
                item.rect.right >= (w * 0.78f).toInt() &&
                kotlin.math.abs(item.rect.centerY() - editorY) <= yTolerance
        }
    }

    private fun waitForSendButtonReady(
        route: RouteResult,
        startedAt: Long,
        poll: Int
    ) {
        if (!processing) return

        val pollDelayMs = 12L
        val maxPolls = 25

        val root = rootInActiveWindow
        if (root == null) {
            if (poll < maxPolls) {
                handler.postDelayed(
                    { waitForSendButtonReady(route, startedAt, poll + 1) },
                    pollDelayMs
                )
            } else {
                holdRouteUntilChatOpen(route, "Perdi a janela antes do botao Enviar ficar pronto.")
            }
            return
        }

        val items = collectNodeItems(root)

        // Se a mensagem sumiu antes de qualquer clique nosso, nao tenta clicar.
        if (!messageStillInEditor(items)) {
            markSent(route)
            return
        }

        val editor = findMessageEditor(items)
        if (editor == null) {
            if (poll < maxPolls) {
                handler.postDelayed(
                    { waitForSendButtonReady(route, startedAt, poll + 1) },
                    pollDelayMs
                )
            } else {
                holdRouteUntilChatOpen(route, "O campo sumiu antes do botao Enviar ficar pronto.")
            }
            return
        }

        if (namedSendButtonReady(items, editor.rect)) {
            val waited = SystemClock.elapsedRealtime() - startedAt
            Prefs.setStatus(
                this,
                "ENVIO READY: botao Enviar apareceu em ${waited}ms | polls=$poll | clicando 1x..."
            )
            tryClickSend(route, 0)
            return
        }

        if (poll < maxPolls) {
            handler.postDelayed(
                { waitForSendButtonReady(route, startedAt, poll + 1) },
                pollDelayMs
            )
            return
        }

        // Fallback controlado: se a versao do WhatsApp nao der nome ao botao,
        // ainda fazemos apenas UMA tentativa, mas somente depois da janela de espera.
        val waited = SystemClock.elapsedRealtime() - startedAt
        Prefs.setStatus(
            this,
            "ENVIO READY: botao nomeado nao apareceu em ${waited}ms | polls=$poll | fallback 1x..."
        )
        tryClickSend(route, 0)
    }

'''

if 'private fun waitForSendButtonReady(' not in s:
    s = s.replace(anchor, helper + anchor, 1)

# Troca somente o disparo apos preencher o campo. O SEND_BUTTON_DELAY existente
# continua servindo como atraso inicial; depois dele entra o polling de readiness.
old_call = '''        handler.postDelayed(
            { tryClickSend(route, 0) },
            SEND_BUTTON_DELAY_MS
        )
'''
new_call = '''        handler.postDelayed(
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
if old_call not in s:
    raise SystemExit('send wait ready: chamada inicial tryClickSend(route, 0) nao encontrada')
s = s.replace(old_call, new_call, 1)

prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND1 POLL =====',
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND READY ====='
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")

print('SEND READY aplicado: espera botao Enviar nomeado a cada 12ms antes do unico clique')
