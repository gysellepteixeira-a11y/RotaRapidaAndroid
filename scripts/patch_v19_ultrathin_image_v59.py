from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

anchor='''    private fun readMediaOriginal(media: MediaImage) {
        if (!processing) return

        if (media.height >= 180) {
            readMediaLargeColorCrop(media)
        } else {
            readMediaOriginalFull(media)
        }
    }

    private fun readMediaOriginalFull(media: MediaImage) {
'''
replacement=r'''    private fun readMediaOriginal(media: MediaImage) {
        if (!processing) return

        // v59: imagens extremamente baixas (ex.: 1536x12) perdem detalhes de
        // caracteres no OCR original. Este caminho e EXCLUSIVO para <100px;
        // imagens normais continuam no fluxo v58 sem qualquer zoom extra.
        if (media.height in 1..99) {
            readMediaUltraThinV59(media)
        } else if (media.height >= 180) {
            readMediaLargeColorCrop(media)
        } else {
            readMediaOriginalFull(media)
        }
    }

    private fun readMediaUltraThinV59(media: MediaImage) {
        if (!processing) return

        try {
            val source = contentResolver.openInputStream(media.uri)?.use { stream ->
                BitmapFactory.decodeStream(stream)
            }

            if (source == null) {
                readMediaOriginalFull(media)
                return
            }

            // Mantem a largura sob controle, mas amplia verticalmente muito mais.
            // Exemplo 1536x12 -> aproximadamente 3600x120.
            val maxWidth = 3600
            val targetWidth = minOf(
                maxWidth,
                maxOf(source.width, (source.width * 2.35f).toInt())
            ).coerceAtLeast(1)

            val targetHeight = maxOf(
                96,
                (source.height * 10f).toInt()
            ).coerceAtMost(260)

            val enlarged = try {
                Bitmap.createScaledBitmap(
                    source,
                    targetWidth,
                    targetHeight,
                    true
                )
            } catch (_: Throwable) {
                source
            }

            if (enlarged !== source) {
                try { source.recycle() } catch (_: Throwable) {}
            }

            val started = SystemClock.elapsedRealtime()
            recognizer.process(InputImage.fromBitmap(enlarged, 0))
                .addOnSuccessListener { visionText ->
                    if (!processing) {
                        try { enlarged.recycle() } catch (_: Throwable) {}
                        return@addOnSuccessListener
                    }

                    val parserStarted = SystemClock.elapsedRealtime()
                    val route = parseVisionText(visionText, enlarged.height)
                    val parserMs = SystemClock.elapsedRealtime() - parserStarted
                    val ocrMs = SystemClock.elapsedRealtime() - started
                    val totalLinhas = contarLinhasVisionText(visionText)

                    try { enlarged.recycle() } catch (_: Throwable) {}

                    if (route != null) {
                        if (isDuplicate(route)) {
                            finishFileOnlyFailure(
                                "Arquivo repetido ignorado | ultrafina OCR=${ocrMs}ms"
                            )
                        } else {
                            Prefs.setStatus(
                                this,
                                "ULTRAFINA v59: ${route.neighborhood} -> ${route.cage} | " +
                                    "OCR=${ocrMs}ms parse=${parserMs}ms | enviando"
                            )
                            sendRouteInCurrentChat(route)
                        }
                    } else {
                        // Fallback exatamente para o fluxo anterior da v58.
                        Prefs.setStatus(
                            this,
                            "ULTRAFINA v59 leu ${totalLinhas} linhas sem fechar rota. " +
                                "Tentando OCR original v58..."
                        )
                        readMediaOriginalFull(media)
                    }
                }
                .addOnFailureListener { error ->
                    try { enlarged.recycle() } catch (_: Throwable) {}
                    if (!processing) return@addOnFailureListener
                    Prefs.setStatus(
                        this,
                        "ULTRAFINA v59 OCR falhou (${error.message ?: "sem detalhes"}). " +
                            "Tentando OCR original v58..."
                    )
                    readMediaOriginalFull(media)
                }
        } catch (_: Throwable) {
            readMediaOriginalFull(media)
        }
    }

    private fun readMediaOriginalFull(media: MediaImage) {
'''

if anchor not in s:
    raise SystemExit("v59 readMediaOriginal anchor missing")

s=s.replace(anchor,replacement,1)

for m in [
    'if (media.height in 1..99)',
    'private fun readMediaUltraThinV59(media: MediaImage)',
    'val targetWidth = minOf(',
    'val targetHeight = maxOf(',
    'Bitmap.createScaledBitmap(',
    'parseVisionText(visionText, enlarged.height)',
    'readMediaOriginalFull(media)',
    'ULTRAFINA v59',
]:
    if m not in s:
        raise SystemExit("v59 verify failed: "+m)

S.write_text(s,encoding="utf-8")
print("v59 aplicado: somente imagens <100px usam OCR ultrafino; demais caminhos v58 preservados")
