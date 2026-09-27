from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

# TESTE ISOLADO DE ENVIO:
# - somente UM clique/tentativa real de envio (attempt=0)
# - espera um pouco mais o WhatsApp atualizar o editor antes da unica confirmacao
# - nao altera OCR, Bairro, Gaiola, MediaStore nem preenchimento do campo
#
# Observacao: no codigo atual attempt comeca em 0. Portanto SEND_MAX_ATTEMPTS=0
# significa exatamente 1 tentativa total. Se fosse =1, ainda permitiria attempt 0 e 1.

old_max = '        private const val SEND_MAX_ATTEMPTS = 9\n'
new_max = '        private const val SEND_MAX_ATTEMPTS = 0\n'
if old_max not in s:
    raise SystemExit("send one attempt: SEND_MAX_ATTEMPTS=9 nao encontrado")
s = s.replace(old_max, new_max, 1)

# A v0.17 reduziu a confirmacao do ACTION_CLICK para 70ms. Como agora nao existe
# segundo clique, damos 140ms para o WhatsApp esvaziar o campo antes de decidir.
old_action = '''        if (candidate != null && clickNodeOrParent(candidate.node)) {
            handler.postDelayed(
                { verifySendResult(route, attempt) },
                70L
            )
            return
        }
'''
new_action = '''        if (candidate != null && clickNodeOrParent(candidate.node)) {
            handler.postDelayed(
                { verifySendResult(route, attempt) },
                140L
            )
            return
        }
'''
if old_action not in s:
    raise SystemExit("send one attempt: bloco ACTION_CLICK 70ms nao encontrado")
s = s.replace(old_action, new_action, 1)

prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW =====',
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND1 ====='
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")

print("SEND1 aplicado: 1 tentativa real; ACTION_CLICK confirmado apos 140ms; sem segundo clique")
