from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.28 - OCR DENSO DIRETO POR CELULAS EM PAINEIS PEQUENOS
#
# A v0.27 ainda falhou na imagem 1074x666 / 38 rotas, embora a coluna Bairro
# isolada fique visualmente legivel. O problema restante e deixar o ML Kit tentar
# segmentar muitas linhas/tiras em uma unica imagem. Nesta versao:
#   - detecta as linhas de dados DIRETAMENTE pelos botoes verdes/laranjas da Agencia;
#   - detecta Gaiola/Bairro pelas linhas verticais da grade usando apenas os centros
#     dessas linhas (sem depender do cabecalho nem do corte do topo);
#   - para 31+ rotas densas, cria paineis pequenos de no maximo 7 bairros;
#   - cada celula Bairro e isolada da grade, ampliada para ~72 px de altura e colocada
#     em fundo branco com espacamento fixo;
#   - OCR sequencial dos paineis, compara a prioridade global e so depois le a Gaiola
#     da linha vencedora;
#   - se esse caminho nao fechar, cai no fluxo v0.27/v0.26 e depois no reforcado.
#
# 29/30 linhas continuam fora deste caminho para preservar o modo rapido que ja
# chegou a ~1.2-1.4s. Prioridades removidas na v0.24 continuam removidas.

insert_at = s.find('    private fun readDenseGridTwoStage(\n')
if insert_at < 0:
    raise SystemExit('Patch v0.28: readDenseGridTwoStage nao encontrado')

