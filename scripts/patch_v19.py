from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - TABELA DENSA MESMO QUANDO O ARQUIVO E BAIXO
#
# A v0.18 decidia se a rota era "grande" quase so pela ALTURA do arquivo
# (>= 2200 px). A imagem que falhou tem muitas linhas, mas mede aproximadamente
# 1074x666: cada linha fica com ~18 px e o OCR completo pode nao reconhecer o
# bairro prioritario. Agora contamos as faixas verde/laranja da coluna Agency.
# Se houver muitas linhas, tratamos como tabela densa independentemente da altura,
# recortamos Gaiola+Bairro e ampliamos o recorte antes de UM unico OCR.
#
# Texto, prioridade e envio da v0.16/v0.17 ficam intactos.

const_anchor = '        private const val LARGE_FILE_HEIGHT_PX = 2_200\n'
if 'DENSE_MIN_ROWS' not in s:
    if const_anchor not in s:
        raise SystemExit('Patch v0.19: constante LARGE_FILE_HEIGHT_PX nao encontrada')
    s = s.replace(
        const_anchor,
        const_anchor + '        private const val DENSE_MIN_ROWS = 14\n',
        1
    )

# O crop agora carrega tambem a quantidade estimada de linhas da tabela.
old_data = '''    private data class ColorTableCrop(\n        val bitmap: Bitmap,\n        val widthRatio: Float,\n        val scanMs: Long\n    )\n'''
new_data = '''    private data class ColorTableCrop(\n        val bitmap: Bitmap,\n        val widthRatio: Float,\n        val scanMs: Long,\n        val rowCount: Int\n    )\n'''
if old_data not in s:
    raise SystemExit('Patch v0.19: ColorTableCrop da v0.18 nao encontrado')
s = s.replace(old_data, new_data, 1)

# Aceita imagens densas que tenham pouca altura total.
s = s.replace(
    '        if (w < 300 || h < 500) return null\n',
    '        if (w < 500 || h < 260) return null\n',
    1
)
s = s.replace(
    '        val xStart = (w * 0.46f).toInt().coerceIn(0, w - 1)\n',
    '        val xStart = (w * 0.38f).toInt().coerceIn(0, w - 1)\n',
    1
)
s = s.replace(
    '        val yStart = (h * 0.04f).toInt().coerceIn(0, h - 1)\n',
    '        val yStart = (h * 0.015f).toInt().coerceIn(0, h - 1)\n',
    1
)

# Nesta planilha Agency comeca perto de 47% da largura, portanto o limite 52%
# da v0.18 descartava justamente essa imagem.
s = s.replace(
    '        if (agencyRatio < 0.52f || agencyRatio > 0.95f) return null\n',
    '        if (agencyRatio < 0.42f || agencyRatio > 0.95f) return null\n',
    1
)
s = s.replace(
    '        if (widthRatio > 0.90f || widthRatio < 0.48f) return null\n',
    '        if (widthRatio > 0.90f || widthRatio < 0.42f) return null\n',
    1
)

# Insere contagem de linhas pelas faixas coloridas. Fazemos isso na banda estreita
# de Agency, entao o custo e muito menor que um OCR extra.
anchor = '''        if (bandHits < 12 || maxColorY <= minColorY) return null\n\n        val yMargin = maxOf(18, (h * 0.012f).toInt())\n'''
insert = '''        if (bandHits < 12 || maxColorY <= minColorY) return null\n\n        // Conta blocos horizontais verdes/laranjas. Cada botao de Agency ocupa\n        // uma linha da tabela e existe pelo menos uma pequena separacao vertical\n        // entre dois botoes consecutivos.\n        val rowScanX1 = agencyLeft.coerceIn(0, w - 1)\n        val rowScanX2 = (agencyLeft + maxOf(70, w / 9))\n            .coerceIn(rowScanX1 + 1, w)\n        val rowThreshold = maxOf(5, (rowScanX2 - rowScanX1) / 16)\n\n        var rowCount = 0\n        var insideColorRow = false\n        var yy = yStart\n        while (yy < yEnd) {\n            var colorCount = 0\n            var xx = rowScanX1\n            while (xx < rowScanX2) {\n                if (isAgencyColor(source.getPixel(xx, yy))) {\n                    colorCount++\n                }\n                xx += 2\n            }\n\n            val active = colorCount >= rowThreshold\n            if (active && !insideColorRow) {\n                rowCount++\n                insideColorRow = true\n            } else if (!active) {\n                insideColorRow = false\n            }\n            yy++\n        }\n\n        if (rowCount < 2) return null\n\n        val yMargin = maxOf(18, (h * 0.012f).toInt())\n'''
if anchor not in s:
    raise SystemExit('Patch v0.19: ponto de contagem de linhas nao encontrado')
s = s.replace(anchor, insert, 1)

old_return = '''        return ColorTableCrop(\n            bitmap = crop,\n            widthRatio = widthRatio,\n            scanMs = SystemClock.elapsedRealtime() - started\n        )\n'''
new_return = '''        return ColorTableCrop(\n            bitmap = crop,\n            widthRatio = widthRatio,\n            scanMs = SystemClock.elapsedRealtime() - started,\n            rowCount = rowCount\n        )\n'''
if old_return not in s:
    raise SystemExit('Patch v0.19: retorno ColorTableCrop nao encontrado')
