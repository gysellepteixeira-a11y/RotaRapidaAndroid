from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.27 - DENSAS POR LINHAS REAIS DA AGENCIA + BAIRRO EM TIRAS CONTINUAS
#
# A v0.26 estabilizou a grade, mas a imagem 1074x666 com 38 rotas ainda nao
# fechou a rota. Ao reproduzir o recorte, o texto fica perfeitamente legivel
# quando isolamos apenas Bairro em grupos pequenos. Portanto esta versao usa a
# coluna colorida Agencia para localizar exatamente as linhas de DADOS (sem
# cabecalho), monta um unico bitmap com 3-4 tiras CONTINUAS da coluna Bairro e
# faz UM OCR. Depois le somente a celula Gaiola da linha escolhida.
#
# Diferente da v0.24, nao redimensiona cada celula separadamente e nao altera a
# proporcao das letras. Cada tira preserva a aparencia real da planilha, apenas
# ampliada uniformemente. O recorte do topo nao importa: linhas parciais sao
# ignoradas/ajustadas pela faixa verde da Agencia.
#
# Se este caminho nao puder ser montado ou nao achar prioridade, preserva a
# leitura GRID VIRTUAL da v0.26 como fallback.

insert_at = s.find('    private fun readDenseGridTwoStage(\n')
if insert_at < 0:
    raise SystemExit('Patch v0.27: readDenseGridTwoStage da v0.26 nao encontrado')

