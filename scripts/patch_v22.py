from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
parser_path = Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")

s = service_path.read_text(encoding="utf-8")
p = parser_path.read_text(encoding="utf-8")

# v0.22 - GRID-FIRST EM DUAS ETAPAS PARA TABELA DENSA
#
# O teste mostrou algo importante: a MESMA planilha pode ler ou nao dependendo
# de poucos pixels cortados no topo. Isso indica que nao devemos deixar o OCR
# decidir a linha inteira da tabela compactada.
#
# Nesta versao, para planilhas densas/baixas:
#   1) detecta a grade preta diretamente pelos pixels, sem depender do cabecalho
#      nem da coluna verde Agencia;
#   2) ignora linhas parcialmente cortadas no topo/rodape usando apenas os
#      intervalos ENTRE linhas horizontais reais da grade;
#   3) OCR SOMENTE da coluna Bairro e escolhe a maior prioridade;
#   4) pela coordenada Y do bairro, descobre exatamente qual linha da grade e;
#   5) OCR SOMENTE da celula Gaiola daquela linha.
#
# Assim o bairro e a gaiola nunca precisam ser reconhecidos no mesmo OCR e o
# recorte no topo deixa de alterar o pareamento. Se esse caminho nao fechar,
# preserva o fallback reforcado da v0.19/v0.21. Texto e envio nao sao alterados.

# -----------------------------------------------------------------------------
# Expor somente o casamento de prioridade que ja existe no RouteParser.
# A ordem da lista permanece exatamente a mesma.
# -----------------------------------------------------------------------------
priority_anchor = '''    private fun priorityFor(text: String): Pair<Int, String>? {\n        val normalized = normalize(text)\n        if (normalized.isBlank()) return null\n\n        priorities.forEachIndexed { index, rule ->\n            if (rule.requiredTokens.all { normalized.contains(it) }) {\n                return index to rule.name\n            }\n        }\n\n        return null\n    }\n'''

priority_replacement = priority_anchor + '''\n    fun matchPriority(text: String): Pair<Int, String>? {\n        return priorityFor(text)\n    }\n'''

if 'fun matchPriority(text: String)' not in p:
    if priority_anchor not in p:
        raise SystemExit('Patch v0.22: priorityFor nao encontrado')
    p = p.replace(priority_anchor, priority_replacement, 1)

parser_path.write_text(p, encoding="utf-8")

# -----------------------------------------------------------------------------
# Helpers grid-first. Inserimos antes do readMediaLargeColorCrop da v0.21.
# -----------------------------------------------------------------------------
insert_at = s.find('    private fun readMediaLargeColorCrop(media: MediaImage) {')
if insert_at < 0:
    raise SystemExit('Patch v0.22: readMediaLargeColorCrop nao encontrado')

