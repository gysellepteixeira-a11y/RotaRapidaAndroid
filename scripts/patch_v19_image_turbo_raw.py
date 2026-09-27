from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

# IMAGE TURBO RAW
# Base esperada: DIRECT FAST (sem SIBLING FAST).
# 1) MediaStore 25 -> 10 ms.
# 2) scan de cor mais leve.
# 3) Bairro usa crop RAW, sem ampliar a tabela inteira.
# 4) Gaiola continua usando o zoom forte do readDenseCageOnly.
# 5) fallback denso recompõe o zoom antigo para preservar robustez.
# 6) remove status redundantes antes de iniciar OCR.

# -----------------------------------------------------------------------------
# 1) MEDIASTORE 25 -> 10 ms
# -----------------------------------------------------------------------------
old_media = '        private const val DIRECT_MEDIASTORE_WATCH_MS = 25L\n'
new_media = '        private const val DIRECT_MEDIASTORE_WATCH_MS = 10L\n'
if old_media not in s:
    raise SystemExit('IMAGE TURBO: DIRECT_MEDIASTORE_WATCH_MS=25L nao encontrado')
s = s.replace(old_media, new_media, 1)

# -----------------------------------------------------------------------------
# 2) SCAN DE COR MAIS LEVE
# -----------------------------------------------------------------------------
old_step = '''        // Passo 4 reduz muito o custo sem perder a faixa larga dos botoes.
        val step = 4
'''
new_step = '''        // Passo 6: menos amostras, mantendo margem ampla para a coluna Agency.
        val step = 6
'''
if old_step not in s:
    raise SystemExit('IMAGE TURBO: step=4 do detector de cor nao encontrado')
s = s.replace(old_step, new_step, 1)

# Com step 6 ha ~44% das amostras do step 4.
s = s.replace('        if (totalHits < 120) return null\n', '        if (totalHits < 60) return null\n', 1)
s = s.replace('        if (bandHits < 12 || maxColorY <= minColorY) return null\n', '        if (bandHits < 8 || maxColorY <= minColorY) return null\n', 1)

# A contagem de linhas e uma terceira varredura. Mantemos Y por pixel para nao
# juntar linhas vizinhas, mas reduzimos pela metade as amostras horizontais.
old_row = '''        val rowThreshold = maxOf(5, (rowScanX2 - rowScanX1) / 16)

        var rowCount = 0
        var insideColorRow = false
        var yy = yStart
        while (yy < yEnd) {
            var colorCount = 0
            var xx = rowScanX1
            while (xx < rowScanX2) {
                if (isAgencyColor(source.getPixel(xx, yy))) {
                    colorCount++
                }
                xx += 2
            }
'''
new_row = '''        val rowThreshold = maxOf(3, (rowScanX2 - rowScanX1) / 32)

        var rowCount = 0
        var insideColorRow = false
        var yy = yStart
        while (yy < yEnd) {
            var colorCount = 0
            var xx = rowScanX1
            while (xx < rowScanX2) {
                if (isAgencyColor(source.getPixel(xx, yy))) {
                    colorCount++
                }
                xx += 4
            }
'''
if old_row not in s:
    raise SystemExit('IMAGE TURBO: scan horizontal da contagem de linhas nao encontrado')
s = s.replace(old_row, new_row, 1)

# -----------------------------------------------------------------------------
# 3) REMOVE STATUS REDUNDANTE ANTES DO OCR DO BAIRRO
# -----------------------------------------------------------------------------
old_bairro_status = '''        val started = SystemClock.elapsedRealtime()
        Prefs.setStatus(
            this,
            "BAIRRO PRIMEIRO: $rowCount linhas | faixa ${bairroWidth}px | OCR Bairro..."
        )

        recognizer.process(InputImage.fromBitmap(bairroBitmap, 0))
'''
new_bairro_status = '''        val started = SystemClock.elapsedRealtime()

        // Comeca o OCR imediatamente; evita SharedPreferences no caminho critico.
        recognizer.process(InputImage.fromBitmap(bairroBitmap, 0))
'''
if old_bairro_status not in s:
    raise SystemExit('IMAGE TURBO: status pre-OCR Bairro nao encontrado')
s = s.replace(old_bairro_status, new_bairro_status, 1)

# -----------------------------------------------------------------------------
# 4) BAIRRO RAW: NAO AMPLIA A TABELA INTEIRA NO FAST PATH
# -----------------------------------------------------------------------------
start = s.find('    private fun readMediaLargeColorCrop(media: MediaImage) {')
end = s.find('\n    private fun readDenseCageOnly(', start)
if start < 0 or end < 0:
    raise SystemExit(f'IMAGE TURBO: readMediaLargeColorCrop nao encontrado ({start}, {end})')

