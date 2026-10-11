from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
r=R.read_text(encoding="utf-8")
s=S.read_text(encoding="utf-8")

anchor='''    fun parseImageScreenTexts(items: List<ScreenText>): RouteResult? {
'''
if anchor not in r:
    raise SystemExit("v62 image parser anchor missing")

helper=r'''    @Volatile
    var lastImagePackageTieV62: String = "packageTieV62=used=false | reason=not_checked"
        private set

    private fun packageCountV62(value: String): Int? {
        var afterOrder = false
        for (raw in value.uppercase(Locale.ROOT).split(' ', '\t', '\n', '\r')) {
            val token = raw.filter { it.isLetterOrDigit() }
            if (token.isBlank()) continue

            if (!afterOrder) {
                if (
                    token == "AT" || token == "TO" ||
                    (token.length >= 4 && (token.startsWith("AT") || token.startsWith("TO")))
                ) afterOrder = true
                continue
            }

            // SPR (Rot) validado nesta tabela: inteiro curto. Limitar a 3
            // digitos evita confundir partes numericas do codigo AT/TO.
            if (token.length in 1..3 && token.all { it in '0'..'9' }) {
                return token.toIntOrNull()
            }
        }
        return null
    }

'''
r=r.replace(anchor,helper+anchor,1)

old=r'''        val topPriority = neighborhoodHits.minOf { it.first }
        val chosen = neighborhoodHits
            .filter { it.first == topPriority }
            .minByOrNull { it.third.top }
            ?: return null
'''
new=r'''        val topPriority = neighborhoodHits.minOf { it.first }
        val topHits = neighborhoodHits.filter { it.first == topPriority }
        val baseChosen = topHits.minByOrNull { it.third.top } ?: return null

        // v62: somente a prioridade vencedora participa. O desempate por SPR
        // (Rot) roda no fast-path de linha reconstruida, que ja contem Gaiola,
        // AT/TO, quantidade e Bairro no MESMO texto. Nao ha OCR adicional.
        val directRoutes = topHits.mapNotNull { hit ->
            val cage = extractCage(hit.third.text) ?: return@mapNotNull null
            val packages = packageCountV62(hit.third.text) ?: return@mapNotNull null
            Triple(hit, cage, packages)
        }.distinctBy { it.second }

        val directCages = topHits
            .mapNotNull { hit -> extractCage(hit.third.text) }
            .distinct()

        val chosen = if (
            directRoutes.size >= 2 &&
            directRoutes.size == directCages.size
        ) {
            val winner = directRoutes.sortedWith(
                compareByDescending<Triple<Triple<Int, String, ScreenText>, String, Int>> { it.third }
                    .thenBy { it.first.third.top }
            ).first()

            val summary = directRoutes.joinToString(",") { "${it.second}:${it.third}" }
            val baseCage = extractCage(baseChosen.third.text).orEmpty()
            val used = winner.second != baseCage
            lastImagePackageTieV62 =
                "packageTieV62=used=$used | candidates=${directRoutes.size} | packages=$summary | " +
                "winner=${winner.second}:${winner.third} | reason=" +
                if (used) "higher_packages" else "original_already_max"
            winner.first
        } else {
            val summary = if (directRoutes.isEmpty()) "--" else
                directRoutes.joinToString(",") { "${it.second}:${it.third}" }
            val reason = when {
                directCages.size < 2 -> "single_top_priority"
                directRoutes.size < directCages.size -> "package_missing"
                else -> "no_tiebreak"
            }
            lastImagePackageTieV62 =
                "packageTieV62=used=false | candidates=${directCages.size} | packages=$summary | reason=$reason"
            baseChosen
        }
'''
if old not in r:
    raise SystemExit("v62 winner block missing")
r=r.replace(old,new,1)

# Expose the decision in the existing image diagnostic without touching text/admin.
old_diag='''            appendLine("[${idA(idRoute)}] Rota pronta: ${route.neighborhood} -> ${route.cage}")
            appendLine("[${idA(idEditor)}] Editor encontrado | collectEnvio=${idSendCollect}ms")
'''
new_diag='''            appendLine("[${idA(idRoute)}] Rota pronta: ${route.neighborhood} -> ${route.cage}")
            appendLine(RouteParser.lastImagePackageTieV62)
            appendLine("[${idA(idEditor)}] Editor encontrado | collectEnvio=${idSendCollect}ms")
'''
if old_diag not in s:
    raise SystemExit("v62 diagnostic route anchor missing")
s=s.replace(old_diag,new_diag,1)

old_title='===== DIAGNOSTICO IMAGEM v19 | V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
new_title='===== DIAGNOSTICO IMAGEM v19 | V62 PACKAGE TIEBREAK + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
if old_title not in s:
    raise SystemExit("v62 diagnostic title anchor missing")
s=s.replace(old_title,new_title,1)

for marker in [
    'lastImagePackageTieV62',
    'packageCountV62',
    'higher_packages',
    'package_missing',
    'V62 PACKAGE TIEBREAK',
]:
    if marker not in r+s:
        raise SystemExit("v62 verify failed: "+marker)

R.write_text(r,encoding="utf-8")
S.write_text(s,encoding="utf-8")
print("v62 aplicado: prioridade intacta; SPR (Rot) desempata apenas rotas da prioridade vencedora; sem OCR extra")
