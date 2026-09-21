from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.26 - GRADE VIRTUAL INDEPENDENTE DO RECORTE DO TOPO
#
# O problema observado: a mesma tabela le normal inteira, mas pode parar quando
# alguns pixels/linhas sao cortados no topo. A causa e que o detector anterior
# usava apenas as linhas horizontais fisicamente visiveis e depois escolhia a
# estrategia pelo total de linhas detectadas. Um recorte pequeno podia mudar
# 31 -> 30 e trocar completamente o caminho de OCR.
#
# Agora:
#   1) detecta o passo real da grade (ex.: 17/18 px) pelas linhas horizontais;
#   2) reconstrói uma grade VIRTUAL com esse passo, inclusive y=0/y=altura quando
#      o arquivo comeca/termina no meio de uma linha;
#   3) nao escolhe mais OCR por 29/30/31/34 linhas; escolhe pela DENSIDADE real
#      (rowSpacing <= 20 px);
#   4) toda tabela densa e dividida em fatias REAIS da planilha, equilibradas em
#      ~10-14 linhas por OCR, preservando Gaiola + Bairro na mesma imagem;
#   5) a prioridade continua sendo comparada entre TODAS as fatias antes de enviar
#      (com termino antecipado somente em Valparaiso, prioridade 0).
#
# Assim, cortar o cabecalho, algumas linhas ou comecar no meio de uma linha nao
# deve mais trocar de algoritmo nem deslocar o pareamento. As prioridades
# removidas na v0.24 continuam removidas.

# -----------------------------------------------------------------------------
# 1) SUBSTITUI O DETECTOR DE GRADE POR UMA VERSAO COM RECONSTRUCAO VIRTUAL.
# -----------------------------------------------------------------------------
start = s.find('    private fun detectDenseGridLayout(source: Bitmap): DenseGridLayout? {')
end = s.find('\n    private fun scaledCrop(', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'Patch v0.26: detectDenseGridLayout nao encontrado (start={start}, end={end})'
    )

new_detector = r'''    private fun detectDenseGridLayout(source: Bitmap): DenseGridLayout? {
        val started = SystemClock.elapsedRealtime()
        val w = source.width
        val h = source.height

        if (w < 750 || h < 260) return null

        // ---------- LINHAS VERTICAIS ----------
        val yStep = 3
        val sampledY = ((h + yStep - 1) / yStep).coerceAtLeast(1)
        val minVerticalHits = maxOf(24, (sampledY * 0.50f).toInt())
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

        // ---------- LINHAS HORIZONTAIS REAIS ----------
        val xStep = 4
        val sampledX = ((w + xStep - 1) / xStep).coerceAtLeast(1)
        val minHorizontalHits = maxOf(35, (sampledX * 0.33f).toInt())
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

        if (horizontal.size < 8) return null

        // O passo da tabela vem dos gaps mais frequentes/consistentes. Ignoramos
        // gaps muito pequenos (linha grossa duplicada) e grandes (linha perdida).
        val gaps = horizontal.zipWithNext()
            .map { (a, b) -> b - a }
            .filter { it in 8..45 }

        if (gaps.size < 6) return null

        // Moda aproximada e mais robusta que depender somente da mediana quando
        // existe cabecalho com altura diferente.
        val buckets = gaps.groupingBy { it }.eachCount()
        val modeGap = buckets.maxByOrNull { it.value }?.key ?: return null
        val nearMode = gaps
            .filter { kotlin.math.abs(it - modeGap) <= 2 }
            .sorted()
        if (nearMode.size < 4) return null

        val rowSpacing = nearMode[nearMode.size / 2].toFloat()
        if (rowSpacing < 8f || rowSpacing > 45f) return null

        // ---------- GRADE VIRTUAL ----------
        // Escolhe uma linha real em regiao central como ancora e projeta o passo
        // para cima e para baixo. Para cada previsao, usa a linha real mais
        // proxima se ela estiver dentro da tolerancia; senao mantem a previsao.
        val anchor = horizontal[horizontal.size / 2]
        val tolerance = maxOf(2, (rowSpacing * 0.22f).toInt())
        val virtual = mutableListOf<Int>()

        var predicted = anchor.toFloat()
        while (predicted - rowSpacing >= 0f) {
            predicted -= rowSpacing
        }

        while (predicted <= h - 1 + rowSpacing * 0.25f) {
            val p = predicted.toInt().coerceIn(0, h - 1)
            val nearest = horizontal.minByOrNull { kotlin.math.abs(it - p) }
            val chosen = if (nearest != null && kotlin.math.abs(nearest - p) <= tolerance) {
                nearest
            } else {
                p
            }

            if (virtual.isEmpty() || chosen - virtual.last() >= maxOf(4, (rowSpacing * 0.45f).toInt())) {
                virtual += chosen
            }
            predicted += rowSpacing
        }

        if (virtual.size < 8) return null

        // Se o arquivo comecou/terminou no meio de uma linha, y=0 e/ou h-1 viram
        // bordas virtuais. Isso inclui a linha parcial sem deslocar as demais.
        val first = virtual.first()
        if (first > rowSpacing * 0.35f) {
            virtual.add(0, 0)
        } else if (first <= 2) {
            virtual[0] = 0
        }

        val last = virtual.last()
        val remaining = (h - 1) - last
        if (remaining > rowSpacing * 0.35f) {
            virtual += (h - 1)
        } else if (remaining in 0..2) {
            virtual[virtual.lastIndex] = h - 1
        }

        // Remove qualquer duplicata/intervalo residual muito curto.
        val clean = mutableListOf<Int>()
        for (value in virtual.distinct().sorted()) {
            if (clean.isEmpty()) {
                clean += value
            } else {
                val d = value - clean.last()
                if (d >= maxOf(4, (rowSpacing * 0.35f).toInt())) {
                    clean += value
                }
            }
        }

        if (clean.size < 8) return null

        return DenseGridLayout(
            gaiolaRight = gaiolaRight,
            bairroLeft = bairroLeft,
            bairroRight = bairroRight,
            horizontalLines = clean,
            rowCount = clean.size - 1,
            rowSpacing = rowSpacing,
            scanMs = SystemClock.elapsedRealtime() - started
        )
    }
'''

