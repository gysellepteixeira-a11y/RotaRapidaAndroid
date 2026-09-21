from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.18 - EXPERIMENTO PARA TABELAS GRANDES
#
# A v0.17 fazia DOIS OCRs nas imagens grandes: primeiro no cabecalho para achar
# as colunas e depois no recorte. Nos testes isso nao trouxe ganho e o total ficou
# em ~2.5-2.7 s. A v0.18 elimina esse OCR extra.
#
# Para tabelas grandes, detectamos a coluna colorida de Agency diretamente pelos
# PIXELS (verde/laranja) do arquivo. Isso e muito barato. Como Gaiola + Bairro
# ficam a esquerda de Agency, recortamos a imagem imediatamente antes da coluna
# colorida e fazemos APENAS UM OCR nesse recorte. Se a deteccao por cor nao for
# confiavel ou o OCR nao fechar a rota, cai no OCR completo da v0.16/v0.17.
#
# Rotas pequenas, rota de texto, prioridade e envio ficam intactos.

start = s.find('    private fun readMediaOriginal(media: MediaImage) {')
end = s.find('    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'Patch v0.18: bloco OCR grande da v0.17 nao encontrado (start={start}, end={end})'
    )

new_read = r'''    private data class ColorTableCrop(
        val bitmap: Bitmap,
        val widthRatio: Float,
        val scanMs: Long
    )

    private fun isAgencyColor(pixel: Int): Boolean {
        val r = (pixel shr 16) and 0xFF
        val g = (pixel shr 8) and 0xFF
        val b = pixel and 0xFF

        val maxC = maxOf(r, g, b)
        val minC = minOf(r, g, b)
        if (maxC - minC < 38) return false

        // Verde vivo dos botoes/estado disponivel.
        val green =
            g >= 95 &&
            g >= r + 24 &&
            g >= b + 18

        // Laranja vivo usado em outro estado da coluna Agency.
        val orange =
            r >= 145 &&
            g >= 65 &&
            g <= 205 &&
            r >= g + 22 &&
            g >= b + 18

        return green || orange
    }

    private fun detectLargeTableCrop(source: Bitmap): ColorTableCrop? {
        val started = SystemClock.elapsedRealtime()
        val w = source.width
        val h = source.height

        if (w < 300 || h < 500) return null

        // Procura a coluna colorida apenas na metade direita, onde Agency fica.
        // Passo 4 reduz muito o custo sem perder a faixa larga dos botoes.
        val step = 4
        val xStart = (w * 0.46f).toInt().coerceIn(0, w - 1)
        val yStart = (h * 0.04f).toInt().coerceIn(0, h - 1)
        val yEnd = (h * 0.985f).toInt().coerceIn(yStart + 1, h)

        val bins = ((w - xStart) / step + 2).coerceAtLeast(2)
        val xHits = IntArray(bins)

        var totalHits = 0

        var y = yStart
        while (y < yEnd) {
            var x = xStart
            while (x < w) {
                val pixel = source.getPixel(x, y)
                if (isAgencyColor(pixel)) {
                    val bin = ((x - xStart) / step).coerceIn(0, bins - 1)
                    xHits[bin]++
                    totalHits++
                }
                x += step
            }
            y += step
        }

        if (totalHits < 120) return null

        var bestBin = -1
        var bestHits = 0
        for (i in xHits.indices) {
            if (xHits[i] > bestHits) {
                bestHits = xHits[i]
                bestBin = i
            }
        }

        // Uma coluna real precisa aparecer em muitas alturas diferentes.
        val sampledRows = ((yEnd - yStart) / step).coerceAtLeast(1)
        val minColumnHits = maxOf(18, (sampledRows * 0.055f).toInt())
        if (bestBin < 0 || bestHits < minColumnHits) return null

        // Expande para a esquerda/direita enquanto o histograma ainda parece
        // pertencer ao mesmo bloco colorido. O limite esquerdo e o que importa.
        val bandThreshold = maxOf(4, (bestHits * 0.22f).toInt())

        var leftBin = bestBin
        var gaps = 0
        var i = bestBin - 1
        while (i >= 0) {
            if (xHits[i] >= bandThreshold) {
                leftBin = i
                gaps = 0
            } else {
                gaps++
                if (gaps >= 3) break
            }
            i--
        }

        val agencyLeft = xStart + leftBin * step

        // Agency precisa estar realmente na metade direita. Se cair cedo demais,
        // provavelmente detectamos outra cor da imagem e nao arriscamos o crop.
        val agencyRatio = agencyLeft.toFloat() / w.toFloat()
        if (agencyRatio < 0.52f || agencyRatio > 0.95f) return null

        // Mantem alguns pixels antes de Agency para nao cortar o final do Bairro.
        val rightMargin = maxOf(12, (w * 0.012f).toInt())
        val cropRight = (agencyLeft + rightMargin).coerceIn(1, w)
        val widthRatio = cropRight.toFloat() / w.toFloat()

        // Se quase nao houver reducao, nao vale criar bitmap/rodar caminho especial.
        if (widthRatio > 0.90f || widthRatio < 0.48f) return null

        // Agora descobre a faixa vertical da tabela olhando APENAS perto da coluna
        // Agency detectada. Isso remove cabecalho/rodape/espacos sem fazer OCR.
        val bandX1 = (agencyLeft - maxOf(12, w / 80)).coerceIn(0, w - 1)
        val bandX2 = (agencyLeft + maxOf(60, w / 10)).coerceIn(bandX1 + 1, w)

        var minColorY = h
        var maxColorY = -1
        var bandHits = 0

        y = yStart
        while (y < yEnd) {
            var x = bandX1
            var rowHit = false
            while (x < bandX2) {
                if (isAgencyColor(source.getPixel(x, y))) {
                    rowHit = true
                    bandHits++
                    break
                }
                x += step
            }

            if (rowHit) {
                if (y < minColorY) minColorY = y
                if (y > maxColorY) maxColorY = y
            }
            y += step
        }

        if (bandHits < 12 || maxColorY <= minColorY) return null

        val yMargin = maxOf(18, (h * 0.012f).toInt())
        val cropTop = (minColorY - yMargin).coerceIn(0, h - 1)
        val cropBottom = (maxColorY + yMargin).coerceIn(cropTop + 1, h)
        val cropHeight = cropBottom - cropTop

        // Nao aceita uma faixa vertical suspeitamente pequena.
        if (cropHeight < (h * 0.28f).toInt()) return null

        val crop = try {
            Bitmap.createBitmap(
                source,
                0,
                cropTop,
                cropRight,
                cropHeight
            )
        } catch (_: Throwable) {
            null
        } ?: return null

        return ColorTableCrop(
            bitmap = crop,
            widthRatio = widthRatio,
            scanMs = SystemClock.elapsedRealtime() - started
        )
    }

    private fun readMediaOriginal(media: MediaImage) {
        if (!processing) return

        if (media.height >= LARGE_FILE_HEIGHT_PX) {
            readMediaLargeColorCrop(media)
        } else {
            readMediaOriginalFull(media)
        }
    }

    private fun readMediaOriginalFull(media: MediaImage) {
        if (!processing) return

        val ageMs = (System.currentTimeMillis() - media.dateAddedMs).coerceAtLeast(0L)
        Prefs.setStatus(
            this,
            "ARQUIVO h=${media.height}: OCR completo... (${ageMs}ms desde arquivo)"
        )

        try {
            val input = InputImage.fromFilePath(this, media.uri)
            val started = SystemClock.elapsedRealtime()

            recognizer.process(input)
                .addOnSuccessListener { visionText ->
                    if (!processing) return@addOnSuccessListener

                    val parseHeight = if (media.height > 0) {
                        media.height
                    } else {
                        resources.displayMetrics.heightPixels
                    }

                    val route = parseVisionText(visionText, parseHeight)
                    val elapsed = SystemClock.elapsedRealtime() - started
                    val totalLinhas = contarLinhasVisionText(visionText)

                    if (route != null) {
                        if (isDuplicate(route)) {
                            finishFileOnlyFailure(
                                "Arquivo repetido ignorado | OCR=${elapsed}ms"
                            )
                        } else {
                            Prefs.setStatus(
                                this,
                                "ARQUIVO: ${route.neighborhood} -> ${route.cage} | " +
                                    "OCR=${elapsed}ms | enviando"
                            )
                            sendRouteInCurrentChat(route)
                        }
                    } else {
                        Prefs.setStatus(
                            this,
                            "OCR completo leu $totalLinhas linhas sem fechar a rota. " +
                                "Reforcando o mesmo arquivo..."
                        )
                        readMediaEnhanced(media)
                    }
                }
                .addOnFailureListener { error ->
                    if (!processing) return@addOnFailureListener
                    Prefs.setStatus(
                        this,
                        "OCR completo falhou (${error.message ?: "sem detalhes"}). " +
                            "Tentando leitura reforcada..."
                    )
                    readMediaEnhanced(media)
                }
        } catch (error: Throwable) {
            Prefs.setStatus(
                this,
                "Falha ao abrir arquivo original. Tentando leitura reforcada..."
            )
            readMediaEnhanced(media)
        }
    }

    private fun readMediaLargeColorCrop(media: MediaImage) {
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
            Prefs.setStatus(
                this,
                "Imagem grande: cor Agency nao fechou crop. OCR completo..."
            )
            readMediaOriginalFull(media)
            return
        }

        val crop = detected.bitmap
        try { source.recycle() } catch (_: Throwable) {}

        val started = SystemClock.elapsedRealtime()
        val input = InputImage.fromBitmap(crop, 0)

        Prefs.setStatus(
            this,
            "GRANDE: crop por cor ${(detected.widthRatio * 100).toInt()}% | " +
                "decode=${decodeMs}ms scan=${detected.scanMs}ms | OCR..."
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
                            "Arquivo repetido ignorado | OCR crop=${elapsed}ms"
                        )
                    } else {
                        Prefs.setStatus(
                            this,
                            "GRANDE: ${route.neighborhood} -> ${route.cage} | " +
                                "decode=${decodeMs}ms scan=${detected.scanMs}ms " +
                                "OCR=${elapsed}ms | enviando"
                        )
                        sendRouteInCurrentChat(route)
                    }
                } else {
                    Prefs.setStatus(
                        this,
                        "Crop por cor leu $totalLinhas linhas sem fechar rota. " +
                            "OCR completo..."
                    )
                    readMediaOriginalFull(media)
                }
            }
            .addOnFailureListener {
                try { crop.recycle() } catch (_: Throwable) {}
                if (!processing) return@addOnFailureListener
                readMediaOriginalFull(media)
            }
    }

'''

s = s[:start] + new_read + s[end:]
service_path.write_text(s, encoding="utf-8")
print("Patch v0.18 aplicado: tabelas grandes usam crop por pixels coloridos + apenas um OCR")
