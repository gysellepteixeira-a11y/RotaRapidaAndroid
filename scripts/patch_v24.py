from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
parser_path = Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")

s = service_path.read_text(encoding="utf-8")
p = parser_path.read_text(encoding="utf-8")

# v0.24
# 1) Remove quatro bairros da lista de prioridades do APK:
#    Maringa, Barcelona, Helio Ferraz e Parque Residencial Laranjeiras.
# 2) Para tabelas densas (31+ linhas), nao manda mais 31-40 bairros em uma unica
#    coluna alta para o ML Kit. Cada celula de Bairro e ampliada e distribuida em
#    2 ou 3 PAINEIS lado a lado, com no maximo ~16 linhas por painel. Isso imita
#    o comportamento observado nos testes: quando a imagem e cortada e ficam
#    menos linhas visiveis, o OCR passa a ler. Continua sendo apenas UM OCR para
#    todos os bairros e depois UM OCR pequeno para a gaiola escolhida.
# 3) 29/30 linhas e demais rotas continuam no caminho rapido da v0.19.

# -----------------------------------------------------------------------------
# PRIORIDADES
# -----------------------------------------------------------------------------
for line in [
    '        PriorityRule("Helio Ferraz", listOf("helio", "ferraz")),\n',
    '        PriorityRule("Parque Residencial Laranjeiras", listOf("parque", "residencial", "laranjeiras")),\n',
    '        PriorityRule("Barcelona", listOf("barcelona")),\n',
    '        PriorityRule("Maringa", listOf("maringa"))\n',
]:
    p = p.replace(line, '')

# Depois das remocoes pode sobrar virgula correta em Rosario; Kotlin aceita a
# ultima entrada com ou sem virgula. Nao alteramos as sete prioridades restantes.
parser_path.write_text(p, encoding="utf-8")

# -----------------------------------------------------------------------------
# SUBSTITUI O BLOCO NORMALIZADO DA v0.23
# -----------------------------------------------------------------------------
start = s.find('    private data class NormalizedNeighborhoodSheet(')
end = s.find('\n    private fun readMediaLargeColorCrop(media: MediaImage) {', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'Patch v0.24: bloco GRID NORM da v0.23 nao encontrado (start={start}, end={end})'
    )

