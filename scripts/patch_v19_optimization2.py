from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - OTIMIZACAO 2
#
# Base: OTIMIZACAO 1 + diagnostico.
# Os testes reais mostraram que todo envio estava chegando a tentativas=2 com
# ACTION_CLICK. A primeira verificacao acontece muito cedo e, se o campo ainda
# nao tiver atualizado na arvore de acessibilidade, o app dispara um segundo
# clique mesmo quando o primeiro ja foi aceito pelo WhatsApp.
#
# Nesta etapa NAO mexemos em OCR, parser, prioridades ou deteccao de imagem.
# Mudamos somente a confirmacao do envio:
# - depois de ACTION_CLICK/GESTURE, verifica o campo rapidamente varias vezes;
# - nao clica de novo durante essa pequena janela;
# - assim que o campo esvazia, confirma imediatamente;
# - se continuar preenchido ao final da janela, usa o MESMO retry seguro antigo.
#
# A janela foi escolhida para ser conservadora: 8 verificacoes em ~165 ms.
# Se o primeiro clique realmente falhar, o segundo continua acontecendo; apenas
# deixa de ser prematuro.

# -----------------------------------------------------------------------------
# 1) CONSTANTES DA CONFIRMACAO RAPIDA
# -----------------------------------------------------------------------------
const_anchor = '        private const val SEND_RETRY_DELAY_MS = 35L\n'
const_extra = '''        private const val SEND_FAST_CONFIRM_FIRST_MS = 25L
        private const val SEND_FAST_CONFIRM_INTERVAL_MS = 20L
        private const val SEND_FAST_CONFIRM_MAX_CHECK = 7
'''
if 'SEND_FAST_CONFIRM_FIRST_MS' not in s:
    if const_anchor not in s:
        raise SystemExit('patch_v19_optimization2: SEND_RETRY_DELAY_MS=35L nao encontrado')
    s = s.replace(const_anchor, const_anchor + const_extra, 1)

# -----------------------------------------------------------------------------
# 2) DIAGNOSTICO: quantas verificacoes foram feitas antes da confirmacao
# -----------------------------------------------------------------------------
state_anchor = '    private var speedDiagnosticSendMethod = "nenhum"\n'
if 'private var speedDiagnosticConfirmChecks' not in s:
    if state_anchor not in s:
        raise SystemExit('patch_v19_optimization2: estado speedDiagnosticSendMethod nao encontrado')
    s = s.replace(
        state_anchor,
        state_anchor + '    private var speedDiagnosticConfirmChecks = 0\n',
        1
    )

reset_anchor = '''        speedDiagnosticSendAttempts = 0
        speedDiagnosticSendMethod = "nenhum"
'''
if reset_anchor not in s:
    raise SystemExit('patch_v19_optimization2: reset do diagnostico de envio nao encontrado')
s = s.replace(
    reset_anchor,
    reset_anchor + '        speedDiagnosticConfirmChecks = 0\n',
    1
)

# -----------------------------------------------------------------------------
# 3) PRIMEIRO ACTION_CLICK: nao manda retry apos uma unica verificacao precoce
# -----------------------------------------------------------------------------
old_action = '''        if (candidate != null && clickNodeOrParent(candidate.node)) {
            speedDiagnosticSendMethod = "ACTION_CLICK"
            handler.postDelayed(
                { verifySendResult(route, attempt) },
                70L
            )
            return
        }
'''
new_action = '''        if (candidate != null && clickNodeOrParent(candidate.node)) {
            speedDiagnosticSendMethod = "ACTION_CLICK"
            handler.postDelayed(
                { verifySendResultFast(route, attempt, 0) },
                SEND_FAST_CONFIRM_FIRST_MS
            )
            return
        }
'''
if old_action not in s:
    raise SystemExit('patch_v19_optimization2: bloco ACTION_CLICK de 70ms nao encontrado')
s = s.replace(old_action, new_action, 1)

# GESTURE usa a mesma confirmacao rapida. Nao e o caminho visto nos testes, mas
# deixa os dois metodos com a mesma protecao contra segundo toque prematuro.
old_gesture_callback = '''                override fun onCompleted(gestureDescription: GestureDescription?) {
                    handler.postDelayed(
                        { verifySendResult(route, attempt) },
                        75L
                    )
                }
'''
new_gesture_callback = '''                override fun onCompleted(gestureDescription: GestureDescription?) {
                    handler.postDelayed(
                        { verifySendResultFast(route, attempt, 0) },
                        SEND_FAST_CONFIRM_FIRST_MS
                    )
                }
'''
if old_gesture_callback not in s:
    raise SystemExit('patch_v19_optimization2: callback GESTURE de 75ms nao encontrado')
s = s.replace(old_gesture_callback, new_gesture_callback, 1)

# -----------------------------------------------------------------------------
# 4) CONFIRMACAO RAPIDA SEM NOVO CLIQUE
# -----------------------------------------------------------------------------
verify_anchor = '''    private fun verifySendResult(route: RouteResult, attempt: Int) {
'''
if verify_anchor not in s:
    raise SystemExit('patch_v19_optimization2: verifySendResult nao encontrado')

fast_verify = r'''    private fun verifySendResultFast(
        route: RouteResult,
        attempt: Int,
        check: Int
    ) {
        if (!processing) return

        speedDiagnosticConfirmChecks += 1

        val root = rootInActiveWindow
        if (root != null) {
            val items = collectNodeItems(root)

            // Assim que o WhatsApp retirar a mensagem do editor, confirma sem
            // esperar outro ciclo e SEM tocar novamente em Enviar.
            if (!messageStillInEditor(items)) {
                markSent(route)
                return
            }
        }

        // Ainda pode ser apenas atraso da arvore de acessibilidade. Faz novas
        // leituras curtas antes de concluir que o clique realmente falhou.
        if (check < SEND_FAST_CONFIRM_MAX_CHECK) {
            handler.postDelayed(
                { verifySendResultFast(route, attempt, check + 1) },
                SEND_FAST_CONFIRM_INTERVAL_MS
            )
            return
        }

        // A janela terminou e a mensagem continua no editor: agora sim usa o
        // retry antigo, que continua sendo a rede de seguranca do envio.
        scheduleNextSendAttempt(route, attempt)
    }

'''
s = s.replace(verify_anchor, fast_verify + verify_anchor, 1)

# -----------------------------------------------------------------------------
# 5) STATUS FINAL MOSTRA TAMBEM O NUMERO DE CHECKS
# -----------------------------------------------------------------------------
old_confirm_piece = '''                "envio=${formatElapsedMs(sendStageMs)} | tentativas=${speedDiagnosticSendAttempts} | " +
                "metodo=${speedDiagnosticSendMethod} | app=${formatElapsedMs(elapsed)}"
'''
new_confirm_piece = '''                "envio=${formatElapsedMs(sendStageMs)} | tentativas=${speedDiagnosticSendAttempts} | " +
                "checks=${speedDiagnosticConfirmChecks} | metodo=${speedDiagnosticSendMethod} | " +
                "app=${formatElapsedMs(elapsed)}"
'''
if old_confirm_piece not in s:
    raise SystemExit('patch_v19_optimization2: status CONFIRMADO da otimizacao 1 nao encontrado')
s = s.replace(old_confirm_piece, new_confirm_piece, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 OTIMIZACAO 2 aplicado: confirmacao rapida sem segundo clique prematuro")
