from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.21 - TABELA DENSA/BAIXA: OCR SOMENTE GAIOLA + BAIRRO
#
# A v0.19 melhorou bastante as tabelas grandes normais, mas uma tabela muito
# larga, com ~38 linhas em apenas ~666 px de altura, ainda pode falhar porque o
# OCR recebe Gaiola + AT/TO + SPR + Cidade + Bairro ao mesmo tempo.
#
# Nesta versao, SOMENTE para tabelas densas e baixas:
#   1) usa a coluna colorida de Agencia ja detectada pela v0.19;
#   2) acha as linhas verticais pretas da grade por pixels (sem OCR extra);
#   3) extrai apenas a coluna Gaiola e a coluna Bairro;
#   4) cola as duas lado a lado preservando exatamente o Y das linhas;
#   5) amplia esse bitmap estreito e roda UM OCR.
#
# Assim o parseVisionText continua trabalhando igual: em cada linha visual ele
# ve algo como "J-16  Colina de Laranjeiras", mas sem o ruido das colunas do meio.
# As imagens grandes que ja ficaram rapidas na v0.19 continuam no caminho antigo.

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------
import_anchor = 'import android.graphics.Bitmap\n'
extra_imports = 'import android.graphics.Canvas\nimport android.graphics.Color\nimport android.graphics.Paint\n'
if 'import android.graphics.Canvas' not in s:
    if import_anchor not in s:
        raise SystemExit('Patch v0.21: import Bitmap nao encontrado')
    s = s.replace(import_anchor, import_anchor + extra_imports, 1)

# -----------------------------------------------------------------------------
# ColorTableCrop: guarda tambem o X real onde comeca a coluna Agencia.
# -----------------------------------------------------------------------------
old_data = '''    private data class ColorTableCrop(\n        val bitmap: Bitmap,\n        val widthRatio: Float,\n        val scanMs: Long,\n        val rowCount: Int\n    )\n'''
new_data = '''    private data class ColorTableCrop(\n        val bitmap: Bitmap,\n        val widthRatio: Float,\n        val scanMs: Long,\n        val rowCount: Int,\n        val agencyLeft: Int\n    )\n'''
if old_data not in s:
    raise SystemExit('Patch v0.21: ColorTableCrop da v0.19 nao encontrado')
s = s.replace(old_data, new_data, 1)

old_return = '''        return ColorTableCrop(\n            bitmap = crop,\n            widthRatio = widthRatio,\n            scanMs = SystemClock.elapsedRealtime() - started,\n            rowCount = rowCount\n        )\n'''
new_return = '''        return ColorTableCrop(\n            bitmap = crop,\n            widthRatio = widthRatio,\n            scanMs = SystemClock.elapsedRealtime() - started,\n            rowCount = rowCount,\n            agencyLeft = agencyLeft\n        )\n'''
if old_return not in s:
    raise SystemExit('Patch v0.21: retorno ColorTableCrop da v0.19 nao encontrado')
s = s.replace(old_return, new_return, 1)

# -----------------------------------------------------------------------------
# Helpers de grade compacta.
# -----------------------------------------------------------------------------
insert_at = s.find('    private fun readMediaLargeColorCrop(media: MediaImage) {')
if insert_at < 0:
    raise SystemExit('Patch v0.21: readMediaLargeColorCrop nao encontrado')

