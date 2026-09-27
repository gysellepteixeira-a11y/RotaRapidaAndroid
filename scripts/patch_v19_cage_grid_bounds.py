from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

# v0.19 - GAIOLA PELA GRADE
#
# Caso real: algumas capturas trazem a coluna "Ordem" antes de "Gaiola".
# O recorte narrow anterior comecava em x=0 e, nessas imagens, lia "BACKLOG 2".
#
# Este patch NAO adiciona outro OCR. Ele detecta as primeiras linhas verticais
# pretas da grade usando amostras de pixels e escolhe a celula Gaiola:
# - layout Ordem | Gaiola | AT/TO: usa a SEGUNDA celula;
# - layout Gaiola | AT/TO: usa a PRIMEIRA celula;
# Se a grade nao for detectada com seguranca, preserva o recorte narrow antigo.

anchor = '    private fun readDenseCageOnly(\n'
if anchor not in s:
    raise SystemExit("cage grid: readDenseCageOnly nao encontrado")

helper = r'''    private fun detectDenseCageBounds(bitmap: Bitmap): Pair<Int, Int>? {
        val w = bitmap.width
        val h = bitmap.height
        if (w < 180 || h < 120) return null

        // So precisamos das primeiras colunas. As linhas da grade sao quase
        // continuas verticalmente; letras/numeros nao atingem essa densidade.
        val maxX = (w * 0.46f).toInt().coerceIn(20, w - 1)
        val yStart = (h * 0.025f).toInt().coerceIn(0, h - 1)
        val yEnd = (h * 0.985f).toInt().coerceIn(yStart + 1, h)
        val yStep = maxOf(2, h / 220)

        val candidates = ArrayList<Int>()
        var x = 1
        while (x < maxX) {
            var darkHits = 0
            var samples = 0
            var y = yStart

            while (y < yEnd) {
                val pixel = bitmap.getPixel(x, y)
                val r = (pixel shr 16) and 0xFF
                val g = (pixel shr 8) and 0xFF
                val b = pixel and 0xFF

                if (r < 150 && g < 150 && b < 150) darkHits++
                samples++
                y += yStep
            }

            if (samples > 0 && darkHits * 100 >= samples * 55) {
                candidates += x
            }
            x++
        }

        if (candidates.isEmpty()) return null

        // Agrupa os 1-3 pixels que formam a mesma divisoria apos o resize.
        val lines = ArrayList<Int>()
        var start = candidates[0]
        var prev = candidates[0]

        fun finishCluster(a: Int, b: Int) {
            val center = (a + b) / 2
            // Ignora eventual borda colada no x=0.
            if (center >= maxOf(12, (w * 0.018f).toInt())) {
                lines += center
            }
        }

        for (i in 1 until candidates.size) {
            val current = candidates[i]
            if (current <= prev + 3) {
                prev = current
            } else {
                finishCluster(start, prev)
                start = current
                prev = current
            }
        }
        finishCluster(start, prev)

        if (lines.size < 2) return null

        val first = lines[0]
        val second = lines[1]
        val firstCellWidth = first
        val secondCellWidth = second - first

        if (firstCellWidth < 24 || secondCellWidth < 24) return null

        val margin = maxOf(2, (w * 0.003f).toInt())

        // Se a segunda celula for muito mais larga, o layout comeca em Gaiola
        // e a segunda coluna ja e AT/TO. Caso contrario, a primeira e Ordem e a
        // segunda e Gaiola. Na planilha real: Ordem~54, Gaiola~48, AT/TO~94 px.
        val gaiolaLeft: Int
        val gaiolaRight: Int

        if (secondCellWidth * 100 >= firstCellWidth * 145) {
            gaiolaLeft = margin
            gaiolaRight = first - margin
        } else {
            gaiolaLeft = first + margin
            gaiolaRight = second - margin
        }

        if (gaiolaRight - gaiolaLeft < 20) return null
        return gaiolaLeft to gaiolaRight
    }

'''

if 'private fun detectDenseCageBounds(' not in s:
    s = s.replace(anchor, helper + anchor, 1)

old_slice = '''        val sliceHeight = bottom - top
        val sliceWidth = maxOf(52, (denseBitmap.width * 0.115f).toInt())
            .coerceAtMost(denseBitmap.width)

        val slice = try {
            Bitmap.createBitmap(
                denseBitmap,
                0,
                top,
                sliceWidth,
                sliceHeight
            )
'''

new_slice = '''        val sliceHeight = bottom - top

        val gridBounds = detectDenseCageBounds(denseBitmap)
        val sliceLeft: Int
        val sliceRight: Int

        if (gridBounds != null) {
            sliceLeft = gridBounds.first.coerceIn(0, denseBitmap.width - 2)
            sliceRight = gridBounds.second.coerceIn(sliceLeft + 1, denseBitmap.width)
        } else {
            // Fallback identico ao GAIOLA NARROW anterior.
            sliceLeft = 0
            sliceRight = maxOf(52, (denseBitmap.width * 0.115f).toInt())
                .coerceAtMost(denseBitmap.width)
        }

        val sliceWidth = sliceRight - sliceLeft

        val slice = try {
            Bitmap.createBitmap(
                denseBitmap,
                sliceLeft,
                top,
                sliceWidth,
                sliceHeight
            )
'''

if old_slice not in s:
    raise SystemExit("cage grid: bloco slice narrow nao encontrado")
s = s.replace(old_slice, new_slice, 1)

# Mostra no diagnostico os limites usados, para validar no M52 sem adivinhacao.
s = s.replace(
    '"gaiolaOCR=${cageOcrMs}ms | lido=[$raw] | enviando"',
    '"gaiolaOCR=${cageOcrMs}ms | x=${sliceLeft}-${sliceRight} | lido=[$raw] | enviando"',
    1
)
s = s.replace(
    '"lido=[$raw] | reforcando arquivo inteiro..."',
    '"x=${sliceLeft}-${sliceRight} | lido=[$raw] | reforcando arquivo inteiro..."',
    1
)

prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW =====',
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA GRID ====='
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")

print("Cage GRID aplicado: detecta Ordem/Gaiola/AT por linhas verticais sem OCR extra")
