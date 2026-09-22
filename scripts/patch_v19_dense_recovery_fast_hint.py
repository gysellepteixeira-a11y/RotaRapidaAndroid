from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
parser_path = Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
gradle_path = Path("app/build.gradle.kts")

service = service_path.read_text(encoding="utf-8")
parser = parser_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")
gradle = gradle_path.read_text(encoding="utf-8")

# -----------------------------------------------------------------------------
# OTIMIZACAO SEGURA DO DENSE RECOVERY
# -----------------------------------------------------------------------------
# Nao muda OCR, crop, prioridade, linha escolhida nem envio.
# Apenas elimina o custo de chamar parsePlainTexts(listOf("A00 ...")) para
# cada fragmento OCR quando o parser normal ja falhou numa tabela muito densa.
# A nova funcao publica delega EXATAMENTE para a mesma priorityFor() existente.

priority_anchor = '''    private fun priorityFor(text: String): Pair<Int, String>? {
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

priority_replacement = priority_anchor + '''
    // Usado somente pelo recovery denso. Mantem exatamente as mesmas regras
    // de prioridade do parser normal, sem fabricar uma gaiola temporaria.
    fun priorityHint(text: String): Pair<Int, String>? = priorityFor(text)
'''

if 'fun priorityHint(text: String)' not in parser:
    if priority_anchor not in parser:
        raise SystemExit('fast hint: priorityFor nao encontrado no RouteParser')
    parser = parser.replace(priority_anchor, priority_replacement, 1)

old_block = r'''        data class PriorityHint(
            val result: RouteResult,
            val centerY: Int,
            val top: Int,
            val text: String,
            val rawPart: Boolean
        )

        val hints = ArrayList<PriorityHint>()

        // Primeiro tenta os elementos OCR originais. Para prioridades de uma
        // palavra (Valparaiso, Colina, Eurico, Rosario...) isto fornece o Y mais
        // preciso possivel da celula Bairro.
        for (part in parts) {
            val probe = RouteParser.parsePlainTexts(
                listOf("A00 ${part.text}")
            ) ?: continue

            hints += PriorityHint(
                result = probe,
                centerY = part.centerY,
                top = part.rect.top,
                text = part.text,
                rawPart = true
            )
        }

        // Para bairros com mais de uma palavra, usa tambem a linha reconstruida.
        for (item in reconstructedItems) {
            val probe = RouteParser.parsePlainTexts(
                listOf("A00 ${item.text}")
            ) ?: continue

            hints += PriorityHint(
                result = probe,
                centerY = item.centerY,
                top = item.top,
                text = item.text,
                rawPart = false
            )
        }

        if (hints.isEmpty()) {
            lastDenseRecoveryDebug =
                "recovery=${expectedDenseRows}; prioridade OCR=nenhuma"
            return null
        }

        val bestPriority = hints.minOf { it.result.priorityIndex }
        val samePriority = hints.filter { it.result.priorityIndex == bestPriority }

        // Prefere um elemento bruto quando existir, porque seu centro Y e mais
        // fiel a celula Bairro do que uma linha reconstruida inteira.
        val chosen = samePriority
            .filter { it.rawPart }
            .minByOrNull { it.top }
            ?: samePriority.minByOrNull { it.top }
            ?: return null

        lastDensePriorityNeighborhood = chosen.result.neighborhood
        lastDensePriorityIndex = chosen.result.priorityIndex
        lastDensePriorityCenterY = chosen.centerY
        lastDensePriorityText = chosen.text

        val rowPitch = screenHeight.toFloat() / expectedDenseRows.toFloat()
        lastDenseRecoveryDebug =
            "recovery=${expectedDenseRows}; bairro=${chosen.result.neighborhood}; " +
                "y=${chosen.centerY}; pitch=${String.format(java.util.Locale.US, "%.1f", rowPitch)}; " +
                "texto=${chosen.text.take(70)}"
'''

new_block = r'''        data class PriorityHint(
            val priorityIndex: Int,
            val neighborhood: String,
            val centerY: Int,
            val top: Int,
            val text: String,
            val rawPart: Boolean
        )

        var bestPriority = Int.MAX_VALUE
        var bestRaw: PriorityHint? = null
        var bestAny: PriorityHint? = null

        fun considerPriorityHint(
            text: String,
            centerY: Int,
            top: Int,
            rawPart: Boolean
        ) {
            val priority = RouteParser.priorityHint(text) ?: return
            val index = priority.first
            val hit = PriorityHint(
                priorityIndex = index,
                neighborhood = priority.second,
                centerY = centerY,
                top = top,
                text = text,
                rawPart = rawPart
            )

            if (index < bestPriority) {
                bestPriority = index
                bestRaw = if (rawPart) hit else null
                bestAny = hit
                return
            }

            if (index != bestPriority) return

            if (bestAny == null || top < bestAny!!.top) {
                bestAny = hit
            }

            if (rawPart && (bestRaw == null || top < bestRaw!!.top)) {
                bestRaw = hit
            }
        }

        // Mesmas fontes da versao anterior, mas sem listOf(), sem gaiola A00
        // artificial e sem rodar o parser completo centenas de vezes.
        for (part in parts) {
            considerPriorityHint(
                text = part.text,
                centerY = part.centerY,
                top = part.rect.top,
                rawPart = true
            )
        }

        for (item in reconstructedItems) {
            considerPriorityHint(
                text = item.text,
                centerY = item.centerY,
                top = item.top,
                rawPart = false
            )
        }

        val chosen = bestRaw ?: bestAny
        if (chosen == null) {
            lastDenseRecoveryDebug =
                "recovery=${expectedDenseRows}; prioridade OCR=nenhuma"
            return null
        }

        lastDensePriorityNeighborhood = chosen.neighborhood
        lastDensePriorityIndex = chosen.priorityIndex
        lastDensePriorityCenterY = chosen.centerY
        lastDensePriorityText = chosen.text

        val rowPitch = screenHeight.toFloat() / expectedDenseRows.toFloat()
        lastDenseRecoveryDebug =
            "recovery=${expectedDenseRows}; bairro=${chosen.neighborhood}; " +
                "y=${chosen.centerY}; pitch=${String.format(java.util.Locale.US, "%.1f", rowPitch)}; " +
                "texto=${chosen.text.take(70)}"
'''

if old_block not in service:
    raise SystemExit('fast hint: bloco de recovery anterior nao encontrado')
service = service.replace(old_block, new_block, 1)

# Marca versao para confirmar instalacao e permitir atualizar sobre a anterior.
prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 DENSA RECOVERY =====',
    '===== DIAGNOSTICO IMAGEM v0.19 DENSA RECOVERY FAST ====='
)
gradle = gradle.replace('versionCode = 2', 'versionCode = 3')
gradle = gradle.replace(
    'versionName = "0.19-densa-recovery"',
    'versionName = "0.19-densa-recovery-fast"'
)

service_path.write_text(service, encoding="utf-8")
parser_path.write_text(parser, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")
gradle_path.write_text(gradle, encoding="utf-8")

print("Dense recovery FAST aplicado: mesma prioridade/linha, menos custo no hint + versionCode 3")
