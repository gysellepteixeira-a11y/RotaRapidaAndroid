from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

# TESTE ISOLADO DE ENVIO:
# - somente UMA entrada em tryClickSend (attempt=0)
# - portanto, no diagnostico, o objetivo e aparecer tentativas=1
# - espera 140ms antes da unica verificacao do campo
# - se ainda estiver preenchido, NAO clica novamente
# - nao altera OCR, Bairro, Gaiola, MediaStore nem preenchimento do campo
#
# No codigo atual attempt comeca em 0. Portanto SEND_MAX_ATTEMPTS=0 significa
# exatamente uma tentativa total. SEND_MAX_ATTEMPTS=1 ainda permitiria 0 e 1.

old_max = '        private const val SEND_MAX_ATTEMPTS = 9\n'
new_max = '        private const val SEND_MAX_ATTEMPTS = 0\n'
if old_max not in s:
    raise SystemExit("send one attempt: SEND_MAX_ATTEMPTS=9 nao encontrado")
s = s.replace(old_max, new_max, 1)

# A OTIMIZACAO 1 injeta a linha de diagnostico do metodo antes do handler.
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
                { verifySendResult(route, attempt) },
                140L
            )
            return
        }
'''
if old_action not in s:
    raise SystemExit("send one attempt: bloco ACTION_CLICK diagnosticado 70ms nao encontrado")
s = s.replace(old_action, new_action, 1)

prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW =====',
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND1 ====='
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")

print("SEND1 aplicado: tentativas maximas=1 total; ACTION_CLICK confirmado apos 140ms; sem retry")
