from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

# BAIRRO FIRST - GAIOLA NARROW
# Nos testes reais o OCR pequeno da Gaiola leu "-10 AT2026".
# Isso confirma que o recorte antigo de 20% ainda invadia a coluna AT.
# A Gaiola ocupa aproximadamente 10.8% do crop denso (crop ~50% do arquivo).
# Usamos 11.5% com margem pequena: suficiente para I10/J16/F23 etc., sem AT.

old_width = '''        val sliceWidth = maxOf(90, (denseBitmap.width * 0.20f).toInt())
            .coerceAtMost(denseBitmap.width)
'''
new_width = '''        val sliceWidth = maxOf(52, (denseBitmap.width * 0.115f).toInt())
            .coerceAtMost(denseBitmap.width)
'''

if old_width not in s:
    raise SystemExit("cage narrow: sliceWidth antigo 20% nao encontrado")
s = s.replace(old_width, new_width, 1)

# Diagnostico inequivoco da build.
prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST =====',
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW ====='
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")

print("Cage narrow aplicado: recorte Gaiola 20% -> 11.5%, sem invadir AT")