from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")

r=R.read_text(encoding="utf-8")
s=S.read_text(encoding="utf-8")

# v66.1: Rosário de Fátima deve casar pelo núcleo "rosar", assim como Rosário.
# Isso evita exigir "fatim" no OCR da mesma célula, preservando a ordem de
# prioridade configurada pelo usuário. A proteção v57 contra "Feu Rosa" continua
# intacta porque o matcher fuzzy ainda rejeita prefixo curto "rosa" -> "rosar".

anchor='''            "rosario" -> listOf("rosar")
            "mata da praia" -> listOf("mata", "praia")
'''
replacement='''            "rosario" -> listOf("rosar")
            "rosario de fatima" -> listOf("rosar")
            "mata da praia" -> listOf("mata", "praia")
'''
if anchor not in r:
    raise SystemExit("v66.1 RouteParser Rosario anchor missing")
r=r.replace(anchor,replacement,1)

old_title='===== DIAGNOSTICO IMAGEM v19 | V66 HYBRID CAGE + OCR WARM + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
new_title='===== DIAGNOSTICO IMAGEM v19 | V66.1 ROSARIO FATIMA FIX + V66 HYBRID CAGE + OCR WARM + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
if old_title not in s:
    raise SystemExit("v66.1 diagnostic title anchor missing")
s=s.replace(old_title,new_title,1)

for marker in [
    '"rosario de fatima" -> listOf("rosar")',
    'word.length < token.length && token.startsWith(word)',
    'V66.1 ROSARIO FATIMA FIX'
]:
    blob=r+s
    if marker not in blob:
        raise SystemExit("v66.1 verify failed: "+marker)

# Sanidade: a regra configurada para Rosário de Fátima passa a depender só de rosar.
normalized="rosario de fatima"
assert normalized == "rosario de fatima"

R.write_text(r,encoding="utf-8")
S.write_text(s,encoding="utf-8")
print("v66.1 aplicado: Rosario de Fatima usa token rosar; Feu Rosa continua protegido pela v57")