# Dentro desse intervalo tambem existe readDenseFullFallback. Vamos trocar
# primeiro somente a funcao readMediaLargeColorCrop pelo bloco RAW.
large_start = s.find('    private fun readMediaLargeColorCrop(media: MediaImage) {', start, end)
if large_start < 0:
    raise SystemExit('IMAGE TURBO: inicio readMediaLargeColorCrop nao encontrado')

# A funcao e a ultima antes de readDenseCageOnly neste patch chain.
large_end = end
new_large = r'''    private fun readMediaLargeColorCrop(media: MediaImage) {
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

        // FAST PATH: mantem o crop em resolucao original para o OCR do Bairro.
        // O OCR da Gaiola ja possui zoom proprio forte dentro de readDenseCageOnly.
        val crop = detected.bitmap
        try { source.recycle() } catch (_: Throwable) {}

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

s = s[:large_start] + new_large + s[large_end:]

# -----------------------------------------------------------------------------
# 5) FALLBACK: SE RAW NAO FECHAR, REFAZ O ZOOM ANTIGO SO AQUI
# -----------------------------------------------------------------------------
fb_start = s.find('    private fun readDenseFullFallback(')
fb_end = s.find('    private fun readMediaLargeColorCrop(media: MediaImage) {', fb_start)
if fb_start < 0 or fb_end < 0:
    raise SystemExit(f'IMAGE TURBO: readDenseFullFallback nao encontrado ({fb_start}, {fb_end})')

new_fallback = r'''    private fun readDenseFullFallback(
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

        // O fast path nao amplia. Somente o fallback recupera a escala antiga,
        // preservando a robustez das tabelas mais dificeis.
        val desiredScale = (
            (rowCount * 28f) / crop.height.toFloat()
        ).coerceIn(1.15f, 1.85f)
        val biggest = maxOf(crop.width, crop.height).toFloat()
        val maxAllowed = if (biggest > 0f) 2_400f / biggest else 1f
        val scale = minOf(desiredScale, maxAllowed.coerceAtLeast(1f))

        var work = if (scale > 1.04f) {
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
        if (work !== crop) {
            try { crop.recycle() } catch (_: Throwable) {}
        }

        val started = SystemClock.elapsedRealtime()
        Prefs.setStatus(
            this,
            "DENSA FALLBACK: $rowCount linhas | $reason | x${String.format(java.util.Locale.US, "%.2f", scale)} | OCR..."
        )

        recognizer.process(InputImage.fromBitmap(work, 0))
            .addOnSuccessListener { visionText ->
                if (!processing) {
                    try { work.recycle() } catch (_: Throwable) {}
                    return@addOnSuccessListener
                }

                val ocrFinishedAt = SystemClock.elapsedRealtime()
                val parserStarted = SystemClock.elapsedRealtime()
                val route = parseVisionText(
                    visionText,
                    work.height,
                    rowCount
                )
                val parserMs = SystemClock.elapsedRealtime() - parserStarted
                val elapsed = ocrFinishedAt - started
                val totalLinhas = contarLinhasVisionText(visionText)

                if (route != null) {
                    try { work.recycle() } catch (_: Throwable) {}

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
                        denseBitmap = work,
                        rowCount = rowCount,
                        decodeMs = decodeMs,
                        scanMs = scanMs,
                        denseOcrMs = elapsed,
                        denseParseMs = parserMs
                    )
                } else {
                    try { work.recycle() } catch (_: Throwable) {}
                    Prefs.setStatus(
                        this,
                        "DENSA FALLBACK leu $totalLinhas linhas sem fechar rota. " +
                            "Tentando leitura reforcada..."
                    )
                    readMediaEnhanced(media)
                }
            }
            .addOnFailureListener { error ->
                try { work.recycle() } catch (_: Throwable) {}
                if (!processing) return@addOnFailureListener

                Prefs.setStatus(
                    this,
                    "DENSA FALLBACK OCR falhou (${error.message ?: "sem detalhes"}). " +
                        "Tentando leitura reforcada..."
                )
                readMediaEnhanced(media)
            }
    }

'''

s = s[:fb_start] + new_fallback + s[fb_end:]

# Marca inequivocamente a build no diagnostico.
prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND READY ADMIN ULTRA DIRECT FAST =====',
    '===== DIAGNOSTICO IMAGEM v0.19 DIRECT FAST IMAGE TURBO RAW SCAN6 MEDIA10 ====='
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")
print('IMAGE TURBO RAW aplicado: Bairro RAW + Gaiola zoom + scan6 + MediaStore10 + menos status critico')