helpers = r'''    private data class CompactGrid(
        val gaiolaRight: Int,
        val bairroLeft: Int,
        val bairroRight: Int
    )

    private fun detectCompactGrid(source: Bitmap, agencyLeft: Int): CompactGrid? {
        val w = source.width
        val h = source.height
        if (w < 500 || h < 300) return null

        // Linhas verticais da planilha sao muito escuras e atravessam quase toda
        // a altura. Texto tambem e escuro, mas nao permanece no mesmo X em mais
        // de ~70% da imagem; por isso o limiar abaixo separa bem grade de letras.
        val yStep = 3
        val sampledRows = ((h + yStep - 1) / yStep).coerceAtLeast(1)
        val minDarkHits = maxOf(30, (sampledRows * 0.70f).toInt())

        val xMin = (w * 0.018f).toInt().coerceAtLeast(1)
        val xMax = (agencyLeft + maxOf(4, w / 250)).coerceIn(xMin + 1, w - 1)

        val rawLines = mutableListOf<Int>()

        var x = xMin
        while (x <= xMax) {
            var hits = 0
            var y = 0
            while (y < h) {
                val pixel = source.getPixel(x, y)
                val r = (pixel shr 16) and 0xFF
                val g = (pixel shr 8) and 0xFF
                val b = pixel and 0xFF

                if (r <= 120 && g <= 120 && b <= 120) {
                    hits++
                }
                y += yStep
            }

            if (hits >= minDarkHits) {
                rawLines += x
            }
            x++
        }

        if (rawLines.size < 4) return null

        // Agrupa linhas de 1-3 px de espessura numa unica coordenada.
        val groups = mutableListOf<MutableList<Int>>()
        for (value in rawLines) {
            val last = groups.lastOrNull()
            if (last == null || value - last.last() > 2) {
                groups += mutableListOf(value)
            } else {
                last += value
            }
        }

        val lines = groups
            .map { group -> group.average().toInt() }
            .filter { it < agencyLeft + maxOf(5, w / 200) }
            .sorted()

        if (lines.size < 5) return null

        // Estrutura da tabela: Gaiola | AT/TO | SPR | Cidade | Bairro | Agencia.
        // Portanto: primeira divisoria = fim de Gaiola; duas ultimas antes de
        // Agencia = inicio e fim de Bairro.
        val gaiolaRight = lines.first()
        val bairroRight = lines.last()
        val bairroLeft = lines[lines.lastIndex - 1]

        val gaiolaRatio = gaiolaRight.toFloat() / w.toFloat()
        if (gaiolaRatio < 0.025f || gaiolaRatio > 0.18f) return null

        val bairroWidth = bairroRight - bairroLeft
        if (bairroWidth < maxOf(70, (w * 0.09f).toInt())) return null

        // O fim do Bairro deve ficar praticamente colado ao inicio da Agencia.
        if (kotlin.math.abs(agencyLeft - bairroRight) > maxOf(32, (w * 0.045f).toInt())) {
            return null
        }

        return CompactGrid(
            gaiolaRight = gaiolaRight,
            bairroLeft = bairroLeft,
            bairroRight = bairroRight
        )
    }

    private fun buildCompactGaiolaBairroBitmap(
        source: Bitmap,
        grid: CompactGrid,
        rowCount: Int
    ): Pair<Bitmap, Float>? {
        val w = source.width
        val h = source.height

        val gaiolaX1 = 0
        val gaiolaX2 = (grid.gaiolaRight + 1).coerceIn(2, w)
        val bairroX1 = (grid.bairroLeft + 1).coerceIn(0, w - 2)
        val bairroX2 = grid.bairroRight.coerceIn(bairroX1 + 2, w)

        val gaiolaWidth = gaiolaX2 - gaiolaX1
        val bairroWidth = bairroX2 - bairroX1
        val gap = maxOf(8, w / 90)
        val combinedWidth = gaiolaWidth + gap + bairroWidth

        if (gaiolaWidth < 20 || bairroWidth < 60 || combinedWidth < 100) return null

        val combined = try {
            Bitmap.createBitmap(
                combinedWidth,
                h,
                Bitmap.Config.ARGB_8888
            )
        } catch (_: Throwable) {
            return null
        }

        try {
            val canvas = Canvas(combined)
            canvas.drawColor(Color.WHITE)
            val paint = Paint(Paint.FILTER_BITMAP_FLAG)

            canvas.drawBitmap(
                source,
                Rect(gaiolaX1, 0, gaiolaX2, h),
                Rect(0, 0, gaiolaWidth, h),
                paint
            )

            canvas.drawBitmap(
                source,
                Rect(bairroX1, 0, bairroX2, h),
                Rect(gaiolaWidth + gap, 0, combinedWidth, h),
                paint
            )
        } catch (_: Throwable) {
            try { combined.recycle() } catch (_: Throwable) {}
            return null
        }

        // Nesta classe de imagem cada linha original pode ter apenas ~15-20 px.
        // Como o bitmap ficou muito estreito, podemos ampliar forte sem custo alto.
        val desiredScale = ((rowCount * 40f) / h.toFloat()).coerceIn(2.15f, 2.65f)
        val biggest = maxOf(combined.width, combined.height).toFloat()
        val maxAllowed = if (biggest > 0f) 2_100f / biggest else 1f
        val scale = minOf(desiredScale, maxAllowed.coerceAtLeast(1f))

        if (scale <= 1.04f) {
            return combined to 1f
        }

        val scaled = try {
            Bitmap.createScaledBitmap(
                combined,
                (combined.width * scale).toInt().coerceAtLeast(1),
                (combined.height * scale).toInt().coerceAtLeast(1),
                true
            )
        } catch (_: Throwable) {
            combined
        }

        if (scaled !== combined) {
            try { combined.recycle() } catch (_: Throwable) {}
        }

        return scaled to scale
    }

    private fun readCompactDenseColumns(
        media: MediaImage,
        source: Bitmap,
        detected: ColorTableCrop,
        decodeMs: Long
    ): Boolean {
        val gridStarted = SystemClock.elapsedRealtime()
        val grid = detectCompactGrid(source, detected.agencyLeft) ?: return false
        val gridMs = SystemClock.elapsedRealtime() - gridStarted

        val built = buildCompactGaiolaBairroBitmap(
            source = source,
            grid = grid,
            rowCount = detected.rowCount
        ) ?: return false

        val compact = built.first
        val scale = built.second

        // Nao precisamos mais do crop normal da v0.19 nem da imagem completa.
        try { detected.bitmap.recycle() } catch (_: Throwable) {}
        try { source.recycle() } catch (_: Throwable) {}

        val input = InputImage.fromBitmap(compact, 0)
        val started = SystemClock.elapsedRealtime()

        Prefs.setStatus(
            this,
            "COMPACTA: ${detected.rowCount} linhas | Gaiola+Bairro | " +
                "x${String.format(java.util.Locale.US, "%.2f", scale)} | OCR..."
        )

        recognizer.process(input)
            .addOnSuccessListener { visionText ->
                if (!processing) {
                    try { compact.recycle() } catch (_: Throwable) {}
                    return@addOnSuccessListener
                }

                val route = parseVisionText(visionText, compact.height)
                val elapsed = SystemClock.elapsedRealtime() - started
                val totalLinhas = contarLinhasVisionText(visionText)

                try { compact.recycle() } catch (_: Throwable) {}

                if (route != null) {
                    if (isDuplicate(route)) {
                        finishFileOnlyFailure(
                            "Arquivo repetido ignorado | OCR compacto=${elapsed}ms"
                        )
                    } else {
                        Prefs.setStatus(
                            this,
                            "COMPACTA ${detected.rowCount}: ${route.neighborhood} -> ${route.cage} | " +
                                "decode=${decodeMs}ms grid=${gridMs}ms OCR=${elapsed}ms | enviando"
                        )
                        sendRouteInCurrentChat(route)
                    }
                } else {
                    Prefs.setStatus(
                        this,
                        "OCR compacto leu $totalLinhas linhas sem fechar rota. " +
                            "Tentando leitura reforcada do arquivo..."
                    )
                    readMediaEnhanced(media)
                }
            }
            .addOnFailureListener {
                try { compact.recycle() } catch (_: Throwable) {}
                if (!processing) return@addOnFailureListener
                readMediaEnhanced(media)
            }

        return true
    }

'''

s = s[:insert_at] + helpers + s[insert_at:]

# -----------------------------------------------------------------------------
# No caminho v0.19, tenta o modo compacto APENAS para tabela realmente densa e
# baixa. Todo o restante continua exatamente no caminho que ja chegou a 1.2-1.4s.
# -----------------------------------------------------------------------------
anchor = '''        val decodeMs = SystemClock.elapsedRealtime() - decodeStarted\n        val detected = detectLargeTableCrop(source)\n\n        if (detected == null) {\n'''
replacement = '''        val decodeMs = SystemClock.elapsedRealtime() - decodeStarted\n        val detected = detectLargeTableCrop(source)\n\n        if (detected != null &&\n            detected.rowCount >= 20 &&\n            source.height <= 1_100\n        ) {\n            if (readCompactDenseColumns(media, source, detected, decodeMs)) {\n                return\n            }\n        }\n\n        if (detected == null) {\n'''
if anchor not in s:
    raise SystemExit('Patch v0.21: ponto de dispatch compacto nao encontrado')
s = s.replace(anchor, replacement, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.21 aplicado: tabelas densas/baixas usam bitmap Gaiola+Bairro lado a lado")
