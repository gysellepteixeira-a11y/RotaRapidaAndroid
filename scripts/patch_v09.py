from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.9: substitui a espera baseada apenas no retangulo por estabilidade REAL dos pixels.
start = s.find('    private fun waitForImageDownloadAndOpen(')
end = s.find('    private fun hasMediaDownloadIndicator(', start)
if start < 0 or end < 0:
    raise SystemExit('Patch v0.9: helper de download v0.8 nao encontrado')

new_wait = r'''    private fun waitForImageDownloadAndOpen(
        targetRect: Rect,
        startedAt: Long,
        stableChecks: Int,
        previousPixels: IntArray? = null
    ) {
        if (!processing) return

        val now = SystemClock.elapsedRealtime()
        val elapsed = now - startedAt

        val root = rootInActiveWindow
        if (root == null) {
            if (elapsed < IMAGE_DOWNLOAD_TIMEOUT_MS) {
                handler.postDelayed(
                    {
                        waitForImageDownloadAndOpen(
                            targetRect,
                            startedAt,
                            0,
                            previousPixels
                        )
                    },
                    IMAGE_DOWNLOAD_POLL_MS
                )
            } else {
                processing = false
                previousImageFingerprints = emptySet()
                Prefs.setStatus(this, "Nao consegui acompanhar o download da imagem.")
            }
            return
        }

        val items = collectNodeItems(root)
        val group = Prefs.groupName(this)

        if (group.isNotBlank() && !isTargetGroup(items, group)) {
            processing = false
            Prefs.setStatus(this, "Saiu do grupo antes de abrir a imagem.")
            return
        }

        val candidates = findImageCandidates(items)
        val candidate = candidates.minByOrNull { item ->
            abs(item.rect.centerX() - targetRect.centerX()) +
                abs(item.rect.centerY() - targetRect.centerY()) +
                abs(item.rect.width() - targetRect.width()) / 2 +
                abs(item.rect.height() - targetRect.height()) / 2
        }

        if (candidate == null) {
            if (elapsed < IMAGE_DOWNLOAD_TIMEOUT_MS) {
                handler.postDelayed(
                    {
                        waitForImageDownloadAndOpen(
                            targetRect,
                            startedAt,
                            0,
                            previousPixels
                        )
                    },
                    IMAGE_DOWNLOAD_POLL_MS
                )
            } else {
                processing = false
                previousImageFingerprints = emptySet()
                Prefs.setStatus(this, "A miniatura sumiu antes de terminar o download.")
            }
            return
        }

        val pending = hasMediaDownloadIndicator(items, candidate.rect)

        if (pending || elapsed < 220L) {
            if (pending) {
                Prefs.setStatus(this, "Imagem ainda baixando...")
            }

            handler.postDelayed(
                {
                    waitForImageDownloadAndOpen(
                        Rect(candidate.rect),
                        startedAt,
                        0,
                        previousPixels
                    )
                },
                IMAGE_DOWNLOAD_POLL_MS
            )
            return
        }

        // A partir daqui verificamos o CONTEUDO VISUAL da miniatura.
        // Ela precisa ficar praticamente igual em 3 capturas consecutivas.
        try {
            takeScreenshot(
                Display.DEFAULT_DISPLAY,
                mainExecutor,
                object : TakeScreenshotCallback {
                    override fun onSuccess(screenshot: ScreenshotResult) {
                        if (!processing) {
                            try { screenshot.hardwareBuffer.close() } catch (_: Throwable) {}
                            return
                        }

                        try {
                            val buffer = screenshot.hardwareBuffer
                            val wrapped = Bitmap.wrapHardwareBuffer(buffer, screenshot.colorSpace)
                            val bitmap = wrapped?.copy(Bitmap.Config.ARGB_8888, false)
                            buffer.close()

                            if (bitmap == null) {
                                scheduleImageDownloadPixelRetry(
                                    candidate.rect,
                                    startedAt,
                                    0,
                                    previousPixels
                                )
                                return
                            }

                            val currentPixels = sampleImagePixels(bitmap, candidate.rect)
                            bitmap.recycle()

                            val difference = pixelSampleDifference(previousPixels, currentPixels)
                            val nextStable =
                                if (previousPixels != null && difference <= 2.4) stableChecks + 1
                                else 0

                            val elapsedNow = SystemClock.elapsedRealtime() - startedAt
                            val ready =
                                elapsedNow >= IMAGE_MIN_DOWNLOAD_WAIT_MS &&
                                nextStable >= 3

                            if (ready) {
                                lastOpenedImageFingerprint = imageFingerprint(candidate)
                                lastOpenedImageAt = SystemClock.elapsedRealtime()

                                Prefs.setStatus(
                                    this@WhatsRouteAccessibilityService,
                                    "Imagem terminou de carregar. Abrindo..."
                                )

                                if (clickImageCandidateSafely(candidate)) {
                                    handler.postDelayed(
                                        { verifyImageViewerAndRead(attempt = 0) },
                                        IMAGE_OPEN_DELAY_MS
                                    )
                                } else {
                                    processing = false
                                    Prefs.setStatus(
                                        this@WhatsRouteAccessibilityService,
                                        "Imagem carregou, mas nao consegui abrir."
                                    )
                                }
                                return
                            }

                            if (elapsedNow >= IMAGE_DOWNLOAD_TIMEOUT_MS) {
                                processing = false
                                previousImageFingerprints = emptySet()
                                Prefs.setStatus(
                                    this@WhatsRouteAccessibilityService,
                                    "A imagem nao terminou de estabilizar; nao abri incompleta."
                                )
                                return
                            }

                            Prefs.setStatus(
                                this@WhatsRouteAccessibilityService,
                                "Aguardando imagem estabilizar..."
                            )

                            scheduleImageDownloadPixelRetry(
                                candidate.rect,
                                startedAt,
                                nextStable,
                                currentPixels
                            )
                        } catch (_: Throwable) {
                            scheduleImageDownloadPixelRetry(
                                candidate.rect,
                                startedAt,
                                0,
                                previousPixels
                            )
                        }
                    }

                    override fun onFailure(errorCode: Int) {
                        scheduleImageDownloadPixelRetry(
                            candidate.rect,
                            startedAt,
                            0,
                            previousPixels
                        )
                    }
                }
            )
        } catch (_: Throwable) {
            scheduleImageDownloadPixelRetry(
                candidate.rect,
                startedAt,
                0,
                previousPixels
            )
        }
    }

    private fun scheduleImageDownloadPixelRetry(
        rect: Rect,
        startedAt: Long,
        stableChecks: Int,
        pixels: IntArray?
    ) {
        if (!processing) return

        if (SystemClock.elapsedRealtime() - startedAt >= IMAGE_DOWNLOAD_TIMEOUT_MS) {
            processing = false
            previousImageFingerprints = emptySet()
            Prefs.setStatus(this, "Tempo esgotado esperando o download da imagem.")
            return
        }

        handler.postDelayed(
            {
                waitForImageDownloadAndOpen(
                    Rect(rect),
                    startedAt,
                    stableChecks,
                    pixels
                )
            },
            IMAGE_DOWNLOAD_POLL_MS
        )
    }

    private fun sampleImagePixels(bitmap: Bitmap, rect: Rect): IntArray {
        val left = rect.left.coerceIn(0, bitmap.width - 1)
        val top = rect.top.coerceIn(0, bitmap.height - 1)
        val right = rect.right.coerceIn(left + 1, bitmap.width)
        val bottom = rect.bottom.coerceIn(top + 1, bitmap.height)

        val cols = 9
        val rows = 9
        val result = IntArray(cols * rows)
        var index = 0

        for (row in 0 until rows) {
            val y = top + (((row + 0.5) / rows) * (bottom - top)).toInt()
                .coerceIn(0, bitmap.height - 1)

            for (col in 0 until cols) {
                val x = left + (((col + 0.5) / cols) * (right - left)).toInt()
                    .coerceIn(0, bitmap.width - 1)
                result[index++] = bitmap.getPixel(x, y)
            }
        }

        return result
    }

    private fun pixelSampleDifference(a: IntArray?, b: IntArray): Double {
        if (a == null || a.size != b.size) return Double.MAX_VALUE

        var total = 0L
        for (i in b.indices) {
            val ca = a[i]
            val cb = b[i]

            total += abs(((ca shr 16) and 0xFF) - ((cb shr 16) and 0xFF))
            total += abs(((ca shr 8) and 0xFF) - ((cb shr 8) and 0xFF))
            total += abs((ca and 0xFF) - (cb and 0xFF))
        }

        return total.toDouble() / (b.size * 3.0)
    }

'''

