from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

start=s.find('    private fun readMediaUltraThinV59(media: MediaImage) {')
end=s.find('\n    private fun readMediaOriginalFull(media: MediaImage) {', start)
if start<0 or end<0:
    raise SystemExit("v60 ultrathin function bounds missing")

new_fun=r'''    private fun readMediaUltraThinV59(media: MediaImage) {
        if (!processing) return

        val source = try {
            contentResolver.openInputStream(media.uri)?.use { stream ->
                BitmapFactory.decodeStream(stream)
            }
        } catch (_: Throwable) {
            null
        }

        if (source == null) {
            readMediaEnhanced(media)
            return
        }

        val tileWidth = minOf(
            source.width,
            maxOf(420, (source.width * 0.42f).toInt())
        ).coerceAtLeast(1)
        val overlap = maxOf(40, (tileWidth * 0.22f).toInt())
        val stride = maxOf(1, tileWidth - overlap)

        val starts = ArrayList<Int>()
        var cursor = 0
        while (true) {
            val x = if (cursor + tileWidth >= source.width) {
                maxOf(0, source.width - tileWidth)
            } else {
                cursor
            }

            if (starts.lastOrNull() != x) starts += x
            if (x + tileWidth >= source.width) break
            cursor = x + stride

            if (starts.size >= 6) break
        }

        val screenItems = ArrayList<ScreenText>()
        val rawTexts = ArrayList<String>()
        val startedAll = SystemClock.elapsedRealtime()

        fun finishUltraThin() {
            if (!processing) {
                try { source.recycle() } catch (_: Throwable) {}
                return
            }

            val routeFromGeometry = RouteParser.parseImageScreenTexts(screenItems)

            val oneRowRoute = if (
                routeFromGeometry == null &&
                source.height <= 40 &&
                rawTexts.isNotEmpty()
            ) {
                RouteParser.parsePlainTexts(
                    listOf(rawTexts.joinToString(" "))
                )
            } else {
                null
            }

            val route = routeFromGeometry ?: oneRowRoute
            val elapsed = SystemClock.elapsedRealtime() - startedAll
            val textCount = rawTexts.size

            try { source.recycle() } catch (_: Throwable) {}

            if (route != null) {
                if (isDuplicate(route)) {
                    finishFileOnlyFailure(
                        "Arquivo repetido ignorado | ultrafina v60=${elapsed}ms"
                    )
                } else {
                    Prefs.setStatus(
                        this,
                        "ULTRAFINA v60: ${route.neighborhood} -> ${route.cage} | " +
                            "tiles=${starts.size} textos=$textCount OCR=${elapsed}ms | enviando"
                    )
                    sendRouteInCurrentChat(route)
                }
            } else {
                Prefs.setStatus(
                    this,
                    "ULTRAFINA v60 leu $textCount trechos em ${starts.size} faixas " +
                        "sem fechar rota. Tentando leitura reforcada segura..."
                )
                readMediaEnhanced(media)
            }
        }

        fun processTile(index: Int) {
            if (!processing) {
                try { source.recycle() } catch (_: Throwable) {}
                return
            }

            if (index >= starts.size) {
                finishUltraThin()
                return
            }

            val x = starts[index]
            val width = minOf(tileWidth, source.width - x).coerceAtLeast(1)

            val tile = try {
                Bitmap.createBitmap(source, x, 0, width, source.height)
            } catch (_: Throwable) {
                null
            }

            if (tile == null) {
                processTile(index + 1)
                return
            }

            val desiredScale = maxOf(
                1f,
                56f / tile.height.toFloat().coerceAtLeast(1f)
            )
            val maxByWidth = 3000f / tile.width.toFloat().coerceAtLeast(1f)
            val scale = minOf(desiredScale, maxByWidth.coerceAtLeast(1f))

            val targetWidth = maxOf(
                32,
                (tile.width * scale).toInt()
            ).coerceAtMost(3000)
            val targetHeight = maxOf(
                32,
                (tile.height * scale).toInt()
            ).coerceAtMost(240)

            val work = try {
                Bitmap.createScaledBitmap(
                    tile,
                    targetWidth,
                    targetHeight,
                    true
                )
            } catch (_: Throwable) {
                tile
            }

            if (work !== tile) {
                try { tile.recycle() } catch (_: Throwable) {}
            }

            val scaleX = work.width.toFloat() / width.toFloat().coerceAtLeast(1f)
            val scaleY = work.height.toFloat() / source.height.toFloat().coerceAtLeast(1f)

            recognizer.process(InputImage.fromBitmap(work, 0))
                .addOnSuccessListener { visionText ->
                    if (!processing) {
                        try { work.recycle() } catch (_: Throwable) {}
                        try { source.recycle() } catch (_: Throwable) {}
                        return@addOnSuccessListener
                    }

                    for (block in visionText.textBlocks) {
                        for (line in block.lines) {
                            if (line.text.isNotBlank()) rawTexts += line.text

                            val box = line.boundingBox
                            if (box != null) {
                                screenItems += ScreenText(
                                    text = line.text,
                                    left = x + (box.left / scaleX).toInt(),
                                    top = (box.top / scaleY).toInt(),
                                    right = x + (box.right / scaleX).toInt(),
                                    bottom = (box.bottom / scaleY).toInt()
                                )
                            }

                            for (element in line.elements) {
                                if (element.text.isNotBlank()) rawTexts += element.text

                                val eb = element.boundingBox ?: continue
                                screenItems += ScreenText(
                                    text = element.text,
                                    left = x + (eb.left / scaleX).toInt(),
                                    top = (eb.top / scaleY).toInt(),
                                    right = x + (eb.right / scaleX).toInt(),
                                    bottom = (eb.bottom / scaleY).toInt()
                                )
                            }
                        }
                    }

                    try { work.recycle() } catch (_: Throwable) {}
                    processTile(index + 1)
                }
                .addOnFailureListener {
                    try { work.recycle() } catch (_: Throwable) {}
                    if (!processing) {
                        try { source.recycle() } catch (_: Throwable) {}
                        return@addOnFailureListener
                    }
                    processTile(index + 1)
                }
        }

        processTile(0)
    }
'''

