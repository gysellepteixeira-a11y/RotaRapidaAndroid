from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# Corrige apenas a formatacao do texto de status inserido pela v0.19.
# A primeira versao do patch deixou barras invertidas literais dentro da
# expressao Kotlin String.format(), quebrando a compilacao.
variants = [
    'String.format(java.util.Locale.US, \\\\\\"%.2f\\\\\\", scale)',
    'String.format(java.util.Locale.US, \\\\"%.2f\\\\", scale)',
    'String.format(java.util.Locale.US, \\"%.2f\\", scale)',
]

fixed = 'String.format(java.util.Locale.US, "%.2f", scale)'
changed = False
for old in variants:
    if old in s:
        s = s.replace(old, fixed)
        changed = True

if not changed:
    # Fallback: remove qualquer escape imediatamente ao redor de %.2f.
    s = s.replace('\\"%.2f\\"', '"%.2f"')
    s = s.replace('\\\\"%.2f\\\\"', '"%.2f"')
    s = s.replace('\\\\\\"%.2f\\\\\\"', '"%.2f"')

service_path.write_text(s, encoding="utf-8")
print("Patch v0.20 aplicado: corrigida formatacao Kotlin do status da v0.19")
