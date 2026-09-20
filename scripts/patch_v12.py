from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.12: o ML Kit pode separar as celulas da mesma linha da tabela em blocos/linhas
# diferentes. A v0.11 tentava casar bairro e gaiola pela caixa vertical de cada bloco,
# e isso podia falhar mesmo quando os dois textos tinham sido reconhecidos.
# Agora reconstruimos as LINHAS VISUAIS da tabela usando os elementos do ML Kit:
# agrupamos tudo que esta na mesma altura, ordenamos da esquerda para a direita e
# passamos a linha completa ao RouteParser. Assim "I-15 ... Colina de Laranjeiras"
# volta a ser uma unica linha logica, como no bot do PC.

start = s.find('    private fun parseVisionText(\n')
end = s.find('\n    private fun closeImageWithoutSending(', start)
if start < 0 or end < 0:
    raise SystemExit('Patch v0.12: parseVisionText nao encontrado')

new_parse = r'''    private fun parseVisionText(
        visionText: Text,
        screenHeight: Int
    ): RouteResult? {
        data class OcrPart(
            val text: String,
            val rect: Rect
        ) {
            val centerY: Int get() = (rect.top + rect.bottom) / 2
            val height: Int get() = (rect.bottom - rect.top).coerceAtLeast(1)
        }

        val parts = mutableListOf<OcrPart>()

        for (block in visionText.textBlocks) {
            for (line in block.lines) {
                // Preferimos ELEMENTOS (palavras/celulas) porque o ML Kit pode
                // criar uma Text.Line diferente para cada celula da planilha.
                var addedElement = false
                for (element in line.elements) {
                    val box = element.boundingBox ?: continue
                    val text = element.text.trim()
                    if (text.isBlank()) continue
                    parts += OcrPart(text, Rect(box))
                    addedElement = true
                }

                // Fallback para casos em que a linha nao expose elementos.
                if (!addedElement) {
                    val box = line.boundingBox ?: continue
                    val text = line.text.trim()
                    if (text.isNotBlank()) {
                        parts += OcrPart(text, Rect(box))
                    }
                }
            }
        }

        if (parts.isEmpty()) return null

        val medianHeight = parts
            .map { it.height }
            .sorted()
            .let { heights -> heights[heights.size / 2] }
            .coerceAtLeast(6)

        // Menor que a distancia entre duas linhas consecutivas da tabela, mas
        // folgado o suficiente para pequenas diferencas de boundingBox entre celulas.
        val rowTolerance = maxOf(6, (medianHeight * 0.72f).toInt())

        data class RowBucket(
            val parts: MutableList<OcrPart> = mutableListOf(),
            var centerY: Double = 0.0
        )

        val rows = mutableListOf<RowBucket>()

        for (part in parts.sortedBy { it.centerY }) {
            val nearest = rows
                .filter { kotlin.math.abs(it.centerY - part.centerY) <= rowTolerance }
                .minByOrNull { kotlin.math.abs(it.centerY - part.centerY) }

            if (nearest == null) {
                rows += RowBucket(
                    parts = mutableListOf(part),
                    centerY = part.centerY.toDouble()
                )
            } else {
                nearest.parts += part
                nearest.centerY = nearest.parts.map { it.centerY }.average()
            }
        }

        val reconstructedRows = rows
            .map { row ->
                row.parts
                    .sortedBy { it.rect.left }
                    .joinToString(" ") { it.text }
                    .replace(Regex("\\s+"), " ")
                    .trim()
            }
            .filter { it.isNotBlank() }

        // Caminho principal: cada linha reconstruida contem a gaiola da esquerda
        // e o bairro daquela MESMA linha. Nao existe chance de pegar H-40 para I-01.
        RouteParser.parsePlainTexts(reconstructedRows)?.let { return it }

        // Fallback geometrico caso alguma tabela tenha OCR muito fragmentado.
        val screenItems = parts.map { part ->
            ScreenText(
                text = part.text,
                left = part.rect.left,
                top = part.rect.top,
                right = part.rect.right,
                bottom = part.rect.bottom
            )
        }

        return RouteParser.parseImageScreenTexts(screenItems)
    }
'''

s = s[:start] + new_parse + s[end:]
service_path.write_text(s, encoding="utf-8")
print("Patch v0.12 aplicado: OCR reconstrui linhas visuais da tabela antes de escolher bairro/gaiola")