helpers = r'''    private data class DenseGridLayout(
        val gaiolaRight: Int,
        val bairroLeft: Int,
        val bairroRight: Int,
        val horizontalLines: List<Int>,
        val rowCount: Int,
        val rowSpacing: Float,
        val scanMs: Long
    )

    private fun darkPixel(pixel: Int): Boolean {
        val r = (pixel shr 16) and 0xFF
        val g = (pixel shr 8) and 0xFF
        val b = pixel and 0xFF
        return r <= 130 && g <= 130 && b <= 130
    }

    private fun clusterCoordinates(values: List<Int>, maxGap: Int = 2): List<Int> {
        if (values.isEmpty()) return emptyList()

        val groups = mutableListOf<MutableList<Int>>()
        for (value in values.sorted()) {
            val last = groups.lastOrNull()
            if (last == null || value - last.last() > maxGap) {
                groups += mutableListOf(value)
            } else {
                last += value
            }
        }

        return groups.map { group -> group.average().toInt() }
    }

    private fun detectDenseGridLayout(source: Bitmap): DenseGridLayout? {
        val started = SystemClock.elapsedRealtime()
        val w = source.width
        val h = source.height

        if (w < 750 || h < 280) return null

        // ---------- LINHAS VERTICAIS ----------
        // Uma borda de coluna fica escura praticamente em toda a altura, enquanto
        // letras so ocupam pequenos trechos. 52% tolera cabecalho, recorte parcial
        // no topo e pequenas falhas/antialias da grade.
        val yStep = 3
        val sampledY = ((h + yStep - 1) / yStep).coerceAtLeast(1)
        val minVerticalHits = maxOf(24, (sampledY * 0.52f).toInt())
        val rawVertical = mutableListOf<Int>()

        var x = 1
        while (x < w - 1) {
            var hits = 0
            var y = 0
            while (y < h) {
                if (darkPixel(source.getPixel(x, y))) hits++
                y += yStep
            }
            if (hits >= minVerticalHits) rawVertical += x
            x++
        }

        val vertical = clusterCoordinates(rawVertical)
        if (vertical.size < 5) return null

        // Layout observado nas rotas:
        // Gaiola termina perto de 5-7%.
        // Bairro ocupa aproximadamente 30-47% e termina na divisoria da Agencia.
        val gaiolaCandidates = vertical.filter {
            val r = it.toFloat() / w.toFloat()
            r in 0.030f..0.120f
        }
        val gaiolaRight = gaiolaCandidates.minByOrNull {
            kotlin.math.abs(it.toFloat() / w.toFloat() - 0.060f)
        } ?: return null

        val bairroRightCandidates = vertical.filter {
            val r = it.toFloat() / w.toFloat()
            r in 0.420f..0.550f
        }
        val bairroRight = bairroRightCandidates.minByOrNull {
            kotlin.math.abs(it.toFloat() / w.toFloat() - 0.470f)
        } ?: return null

        val bairroLeft = vertical
            .filter { it < bairroRight - maxOf(70, (w * 0.075f).toInt()) }
            .filter {
                val widthRatio = (bairroRight - it).toFloat() / w.toFloat()
                widthRatio in 0.110f..0.220f
            }
            .maxOrNull()
            ?: return null

        if (bairroLeft <= gaiolaRight) return null

        // ---------- LINHAS HORIZONTAIS ----------
        // As bordas horizontais atravessam uma parte enorme da largura. Mesmo com
        // texto e celulas coloridas, 35% de pixels escuros e suficiente para
        // diferenciar a grade das letras.
        val xStep = 4
        val sampledX = ((w + xStep - 1) / xStep).coerceAtLeast(1)
        val minHorizontalHits = maxOf(35, (sampledX * 0.35f).toInt())
        val rawHorizontal = mutableListOf<Int>()

        var y = 0
        while (y < h) {
            var hits = 0
            x = 0
            while (x < w) {
                if (darkPixel(source.getPixel(x, y))) hits++
                x += xStep
            }
            if (hits >= minHorizontalHits) rawHorizontal += y
            y++
        }

        val horizontal = clusterCoordinates(rawHorizontal)
            .filter { it in 0 until h }
            .sorted()

        if (horizontal.size < 12) return null

        val spacings = horizontal.zipWithNext()
            .map { (a, b) -> b - a }
            .filter { it in 7..45 }
            .sorted()

        if (spacings.size < 8) return null

        val rowSpacing = spacings[spacings.size / 2].toFloat()

        // Mantem somente separacoes coerentes com o passo mediano. Isso elimina
        // qualquer falsa linha escura eventual e tambem deixa o topo cortado fora.
        val clean = mutableListOf<Int>()
        for (value in horizontal) {
            if (clean.isEmpty()) {
                clean += value
            } else {
                val d = value - clean.last()
                if (d >= maxOf(5, (rowSpacing * 0.55f).toInt())) {
                    clean += value
                }
            }
        }

        if (clean.size < 12) return null

        val rowCount = clean.size - 1
        if (rowCount < 10) return null

        return DenseGridLayout(
            gaiolaRight = gaiolaRight,
            bairroLeft = bairroLeft,
            bairroRight = bairroRight,
            horizontalLines = clean,
            rowCount = rowCount,
            rowSpacing = rowSpacing,
            scanMs = SystemClock.elapsedRealtime() - started
        )
    }

    private fun scaledCrop(
        source: Bitmap,
        src: Rect,
        scale: Float
    ): Bitmap? {
        if (src.width() <= 1 || src.height() <= 1) return null

        val crop = try {
            Bitmap.createBitmap(
                source,
                src.left,
                src.top,
                src.width(),
                src.height()
            )
        } catch (_: Throwable) {
            return null
        }

        if (scale <= 1.03f) return crop

        val scaled = try {
            Bitmap.createScaledBitmap(
                crop,
                (crop.width * scale).toInt().coerceAtLeast(1),
                (crop.height * scale).toInt().coerceAtLeast(1),
                true
            )
        } catch (_: Throwable) {
            crop
        }

        if (scaled !== crop) {
            try { crop.recycle() } catch (_: Throwable) {}
        }

        return scaled
    }

    private fun readDenseGridTwoStage(
        media: MediaImage,
        source: Bitmap,
        decodeMs: Long
    ): Boolean {
        if (!processing) return false
        if (source.height > 1_200) return false

        val layout = detectDenseGridLayout(source) ?: return false
        if (layout.rowCount < 18) return false

        val yTop = layout.horizontalLines.first().coerceIn(0, source.height - 2)
        val yBottom = layout.horizontalLines.last().coerceIn(yTop + 2, source.height)

        // Mira ~34 px por linha no OCR do Bairro. Como a coluna e estreita, isso
        // continua leve mesmo em 30-40 linhas.
        var bairroScale = (34f / layout.rowSpacing).coerceIn(1.35f, 2.45f)
        val sourceHeight = (yBottom - yTop).coerceAtLeast(1)
        if (sourceHeight * bairroScale > 2_100f) {
            bairroScale = 2_100f / sourceHeight.toFloat()
        }
        bairroScale = bairroScale.coerceAtLeast(1f)

        val bairroRect = Rect(
            (layout.bairroLeft + 1).coerceIn(0, source.width - 2),
            yTop,
            layout.bairroRight.coerceIn(layout.bairroLeft + 2, source.width),
            yBottom
        )

        val bairroBitmap = scaledCrop(source, bairroRect, bairroScale) ?: return false
        val bairroInput = InputImage.fromBitmap(bairroBitmap, 0)
        val bairroStarted = SystemClock.elapsedRealtime()

        Prefs.setStatus(
            this,
            "GRID 2X: ${layout.rowCount} linhas | OCR Bairro x" +
                String.format(java.util.Locale.US, "%.2f", bairroScale) + "..."
        )

        recognizer.process(bairroInput)
            .addOnSuccessListener { visionText ->
                if (!processing) {
                    try { bairroBitmap.recycle() } catch (_: Throwable) {}
                    try { source.recycle() } catch (_: Throwable) {}
                    return@addOnSuccessListener
                }

                data class BairroHit(
                    val priority: Int,
                    val name: String,
                    val centerYScaled: Int,
                    val raw: String
                )

                val hits = mutableListOf<BairroHit>()

                for (block in visionText.textBlocks) {
                    for (line in block.lines) {
                        val box = line.boundingBox ?: continue
                        val priority = RouteParser.matchPriority(line.text) ?: continue
                        hits += BairroHit(
                            priority = priority.first,
                            name = priority.second,
                            centerYScaled = box.centerY(),
                            raw = line.text
                        )
                    }
                }

                // Caso o ML Kit tenha agrupado uma celula em bloco estranho, tenta
                // tambem o texto completo de cada bloco, usando o centro do bloco.
                if (hits.isEmpty()) {
                    for (block in visionText.textBlocks) {
                        val box = block.boundingBox ?: continue
                        val priority = RouteParser.matchPriority(block.text) ?: continue
                        hits += BairroHit(
                            priority = priority.first,
                            name = priority.second,
                            centerYScaled = box.centerY(),
                            raw = block.text
                        )
                    }
                }

                val bairroMs = SystemClock.elapsedRealtime() - bairroStarted
                try { bairroBitmap.recycle() } catch (_: Throwable) {}

                val chosen = hits.minWithOrNull(
                    compareBy<BairroHit>({ it.priority }, { it.centerYScaled })
                )

                if (chosen == null) {
                    try { source.recycle() } catch (_: Throwable) {}
                    Prefs.setStatus(
                        this,
                        "GRID 2X nao achou bairro prioritario. Fallback reforcado..."
                    )
                    readMediaEnhanced(media)
                    return@addOnSuccessListener
                }

                val originalY = (
                    yTop + chosen.centerYScaled.toFloat() / bairroScale
                ).toInt()

                val rowIndex = layout.horizontalLines
                    .zipWithNext()
                    .indexOfFirst { (a, b) -> originalY >= a && originalY <= b }

                val safeRowIndex = if (rowIndex >= 0) {
                    rowIndex
                } else {
                    layout.horizontalLines.zipWithNext()
                        .mapIndexed { index, (a, b) ->
                            index to kotlin.math.abs(((a + b) / 2) - originalY)
                        }
                        .minByOrNull { it.second }
                        ?.first ?: -1
                }

                if (safeRowIndex < 0 || safeRowIndex >= layout.horizontalLines.lastIndex) {
                    try { source.recycle() } catch (_: Throwable) {}
                    readMediaEnhanced(media)
                    return@addOnSuccessListener
                }

                val rowY1 = (layout.horizontalLines[safeRowIndex] + 1)
                    .coerceIn(0, source.height - 2)
                val rowY2 = (layout.horizontalLines[safeRowIndex + 1] - 1)
                    .coerceIn(rowY1 + 1, source.height)
                val rowHeight = (rowY2 - rowY1).coerceAtLeast(1)

                var gaiolaScale = (84f / rowHeight.toFloat()).coerceIn(3.0f, 5.2f)
                val cageWidth = layout.gaiolaRight.coerceAtLeast(2)
                if (cageWidth * gaiolaScale > 520f) {
                    gaiolaScale = 520f / cageWidth.toFloat()
                }
                gaiolaScale = gaiolaScale.coerceAtLeast(2.5f)

                val gaiolaRect = Rect(
                    0,
                    rowY1,
                    (layout.gaiolaRight + 1).coerceIn(2, source.width),
                    rowY2
                )

                val gaiolaBitmap = scaledCrop(source, gaiolaRect, gaiolaScale)
                try { source.recycle() } catch (_: Throwable) {}

                if (gaiolaBitmap == null) {
                    readMediaEnhanced(media)
                    return@addOnSuccessListener
                }

                val gaiolaStarted = SystemClock.elapsedRealtime()
                val gaiolaInput = InputImage.fromBitmap(gaiolaBitmap, 0)

                Prefs.setStatus(
                    this,
                    "GRID 2X: ${chosen.name} linha ${safeRowIndex + 1}; OCR Gaiola..."
                )

                recognizer.process(gaiolaInput)
                    .addOnSuccessListener { cageText ->
                        if (!processing) {
                            try { gaiolaBitmap.recycle() } catch (_: Throwable) {}
                            return@addOnSuccessListener
                        }

                        val gaiolaMs = SystemClock.elapsedRealtime() - gaiolaStarted
                        val cage = RouteParser.extractCage(cageText.text)
                            ?: cageText.textBlocks
                                .asSequence()
                                .flatMap { it.lines.asSequence() }
                                .mapNotNull { RouteParser.extractCage(it.text) }
                                .firstOrNull()

                        try { gaiolaBitmap.recycle() } catch (_: Throwable) {}

                        if (cage != null) {
                            val route = RouteResult(
                                neighborhood = chosen.name,
                                cage = cage,
                                priorityIndex = chosen.priority
                            )

                            if (isDuplicate(route)) {
                                finishFileOnlyFailure(
                                    "Arquivo repetido ignorado | GRID 2X"
                                )
                            } else {
                                Prefs.setStatus(
                                    this,
                                    "GRID 2X: ${route.neighborhood} -> ${route.cage} | " +
                                        "decode=${decodeMs}ms grid=${layout.scanMs}ms " +
                                        "bairro=${bairroMs}ms gaiola=${gaiolaMs}ms | enviando"
                                )
                                sendRouteInCurrentChat(route)
                            }
                        } else {
                            Prefs.setStatus(
                                this,
                                "GRID 2X achou ${chosen.name}, mas nao leu a gaiola. " +
                                    "Fallback reforcado..."
                            )
                            readMediaEnhanced(media)
                        }
                    }
                    .addOnFailureListener {
                        try { gaiolaBitmap.recycle() } catch (_: Throwable) {}
                        if (!processing) return@addOnFailureListener
                        readMediaEnhanced(media)
                    }
            }
            .addOnFailureListener {
                try { bairroBitmap.recycle() } catch (_: Throwable) {}
                try { source.recycle() } catch (_: Throwable) {}
                if (!processing) return@addOnFailureListener
                readMediaEnhanced(media)
            }

        return true
    }

'''

s = s[:insert_at] + helpers + s[insert_at:]

# -----------------------------------------------------------------------------
# Tenta GRID 2X logo apos decodificar o arquivo e ANTES de depender de Agency.
# Se nao for uma tabela densa compativel, retorna false e a v0.21 segue igual.
# -----------------------------------------------------------------------------
old = '''        val decodeMs = SystemClock.elapsedRealtime() - decodeStarted\n        val detected = detectLargeTableCrop(source)\n'''
new = '''        val decodeMs = SystemClock.elapsedRealtime() - decodeStarted\n\n        if (readDenseGridTwoStage(media, source, decodeMs)) {\n            return\n        }\n\n        val detected = detectLargeTableCrop(source)\n'''

if old not in s:
    raise SystemExit('Patch v0.22: ponto apos decode nao encontrado')
s = s.replace(old, new, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.22 aplicado: grade independente do topo + OCR Bairro e Gaiola em duas etapas")