s = s.replace(old_return, new_return, 1)

# Nao depende mais de 2200 px. A partir de 500 px vale fazer o scan barato; se
# nao for densa, voltamos imediatamente para o OCR normal.
old_dispatch = '''        if (media.height >= LARGE_FILE_HEIGHT_PX) {\n            readMediaLargeColorCrop(media)\n        } else {\n            readMediaOriginalFull(media)\n        }\n'''
new_dispatch = '''        if (media.height >= 500) {\n            readMediaLargeColorCrop(media)\n        } else {\n            readMediaOriginalFull(media)\n        }\n'''
if old_dispatch not in s:
    raise SystemExit('Patch v0.19: dispatch grande da v0.18 nao encontrado')
s = s.replace(old_dispatch, new_dispatch, 1)

# Substitui so a funcao que executa o OCR do crop, preservando detectores e
# fallbacks da v0.18.
start = s.find('    private fun readMediaLargeColorCrop(media: MediaImage) {')
end = s.find('\n    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'Patch v0.19: readMediaLargeColorCrop nao encontrado (start={start}, end={end})'
    )

new_fun = r'''    private fun readMediaLargeColorCrop(media: MediaImage) {
        if (!processing) return

        val decodeStarted = SystemClock.elapsedRealtime()
        val source = try {
            contentResolver.openInputStream(media.uri)?.use { stream ->
                BitmapFactory.decodeStream(stream)
            }
        } catch (_: Throwable) {
            null
        }

        if (source == null) {
            readMediaOriginalFull(media)
            return
        }

        val decodeMs = SystemClock.elapsedRealtime() - decodeStarted
        val detected = detectLargeTableCrop(source)

        if (detected == null) {
            try { source.recycle() } catch (_: Throwable) {}
            readMediaOriginalFull(media)
            return
        }

        // Se ha poucas linhas, a rota pequena ja funciona muito bem no OCR normal.
        // Nao aplicamos ampliacao/crop agressivo nela.
        if (detected.rowCount < DENSE_MIN_ROWS) {
            try { detected.bitmap.recycle() } catch (_: Throwable) {}
            try { source.recycle() } catch (_: Throwable) {}
            readMediaOriginalFull(media)
            return
        }

        var crop = detected.bitmap
        try { source.recycle() } catch (_: Throwable) {}

        // Em tabelas muito densas, o numero de pixels por linha fica pequeno.
        // Escala adaptativa: tenta deixar cada linha perto de 28 px de altura.
        val desiredScale = (
            (detected.rowCount * 28f) / crop.height.toFloat()
        ).coerceIn(1.15f, 1.85f)

        val biggest = maxOf(crop.width, crop.height).toFloat()
        val maxAllowed = if (biggest > 0f) 2_400f / biggest else 1f
        val scale = minOf(desiredScale, maxAllowed.coerceAtLeast(1f))

        val ocrBitmap = if (scale > 1.04f) {
            try {
                Bitmap.createScaledBitmap(
                    crop,
                    (crop.width * scale).toInt().coerceAtLeast(1),
                    (crop.height * scale).toInt().coerceAtLeast(1),
                    true
                )
            } catch (_: Throwable) {
                crop
            }
        } else {
            crop
        }

        if (ocrBitmap !== crop) {
            try { crop.recycle() } catch (_: Throwable) {}
            crop = ocrBitmap
        }

        val started = SystemClock.elapsedRealtime()
        val input = InputImage.fromBitmap(crop, 0)

        Prefs.setStatus(
            this,
            "DENSA: ${detected.rowCount} linhas | crop ${(detected.widthRatio * 100).toInt()}% | " +
                "x${String.format(java.util.Locale.US, \"%.2f\", scale)} | OCR..."
        )

        recognizer.process(input)
            .addOnSuccessListener { visionText ->
                if (!processing) {
                    try { crop.recycle() } catch (_: Throwable) {}
                    return@addOnSuccessListener
                }

                val route = parseVisionText(visionText, crop.height)
                val elapsed = SystemClock.elapsedRealtime() - started
                val totalLinhas = contarLinhasVisionText(visionText)

                try { crop.recycle() } catch (_: Throwable) {}

                if (route != null) {
                    if (isDuplicate(route)) {
                        finishFileOnlyFailure(
                            "Arquivo repetido ignorado | OCR denso=${elapsed}ms"
                        )
                    } else {
                        Prefs.setStatus(
                            this,
                            "DENSA ${detected.rowCount}: ${route.neighborhood} -> ${route.cage} | " +
                                "decode=${decodeMs}ms scan=${detected.scanMs}ms " +
                                "OCR=${elapsed}ms | enviando"
                        )
                        sendRouteInCurrentChat(route)
                    }
                } else {
                    Prefs.setStatus(
                        this,
                        "OCR denso leu $totalLinhas linhas sem fechar rota. " +
                            "Tentando leitura reforcada do arquivo inteiro..."
                    )
                    readMediaEnhanced(media)
                }
            }
            .addOnFailureListener {
                try { crop.recycle() } catch (_: Throwable) {}
                if (!processing) return@addOnFailureListener
                readMediaEnhanced(media)
            }
    }

'''

s = s[:start] + new_fun + s[end:]
service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 aplicado: detecta tabela densa por quantidade de linhas coloridas e amplia antes do OCR")
