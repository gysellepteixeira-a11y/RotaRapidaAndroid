from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.23 - NORMALIZA CADA LINHA DO BAIRRO ANTES DO OCR
#
# Os testes mostraram que a mesma planilha pode falhar ou funcionar dependendo
# de poucos pixels cortados no topo. A grade da v0.22 e detectada corretamente,
# mas o ML Kit ainda recebe uma coluna Bairro muito densa, com 30-40 linhas
# espremidas. Nesta versao, para 31+ linhas:
#   1) detecta a grade como na v0.22;
#   2) recorta CADA celula de Bairro entre duas linhas horizontais reais;
#   3) redimensiona cada celula para a mesma altura e cola em uma folha branca,
#      com espacamento entre linhas e sem as linhas pretas da planilha;
#   4) OCR nessa folha limpa para escolher o bairro pela prioridade;
#   5) le somente a celula Gaiola da linha escolhida, tambem ampliada e sem grade.
#
# A partir de 31 linhas usamos este caminho. Tabelas de 29/30 linhas continuam
# no caminho rapido da v0.19 que nos testes ficou em ~1.2-1.4 s.

start = s.find('    private fun readDenseGridTwoStage(\n')
end = s.find('\n    private fun readMediaLargeColorCrop(media: MediaImage) {', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'Patch v0.23: readDenseGridTwoStage nao encontrado (start={start}, end={end})'
    )

