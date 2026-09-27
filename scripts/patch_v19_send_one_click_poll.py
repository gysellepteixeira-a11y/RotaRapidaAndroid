from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

# TESTE ISOLADO SEND1 POLL
# - continua com UMA unica tentativa real de clique (SEND_MAX_ATTEMPTS=0, patch anterior)
# - depois do ACTION_CLICK, NAO repete clique nem preenche o campo novamente
# - apenas consulta a arvore do WhatsApp em intervalos curtos ate o editor esvaziar
# - OCR / MediaStore / Bairro / Gaiola / parser permanecem intocados

# Comeca a conferir cedo. Se o WhatsApp ainda nao atualizou, verifySendResult faz polling.
old_delay = '''        if (candidate != null && clickNodeOrParent(candidate.node)) {
            speedDiagnosticSendMethod = "ACTION_CLICK"
            handler.postDelayed(
                { verifySendResult(route, attempt) },
                140L
            )
            return
        }
'''
new_delay = '''        if (candidate != null && clickNodeOrParent(candidate.node)) {
            speedDiagnosticSendMethod = "ACTION_CLICK"
            handler.postDelayed(
                { verifySendResult(route, attempt) },
                90L
            )
            return
        }
'''
if old_delay not in s:
    raise SystemExit("send one click poll: ACTION_CLICK 140ms nao encontrado")
s = s.replace(old_delay, new_delay, 1)

# Troca SOMENTE a confirmacao. A funcao recebe poll com default para manter
# compativeis todas as chamadas existentes de verifySendResult(route, attempt).
start = s.find('    private fun verifySendResult(route: RouteResult, attempt: Int) {')
end = s.find('    private fun scheduleNextSendAttempt(route: RouteResult, attempt: Int) {', start)
if start < 0 or end < 0:
    raise SystemExit(
        f"send one click poll: bloco verifySendResult nao encontrado (start={start}, end={end})"
    )

new_verify = r'''    private fun verifySendResult(
        route: RouteResult,
        attempt: Int,
        poll: Int = 0
    ) {
        if (!processing) return

        // 90 ms antes da primeira checagem + ate 8 polls de 30 ms.
        // Janela total aproximada: 90..330 ms apos o ACTION_CLICK.
        // Em nenhum momento fazemos um segundo clique.
        val maxPolls = 8
        val pollDelayMs = 30L

        val root = rootInActiveWindow
        if (root == null) {
            if (poll < maxPolls) {
                handler.postDelayed(
                    { verifySendResult(route, attempt, poll + 1) },
                    pollDelayMs
                )
            } else {
                holdRouteUntilChatOpen(route, "Nao consegui confirmar o envio agora.")
            }
            return
        }

        val items = collectNodeItems(root)
        val editor = findMessageEditor(items)

        // Se o editor existe e a mensagem sumiu, o primeiro ACTION_CLICK enviou.
        if (editor != null && !messageStillInEditor(items)) {
            markSent(route)
            return
        }

        // O WhatsApp costuma demorar para atualizar a arvore de acessibilidade.
        // Enquanto a mensagem ainda aparece (ou o editor oscila/some), apenas
        // consulta novamente. Nao clica, nao repoe texto e nao reinicia cronometro.
        if (poll < maxPolls) {
            handler.postDelayed(
                { verifySendResult(route, attempt, poll + 1) },
                pollDelayMs
            )
            return
        }

        holdRouteUntilChatOpen(route, "Nao consegui confirmar o envio agora.")
    }

'''

s = s[:start] + new_verify + s[end:]

prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND1 =====',
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND1 POLL ====='
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")

print("SEND1 POLL aplicado: 1 clique real + polling 90..330ms sem reenviar")
