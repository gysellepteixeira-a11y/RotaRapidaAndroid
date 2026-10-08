from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
r=R.read_text(encoding="utf-8")
s=S.read_text(encoding="utf-8")

# 1) Todos os caminhos principais aceitam letras A-Z.
old_regex='''    private val cageRegex =
        Regex("""(?<![A-Z0-9])([A-I])[-.\\s]?(\\d{2})(?![A-Z0-9])""")
'''
new_regex='''    private val cageRegex =
        Regex("""(?<![A-Z0-9])([A-Z])[-.\\s]?(\\d{2})(?![A-Z0-9])""")
'''
if old_regex not in r:
    raise SystemExit("v58 cageRegex A-I block missing")
r=r.replace(old_regex,new_regex,1)

# 2) O recovery denso deve respeitar a lista editável da v55,
# inclusive Mata da Praia/Republica e qualquer bairro novo.
old_hint=r'''        fun fastPriorityHint(text: String): Pair<Int, String>? {
            val normalized = RouteParser.normalize(text)
            if (normalized.isBlank()) return null

            return when {
                normalized.contains("valparaiso") -> 0 to "Valparaiso"
                normalized.contains("colina") -> 1 to "Colina de Laranjeiras"
                normalized.contains("praia") && normalized.contains("baleia") ->
                    2 to "Praia da Baleia"
                normalized.contains("morada") -> 3 to "Morada de Laranjeiras"
                normalized.contains("eurico") -> 4 to "Eurico"
                normalized.contains("manoel") && normalized.contains("plaza") ->
                    5 to "Manoel Plaza"
                normalized.contains("rosario") -> 6 to "Rosario"
                else -> null
            }
        }
'''
new_hint=r'''        fun fastPriorityHint(text: String): Pair<Int, String>? =
            RouteParser.matchPriority(text)
'''
if old_hint not in s:
    raise SystemExit("v58 static 7-bairro dense hint block missing")
s=s.replace(old_hint,new_hint,1)

# 3) Na imagem 1536x261 observada, Agency comeca em ~58.3% da largura.
# O crop antigo do Bairro terminava em 50.5%, cortando "Mata da Praia".
# denseBitmap ja termina imediatamente depois da coluna Bairro/antes de Agency,
# entao usar 97.5% dele preserva todo o bairro sem incluir a coluna seguinte.
old_right='''        val rightRatio = (0.505f / safeWidthRatio)
            .coerceIn(leftRatio + 0.16f, 0.985f)
'''
new_right='''        val rightRatio = 0.975f
            .coerceAtLeast(leftRatio + 0.16f)
'''
if old_right not in s:
    raise SystemExit("v58 bairro-first rightRatio old block missing")
s=s.replace(old_right,new_right,1)

checks_r=[
    '([A-Z])[-.\\\\s]?(\\\\d{2})',
    'private val cageIFallbackRegex',
    'fun extractCage(value: String): String?',
]
for m in checks_r:
    if m not in r:
        raise SystemExit("v58 RouteParser verify failed: "+m)

checks_s=[
    'fun fastPriorityHint(text: String): Pair<Int, String>? =',
    'RouteParser.matchPriority(text)',
    'val rightRatio = 0.975f',
    'readDenseCageOnly(',
]
for m in checks_s:
    if m not in s:
        raise SystemExit("v58 service verify failed: "+m)

if 'normalized.contains("rosario") -> 6 to "Rosario"' in s:
    raise SystemExit("v58 old static 7-neighborhood hint still present")

R.write_text(r,encoding="utf-8")
S.write_text(s,encoding="utf-8")
print("v58 aplicado: cage A-Z em todos os parsers + dense recovery usa lista editavel + Bairro crop preserva coluna inteira")
