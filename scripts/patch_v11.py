from pathlib import Path

parser_path = Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
r = parser_path.read_text(encoding="utf-8")

# 1) Bairro: tolera um erro pequeno de OCR em palavras de 5+ letras.
old_priority = '''    private fun priorityFor(text: String): Pair<Int, String>? {
        val normalized = normalize(text)
        if (normalized.isBlank()) return null

        priorities.forEachIndexed { index, rule ->
            if (rule.requiredTokens.all { normalized.contains(it) }) {
                return index to rule.name
            }
        }

        return null
    }
'''

new_priority = '''    private fun editDistanceAtMostOne(a: String, b: String): Boolean {
        if (a == b) return true
        if (kotlin.math.abs(a.length - b.length) > 1) return false

        var i = 0
        var j = 0
        var edits = 0

        while (i < a.length && j < b.length) {
            if (a[i] == b[j]) {
                i++
                j++
                continue
            }

            edits++
            if (edits > 1) return false

            when {
                a.length > b.length -> i++
                b.length > a.length -> j++
                else -> {
                    i++
                    j++
                }
            }
        }

        if (i < a.length || j < b.length) edits++
        return edits <= 1
    }

    private fun containsTokenApprox(normalized: String, token: String): Boolean {
        if (normalized.contains(token)) return true
        if (token.length < 5) return false

        return normalized
            .split(' ')
            .filter { it.isNotBlank() }
            .any { word -> editDistanceAtMostOne(word, token) }
    }

    private fun priorityFor(text: String): Pair<Int, String>? {
        val normalized = normalize(text)
        if (normalized.isBlank()) return null

        priorities.forEachIndexed { index, rule ->
            if (rule.requiredTokens.all { token -> containsTokenApprox(normalized, token) }) {
                return index to rule.name
            }
        }

        return null
    }
'''

if old_priority not in r:
    raise SystemExit("Patch v0.11: priorityFor antigo nao encontrado")
r = r.replace(old_priority, new_priority, 1)

# 2) Leitura de IMAGEM: gaiola tem que estar na MESMA linha visual do bairro.
# Nao usa a tolerancia antiga baseada em 2.5% da tela, que no screenshot ampliado
# podia alcancar a linha vizinha (ex.: Parque Residencial Laranjeiras I-01 pegando H-40).
marker = '''    fun parseScreenTexts(items: List<ScreenText>, screenHeight: Int): RouteResult? {
'''
if marker not in r:
    raise SystemExit("Patch v0.11: parseScreenTexts nao encontrado")

strict_fun = '''    fun parseImageScreenTexts(items: List<ScreenText>): RouteResult? {
        if (items.isEmpty()) return null

        val neighborhoodHits = items.mapNotNull { item ->
            val priority = priorityFor(item.text) ?: return@mapNotNull null
            Triple(priority.first, priority.second, item)
        }

        if (neighborhoodHits.isEmpty()) return null

        val topPriority = neighborhoodHits.minOf { it.first }
        val chosen = neighborhoodHits
            .filter { it.first == topPriority }
            .minByOrNull { it.third.top }
            ?: return null

        val neighborhoodItem = chosen.third

        // Caso o ML Kit tenha colocado gaiola + bairro no mesmo elemento/linha.
        extractCage(neighborhoodItem.text)?.let { cage ->
            return RouteResult(chosen.second, cage, chosen.first)
        }

        val rowHeight = (neighborhoodItem.bottom - neighborhoodItem.top).coerceAtLeast(1)
        val yTolerance = maxOf(7, (rowHeight * 0.65f).toInt())

        val cages = items.mapNotNull { item ->
            // A coluna Gaiola fica sempre a esquerda da coluna Bairro.
            if (item.left >= neighborhoodItem.left) return@mapNotNull null

            val cage = extractCage(item.text) ?: return@mapNotNull null
            cage to item
        }

        val nearest = cages
            .filter { (_, item) ->
                abs(item.centerY - neighborhoodItem.centerY) <= yTolerance
            }
            .minWithOrNull(
                compareBy<Pair<String, ScreenText>>(
                    { abs(it.second.centerY - neighborhoodItem.centerY) },
                    { it.second.left }
                )
            )

        val cage = nearest?.first ?: return null
        return RouteResult(chosen.second, cage, chosen.first)
    }

'''

r = r.replace(marker, strict_fun + marker, 1)
parser_path.write_text(r, encoding="utf-8")

# 3) O OCR de imagem usa o parser estrito; rota de texto continua no parser antigo.
service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")
old_call = '        return RouteParser.parseScreenTexts(items, screenHeight)\n'
new_call = '        return RouteParser.parseImageScreenTexts(items)\n'
if old_call not in s:
    raise SystemExit("Patch v0.11: chamada parseScreenTexts da imagem nao encontrada")
s = s.replace(old_call, new_call, 1)
service_path.write_text(s, encoding="utf-8")

print("Patch v0.11 aplicado: bairro com tolerancia OCR + gaiola somente na mesma linha visual")
