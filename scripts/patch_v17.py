from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.17 - OTIMIZACAO CONSERVADORA
#
# Mantem a logica de texto e a prioridade da v0.16 intactas.
# 1) Envio mais rapido: reduz as esperas, mas continua confirmando que o campo
#    realmente esvaziou antes de marcar como ENVIADO.
# 2) MediaStore mais responsivo: consulta a cada 60 ms, mantendo praticamente a
#    mesma janela total de espera.
# 3) Imagem grande: tenta localizar os cabecalhos Gaiola + Bairro e OCR somente
#    nessas duas colunas. So usa o recorte quando encontra tambem o inicio da
#    proxima coluna; caso contrario cai no OCR completo da v0.16. Nunca abre foto.

# -----------------------------------------------------------------------------
# 1) CONSTANTES DE TEMPO
# -----------------------------------------------------------------------------
s = s.replace(
    '        private const val SEND_BUTTON_DELAY_MS = 65L\n',
    '        private const val SEND_BUTTON_DELAY_MS = 20L\n',
    1
)
s = s.replace(
    '        private const val SEND_RETRY_DELAY_MS = 90L\n',
    '        private const val SEND_RETRY_DELAY_MS = 35L\n',
    1
)
s = s.replace(
    '        private const val MEDIASTORE_RETRY_MS = 110L\n',
    '        private const val MEDIASTORE_RETRY_MS = 60L\n',
    1
)
s = s.replace(
    '        private const val MEDIASTORE_MAX_ATTEMPTS = 14\n',
    '        private const val MEDIASTORE_MAX_ATTEMPTS = 26\n',
    1
)

const_anchor = '        private const val MEDIASTORE_TRIGGER_TOLERANCE_MS = 2_500L\n'
if 'LARGE_FILE_HEIGHT_PX' not in s:
    if const_anchor not in s:
        raise SystemExit('Patch v0.17: constantes MediaStore nao encontradas')
    s = s.replace(
        const_anchor,
        const_anchor + '        private const val LARGE_FILE_HEIGHT_PX = 2_200\n',
        1
    )

# -----------------------------------------------------------------------------
# 2) OCR OTIMIZADO PARA IMAGEM GRANDE
# -----------------------------------------------------------------------------
start = s.find('    private fun readMediaOriginal(media: MediaImage) {')
end = s.find('    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'Patch v0.17: readMediaOriginal nao encontrado (start={start}, end={end})'
    )