helpers = r'''    private data class DirectDenseRow(
        val centerY: Int,
        val top: Int,
        val bottom: Int
    )

    private data class DirectDenseGeometry(
        val rows: List<DirectDenseRow>,
        val rowSpacing: Float,
        val gaiolaRight: Int,
        val bairroLeft: Int,
        val bairroRight: Int,
        val scanMs: Long
    )

    private data class DirectBairroPanel(
        val bitmap: Bitmap,
        val firstRow: Int,
        val rowCount: Int,
        val topPad: Int,
        val rowPitch: Int
    )

    private data class DirectDenseHit(
        val priority: Int,
        val name: String,
        val rowIndex: Int
    )

    private fun matchDensePriority(text: String): Pair<Int, String>? {
        RouteParser.matchPriority(text)?.let { return it }

        val n = RouteParser.normalize(text)
        if (n.isBlank()) return null

        // Fallback leve para pequenos erros do ML Kit em fonte muito compacta.
        // Mantem exatamente a ordem das sete prioridades atuais.
        return when {
            "valpar" in n -> 0 to "Valparaiso"
            "colina" in n -> 1 to "Colina de Laranjeiras"
            "baleia" in n || ("praia" in n && "bale" in n) -> 2 to "Praia da Baleia"
            "morada" in n -> 3 to "Morada de Laranjeiras"
            "euric" in n -> 4 to "Eurico"
            "plaza" in n || ("manoel" in n && "pl" in n) -> 5 to "Manoel Plaza"
            "rosar" in n -> 6 to "Rosario"
            else -> null
        }
    }

    private fun detectDirectDenseGeometry(source: Bitmap): DirectDenseGeometry? {
        val started = SystemClock.elapsedRealtime()
        val w = source.width
        val h = source.height
        if (w < 700 || h < 350 || h > 1_250) return null

        // 1) Linhas de DADOS pela cor da Agencia. Nao usa cabecalho nem grade H.
        val colorX1 = (w * 0.40f).toInt().coerceIn(0, w - 2)
        val colorX2 = (w * 0.63f).toInt().coerceIn(colorX1 + 2, w)
        val sampled = ((colorX2 - colorX1 + 1) / 2).coerceAtLeast(1)
        val threshold = maxOf(7, (sampled * 0.07f).toInt())

        val rawBands = mutableListOf<Pair<Int, Int>>()
        var bandStart = -1

        var y = 0
        while (y < h) {
            var hits = 0
            var x = colorX1
            while (x < colorX2) {
                if (isAgencyColor(source.getPixel(x, y))) hits++
                x += 2
            }

            val active = hits >= threshold
            if (active && bandStart < 0) {
                bandStart = y
            } else if (!active && bandStart >= 0) {
                rawBands += bandStart to (y - 1)
                bandStart = -1
            }
            y++
        }
        if (bandStart >= 0) rawBands += bandStart to (h - 1)
        if (rawBands.size < 20) return null

        val heights = rawBands
            .map { (a, b) -> b - a + 1 }
            .filter { it >= 3 }
            .sorted()
        if (heights.size < 20) return null

        val medianHeight = heights[heights.size / 2]
        val minHeight = maxOf(3, (medianHeight * 0.35f).toInt())
        val bands = rawBands
            .filter { (a, b) -> b - a + 1 >= minHeight }
            .sortedBy { it.first }
        if (bands.size < 20) return null

        val centers = bands.map { (a, b) -> (a + b) / 2 }
        val spacings = centers.zipWithNext()
            .map { (a, b) -> b - a }
            .filter { it in 8..32 }
            .sorted()
        if (spacings.size < 10) return null

        val rowSpacing = spacings[spacings.size / 2].toFloat()
        if (rowSpacing > 23f) return null

        // 2) Linhas verticais da grade. Em cada centro de rota as divisorias
        // continuam escuras; texto nao repete o mesmo X em quase todas as linhas.
        val minVerticalHits = maxOf(8, (centers.size * 0.62f).toInt())
        val rawVertical = mutableListOf<Int>()

        var x = 1
        while (x < w - 1) {
            var darkHits = 0
            for (cy in centers) {
                val yy = cy.coerceIn(0, h - 1)
                if (darkPixel(source.getPixel(x, yy))) darkHits++
            }
            if (darkHits >= minVerticalHits) rawVertical += x
            x++
        }

        val vertical = clusterCoordinates(rawVertical)

        var gaiolaRight = vertical
            .filter {
                val r = it.toFloat() / w.toFloat()
                r in 0.030f..0.105f
            }
            .minByOrNull {
                kotlin.math.abs(it.toFloat() / w.toFloat() - 0.055f)
            }

        var bairroRight = vertical
            .filter {
                val r = it.toFloat() / w.toFloat()
                r in 0.420f..0.535f
            }
            .minByOrNull {
                kotlin.math.abs(it.toFloat() / w.toFloat() - 0.466f)
            }

        var bairroLeft = if (bairroRight != null) {
            vertical
                .filter { it < bairroRight!! }
                .filter {
                    val ratio = (bairroRight!! - it).toFloat() / w.toFloat()
                    ratio in 0.115f..0.225f
                }
                .maxOrNull()
        } else null

        // Fallback geometrico seguro para esse layout de planilha. So e usado
        // depois de termos confirmado muitas linhas coloridas regularmente espacadas.
        if (gaiolaRight == null) gaiolaRight = (w * 0.054f).toInt()
        if (bairroRight == null) bairroRight = (w * 0.466f).toInt()
        if (bairroLeft == null) bairroLeft = (w * 0.305f).toInt()

        val gr = gaiolaRight!!.coerceIn(24, w - 10)
        val br = bairroRight!!.coerceIn(gr + 90, w - 5)
        val bl = bairroLeft!!.coerceIn(gr + 40, br - 60)
        if (br - bl < 90) return null

        val half = maxOf(5, (rowSpacing * 0.49f).toInt())
        val rows = centers.map { center ->
            DirectDenseRow(
                centerY = center,
                top = (center - half).coerceIn(0, h - 2),
                bottom = (center + half + 1).coerceIn(2, h)
            )
        }

        if (rows.size < 20) return null

        return DirectDenseGeometry(
            rows = rows,
            rowSpacing = rowSpacing,
            gaiolaRight = gr,
            bairroLeft = bl,
            bairroRight = br,
            scanMs = SystemClock.elapsedRealtime() - started
        )
    }

    private fun buildDirectBairroPanels(
        source: Bitmap,
        geometry: DirectDenseGeometry
    ): List<DirectBairroPanel>? {
        val rowsPerPanel = 7
        val targetHeight = 72
        val rowGap = 10
        val topPad = 12
        val sidePad = 12
        val rowPitch = targetHeight + rowGap

        val x1 = (geometry.bairroLeft + 3).coerceIn(0, source.width - 3)
        val x2 = (geometry.bairroRight - 3).coerceIn(x1 + 2, source.width)
        val cellWidth = x2 - x1
        if (cellWidth < 80) return null

        val typicalCellHeight = maxOf(6, (geometry.rowSpacing - 2f).toInt())
        val scale = targetHeight.toFloat() / typicalCellHeight.toFloat()
        val targetWidth = (cellWidth * scale).toInt().coerceIn(480, 760)

        val panels = mutableListOf<DirectBairroPanel>()
        var first = 0

        while (first < geometry.rows.size) {
            val count = minOf(rowsPerPanel, geometry.rows.size - first)
            val outWidth = targetWidth + sidePad * 2
            val outHeight = topPad * 2 + count * rowPitch - rowGap

            val bitmap = try {
                Bitmap.createBitmap(outWidth, outHeight, Bitmap.Config.ARGB_8888)
            } catch (_: Throwable) {
                panels.forEach { try { it.bitmap.recycle() } catch (_: Throwable) {} }
                return null
            }

            val canvas = Canvas(bitmap)
            canvas.drawColor(Color.WHITE)
            val paint = Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG)

            for (local in 0 until count) {
                val row = geometry.rows[first + local]
                val y1 = (row.top + 1).coerceIn(0, source.height - 2)
                val y2 = (row.bottom - 1).coerceIn(y1 + 1, source.height)
                val cellH = y2 - y1
                if (cellH <= 2) continue

                val crop = try {
                    Bitmap.createBitmap(source, x1, y1, cellWidth, cellH)
                } catch (_: Throwable) {
                    null
                } ?: continue

                val scaled = try {
                    Bitmap.createScaledBitmap(crop, targetWidth, targetHeight, true)
                } catch (_: Throwable) {
                    crop
                }

                val dstTop = topPad + local * rowPitch
                canvas.drawBitmap(
                    scaled,
                    sidePad.toFloat(),
                    dstTop.toFloat(),
                    paint
                )

                if (scaled !== crop) {
                    try { scaled.recycle() } catch (_: Throwable) {}
                }
                try { crop.recycle() } catch (_: Throwable) {}
            }

            panels += DirectBairroPanel(
                bitmap = bitmap,
                firstRow = first,
                rowCount = count,
                topPad = topPad,
                rowPitch = rowPitch
            )
            first += count
        }

        return panels.ifEmpty { null }
    }

    private fun buildDirectCageBitmap(
        source: Bitmap,
        geometry: DirectDenseGeometry,
        rowIndex: Int
    ): Bitmap? {
        val row = geometry.rows.getOrNull(rowIndex) ?: return null
        val x1 = 1
        val x2 = (geometry.gaiolaRight - 2).coerceIn(x1 + 2, source.width)
        val y1 = (row.top + 1).coerceIn(0, source.height - 2)
        val y2 = (row.bottom - 1).coerceIn(y1 + 1, source.height)
        val cw = x2 - x1
        val ch = y2 - y1
        if (cw < 15 || ch < 4) return null

        val targetHeight = 112
        val scale = targetHeight.toFloat() / ch.toFloat()
        val targetWidth = (cw * scale).toInt().coerceIn(200, 560)
        val pad = 20

        val crop = try {
            Bitmap.createBitmap(source, x1, y1, cw, ch)
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
            if (scaled !== crop) try { scaled.recycle() } catch (_: Throwable) {}
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

        if (scaled !== crop) try { scaled.recycle() } catch (_: Throwable) {}
        try { crop.recycle() } catch (_: Throwable) {}
        return out
    }

    private fun readDirectDensePanels(
        media: MediaImage,
        source: Bitmap,
        decodeMs: Long,
        geometry: DirectDenseGeometry
    ): Boolean {
        // Mantem 29/30 no caminho rapido anterior.
        if (geometry.rows.size < 31 || geometry.rowSpacing > 23f) return false

        val panels = buildDirectBairroPanels(source, geometry) ?: return false
        var best: DirectDenseHit? = null
        var totalBairroMs = 0L

        fun finishNeighborhoods() {
            if (!processing) return

            val chosen = best
            if (chosen == null) {
                try { source.recycle() } catch (_: Throwable) {}
                Prefs.setStatus(
                    this,
                    "CELULAS: ${geometry.rows.size} rotas, nenhuma prioridade. Fallback reforcado..."
                )
                readMediaEnhanced(media)
                return
            }

            val cageBitmap = buildDirectCageBitmap(source, geometry, chosen.rowIndex)
            try { source.recycle() } catch (_: Throwable) {}

            if (cageBitmap == null) {
                readMediaEnhanced(media)
                return
            }

            val cageStarted = SystemClock.elapsedRealtime()
            Prefs.setStatus(
                this,
                "CELULAS: ${chosen.name} linha ${chosen.rowIndex + 1}; OCR Gaiola..."
            )

            recognizer.process(InputImage.fromBitmap(cageBitmap, 0))
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

                    if (cage == null) {
                        Prefs.setStatus(
                            this,
                            "CELULAS achou ${chosen.name}, mas nao leu Gaiola. Fallback reforcado..."
                        )
                        readMediaEnhanced(media)
                        return@addOnSuccessListener
                    }

                    val route = RouteResult(
                        neighborhood = chosen.name,
                        cage = cage,
                        priorityIndex = chosen.priority
                    )

                    if (isDuplicate(route)) {
                        finishFileOnlyFailure("Arquivo repetido ignorado | CELULAS")
                    } else {
                        Prefs.setStatus(
                            this,
                            "CELULAS: ${route.neighborhood} -> ${route.cage} | " +
                                "rotas=${geometry.rows.size} scan=${geometry.scanMs}ms " +
                                "bairro=${totalBairroMs}ms gaiola=${cageMs}ms | enviando"
                        )
                        sendRouteInCurrentChat(route)
                    }
                }
                .addOnFailureListener {
                    try { cageBitmap.recycle() } catch (_: Throwable) {}
                    if (!processing) return@addOnFailureListener
                    readMediaEnhanced(media)
                }
        }

        fun processPanel(index: Int) {
            if (!processing) {
                for (i in index until panels.size) {
                    try { panels[i].bitmap.recycle() } catch (_: Throwable) {}
                }
                return
            }

            if (index >= panels.size) {
                finishNeighborhoods()
                return
            }

            val panel = panels[index]
            val started = SystemClock.elapsedRealtime()
            Prefs.setStatus(
                this,
                "CELULAS: ${geometry.rows.size} rotas | painel ${index + 1}/${panels.size}..."
            )

            recognizer.process(InputImage.fromBitmap(panel.bitmap, 0))
                .addOnSuccessListener { visionText ->
                    totalBairroMs += SystemClock.elapsedRealtime() - started

                    if (processing) {
                        fun consider(text: String, box: Rect?) {
                            if (box == null) return
                            val priority = matchDensePriority(text) ?: return
                            val local = ((box.centerY() - panel.topPad) / panel.rowPitch)
                                .coerceIn(0, panel.rowCount - 1)
                            val rowIndex = panel.firstRow + local
                            if (rowIndex !in geometry.rows.indices) return

                            val candidate = DirectDenseHit(
                                priority = priority.first,
                                name = priority.second,
                                rowIndex = rowIndex
                            )

                            val current = best
                            if (current == null ||
                                candidate.priority < current.priority ||
                                (candidate.priority == current.priority && candidate.rowIndex < current.rowIndex)
                            ) {
                                best = candidate
                            }
                        }

                        for (block in visionText.textBlocks) {
                            for (line in block.lines) {
                                consider(line.text, line.boundingBox)
                            }
                        }
                        if (best == null) {
                            for (block in visionText.textBlocks) {
                                consider(block.text, block.boundingBox)
                            }
                        }
                    }

                    try { panel.bitmap.recycle() } catch (_: Throwable) {}

                    // Valparaiso e prioridade absoluta: pode encerrar cedo.
                    if (processing && best?.priority == 0) {
                        for (i in (index + 1) until panels.size) {
                            try { panels[i].bitmap.recycle() } catch (_: Throwable) {}
                        }
                        finishNeighborhoods()
                    } else {
                        processPanel(index + 1)
                    }
                }
                .addOnFailureListener {
                    totalBairroMs += SystemClock.elapsedRealtime() - started
                    try { panel.bitmap.recycle() } catch (_: Throwable) {}
                    if (!processing) return@addOnFailureListener
                    processPanel(index + 1)
                }
        }

        processPanel(0)
        return true
    }

'''

s = s[:insert_at] + helpers + s[insert_at:]

# Troca somente o dispatch da v0.27. Primeiro tenta o caminho deterministico de
# CELULAS em paineis pequenos para 31+ linhas; se nao se aplicar, preserva v0.27.
start = s.find('    private fun readDenseGridTwoStage(\n')
end = s.find('\n    private fun readMediaLargeColorCrop(media: MediaImage) {', start)
if start < 0 or end < 0:
    raise SystemExit('Patch v0.28: dispatch v0.27 nao encontrado')

new_dispatch = r'''    private fun readDenseGridTwoStage(
        media: MediaImage,
        source: Bitmap,
        decodeMs: Long
    ): Boolean {
        if (!processing) return false
        if (source.height > 1_250) return false

        val direct = detectDirectDenseGeometry(source)
        if (direct != null && readDirectDensePanels(
                media = media,
                source = source,
                decodeMs = decodeMs,
                geometry = direct
            )) {
            return true
        }

        // Fallback integral da v0.27/v0.26 para outros formatos.
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
print("Patch v0.28 aplicado: 31+ linhas usam OCR de Bairro por paineis pequenos de celulas")
