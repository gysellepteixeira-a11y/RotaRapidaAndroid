from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - BAIRRO PRIMEIRO -> GAIOLA DEPOIS
#
# Base: DENSA BAIXA + DENSE RECOVERY FAST.
#
# A versao anterior ja fazia OCR pequeno somente da Gaiola, mas APENAS depois de
# gastar o OCR completo do crop denso e o parser falhar. Este patch antecipa o
# caminho barato:
#   1) OCR apenas de uma faixa estreita da coluna Bairro;
#   2) escolhe a prioridade global e guarda o Y exato da linha vencedora;
#   3) reutiliza readDenseCageOnly() para OCR somente da Gaiola dessa linha;
#   4) se Bairro primeiro nao fechar com seguranca, cai no OCR denso completo
#      anterior e depois no mesmo recovery/reforco de antes.
#
# Nao muda prioridade, envio, MediaStore, deteccao de linhas nem fallbacks.

start = s.find('    private fun readMediaLargeColorCrop(media: MediaImage) {')
end = s.find('\n    private fun readDenseCageOnly(', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'bairro first: bloco denso/recovery nao encontrado (start={start}, end={end})'
    )

new_block = r'''    private data class BairroFirstHit(
        val priorityIndex: Int,
        val neighborhood: String,
        val centerY: Int,
        val top: Int,
        val raw: String
    )

    private fun matchBairroFirstPriority(text: String): Pair<Int, String>? {
        val n = RouteParser.normalize(text)
        if (n.isBlank()) return null

        return when {
            "valpar" in n -> 0 to "Valparaiso"
            "colina" in n -> 1 to "Colina de Laranjeiras"
            "baleia" in n || ("praia" in n && "bale" in n) ->
                2 to "Praia da Baleia"
            "morada" in n -> 3 to "Morada de Laranjeiras"
            "euric" in n -> 4 to "Eurico"
            "plaza" in n || ("manoel" in n && "pl" in n) ->
                5 to "Manoel Plaza"
            "rosar" in n -> 6 to "Rosario"
            else -> null
        }
    }

    private fun readDenseBairroFirst(
        media: MediaImage,
        denseBitmap: Bitmap,
        rowCount: Int,
        widthRatio: Float,
        decodeMs: Long,
        scanMs: Long
    ) {
        if (!processing) {
            try { denseBitmap.recycle() } catch (_: Throwable) {}
            return
        }

        // Bairro fica imediatamente antes da coluna Agency. Como denseBitmap ja
        // termina perto de Agency, convertemos os ratios aproximados do arquivo
        // original para o sistema de coordenadas do crop. As margens sao
        // deliberadamente folgadas para tolerar pequenas variacoes de layout.
        val safeWidthRatio = widthRatio.coerceIn(0.42f, 0.90f)
        val leftRatio = (0.270f / safeWidthRatio).coerceIn(0.45f, 0.72f)
        val rightRatio = (0.505f / safeWidthRatio)
            .coerceIn(leftRatio + 0.16f, 0.985f)

        val x1 = (denseBitmap.width * leftRatio).toInt()
            .coerceIn(0, denseBitmap.width - 2)
        val x2 = (denseBitmap.width * rightRatio).toInt()
            .coerceIn(x1 + 2, denseBitmap.width)
        val bairroWidth = x2 - x1

        if (bairroWidth < 80) {
            readDenseFullFallback(
                media = media,
                crop = denseBitmap,
                rowCount = rowCount,
                widthRatio = widthRatio,
                decodeMs = decodeMs,
                scanMs = scanMs,
                reason = "faixa Bairro estreita"
            )
            return
        }

        val bairroBitmap = try {
            Bitmap.createBitmap(
                denseBitmap,
                x1,
                0,
                bairroWidth,
                denseBitmap.height
            )
        } catch (_: Throwable) {
            null
        }

        if (bairroBitmap == null) {
            readDenseFullFallback(
                media = media,
                crop = denseBitmap,
                rowCount = rowCount,
                widthRatio = widthRatio,
                decodeMs = decodeMs,
                scanMs = scanMs,
                reason = "crop Bairro falhou"
            )
            return
        }

        val started = SystemClock.elapsedRealtime()
        Prefs.setStatus(
            this,
            "BAIRRO PRIMEIRO: $rowCount linhas | faixa ${bairroWidth}px | OCR Bairro..."
        )

        recognizer.process(InputImage.fromBitmap(bairroBitmap, 0))
            .addOnSuccessListener { text ->
                val bairroOcrMs = SystemClock.elapsedRealtime() - started

                if (!processing) {
                    try { bairroBitmap.recycle() } catch (_: Throwable) {}
                    try { denseBitmap.recycle() } catch (_: Throwable) {}
                    return@addOnSuccessListener
                }

                var best: BairroFirstHit? = null

                fun consider(rawText: String, box: Rect?) {
                    if (box == null || rawText.isBlank()) return
                    val priority = matchBairroFirstPriority(rawText) ?: return
                    val hit = BairroFirstHit(
                        priorityIndex = priority.first,
                        neighborhood = priority.second,
                        centerY = (box.top + box.bottom) / 2,
                        top = box.top,
                        raw = rawText
                    )

                    val current = best
                    if (
                        current == null ||
                        hit.priorityIndex < current.priorityIndex ||
                        (hit.priorityIndex == current.priorityIndex && hit.top < current.top)
                    ) {
                        best = hit
                    }
                }

                for (block in text.textBlocks) {
                    for (line in block.lines) {
                        // Linha inteira primeiro: resolve bairros de varias palavras.
                        consider(line.text, line.boundingBox)

                        // Elementos tambem ajudam quando o ML Kit quebra uma linha
                        // densa em pedacos, especialmente Valparaiso/Colina/Eurico.
                        for (element in line.elements) {
                            consider(element.text, element.boundingBox)
                        }
                    }
                }

                val rawSample = text.text
                    .replace("\n", " | ")
                    .replace(Regex("\\s+"), " ")
                    .trim()
                    .take(140)

                try { bairroBitmap.recycle() } catch (_: Throwable) {}

                val chosen = best
                if (chosen == null) {
                    Prefs.setStatus(
                        this,
                        "BAIRRO PRIMEIRO sem prioridade em ${bairroOcrMs}ms | " +
                            "amostra=[$rawSample] | fallback OCR denso completo..."
                    )
                    readDenseFullFallback(
                        media = media,
                        crop = denseBitmap,
                        rowCount = rowCount,
                        widthRatio = widthRatio,
                        decodeMs = decodeMs,
                        scanMs = scanMs,
                        reason = "bairro nao confirmado"
                    )
                    return@addOnSuccessListener
                }

                // Y do OCR da coluna Bairro e diretamente compativel com
                // denseBitmap, porque o crop foi SOMENTE horizontal.
                lastDensePriorityNeighborhood = chosen.neighborhood
                lastDensePriorityIndex = chosen.priorityIndex
                lastDensePriorityCenterY = chosen.centerY
                lastDensePriorityText = chosen.raw
                lastDenseRecoveryDebug =
                    "bairro-first=$rowCount; bairro=${chosen.neighborhood}; " +
                        "y=${chosen.centerY}; OCR=${bairroOcrMs}ms"

                Prefs.setStatus(
                    this,
                    "BAIRRO PRIMEIRO: ${chosen.neighborhood} | " +
                        "linhaY=${chosen.centerY} | OCR=${bairroOcrMs}ms | agora Gaiola..."
                )

                // Reutiliza o recovery ja validado: ele le somente a faixa da
                // Gaiola da MESMA linha e, se falhar, usa o reforco antigo.
                readDenseCageOnly(
                    media = media,
                    denseBitmap = denseBitmap,
                    rowCount = rowCount,
                    decodeMs = decodeMs,
                    scanMs = scanMs,
                    denseOcrMs = bairroOcrMs,
                    denseParseMs = 0L
                )
            }
            .addOnFailureListener { error ->
                try { bairroBitmap.recycle() } catch (_: Throwable) {}
                if (!processing) {
                    try { denseBitmap.recycle() } catch (_: Throwable) {}
                    return@addOnFailureListener
                }

                Prefs.setStatus(
                    this,
                    "BAIRRO PRIMEIRO falhou (${error.message ?: "sem detalhes"}). " +
                        "Fallback OCR denso completo..."
                )
                readDenseFullFallback(
                    media = media,
                    crop = denseBitmap,
                    rowCount = rowCount,
                    widthRatio = widthRatio,
                    decodeMs = decodeMs,
                    scanMs = scanMs,
                    reason = "OCR bairro falhou"
                )
            }
    }

    private fun readDenseFullFallback(
        media: MediaImage,
        crop: Bitmap,
        rowCount: Int,
        widthRatio: Float,
        decodeMs: Long,
        scanMs: Long,
        reason: String
    ) {
        if (!processing) {
            try { crop.recycle() } catch (_: Throwable) {}
            return
        }

        val started = SystemClock.elapsedRealtime()
        Prefs.setStatus(
            this,
            "DENSA FALLBACK: $rowCount linhas | $reason | OCR completo do crop..."
        )

        recognizer.process(InputImage.fromBitmap(crop, 0))
            .addOnSuccessListener { visionText ->
                if (!processing) {
                    try { crop.recycle() } catch (_: Throwable) {}
                    return@addOnSuccessListener
                }

                val ocrFinishedAt = SystemClock.elapsedRealtime()
                val parserStarted = SystemClock.elapsedRealtime()
                val route = parseVisionText(
                    visionText,
                    crop.height,
                    rowCount
                )
                val parserMs = SystemClock.elapsedRealtime() - parserStarted
                val elapsed = ocrFinishedAt - started
                val totalLinhas = contarLinhasVisionText(visionText)

                if (route != null) {
                    try { crop.recycle() } catch (_: Throwable) {}

                    if (isDuplicate(route)) {
                        finishFileOnlyFailure(
                            "Arquivo repetido ignorado | OCR denso=${elapsed}ms"
                        )
                    } else {
                        Prefs.setStatus(
                            this,
                            "DENSA FALLBACK $rowCount: ${route.neighborhood} -> ${route.cage} | " +
                                "decode=${decodeMs}ms scan=${scanMs}ms " +
                                "OCR=${elapsed}ms parse=${parserMs}ms | enviando"
                        )
                        sendRouteInCurrentChat(route)
                    }
                    return@addOnSuccessListener
                }

                // Preserva o recovery anterior: se o OCR completo reconheceu o
                // bairro mas nao a Gaiola, ainda tenta somente a Gaiola.
                if (
                    rowCount >= 8 &&
                    lastDensePriorityCenterY >= 0 &&
                    lastDensePriorityIndex >= 0 &&
                    lastDensePriorityNeighborhood.isNotBlank()
                ) {
                    Prefs.setStatus(
                        this,
                        "DENSA FALLBACK leu $totalLinhas linhas | $lastDenseRecoveryDebug | " +
                            "OCR somente Gaiola..."
                    )
                    readDenseCageOnly(
                        media = media,
                        denseBitmap = crop,
                        rowCount = rowCount,
                        decodeMs = decodeMs,
                        scanMs = scanMs,
                        denseOcrMs = elapsed,
                        denseParseMs = parserMs
                    )
                } else {
                    try { crop.recycle() } catch (_: Throwable) {}
                    Prefs.setStatus(
                        this,
                        "DENSA FALLBACK leu $totalLinhas linhas sem fechar rota. " +
                            "Tentando leitura reforcada..."
                    )
                    readMediaEnhanced(media)
                }
            }
            .addOnFailureListener { error ->
                try { crop.recycle() } catch (_: Throwable) {}
                if (!processing) return@addOnFailureListener

                Prefs.setStatus(
                    this,
                    "DENSA FALLBACK OCR falhou (${error.message ?: "sem detalhes"}). " +
                        "Tentando leitura reforcada..."
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
            readMediaOriginalFull(media)
            return
        }

        if (detected.rowCount < DENSE_MIN_ROWS) {
            try { detected.bitmap.recycle() } catch (_: Throwable) {}
            try { source.recycle() } catch (_: Throwable) {}
            readMediaOriginalFull(media)
            return
        }

        var crop = detected.bitmap
        try { source.recycle() } catch (_: Throwable) {}

        // Mantem exatamente a escala adaptativa da versao anterior.
        val desiredScale = (
            (detected.rowCount * 28f) / crop.height.toFloat()
        ).coerceIn(1.15f, 1.85f)

        val biggest = maxOf(crop.width, crop.height).toFloat()
        val maxAllowed = if (biggest > 0f) 2_400f / biggest else 1f
        val scale = minOf(desiredScale, maxAllowed.coerceAtLeast(1f))

        val scaled = if (scale > 1.04f) {
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

        if (scaled !== crop) {
            try { crop.recycle() } catch (_: Throwable) {}
            crop = scaled
        }

        Prefs.setStatus(
            this,
            "DENSA $rowCount BAIRRO->GAIOLA | crop ${(detected.widthRatio * 100).toInt()}% | " +
                "x${String.format(java.util.Locale.US, "%.2f", scale)} | iniciando Bairro..."
        )

        readDenseBairroFirst(
            media = media,
            denseBitmap = crop,
            rowCount = detected.rowCount,
            widthRatio = detected.widthRatio,
            decodeMs = decodeMs,
            scanMs = detected.scanMs
        )
    }

'''

# Corrige pequeno typo de interpolacao antes de gravar.
new_block = new_block.replace('"DENSA $rowCount BAIRRO->GAIOLA', '"DENSA ${detected.rowCount} BAIRRO->GAIOLA')

s = s[:start] + new_block + s[end:]

# Marca diagnostico e versao.
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
gradle_path = Path("app/build.gradle.kts")
prefs = prefs_path.read_text(encoding="utf-8")
gradle = gradle_path.read_text(encoding="utf-8")

prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 DENSA BAIXA =====',
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST ====='
)

# Build de teste atualiza por cima da DENSA BAIXA.
gradle = gradle.replace('versionCode = 5', 'versionCode = 6')
gradle = gradle.replace(
    'versionName = "0.19-densa-baixa"',
    'versionName = "0.19-bairro-first"'
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")
gradle_path.write_text(gradle, encoding="utf-8")

print("BAIRRO FIRST aplicado: OCR coluna Bairro -> linha vencedora -> OCR somente Gaiola; fallback antigo preservado")