new_read = r'''    private fun readMediaOriginal(media: MediaImage) {
        if (!processing) return

        if (media.height >= LARGE_FILE_HEIGHT_PX) {
            readMediaLargeColumns(media)
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

    private fun readMediaLargeColumns(media: MediaImage) {
        if (!processing) return

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

        val headerHeight = minOf(
            source.height,
            maxOf(260, minOf(1_000, (source.height * 0.28f).toInt()))
        )

        val header = try {
            Bitmap.createBitmap(
                source,
                0,
                0,
                source.width,
                headerHeight
            )
        } catch (_: Throwable) {
            try { source.recycle() } catch (_: Throwable) {}
            readMediaOriginalFull(media)
            return
        }

        val headerInput = InputImage.fromBitmap(header, 0)
        val headerStarted = SystemClock.elapsedRealtime()

        Prefs.setStatus(
            this,
            "Imagem grande h=${media.height}. Localizando colunas Gaiola + Bairro..."
        )

        recognizer.process(headerInput)
            .addOnSuccessListener { headerText ->
                if (!processing) {
                    try { header.recycle() } catch (_: Throwable) {}
                    try { source.recycle() } catch (_: Throwable) {}
                    return@addOnSuccessListener
                }

                val headerMs = SystemClock.elapsedRealtime() - headerStarted

                data class HeaderPart(val text: String, val rect: Rect)
                val parts = mutableListOf<HeaderPart>()

                for (block in headerText.textBlocks) {
                    for (line in block.lines) {
                        if (line.elements.isNotEmpty()) {
                            for (element in line.elements) {
                                val box = element.boundingBox ?: continue
                                val text = element.text.trim()
                                if (text.isNotBlank()) {
                                    parts += HeaderPart(text, Rect(box))
                                }
                            }
                        } else {
                            val box = line.boundingBox ?: continue
                            val text = line.text.trim()
                            if (text.isNotBlank()) {
                                parts += HeaderPart(text, Rect(box))
                            }
                        }
                    }
                }

                val gaiola = parts.firstOrNull {
                    RouteParser.normalize(it.text).contains("gaiola")
                }
                val bairro = parts.firstOrNull {
                    RouteParser.normalize(it.text).contains("bairro")
                }

                val nextHeader = if (bairro != null) {
                    parts
                        .filter { it.rect.left > bairro.rect.right + 8 }
                        .filter {
                            kotlin.math.abs(it.rect.centerY() - bairro.rect.centerY()) <=
                                maxOf(40, bairro.rect.height() * 2)
                        }
                        .minByOrNull { it.rect.left }
                } else {
                    null
                }

                try { header.recycle() } catch (_: Throwable) {}

                if (gaiola == null || bairro == null || nextHeader == null) {
                    try { source.recycle() } catch (_: Throwable) {}
                    Prefs.setStatus(
                        this,
                        "Cabecalho nao fechou as colunas em ${headerMs}ms. OCR completo..."
                    )
                    readMediaOriginalFull(media)
                    return@addOnSuccessListener
                }

                val marginLeft = maxOf(18, (source.width * 0.025f).toInt())
                val marginRight = maxOf(8, (source.width * 0.010f).toInt())

                val x1 = (gaiola.rect.left - marginLeft)
                    .coerceIn(0, source.width - 1)
                val x2 = (nextHeader.rect.left - marginRight)
                    .coerceIn(x1 + 1, source.width)
                val cropWidth = x2 - x1

                val ratio = cropWidth.toFloat() / source.width.toFloat()

                // Se o cabecalho produziu um recorte estranho, nao arrisca.
                if (ratio < 0.20f || ratio > 0.82f) {
                    try { source.recycle() } catch (_: Throwable) {}
                    Prefs.setStatus(
                        this,
                        "Recorte de colunas inseguro (${(ratio * 100).toInt()}%). OCR completo..."
                    )
                    readMediaOriginalFull(media)
                    return@addOnSuccessListener
                }

                val crop = try {
                    Bitmap.createBitmap(
                        source,
                        x1,
                        0,
                        cropWidth,
                        source.height
                    )
                } catch (_: Throwable) {
                    null
                }

                try { source.recycle() } catch (_: Throwable) {}

                if (crop == null) {
                    readMediaOriginalFull(media)
                    return@addOnSuccessListener
                }

                val input = InputImage.fromBitmap(crop, 0)
                val started = SystemClock.elapsedRealtime()

                Prefs.setStatus(
                    this,
                    "Colunas localizadas em ${headerMs}ms; OCR rapido em ${(ratio * 100).toInt()}% da largura..."
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
                                    "Arquivo repetido ignorado | OCR colunas=${elapsed}ms"
                                )
                            } else {
                                Prefs.setStatus(
                                    this,
                                    "COLUNAS: ${route.neighborhood} -> ${route.cage} | " +
                                        "header=${headerMs}ms OCR=${elapsed}ms | enviando"
                                )
                                sendRouteInCurrentChat(route)
                            }
                        } else {
                            Prefs.setStatus(
                                this,
                                "OCR de colunas leu $totalLinhas linhas sem fechar rota. " +
                                    "Confirmando no OCR completo..."
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
            .addOnFailureListener {
                try { header.recycle() } catch (_: Throwable) {}
                try { source.recycle() } catch (_: Throwable) {}
                if (!processing) return@addOnFailureListener
                readMediaOriginalFull(media)
            }
    }

'''

s = s[:start] + new_read + s[end:]

# -----------------------------------------------------------------------------
# 3) ENVIO MAIS RAPIDO, SEM REMOVER CONFIRMACAO
# -----------------------------------------------------------------------------
s = s.replace(
    '                140L\n            )\n            return\n',
    '                70L\n            )\n            return\n',
    1
)
s = s.replace(
    '                    55L\n',
    '                    35L\n',
    1
)
s = s.replace(
    '                        150L\n',
    '                        75L\n',
    1
)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.17 aplicado: envio rapido + polling 60ms + OCR por colunas em imagens grandes")