s = s[:start] + new_detector + s[end:]

# -----------------------------------------------------------------------------
# 2) FATIAS EQUILIBRADAS. FUNCIONA PARA QUALQUER TABELA DENSA, NAO SO 34+.
# -----------------------------------------------------------------------------
start = s.find('    private fun buildDenseRouteChunks(\n')
end = s.find('\n    private fun readDenseGridChunks(', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'Patch v0.26: buildDenseRouteChunks nao encontrado (start={start}, end={end})'
    )

new_chunks = r'''    private fun buildDenseRouteChunks(
        source: Bitmap,
        layout: DenseGridLayout
    ): List<DenseRouteChunk>? {
        val rows = layout.horizontalLines.zipWithNext()
        if (rows.size < 12) return null

        // Em vez de 14 + 14 + 3, distribui de forma equilibrada:
        // 31 linhas -> ~11/10/10; 38 linhas -> ~13/13/12.
        val maxRowsPerChunk = 14
        val chunkCount = ((rows.size + maxRowsPerChunk - 1) / maxRowsPerChunk)
            .coerceAtLeast(1)
        val baseSize = rows.size / chunkCount
        val extra = rows.size % chunkCount

        val result = mutableListOf<DenseRouteChunk>()
        val x1 = 0
        val x2 = (layout.bairroRight + 4).coerceIn(2, source.width)

        var first = 0
        for (chunkIndex in 0 until chunkCount) {
            val thisCount = baseSize + if (chunkIndex < extra) 1 else 0
            if (thisCount <= 0) continue

            val lastExclusive = (first + thisCount).coerceAtMost(rows.size)

            val rawY1 = rows[first].first
            val rawY2 = rows[lastExclusive - 1].second
            val y1 = rawY1.coerceIn(0, source.height - 2)
            val y2 = rawY2.coerceIn(y1 + 2, source.height)

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

            // Mira 32-36 px por linha depois da ampliacao, sem criar bitmap enorme.
            var scale = (35f / layout.rowSpacing).coerceIn(1.35f, 2.25f)
            val biggest = maxOf(crop.width, crop.height).toFloat()
            if (biggest * scale > 1_700f) {
                scale = 1_700f / biggest
            }
            scale = scale.coerceAtLeast(1.10f)

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

        return result.ifEmpty { null }
    }
'''

s = s[:start] + new_chunks + s[end:]

# -----------------------------------------------------------------------------
# 3) SELECAO POR DENSIDADE/ESPACAMENTO, NAO POR QUANTIDADE DE LINHAS.
# -----------------------------------------------------------------------------
start = s.find('    private fun readDenseGridTwoStage(\n')
end = s.find('\n    private fun readMediaLargeColorCrop(media: MediaImage) {', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'Patch v0.26: readDenseGridTwoStage nao encontrado (start={start}, end={end})'
    )

new_dispatch = r'''    private fun readDenseGridTwoStage(
        media: MediaImage,
        source: Bitmap,
        decodeMs: Long
    ): Boolean {
        if (!processing) return false
        if (source.height > 1_250) return false

        val layout = detectDenseGridLayout(source) ?: return false

        // O que define a rota dificil e o texto estar espremido (passo pequeno),
        // nao o numero arbitrario de linhas visiveis. Um recorte no topo pode
        // mudar 31 -> 30, mas nao muda o passo de 17/18 px.
        val isDense = layout.rowSpacing <= 20.5f && layout.rowCount >= 12
        if (!isDense) return false

        Prefs.setStatus(
            this,
            "GRID VIRTUAL: ${layout.rowCount} linhas | passo=" +
                String.format(java.util.Locale.US, "%.1f", layout.rowSpacing) +
                "px | fatias reais..."
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

# Ajusta somente os textos de status da funcao de fatias existente para ficar
# claro nos testes que a v0.26 entrou.
s = s.replace('"GRID FATIAS ${layout.rowCount}: nenhuma prioridade encontrada. "',
              '"GRID VIRTUAL ${layout.rowCount}: nenhuma prioridade encontrada. "')
s = s.replace('"Arquivo repetido ignorado | GRID FATIAS"',
              '"Arquivo repetido ignorado | GRID VIRTUAL"')
s = s.replace('"GRID FATIAS ${layout.rowCount}: ${route.neighborhood} -> ${route.cage} | "',
              '"GRID VIRTUAL ${layout.rowCount}: ${route.neighborhood} -> ${route.cage} | "')
s = s.replace('"GRID FATIAS: ${layout.rowCount} linhas | parte ${index + 1}/${chunks.size} "',
              '"GRID VIRTUAL: ${layout.rowCount} linhas | parte ${index + 1}/${chunks.size} "')

service_path.write_text(s, encoding="utf-8")
print("Patch v0.26 aplicado: grade virtual + selecao por espacamento + fatias equilibradas")