new_block = r'''    private data class NeighborhoodPanelSheet(
        val bitmap: Bitmap,
        val panelCount: Int,
        val rowsPerPanel: Int,
        val panelWidth: Int,
        val panelGap: Int,
        val sidePad: Int,
        val topPad: Int,
        val rowPitch: Int,
        val rowCount: Int
    )

    private fun buildNeighborhoodPanelSheet(
        source: Bitmap,
        layout: DenseGridLayout
    ): NeighborhoodPanelSheet? {
        val rows = layout.horizontalLines.zipWithNext()
        if (rows.size < 31) return null

        val bairroX1 = (layout.bairroLeft + 2).coerceIn(0, source.width - 3)
        val bairroX2 = (layout.bairroRight - 2).coerceIn(bairroX1 + 2, source.width)
        val bairroWidth = bairroX2 - bairroX1
        if (bairroWidth < 70) return null

        val innerHeights = rows
            .map { (a, b) -> (b - a - 2).coerceAtLeast(1) }
            .filter { it >= 4 }
            .sorted()
        if (innerHeights.size < 10) return null

        val medianInnerHeight = innerHeights[innerHeights.size / 2].coerceAtLeast(1)

        // No maximo 16 rotas em cada painel. A imagem de 38 linhas vira 3
        // colunas de aproximadamente 13 linhas cada, em vez de 38 linhas
        // minusculas empilhadas.
        val maxRowsPerPanel = 16
        val panelCount = ((rows.size + maxRowsPerPanel - 1) / maxRowsPerPanel)
            .coerceIn(2, 3)
        val rowsPerPanel = ((rows.size + panelCount - 1) / panelCount)
            .coerceAtLeast(1)

        val textHeight = 48
        val rowGap = 10
        val topPad = 12
        val sidePad = 12
        val panelGap = 26
        val rowPitch = textHeight + rowGap

        val scale = textHeight.toFloat() / medianInnerHeight.toFloat()
        val scaledBairroWidth = (bairroWidth * scale)
            .toInt()
            .coerceIn(330, 590)
        val panelWidth = scaledBairroWidth + sidePad * 2

        val visibleRowsInTallestPanel = minOf(rowsPerPanel, rows.size)
        val outHeight = topPad * 2 +
            visibleRowsInTallestPanel * rowPitch - rowGap
        val outWidth = panelCount * panelWidth + (panelCount - 1) * panelGap

        if (outHeight > 1_150 || outWidth > 1_950) return null

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
        val paint = Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG)

        rows.forEachIndexed { index, (a, b) ->
            val panel = (index / rowsPerPanel).coerceAtMost(panelCount - 1)
            val rowInPanel = index % rowsPerPanel

            val y1 = (a + 1).coerceIn(0, source.height - 2)
            val y2 = (b - 1).coerceIn(y1 + 1, source.height)
            val innerHeight = y2 - y1
            if (innerHeight < 3) return@forEachIndexed

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

            val scaled = try {
                Bitmap.createScaledBitmap(
                    cell,
                    scaledBairroWidth,
                    textHeight,
                    true
                )
            } catch (_: Throwable) {
                cell
            }

            val dstLeft = panel * (panelWidth + panelGap) + sidePad
            val dstTop = topPad + rowInPanel * rowPitch

            canvas.drawBitmap(
                scaled,
                dstLeft.toFloat(),
                dstTop.toFloat(),
                paint
            )

            if (scaled !== cell) {
                try { scaled.recycle() } catch (_: Throwable) {}
            }
            try { cell.recycle() } catch (_: Throwable) {}
        }

        return NeighborhoodPanelSheet(
            bitmap = sheet,
            panelCount = panelCount,
            rowsPerPanel = rowsPerPanel,
            panelWidth = panelWidth,
            panelGap = panelGap,
            sidePad = sidePad,
            topPad = topPad,
            rowPitch = rowPitch,
            rowCount = rows.size
        )
    }

    private fun buildPanelCageBitmap(
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

        val targetHeight = 104
        val scale = targetHeight.toFloat() / cellHeight.toFloat()
        val targetWidth = (cellWidth * scale).toInt().coerceIn(180, 500)
        val pad = 18

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
                true
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
        canvas.drawBitmap(
            scaled,
            pad.toFloat(),
            pad.toFloat(),
            Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG)
        )

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

        // Deixa 29/30 linhas exatamente no caminho rapido que ja funcionou bem.
        if (layout.rowCount < 31) return false

        val sheet = buildNeighborhoodPanelSheet(source, layout) ?: return false
        val started = SystemClock.elapsedRealtime()
        val input = InputImage.fromBitmap(sheet.bitmap, 0)

        Prefs.setStatus(
            this,
            "GRID PAINEL: ${layout.rowCount} linhas em ${sheet.panelCount} paineis | OCR Bairro..."
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

                    val panelStride = sheet.panelWidth + sheet.panelGap
                    val panel = (box.centerX() / panelStride)
                        .coerceIn(0, sheet.panelCount - 1)
                    val rowInPanel = ((box.centerY() - sheet.topPad) / sheet.rowPitch)
                        .coerceIn(0, sheet.rowsPerPanel - 1)
                    val rowIndex = panel * sheet.rowsPerPanel + rowInPanel

                    if (rowIndex !in 0 until sheet.rowCount) return

                    hits += BairroHit(
                        priority = priority.first,
                        name = priority.second,
                        rowIndex = rowIndex,
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
                        "GRID PAINEL nao achou bairro prioritario. Fallback reforcado..."
                    )
                    readMediaEnhanced(media)
                    return@addOnSuccessListener
                }

                val cageBitmap = buildPanelCageBitmap(
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
                    "GRID PAINEL: ${chosen.name} linha ${chosen.rowIndex + 1}; OCR Gaiola..."
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
                                    "Arquivo repetido ignorado | GRID PAINEL"
                                )
                            } else {
                                Prefs.setStatus(
                                    this,
                                    "GRID PAINEL: ${route.neighborhood} -> ${route.cage} | " +
                                        "decode=${decodeMs}ms grid=${layout.scanMs}ms " +
                                        "bairro=${bairroMs}ms gaiola=${cageMs}ms | enviando"
                                )
                                sendRouteInCurrentChat(route)
                            }
                        } else {
                            Prefs.setStatus(
                                this,
                                "GRID PAINEL achou ${chosen.name}, mas nao leu gaiola. " +
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
print("Patch v0.24 aplicado: 31+ linhas em paineis + removidas 4 prioridades")