new_block = r'''    private data class NormalizedNeighborhoodSheet(
        val bitmap: Bitmap,
        val rowPitch: Int,
        val topPad: Int,
        val rowCount: Int,
        val textHeight: Int
    )

    private fun buildNormalizedNeighborhoodSheet(
        source: Bitmap,
        layout: DenseGridLayout
    ): NormalizedNeighborhoodSheet? {
        val rows = layout.horizontalLines.zipWithNext()
        if (rows.size < 31) return null

        val bairroX1 = (layout.bairroLeft + 2).coerceIn(0, source.width - 3)
        val bairroX2 = (layout.bairroRight - 2).coerceIn(bairroX1 + 2, source.width)
        val bairroWidth = bairroX2 - bairroX1
        if (bairroWidth < 70) return null

        val innerHeights = rows
            .map { (a, b) -> (b - a - 2).coerceAtLeast(1) }
            .sorted()
        if (innerHeights.isEmpty()) return null

        val medianInnerHeight = innerHeights[innerHeights.size / 2].coerceAtLeast(1)

        // 40 px de altura util por bairro ja deixa a fonte muito mais legivel.
        // O espacamento branco impede o ML Kit de fundir duas linhas vizinhas.
        val textHeight = 40
        val rowGap = 7
        val topPad = 8
        val sidePad = 10
        val rowPitch = textHeight + rowGap

        val scale = textHeight.toFloat() / medianInnerHeight.toFloat()
        val scaledBairroWidth = (bairroWidth * scale)
            .toInt()
            .coerceIn(300, 700)

        val outWidth = scaledBairroWidth + sidePad * 2
        val outHeight = topPad * 2 + rows.size * rowPitch - rowGap

        // Mantem a imagem confortavelmente dentro do que o ML Kit lida bem.
        if (outHeight > 2_200 || outWidth > 900) return null

        val sheet = try {
            Bitmap.createBitmap(
                outWidth,
                outHeight,
                Bitmap.Config.ARGB_8888
            )
        } catch (_: Throwable) {
            return null
        }

        val canvas = Canvas(sheet)
        canvas.drawColor(Color.WHITE)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG)

        rows.forEachIndexed { index, (a, b) ->
            val y1 = (a + 1).coerceIn(0, source.height - 2)
            val y2 = (b - 1).coerceIn(y1 + 1, source.height)
            val innerHeight = y2 - y1
            if (innerHeight <= 1) return@forEachIndexed

            val cell = try {
                Bitmap.createBitmap(
                    source,
                    bairroX1,
                    y1,
                    bairroWidth,
                    innerHeight
                )
            } catch (_: Throwable) {
                null
            } ?: return@forEachIndexed

            // FILTER=false preserva os tracos finos da fonte original. Nos testes
            // visuais ficou mais nitido que interpolar uma linha de 15-18 px.
            val scaled = try {
                Bitmap.createScaledBitmap(
                    cell,
                    scaledBairroWidth,
                    textHeight,
                    false
                )
            } catch (_: Throwable) {
                cell
            }

            val dstTop = topPad + index * rowPitch
            canvas.drawBitmap(
                scaled,
                sidePad.toFloat(),
                dstTop.toFloat(),
                paint
            )

            if (scaled !== cell) {
                try { scaled.recycle() } catch (_: Throwable) {}
            }
            try { cell.recycle() } catch (_: Throwable) {}
        }

        return NormalizedNeighborhoodSheet(
            bitmap = sheet,
            rowPitch = rowPitch,
            topPad = topPad,
            rowCount = rows.size,
            textHeight = textHeight
        )
    }

    private fun buildNormalizedCageBitmap(
        source: Bitmap,
        layout: DenseGridLayout,
        rowIndex: Int
    ): Bitmap? {
        if (rowIndex !in 0 until layout.horizontalLines.lastIndex) return null

        val y1 = (layout.horizontalLines[rowIndex] + 1)
            .coerceIn(0, source.height - 2)
        val y2 = (layout.horizontalLines[rowIndex + 1] - 1)
            .coerceIn(y1 + 1, source.height)

        val x1 = 1
        val x2 = (layout.gaiolaRight - 1).coerceIn(x1 + 2, source.width)
        val cellWidth = x2 - x1
        val cellHeight = y2 - y1
        if (cellWidth < 15 || cellHeight < 4) return null

        val targetHeight = 92
        val scale = targetHeight.toFloat() / cellHeight.toFloat()
        val targetWidth = (cellWidth * scale).toInt().coerceIn(160, 480)
        val pad = 14

        val cell = try {
            Bitmap.createBitmap(source, x1, y1, cellWidth, cellHeight)
        } catch (_: Throwable) {
            return null
        }

        val scaled = try {
            Bitmap.createScaledBitmap(
                cell,
                targetWidth,
                targetHeight,
                false
            )
        } catch (_: Throwable) {
            cell
        }

        val out = try {
            Bitmap.createBitmap(
                targetWidth + pad * 2,
                targetHeight + pad * 2,
                Bitmap.Config.ARGB_8888
            )
        } catch (_: Throwable) {
            if (scaled !== cell) {
                try { scaled.recycle() } catch (_: Throwable) {}
            }
            try { cell.recycle() } catch (_: Throwable) {}
            return null
        }

        val canvas = Canvas(out)
        canvas.drawColor(Color.WHITE)
        canvas.drawBitmap(scaled, pad.toFloat(), pad.toFloat(), Paint(Paint.ANTI_ALIAS_FLAG))

        if (scaled !== cell) {
            try { scaled.recycle() } catch (_: Throwable) {}
        }
        try { cell.recycle() } catch (_: Throwable) {}

        return out
    }

    private fun readDenseGridTwoStage(
        media: MediaImage,
        source: Bitmap,
        decodeMs: Long
    ): Boolean {
        if (!processing) return false
        if (source.height > 1_200) return false

        val layout = detectDenseGridLayout(source) ?: return false

        // 29/30 linhas ja estao muito rapidas no caminho da v0.19. O novo modo
        // serve para as tabelas mais densas que ainda estavam falhando.
        if (layout.rowCount < 31) return false

        val sheet = buildNormalizedNeighborhoodSheet(source, layout) ?: return false
        val started = SystemClock.elapsedRealtime()
        val input = InputImage.fromBitmap(sheet.bitmap, 0)

        Prefs.setStatus(
            this,
            "GRID NORM: ${layout.rowCount} linhas | bairros separados | OCR..."
        )

        recognizer.process(input)
            .addOnSuccessListener { visionText ->
                if (!processing) {
                    try { sheet.bitmap.recycle() } catch (_: Throwable) {}
                    try { source.recycle() } catch (_: Throwable) {}
                    return@addOnSuccessListener
                }

                data class BairroHit(
                    val priority: Int,
                    val name: String,
                    val rowIndex: Int,
                    val raw: String
                )

                val hits = mutableListOf<BairroHit>()

                fun addHit(text: String, box: Rect?) {
                    if (box == null) return
                    val priority = RouteParser.matchPriority(text) ?: return

                    val row = ((box.centerY() - sheet.topPad) / sheet.rowPitch)
                        .coerceIn(0, sheet.rowCount - 1)

                    hits += BairroHit(
                        priority = priority.first,
                        name = priority.second,
                        rowIndex = row,
                        raw = text
                    )
                }

                for (block in visionText.textBlocks) {
                    for (line in block.lines) {
                        addHit(line.text, line.boundingBox)
                    }
                }

                if (hits.isEmpty()) {
                    for (block in visionText.textBlocks) {
                        addHit(block.text, block.boundingBox)
                    }
                }

                val bairroMs = SystemClock.elapsedRealtime() - started
                try { sheet.bitmap.recycle() } catch (_: Throwable) {}

                val chosen = hits.minWithOrNull(
                    compareBy<BairroHit>({ it.priority }, { it.rowIndex })
                )

                if (chosen == null) {
                    try { source.recycle() } catch (_: Throwable) {}
                    Prefs.setStatus(
                        this,
                        "GRID NORM nao achou bairro prioritario. Fallback reforcado..."
                    )
                    readMediaEnhanced(media)
                    return@addOnSuccessListener
                }

                val cageBitmap = buildNormalizedCageBitmap(
                    source = source,
                    layout = layout,
                    rowIndex = chosen.rowIndex
                )

                try { source.recycle() } catch (_: Throwable) {}

                if (cageBitmap == null) {
                    readMediaEnhanced(media)
                    return@addOnSuccessListener
                }

                val cageStarted = SystemClock.elapsedRealtime()
                val cageInput = InputImage.fromBitmap(cageBitmap, 0)

                Prefs.setStatus(
                    this,
                    "GRID NORM: ${chosen.name} linha ${chosen.rowIndex + 1}; OCR Gaiola..."
                )

                recognizer.process(cageInput)
                    .addOnSuccessListener { cageText ->
                        if (!processing) {
                            try { cageBitmap.recycle() } catch (_: Throwable) {}
                            return@addOnSuccessListener
                        }

                        val cageMs = SystemClock.elapsedRealtime() - cageStarted
                        val cage = RouteParser.extractCage(cageText.text)
                            ?: cageText.textBlocks
                                .asSequence()
                                .flatMap { it.lines.asSequence() }
                                .mapNotNull { RouteParser.extractCage(it.text) }
                                .firstOrNull()

                        try { cageBitmap.recycle() } catch (_: Throwable) {}

                        if (cage != null) {
                            val route = RouteResult(
                                neighborhood = chosen.name,
                                cage = cage,
                                priorityIndex = chosen.priority
                            )

                            if (isDuplicate(route)) {
                                finishFileOnlyFailure(
                                    "Arquivo repetido ignorado | GRID NORM"
                                )
                            } else {
                                Prefs.setStatus(
                                    this,
                                    "GRID NORM: ${route.neighborhood} -> ${route.cage} | " +
                                        "decode=${decodeMs}ms grid=${layout.scanMs}ms " +
                                        "bairro=${bairroMs}ms gaiola=${cageMs}ms | enviando"
                                )
                                sendRouteInCurrentChat(route)
                            }
                        } else {
                            Prefs.setStatus(
                                this,
                                "GRID NORM achou ${chosen.name}, mas nao leu a gaiola. " +
                                    "Fallback reforcado..."
                            )
                            readMediaEnhanced(media)
                        }
                    }
                    .addOnFailureListener {
                        try { cageBitmap.recycle() } catch (_: Throwable) {}
                        if (!processing) return@addOnFailureListener
                        readMediaEnhanced(media)
                    }
            }
            .addOnFailureListener {
                try { sheet.bitmap.recycle() } catch (_: Throwable) {}
                try { source.recycle() } catch (_: Throwable) {}
                if (!processing) return@addOnFailureListener
                readMediaEnhanced(media)
            }

        return true
    }

'''

s = s[:start] + new_block + s[end:]
service_path.write_text(s, encoding="utf-8")
print("Patch v0.23 aplicado: 31+ linhas usam bairros normalizados por celula + gaiola isolada")
