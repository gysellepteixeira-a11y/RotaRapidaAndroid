from pathlib import Path

service_path=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
parser_path=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")

s=service_path.read_text(encoding="utf-8")
p=parser_path.read_text(encoding="utf-8")

required_service=[
    'private fun matchBairroFirstPriority(text: String): Pair<Int, String>?',
    '"rosar" in n -> 6 to "Rosario"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required_service:
    if m not in s:
        raise SystemExit("v46 service base inesperada: "+m)

old_service='''            "rosar" in n -> 6 to "Rosario"
            else -> null
'''
new_service='''            "rosar" in n -> 6 to "Rosario"
            ("mata" in n && "praia" in n) -> 7 to "Mata da Praia"
            "republic" in n -> 8 to "Republica"
            else -> null
'''
if old_service not in s:
    raise SystemExit("v46 anchor prioridade imagem nao encontrado")
s=s.replace(old_service,new_service,1)

old_header='===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS ====='
new_header='===== DIAGNOSTICO IMAGEM v17 | V37 + MATA DA PRAIA + REPUBLICA ====='
s=s.replace(old_header,new_header,1)

start=p.find('    private val priorities = listOf(')
end=p.find('\n\n    private val cageRegex', start)
if start<0 or end<0:
    raise SystemExit(f"v46 priorities block nao encontrado: start={start}, end={end}")

new_priorities='''    private val priorities = listOf(
        PriorityRule("Valparaiso", listOf("valparaiso")),
        PriorityRule("Colina de Laranjeiras", listOf("colina")),
        PriorityRule("Praia da Baleia", listOf("praia", "baleia")),
        PriorityRule("Morada de Laranjeiras", listOf("morada")),
        PriorityRule("Eurico", listOf("eurico")),
        PriorityRule("Manoel Plaza", listOf("manoel", "plaza")),
        PriorityRule("Rosario", listOf("rosario")),
        PriorityRule("Mata da Praia", listOf("mata", "praia")),
        PriorityRule("Republica", listOf("republica"))
    )'''
p=p[:start]+new_priorities+p[end:]

for m in [
    '7 to "Mata da Praia"',
    '8 to "Republica"',
    new_header,
]:
    if m not in s:
        raise SystemExit("v46 verify service falhou: "+m)

for m in [
    'PriorityRule("Mata da Praia", listOf("mata", "praia"))',
    'PriorityRule("Republica", listOf("republica"))',
]:
    if m not in p:
        raise SystemExit("v46 verify parser falhou: "+m)

for forbidden in [
    'PriorityRule("Helio Ferraz"',
    'PriorityRule("Parque Residencial Laranjeiras"',
    'PriorityRule("Barcelona"',
    'PriorityRule("Maringa"',
]:
    if forbidden in p:
        raise SystemExit("v46 prioridade extra ainda ativa: "+forbidden)

service_path.write_text(s,encoding="utf-8")
parser_path.write_text(p,encoding="utf-8")
print("v46 aplicado: prioridades 0-8 = 7 atuais + Mata da Praia + Republica; Mata > Republica")
