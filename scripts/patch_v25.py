from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.25 - HIBRIDA PARA TABELAS DENSAS
#
# Descobrimos pelos testes que a mesma imagem de 31 linhas que lia na v0.22
# deixou de ler na v0.24. Portanto:
#   - 31 a 33 linhas: volta EXATAMENTE para a estrategia da v0.22
#     (OCR somente Bairro -> acha a linha -> OCR somente Gaiola daquela linha).
#   - 34+ linhas: nao reorganiza mais as celulas em paineis artificiais.
#     Divide a planilha ORIGINAL em fatias horizontais de no maximo 14 linhas,
#     preservando a aparencia real da tabela. E o mesmo efeito do teste manual
#     em que cortar algumas linhas de cima fez o OCR funcionar.
#   - 29/30 linhas continuam no caminho rapido da v0.19.
#
# As prioridades removidas na v0.24 permanecem removidas.

start = s.find('    private fun readDenseGridTwoStage(\n')
end = s.find('\n    private fun readMediaLargeColorCrop(media: MediaImage) {', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'Patch v0.25: readDenseGridTwoStage nao encontrado (start={start}, end={end})'
    )

new_block = r'''    private data class DenseRouteChunk(
        val bitmap: Bitmap,
        val firstRow: Int,
        val rowCount: Int
    )

    private fun readDenseGridClassicV22(
        media: MediaImage,
        source: Bitmap,
        decodeMs: Long,
        layout: DenseGridLayout
    ) {
        val yTop = layout.horizontalLines.first().coerceIn(0, source.height - 2)
        val yBottom = layout.horizontalLines.last().coerceIn(yTop + 2, source.height)

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

        val bairroBitmap = scaledCrop(source, bairroRect, bairroScale)
        if (bairroBitmap == null) {
            try { source.recycle() } catch (_: Throwable) {}
            readMediaEnhanced(media)
            return
        }

        val bairroInput = InputImage.fromBitmap(bairroBitmap, 0)
        val bairroStarted = SystemClock.elapsedRealtime()

        Prefs.setStatus(
            this,
            "GRID 31: ${layout.rowCount} linhas | OCR Bairro x" +
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
                    val centerYScaled: Int
                )

                val hits = mutableListOf<BairroHit>()

                fun addHit(text: String, box: Rect?) {
                    if (box == null) return
                    val priority = RouteParser.matchPriority(text) ?: return
                    hits += BairroHit(
                        priority = priority.first,
                        name = priority.second,
                        centerYScaled = box.centerY()
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

                val bairroMs = SystemClock.elapsedRealtime() - bairroStarted
                try { bairroBitmap.recycle() } catch (_: Throwable) {}

                val chosen = hits.minWithOrNull(
                    compareBy<BairroHit>({ it.priority }, { it.centerYScaled })
                )

                if (chosen == null) {
                    try { source.recycle() } catch (_: Throwable) {}
                    Prefs.setStatus(
                        this,
                        "GRID 31 nao achou bairro prioritario. Fallback reforcado..."
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

                val cageBitmap = buildPanelCageBitmap(
                    source = source,
                    layout = layout,
                    rowIndex = safeRowIndex
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
                    "GRID 31: ${chosen.name} linha ${safeRowIndex + 1}; OCR Gaiola..."
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
                                    "Arquivo repetido ignorado | GRID 31"
                                )
                            } else {
                                Prefs.setStatus(
                                    this,
                                    "GRID 31: ${route.neighborhood} -> ${route.cage} | " +
                                        "decode=${decodeMs}ms grid=${layout.scanMs}ms " +
                                        "bairro=${bairroMs}ms gaiola=${cageMs}ms | enviando"
                                )
                                sendRouteInCurrentChat(route)
                            }
                        } else {
                            Prefs.setStatus(
                                this,
                                "GRID 31 achou ${chosen.name}, mas nao leu gaiola. " +
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
                try { bairroBitmap.recycle() } catch (_: Throwable) {}
                try { source.recycle() } catch (_: Throwable) {}
                if (!processing) return@addOnFailureListener
                readMediaEnhanced(media)
            }
    }

    private fun buildDenseRouteChunks(
        source: Bitmap,
        layout: DenseGridLayout
    ): List<DenseRouteChunk>? {
        val rows = layout.horizontalLines.zipWithNext()
        if (rows.size < 34) return null

        // Mantemos no maximo 14 linhas por OCR. A imagem continua com a mesma
        // estrutura real da planilha; apenas cortamos verticalmente em partes.
        val maxRows = 14
        val result = mutableListOf<DenseRouteChunk>()
        val x1 = 0
        val x2 = (layout.bairroRight + 4).coerceIn(2, source.width)

        var first = 0
        while (first < rows.size) {
            val lastExclusive = minOf(first + maxRows, rows.size)
            val y1 = (rows[first].first + 1).coerceIn(0, source.height - 2)
            val y2 = (rows[lastExclusive - 1].second - 1)
                .coerceIn(y1 + 2, source.height)

            val crop = try {
                Bitmap.createBitmap(
                    source,
                    x1,
                    y1,
                    x2 - x1,
                    y2 - y1
                )
            } catch (_: Throwable) {
                null
            }

            if (crop == null) {
                result.forEach {
                    try { it.bitmap.recycle() } catch (_: Throwable) {}
                }
                return null
            }

            var scale = (34f / layout.rowSpacing).coerceIn(1.45f, 2.10f)
            val biggest = maxOf(crop.width, crop.height).toFloat()
            if (biggest * scale > 1_650f) {
                scale = 1_650f / biggest
            }
            scale = scale.coerceAtLeast(1.15f)

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

            result += DenseRouteChunk(
                bitmap = scaled,
                firstRow = first,
                rowCount = lastExclusive - first
            )

            first = lastExclusive
        }

        return result
    }

    private fun readDenseGridChunks(
        media: MediaImage,
        source: Bitmap,
        decodeMs: Long,
        layout: DenseGridLayout
    ) {
        val chunks = buildDenseRouteChunks(source, layout)
        try { source.recycle() } catch (_: Throwable) {}

        if (chunks.isNullOrEmpty()) {
            readMediaEnhanced(media)
            return
        }

        var bestRoute: RouteResult? = null
        var totalOcrMs = 0L

        fun finishChunks() {
            if (!processing) return

            val route = bestRoute
            if (route == null) {
                Prefs.setStatus(
                    this,
                    "GRID FATIAS ${layout.rowCount}: nenhuma prioridade encontrada. " +
                        "Fallback reforcado..."
                )
                readMediaEnhanced(media)
                return
            }

            if (isDuplicate(route)) {
                finishFileOnlyFailure(
                    "Arquivo repetido ignorado | GRID FATIAS"
                )
            } else {
                Prefs.setStatus(
                    this,
                    "GRID FATIAS ${layout.rowCount}: ${route.neighborhood} -> ${route.cage} | " +
                        "decode=${decodeMs}ms grid=${layout.scanMs}ms OCR=${totalOcrMs}ms | enviando"
                )
                sendRouteInCurrentChat(route)
            }
        }

        fun processChunk(index: Int) {
            if (!processing) {
                for (i in index until chunks.size) {
                    try { chunks[i].bitmap.recycle() } catch (_: Throwable) {}
                }
                return
            }

            if (index >= chunks.size) {
                finishChunks()
                return
            }

            val chunk = chunks[index]
            val started = SystemClock.elapsedRealtime()

            Prefs.setStatus(
                this,
                "GRID FATIAS: ${layout.rowCount} linhas | parte ${index + 1}/${chunks.size} " +
                    "(${chunk.rowCount} linhas)..."
            )

            recognizer.process(InputImage.fromBitmap(chunk.bitmap, 0))
                .addOnSuccessListener { visionText ->
                    val elapsed = SystemClock.elapsedRealtime() - started
                    totalOcrMs += elapsed

                    if (processing) {
                        val route = parseVisionText(visionText, chunk.bitmap.height)
                        if (route != null &&
                            (bestRoute == null || route.priorityIndex < bestRoute!!.priorityIndex)
                        ) {
                            bestRoute = route
                        }
                    }

                    try { chunk.bitmap.recycle() } catch (_: Throwable) {}

                    // Valparaiso e prioridade 0: nao existe bairro que possa
                    // superar esse resultado, entao podemos terminar cedo.
                    if (processing && bestRoute?.priorityIndex == 0) {
                        for (i in (index + 1) until chunks.size) {
                            try { chunks[i].bitmap.recycle() } catch (_: Throwable) {}
                        }
                        finishChunks()
                    } else {
                        processChunk(index + 1)
                    }
                }
                .addOnFailureListener {
                    totalOcrMs += SystemClock.elapsedRealtime() - started
                    try { chunk.bitmap.recycle() } catch (_: Throwable) {}
                    if (!processing) return@addOnFailureListener
                    processChunk(index + 1)
                }
        }

        processChunk(0)
    }

    private fun readDenseGridTwoStage(
        media: MediaImage,
        source: Bitmap,
        decodeMs: Long
    ): Boolean {
        if (!processing) return false
        if (source.height > 1_200) return false

        val layout = detectDenseGridLayout(source) ?: return false

        // 29/30 continuam no caminho rapido da v0.19.
        if (layout.rowCount < 31) return false

        if (layout.rowCount <= 33) {
            readDenseGridClassicV22(
                media = media,
                source = source,
                decodeMs = decodeMs,
                layout = layout
            )
        } else {
            readDenseGridChunks(
                media = media,
                source = source,
                decodeMs = decodeMs,
                layout = layout
            )
        }

        return true
    }

'''

s = s[:start] + new_block + s[end:]
service_path.write_text(s, encoding="utf-8")
print("Patch v0.25 aplicado: 31-33 volta ao GRID v0.22; 34+ usa fatias reais da planilha")