helpers = r'''    private data class AgencyDataRow(
        val centerY: Int,
        val top: Int,
        val bottom: Int
    )

    private data class BairroStripMeta(
        val firstRow: Int,
        val rowCount: Int,
        val dstLeft: Int,
        val dstTop: Int,
        val dstWidth: Int,
        val dstHeight: Int,
        val sourceTop: Int,
        val scale: Float
    )

    private data class BairroStripSheet(
        val bitmap: Bitmap,
        val rows: List<AgencyDataRow>,
        val strips: List<BairroStripMeta>
    )

    private fun detectAgencyDataRows(
        source: Bitmap,
        layout: DenseGridLayout
    ): List<AgencyDataRow>? {
        val w = source.width
        val h = source.height

        val x1 = (layout.bairroRight + 4).coerceIn(0, w - 2)
        val x2 = (layout.bairroRight + maxOf(74, (w * 0.125f).toInt()))
            .coerceIn(x1 + 2, w)

        val sampledPerRow = ((x2 - x1 + 1) / 2).coerceAtLeast(1)
        val activeThreshold = maxOf(5, (sampledPerRow * 0.09f).toInt())

        val rawBands = mutableListOf<Pair<Int, Int>>()
        var activeStart = -1

        var y = 0
        while (y < h) {
            var hits = 0
            var x = x1
            while (x < x2) {
                if (isAgencyColor(source.getPixel(x, y))) hits++
                x += 2
            }

            val active = hits >= activeThreshold
            if (active && activeStart < 0) {
                activeStart = y
            } else if (!active && activeStart >= 0) {
                rawBands += activeStart to (y - 1)
                activeStart = -1
            }
            y++
        }

        if (activeStart >= 0) {
            rawBands += activeStart to (h - 1)
        }

        if (rawBands.size < 8) return null

        val heights = rawBands
            .map { (a, b) -> b - a + 1 }
            .filter { it > 0 }
            .sorted()
        if (heights.isEmpty()) return null

        val medianHeight = heights[heights.size / 2]
        val minBandHeight = maxOf(4, (medianHeight * 0.45f).toInt())

        val cleanBands = rawBands
            .filter { (a, b) -> b - a + 1 >= minBandHeight }

        if (cleanBands.size < 8) return null

        val rows = mutableListOf<AgencyDataRow>()

        for ((bandTop, bandBottom) in cleanBands) {
            val center = (bandTop + bandBottom) / 2

            val pair = layout.horizontalLines
                .zipWithNext()
                .firstOrNull { (a, b) -> center >= a && center <= b }

            val top: Int
            val bottom: Int

            if (pair != null) {
                top = pair.first.coerceIn(0, h - 2)
                bottom = pair.second.coerceIn(top + 2, h)
            } else {
                val half = maxOf(4, (layout.rowSpacing * 0.50f).toInt())
                top = (center - half).coerceIn(0, h - 2)
                bottom = (center + half).coerceIn(top + 2, h)
            }

            // Evita duas faixas coloridas acabarem mapeadas para a mesma linha.
            if (rows.none { kotlin.math.abs(it.centerY - center) < maxOf(4, (layout.rowSpacing * 0.45f).toInt()) }) {
                rows += AgencyDataRow(
                    centerY = center,
                    top = top,
                    bottom = bottom
                )
            }
        }

        if (rows.size < 8) return null
        return rows.sortedBy { it.centerY }
    }

    private fun buildBairroStripSheet(
        source: Bitmap,
        layout: DenseGridLayout,
        rows: List<AgencyDataRow>
    ): BairroStripSheet? {
        if (rows.size < 8) return null

        val x1 = (layout.bairroLeft + 1).coerceIn(0, source.width - 3)
        val x2 = (layout.bairroRight - 1).coerceIn(x1 + 2, source.width)
        val bairroWidth = x2 - x1
        if (bairroWidth < 70) return null

        val maxRowsPerStrip = 10
        val stripCount = ((rows.size + maxRowsPerStrip - 1) / maxRowsPerStrip)
            .coerceAtLeast(1)

        // Mira ~36 px por linha. Mantemos a proporcao inteira da tira.
        var scale = (36f / layout.rowSpacing).coerceIn(1.65f, 2.35f)
        val scaledWidth = (bairroWidth * scale).toInt().coerceAtLeast(1)
        if (scaledWidth > 460) {
            scale = 460f / bairroWidth.toFloat()
        }

        val gap = 24
        val pad = 10

        val stripBitmaps = mutableListOf<Triple<Int, Int, Bitmap>>()
        var first = 0
        while (first < rows.size) {
            val lastExclusive = minOf(first + maxRowsPerStrip, rows.size)
            val y1 = rows[first].top.coerceIn(0, source.height - 2)
            val y2 = rows[lastExclusive - 1].bottom.coerceIn(y1 + 2, source.height)

            val crop = try {
                Bitmap.createBitmap(
                    source,
                    x1,
                    y1,
                    bairroWidth,
                    y2 - y1
                )
            } catch (_: Throwable) {
                null
            }

            if (crop == null) {
                stripBitmaps.forEach { (_, _, b) ->
                    try { b.recycle() } catch (_: Throwable) {}
                }
                return null
            }

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

            stripBitmaps += Triple(first, y1, scaled)
            first = lastExclusive
        }

        if (stripBitmaps.isEmpty()) return null

        val outWidth = pad * 2 +
            stripBitmaps.sumOf { it.third.width } +
            gap * (stripBitmaps.size - 1)
        val outHeight = pad * 2 + stripBitmaps.maxOf { it.third.height }

        if (outWidth > 2_050 || outHeight > 1_050) {
            stripBitmaps.forEach { (_, _, b) ->
                try { b.recycle() } catch (_: Throwable) {}
            }
            return null
        }

        val sheet = try {
            Bitmap.createBitmap(
                outWidth,
                outHeight,
                Bitmap.Config.ARGB_8888
            )
        } catch (_: Throwable) {
            stripBitmaps.forEach { (_, _, b) ->
                try { b.recycle() } catch (_: Throwable) {}
            }
            return null
        }

        val canvas = Canvas(sheet)
        canvas.drawColor(Color.WHITE)
        val paint = Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG)

        val metas = mutableListOf<BairroStripMeta>()
        var dstLeft = pad

        for ((firstRow, sourceTop, strip) in stripBitmaps) {
            canvas.drawBitmap(strip, dstLeft.toFloat(), pad.toFloat(), paint)

            val rowCount = minOf(maxRowsPerStrip, rows.size - firstRow)
            metas += BairroStripMeta(
                firstRow = firstRow,
                rowCount = rowCount,
                dstLeft = dstLeft,
                dstTop = pad,
                dstWidth = strip.width,
                dstHeight = strip.height,
                sourceTop = sourceTop,
                scale = scale
            )

            dstLeft += strip.width + gap
            try { strip.recycle() } catch (_: Throwable) {}
        }

        return BairroStripSheet(
            bitmap = sheet,
            rows = rows,
            strips = metas
        )
    }

    private fun buildAgencyCageBitmap(
        source: Bitmap,
        layout: DenseGridLayout,
        row: AgencyDataRow
    ): Bitmap? {
        val x1 = 1
        val x2 = (layout.gaiolaRight - 1).coerceIn(x1 + 2, source.width)
        val y1 = (row.top + 1).coerceIn(0, source.height - 2)
        val y2 = (row.bottom - 1).coerceIn(y1 + 1, source.height)

        val cellWidth = x2 - x1
        val cellHeight = y2 - y1
        if (cellWidth < 15 || cellHeight < 4) return null

        val targetHeight = 104
        val scale = targetHeight.toFloat() / cellHeight.toFloat()
        val targetWidth = (cellWidth * scale).toInt().coerceIn(180, 520)
        val pad = 18

        val crop = try {
            Bitmap.createBitmap(source, x1, y1, cellWidth, cellHeight)
        } catch (_: Throwable) {
            return null
        }

        val scaled = try {
            Bitmap.createScaledBitmap(crop, targetWidth, targetHeight, true)
        } catch (_: Throwable) {
            crop
        }

        val out = try {
            Bitmap.createBitmap(
                targetWidth + pad * 2,
                targetHeight + pad * 2,
                Bitmap.Config.ARGB_8888
            )
        } catch (_: Throwable) {
            if (scaled !== crop) {
                try { scaled.recycle() } catch (_: Throwable) {}
            }
            try { crop.recycle() } catch (_: Throwable) {}
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

        if (scaled !== crop) {
            try { scaled.recycle() } catch (_: Throwable) {}
        }
        try { crop.recycle() } catch (_: Throwable) {}

        return out
    }

    private fun readDenseAgencyStrips(
        media: MediaImage,
        source: Bitmap,
        decodeMs: Long,
        layout: DenseGridLayout
    ): Boolean {
        val rows = detectAgencyDataRows(source, layout) ?: return false

        // Este caminho e focado nas tabelas compactas onde o OCR da linha inteira
        // vinha falhando. Em rotas pequenas continuamos no fluxo normal.
        if (rows.size < 12 || layout.rowSpacing > 21f) return false

        val sheet = buildBairroStripSheet(source, layout, rows) ?: return false
        val started = SystemClock.elapsedRealtime()

        Prefs.setStatus(
            this,
            "BAIRRO TIRAS: ${rows.size} rotas | ${sheet.strips.size} tiras | OCR..."
        )

        recognizer.process(InputImage.fromBitmap(sheet.bitmap, 0))
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

                    val cx = box.centerX()
                    val cy = box.centerY()
                    val strip = sheet.strips.firstOrNull { meta ->
                        cx >= meta.dstLeft &&
                            cx <= meta.dstLeft + meta.dstWidth &&
                            cy >= meta.dstTop - 6 &&
                            cy <= meta.dstTop + meta.dstHeight + 6
                    } ?: return

                    val originalY = (
                        strip.sourceTop +
                            (cy - strip.dstTop).toFloat() / strip.scale
                    ).toInt()

                    val start = strip.firstRow
                    val end = minOf(start + strip.rowCount, sheet.rows.size)
                    if (start >= end) return

                    val nearest = (start until end)
                        .minByOrNull { idx ->
                            kotlin.math.abs(sheet.rows[idx].centerY - originalY)
                        } ?: return

                    hits += BairroHit(
                        priority = priority.first,
                        name = priority.second,
                        rowIndex = nearest,
                        raw = text
                    )
                }

                for (block in visionText.textBlocks) {
                    for (line in block.lines) {
                        addHit(line.text, line.boundingBox)
                        for (element in line.elements) {
                            addHit(element.text, element.boundingBox)
                        }
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
                    Prefs.setStatus(
                        this,
                        "BAIRRO TIRAS nao achou prioridade. Tentando GRID VIRTUAL..."
                    )
                    readDenseGridChunks(
                        media = media,
                        source = source,
                        decodeMs = decodeMs,
                        layout = layout
                    )
                    return@addOnSuccessListener
                }

                val selectedRow = sheet.rows.getOrNull(chosen.rowIndex)
                val cageBitmap = selectedRow?.let {
                    buildAgencyCageBitmap(source, layout, it)
                }

                if (cageBitmap == null) {
                    readDenseGridChunks(
                        media = media,
                        source = source,
                        decodeMs = decodeMs,
                        layout = layout
                    )
                    return@addOnSuccessListener
                }

                val cageStarted = SystemClock.elapsedRealtime()

                Prefs.setStatus(
                    this,
                    "BAIRRO TIRAS: ${chosen.name} linha ${chosen.rowIndex + 1}; OCR Gaiola..."
                )

                recognizer.process(InputImage.fromBitmap(cageBitmap, 0))
                    .addOnSuccessListener { cageText ->
                        if (!processing) {
                            try { cageBitmap.recycle() } catch (_: Throwable) {}
                            try { source.recycle() } catch (_: Throwable) {}
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

                        if (cage == null) {
                            Prefs.setStatus(
                                this,
                                "BAIRRO TIRAS achou ${chosen.name}, mas nao leu Gaiola. " +
                                    "Tentando GRID VIRTUAL..."
                            )
                            readDenseGridChunks(
                                media = media,
                                source = source,
                                decodeMs = decodeMs,
                                layout = layout
                            )
                            return@addOnSuccessListener
                        }

                        try { source.recycle() } catch (_: Throwable) {}

                        val route = RouteResult(
                            neighborhood = chosen.name,
                            cage = cage,
                            priorityIndex = chosen.priority
                        )

                        if (isDuplicate(route)) {
                            finishFileOnlyFailure(
                                "Arquivo repetido ignorado | BAIRRO TIRAS"
                            )
                        } else {
                            Prefs.setStatus(
                                this,
                                "BAIRRO TIRAS: ${route.neighborhood} -> ${route.cage} | " +
                                    "rotas=${rows.size} bairro=${bairroMs}ms gaiola=${cageMs}ms | enviando"
                            )
                            sendRouteInCurrentChat(route)
                        }
                    }
                    .addOnFailureListener {
                        try { cageBitmap.recycle() } catch (_: Throwable) {}
                        if (!processing) {
                            try { source.recycle() } catch (_: Throwable) {}
                            return@addOnFailureListener
                        }
                        readDenseGridChunks(
                            media = media,
                            source = source,
                            decodeMs = decodeMs,
                            layout = layout
                        )
                    }
            }
            .addOnFailureListener {
                try { sheet.bitmap.recycle() } catch (_: Throwable) {}
                if (!processing) {
                    try { source.recycle() } catch (_: Throwable) {}
                    return@addOnFailureListener
                }
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

s = s[:insert_at] + helpers + s[insert_at:]

# Troca apenas o dispatch da v0.26. Primeiro tenta o novo OCR de Bairro em tiras;
# se nao der para detectar as linhas da Agencia, usa o GRID VIRTUAL anterior.
start = s.find('    private fun readDenseGridTwoStage(\n')
end = s.find('\n    private fun readMediaLargeColorCrop(media: MediaImage) {', start)
if start < 0 or end < 0:
    raise SystemExit('Patch v0.27: bloco dispatch nao encontrado')

new_dispatch = r'''    private fun readDenseGridTwoStage(
        media: MediaImage,
        source: Bitmap,
        decodeMs: Long
    ): Boolean {
        if (!processing) return false
        if (source.height > 1_250) return false

        val layout = detectDenseGridLayout(source) ?: return false

        val isDense = layout.rowSpacing <= 20.5f && layout.rowCount >= 12
        if (!isDense) return false

        if (readDenseAgencyStrips(
                media = media,
                source = source,
                decodeMs = decodeMs,
                layout = layout
            )) {
            return true
        }

        Prefs.setStatus(
            this,
            "GRID VIRTUAL fallback: ${layout.rowCount} linhas | passo=" +
                String.format(java.util.Locale.US, "%.1f", layout.rowSpacing) + "px"
        )

        readDenseGridChunks(
            media = media,
            source = source,
            decodeMs = decodeMs,
            layout = layout
        )
        return true
    }
'''

s = s[:start] + new_dispatch + s[end:]
service_path.write_text(s, encoding="utf-8")
print("Patch v0.27 aplicado: linhas pela Agencia + Bairro em tiras continuas + Gaiola isolada")
