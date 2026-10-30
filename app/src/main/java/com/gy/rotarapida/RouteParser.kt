package com.gy.rotarapida

import java.text.Normalizer
import java.util.Locale
import kotlin.math.abs

data class ScreenText(
    val text: String,
    val left: Int,
    val top: Int,
    val right: Int,
    val bottom: Int
) {
    val centerY: Int get() = (top + bottom) / 2
}

data class RouteResult(
    val neighborhood: String,
    val cage: String,
    val priorityIndex: Int
)

object RouteParser {

    private data class PriorityRule(
        val name: String,
        val requiredTokens: List<String>
    )

    private val priorities = listOf(
        PriorityRule("Valparaiso", listOf("valparaiso")),
        PriorityRule("Colina de Laranjeiras", listOf("colina")),
        PriorityRule("Praia da Baleia", listOf("praia", "baleia")),
        PriorityRule("Morada de Laranjeiras", listOf("morada")),
        PriorityRule("Eurico", listOf("eurico")),
        PriorityRule("Manoel Plaza", listOf("manoel", "plaza")),
        PriorityRule("Rosario", listOf("rosario")),
        PriorityRule("Helio Ferraz", listOf("helio", "ferraz")),
        PriorityRule("Parque Residencial Laranjeiras", listOf("parque", "residencial", "laranjeiras")),
        PriorityRule("Barcelona", listOf("barcelona")),
        PriorityRule("Maringa", listOf("maringa"))
    )

    private val cageRegex =
        Regex("""(?<![A-Z0-9])([A-Z1])[-.\s]?(\d{2})(?!\d)""")

    private val cageFallbackRegex =
        Regex("""([A-Z1])[-.\s]?(\d{2})(?!\d)""")

    fun normalize(value: String): String {
        val decomposed = Normalizer.normalize(
            value.lowercase(Locale.ROOT).trim(),
            Normalizer.Form.NFD
        )

        return decomposed
            .replace(Regex("""\p{Mn}+"""), "")
            .replace(Regex("""[^a-z0-9\s]"""), " ")
            .replace(Regex("""\s+"""), " ")
            .trim()
    }

    fun extractCage(value: String): String? {
        val upper = value.uppercase(Locale.ROOT).trim()
        val match = cageRegex.find(upper) ?: cageFallbackRegex.find(upper) ?: return null

        var letter = match.groupValues[1]
        if (letter == "1") letter = "I"

        return letter.lowercase(Locale.ROOT) + match.groupValues[2]
    }

    private fun priorityFor(text: String): Pair<Int, String>? {
        val normalized = normalize(text)
        if (normalized.isBlank()) return null

        priorities.forEachIndexed { index, rule ->
            if (rule.requiredTokens.all { normalized.contains(it) }) {
                return index to rule.name
            }
        }

        return null
    }

    /**
     * Primeiro tenta o caso ideal: cada linha contém gaiola + bairro.
     * Isso é o que normalmente acontece quando o WhatsApp expõe a mensagem
     * de texto como um bloco com quebras de linha.
     */
    fun parsePlainTexts(texts: List<String>): RouteResult? {
        val candidates = mutableListOf<Triple<Int, String, String>>()

        for (raw in texts) {
            val lines = raw
                .replace("\r", "\n")
                .split("\n")
                .map { it.trim() }
                .filter { it.isNotBlank() }

            for (line in lines) {
                val priority = priorityFor(line) ?: continue
                val cage = extractCage(line) ?: continue
                candidates += Triple(priority.first, priority.second, cage)
            }
        }

        if (candidates.isEmpty()) return null

        val winner = candidates.minByOrNull { it.first } ?: return null
        return RouteResult(winner.second, winner.third, winner.first)
    }

    /**
     * Fallback visual: bairro e gaiola podem aparecer em elementos separados.
     * Escolhe PRIMEIRO o bairro de maior prioridade. Só então procura a gaiola
     * na mesma altura. Se essa gaiola não estiver legível, NÃO troca por um
     * bairro de prioridade menor.
     */
    fun parseScreenTexts(items: List<ScreenText>, screenHeight: Int): RouteResult? {
        parsePlainTexts(items.map { it.text })?.let { return it }

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

        extractCage(neighborhoodItem.text)?.let { cage ->
            return RouteResult(chosen.second, cage, chosen.first)
        }

        val yTolerance = maxOf(24, (screenHeight * 0.025).toInt())

        val cages = items.mapNotNull { item ->
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
}