s = s[:start] + new_wait + s[end:]
service_path.write_text(s, encoding="utf-8")

# Corrige definitivamente o falso "i18/i15" vindo de colunas numericas como SPR 118/115.
# O OCR pode confundir o primeiro 1 com I; agora 1 so vira I se houver separador explicito: 1-18, 1 18 etc.
parser_path = Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
r = parser_path.read_text(encoding="utf-8")

old_regex = '''    private val cageRegex =
        Regex("""(?<![A-Z0-9])([A-I1])[-.\\s]?(\\d{2})(?![A-Z0-9])""")
'''
new_regex = '''    private val cageRegex =
        Regex("""(?<![A-Z0-9])([A-I])[-.\\s]?(\\d{2})(?![A-Z0-9])""")

    private val cageIFallbackRegex =
        Regex("""(?<![A-Z0-9])1[-.\\s](\\d{2})(?![A-Z0-9])""")
'''
if old_regex not in r:
    raise SystemExit('Patch v0.9: regex v0.8 nao encontrado')
r = r.replace(old_regex, new_regex, 1)

old_extract = '''        val match = cageRegex.find(upper) ?: return null

        var letter = match.groupValues[1]
        if (letter == "1") letter = "I"

        return letter.lowercase(Locale.ROOT) + match.groupValues[2]
'''
new_extract = '''        val match = cageRegex.find(upper)
        if (match != null) {
            return match.groupValues[1].lowercase(Locale.ROOT) + match.groupValues[2]
        }

        val iFallback = cageIFallbackRegex.find(upper) ?: return null
        return "i" + iFallback.groupValues[1]
'''
if old_extract not in r:
    raise SystemExit('Patch v0.9: extractCage v0.8 nao encontrado')
r = r.replace(old_extract, new_extract, 1)

parser_path.write_text(r, encoding="utf-8")

print("Patch v0.9 aplicado: estabilidade real por pixels + SPR 115/118 nao vira mais i15/i18")
