from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
r=R.read_text(encoding="utf-8")

old_data='''    private data class PriorityRule(
        val name: String,
        val requiredTokens: List<String>
    )
'''
new_data='''    private data class PriorityRule(
        val name: String,
        val requiredTokens: List<String>,
        val normalizedName: String
    )
'''
if old_data not in r:
    raise SystemExit("v57 PriorityRule anchor missing")
r=r.replace(old_data,new_data,1)

old_return='''        return PriorityRule(name.trim(), required)
'''
new_return='''        return PriorityRule(
            name = name.trim(),
            requiredTokens = required,
            normalizedName = normalized
        )
'''
if old_return not in r:
    raise SystemExit("v57 buildPriorityRule return missing")
r=r.replace(old_return,new_return,1)

old_priority='''    private fun priorityFor(text: String): Pair<Int, String>? {
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
new_priority='''    private fun selectPriorityV57(normalized: String): Pair<Int, String>? {
        if (normalized.isBlank()) return null

        val matches = priorities.mapIndexedNotNull { index, rule ->
            if (rule.requiredTokens.all { normalized.contains(it) }) {
                index to rule
            } else {
                null
            }
        }
        if (matches.isEmpty()) return null

        // Primeiro privilegia nome completo visível no MESMO trecho OCR.
        // Ex.: "feu rosar..." contém "feu rosa", mas não contém "rosario".
        val phraseMatches = matches.filter { (_, rule) ->
            rule.normalizedName.isNotBlank() &&
                normalized.contains(rule.normalizedName)
        }

        val pool = if (phraseMatches.isNotEmpty()) phraseMatches else matches

        // Em colisões dentro do mesmo trecho OCR, ganha a correspondência mais
        // específica. A prioridade da lista continua como desempate e continua
        // valendo normalmente entre linhas/candidatos diferentes.
        val winner = pool.minWithOrNull(
            compareBy<Pair<Int, PriorityRule>>(
                { -it.second.normalizedName.length },
                { -it.second.requiredTokens.size },
                { -it.second.requiredTokens.sumOf(String::length) },
                { it.first }
            )
        ) ?: return null

        return winner.first to winner.second.name
    }

    private fun priorityFor(text: String): Pair<Int, String>? =
        selectPriorityV57(normalize(text))
'''
if old_priority not in r:
    raise SystemExit("v57 priorityFor block missing")
r=r.replace(old_priority,new_priority,1)

old_v36='''    private fun priorityForNormalizedV36(normalized: String): Pair<Int, String>? {
        if(normalized.isBlank())return null
        priorities.forEachIndexed { index, rule ->
            if(rule.requiredTokens.all { normalized.contains(it) }){
                return index to rule.name
            }
        }
        return null
    }
'''
new_v36='''    private fun priorityForNormalizedV36(normalized: String): Pair<Int, String>? =
        selectPriorityV57(normalized)
'''
if old_v36 not in r:
    raise SystemExit("v57 priorityForNormalizedV36 block missing")
r=r.replace(old_v36,new_v36,1)

# Strong self-checks for the exact collision that motivated the patch.
for m in [
    'val normalizedName: String',
    'private fun selectPriorityV57(normalized: String)',
    'normalized.contains(rule.normalizedName)',
    'priorityForNormalizedV36(normalized: String): Pair<Int, String>? =',
    'selectPriorityV57(normalized)',
]:
    if m not in r:
        raise SystemExit("v57 verify failed: "+m)

R.write_text(r,encoding="utf-8")
print("v57 aplicado: colisões no mesmo trecho OCR escolhem nome mais específico; prioridade segue como desempate")