s=s[:start]+new_fun+s[end:]

old_enhanced=r'''    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {
        // v0.16: NAO corta mais a direita. Em algumas tabelas pequenas a coluna
        // Bairro chega perto de 85% da largura e o crop de 82% da v0.15 podia
        // cortar Valparaiso/Colina no meio.
        val wantedScale = 1.85f
        val maxDimension = 3_600f
        val biggest = maxOf(source.width, source.height).toFloat()
        val maxAllowed = if (biggest > 0f) maxDimension / biggest else 1f
        val scale = minOf(wantedScale, maxAllowed.coerceAtLeast(1f))

        if (scale <= 1.01f) {
            return source
        }

        val scaled = Bitmap.createScaledBitmap(
            source,
            (source.width * scale).toInt().coerceAtLeast(1),
            (source.height * scale).toInt().coerceAtLeast(1),
            true
        )

        if (scaled !== source) {
            source.recycle()
        }

        return scaled
    }
'''

new_enhanced=r'''    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {
        // v60: preserva o comportamento antigo para imagens normais, mas garante
        // o minimo 32x32 exigido pelo ML Kit em arquivos ultrafinos.
        val wantedScale = 1.85f
        val maxDimension = 3_600f
        val biggest = maxOf(source.width, source.height).toFloat()
        val maxAllowed = if (biggest > 0f) maxDimension / biggest else 1f
        val scale = minOf(wantedScale, maxAllowed.coerceAtLeast(1f))

        val targetWidth = maxOf(
            32,
            (source.width * scale).toInt().coerceAtLeast(1)
        ).coerceAtMost(3600)

        val targetHeight = maxOf(
            32,
            (source.height * scale).toInt().coerceAtLeast(1)
        )

        if (
            targetWidth == source.width &&
            targetHeight == source.height
        ) {
            return source
        }

        val scaled = Bitmap.createScaledBitmap(
            source,
            targetWidth,
            targetHeight,
            true
        )

        if (scaled !== source) {
            source.recycle()
        }

        return scaled
    }
'''

if old_enhanced not in s:
    raise SystemExit("v60 prepareEnhancedFileBitmap block missing")
s=s.replace(old_enhanced,new_enhanced,1)

for m in [
    'ULTRAFINA v60',
    'val tileWidth = minOf(',
    'val overlap = maxOf(',
    'RouteParser.parseImageScreenTexts(screenItems)',
    'source.height <= 40',
    'rawTexts.joinToString(" ")',
    'targetHeight = maxOf(',
    'readMediaEnhanced(media)',
]:
    if m not in s:
        raise SystemExit("v60 verify failed: "+m)

S.write_text(s,encoding="utf-8")
print("v60 aplicado: ultrafina em tiles + coordenadas reconstruidas + fallback ML Kit minimo 32px")
