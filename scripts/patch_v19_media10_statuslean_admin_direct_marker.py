from pathlib import Path

prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")

prefs = prefs_path.read_text(encoding="utf-8")
s = service_path.read_text(encoding="utf-8")

# Confirma que a combinacao esperada foi realmente aplicada.
required = [
    'private const val DIRECT_MEDIASTORE_WATCH_MS = 10L',
    'private const val PENDING_ROUTE_SEND_WATCH_MS = 10L',
    'private fun findAdminUltraSendNodeFast(',
    'private fun verifyAdminUltraFast(',
    'ADMIN ULTRA DIRECT: liberado + preenchido',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'MEDIA10 + ADMIN DIRECT: marcador ausente: {marker}')

old = '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND READY MEDIA10 STATUSLEAN ====='
new = '===== DIAGNOSTICO IMAGEM v0.19 MEDIA10 STATUSLEAN ADMIN ULTRA DIRECT FAST ====='

if old not in prefs:
    raise SystemExit('MEDIA10 + ADMIN DIRECT: cabecalho STATUSLEAN nao encontrado')

prefs = prefs.replace(old, new, 1)
prefs_path.write_text(prefs, encoding="utf-8")

print('MEDIA10 STATUSLEAN + ADMIN ULTRA DIRECT FAST confirmado e marcado')
