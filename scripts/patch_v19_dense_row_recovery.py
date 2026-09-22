from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - RECUPERACAO SEGURA PARA TABELAS MUITO DENSAS
# Base: OTIMIZACAO 1 (NAO usa a Otimizacao 2 de envio).
#
# Caso observado: tabela de 38 linhas, Colina de Laranjeiras visivel em J-16.
# O OCR denso reconhece o bairro mas a gaiola muito pequena pode sair quebrada.
#
# Estrategia:
# 1) parser normal continua sendo a primeira opcao, sem alteracao;
# 2) se falhar em tabela de 20+ linhas, guardamos a linha Y do bairro de maior
#    prioridade reconhecido pelo MESMO RouteParser;
# 3) fazemos UM OCR extra muito pequeno, somente na faixa da coluna Gaiola e
#    somente naquela linha. Isso evita pegar a gaiola de cima/baixo e e muito
#    mais barato do que reler a imagem inteira;
# 4) se ainda falhar, continua existindo o fallback reforcado antigo.

state_anchor = '    private var speedDiagnosticSendMethod = "nenhum"\n'
state_extra = '''    private var lastDenseRecoveryDebug = ""
    private var lastDensePriorityNeighborhood = ""
    private var lastDensePriorityIndex = -1
    private var lastDensePriorityCenterY = -1
    private var lastDensePriorityText = ""
'''
if 'private var lastDensePriorityCenterY' not in s:
    if state_anchor not in s:
        raise SystemExit('dense recovery: estado da Otimizacao 1 nao encontrado')
    s = s.replace(state_anchor, state_anchor + state_extra, 1)

old_signature = '''    private fun parseVisionText(
        visionText: Text,
        screenHeight: Int
    ): RouteResult? {
'''
new_signature = '''    private fun parseVisionText(
        visionText: Text,
        screenHeight: Int,
        expectedDenseRows: Int = 0
    ): RouteResult? {
'''
if old_signature not in s:
    raise SystemExit('dense recovery: assinatura parseVisionText nao encontrada')
s = s.replace(old_signature, new_signature, 1)

old_tail = '''        screenItems.addAll(reconstructedItems)

        return RouteParser.parseImageScreenTexts(screenItems)
    }
'''
new_tail = r'''        screenItems.addAll(reconstructedItems)

        val strictResult = RouteParser.parseImageScreenTexts(screenItems)
        if (strictResult != null) {
            lastDenseRecoveryDebug = "estrito=ok"
            return strictResult
        }

        // So prepara recovery especial quando a tabela e realmente densa.
        if (expectedDenseRows < 20) return null

        lastDensePriorityNeighborhood = ""
        lastDensePriorityIndex = -1
        lastDensePriorityCenterY = -1
        lastDensePriorityText = ""

        data class PriorityHint(
            val result: RouteResult,
            val centerY: Int,
            val top: Int,
            val text: String,
            val rawPart: Boolean
        )

        val hints = ArrayList<PriorityHint>()

        // Primeiro tenta os elementos OCR originais. Para prioridades de uma
        // palavra (Valparaiso, Colina, Eurico, Rosario...) isto fornece o Y mais
        // preciso possivel da celula Bairro.
        for (part in parts) {
            val probe = RouteParser.parsePlainTexts(
                listOf("A00 ${part.text}")
            ) ?: continue

            hints += PriorityHint(
                result = probe,
                centerY = part.centerY,
                top = part.rect.top,
                text = part.text,
                rawPart = true
            )
        }

        // Para bairros com mais de uma palavra, usa tambem a linha reconstruida.
        for (item in reconstructedItems) {
            val probe = RouteParser.parsePlainTexts(
                listOf("A00 ${item.text}")
            ) ?: continue

            hints += PriorityHint(
                result = probe,
                centerY = item.centerY,
                top = item.top,
                text = item.text,
                rawPart = false
            )
        }

        if (hints.isEmpty()) {
            lastDenseRecoveryDebug =
                "recovery=${expectedDenseRows}; prioridade OCR=nenhuma"
            return null
        }

        val bestPriority = hints.minOf { it.result.priorityIndex }
        val samePriority = hints.filter { it.result.priorityIndex == bestPriority }

        // Prefere um elemento bruto quando existir, porque seu centro Y e mais
        // fiel a celula Bairro do que uma linha reconstruida inteira.
        val chosen = samePriority
            .filter { it.rawPart }
            .minByOrNull { it.top }
            ?: samePriority.minByOrNull { it.top }
            ?: return null

        lastDensePriorityNeighborhood = chosen.result.neighborhood
        lastDensePriorityIndex = chosen.result.priorityIndex
        lastDensePriorityCenterY = chosen.centerY
        lastDensePriorityText = chosen.text

        val rowPitch = screenHeight.toFloat() / expectedDenseRows.toFloat()
        lastDenseRecoveryDebug =
            "recovery=${expectedDenseRows}; bairro=${chosen.result.neighborhood}; " +
                "y=${chosen.centerY}; pitch=${String.format(java.util.Locale.US, "%.1f", rowPitch)}; " +
                "texto=${chosen.text.take(70)}"

        return null
    }
'''
if old_tail not in s:
    raise SystemExit('dense recovery: final do parser da Otimizacao 1 nao encontrado')
s = s.replace(old_tail, new_tail, 1)

# Caminho DENSA: passa a quantidade real de linhas para o parser.
dense_start = s.find('    private fun readMediaLargeColorCrop(media: MediaImage) {')
dense_end = s.find('    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {', dense_start)
if dense_start < 0 or dense_end < 0:
    raise SystemExit('dense recovery: bloco DENSA nao encontrado')

dense_block = s[dense_start:dense_end]
old_call = '                val route = parseVisionText(visionText, crop.height)\n'
new_call = '                val route = parseVisionText(visionText, crop.height, detected.rowCount)\n'
if old_call not in dense_block:
    raise SystemExit('dense recovery: chamada parseVisionText DENSA nao encontrada')
dense_block = dense_block.replace(old_call, new_call, 1)

# O crop nao pode ser reciclado antes do OCR pequeno da Gaiola.
old_recycle_if = '''                try { crop.recycle() } catch (_: Throwable) {}

                if (route != null) {
'''
new_recycle_if = '''                if (route != null) {
                    try { crop.recycle() } catch (_: Throwable) {}
'''
if old_recycle_if not in dense_block:
    raise SystemExit('dense recovery: recycle antes do resultado nao encontrado')
dense_block = dense_block.replace(old_recycle_if, new_recycle_if, 1)

old_fail = '''                } else {
                    Prefs.setStatus(
                        this,
                        "OCR denso leu $totalLinhas linhas sem fechar rota. " +
                            "Tentando leitura reforcada do arquivo inteiro..."
                    )
                    readMediaEnhanced(media)
                }
'''
new_fail = '''                } else {
                    if (
                        detected.rowCount >= 20 &&
                        lastDensePriorityCenterY >= 0 &&
                        lastDensePriorityIndex >= 0 &&
                        lastDensePriorityNeighborhood.isNotBlank()
                    ) {
                        Prefs.setStatus(
                            this,
                            "OCR denso leu $totalLinhas linhas sem fechar rota | " +
                                "$lastDenseRecoveryDebug | OCR somente Gaiola..."
                        )
                        readDenseCageOnly(
                            media = media,
                            denseBitmap = crop,
                            rowCount = detected.rowCount,
                            decodeMs = decodeMs,
                            scanMs = detected.scanMs,
                            denseOcrMs = elapsed,
                            denseParseMs = parserMs
                        )
                    } else {
                        try { crop.recycle() } catch (_: Throwable) {}
                        Prefs.setStatus(
                            this,
                            "OCR denso leu $totalLinhas linhas sem fechar rota | " +
                                "$lastDenseRecoveryDebug | Tentando leitura reforcada do arquivo inteiro..."
                        )
                        readMediaEnhanced(media)
                    }
                }
'''
if old_fail not in dense_block:
    raise SystemExit('dense recovery: branch de falha DENSA nao encontrado')
dense_block = dense_block.replace(old_fail, new_fail, 1)

s = s[:dense_start] + dense_block + s[dense_end:]

# OCR direcionado para a celula Gaiola da MESMA linha do bairro prioritario.
helper_anchor = '    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {'
helper = r'''    private fun readDenseCageOnly(
        media: MediaImage,
        denseBitmap: Bitmap,
        rowCount: Int,
        decodeMs: Long,
        scanMs: Long,
        denseOcrMs: Long,
        denseParseMs: Long
    ) {
        if (!processing) {
            try { denseBitmap.recycle() } catch (_: Throwable) {}
            return
        }

        val centerY = lastDensePriorityCenterY
        if (centerY < 0 || centerY >= denseBitmap.height) {
            try { denseBitmap.recycle() } catch (_: Throwable) {}
            readMediaEnhanced(media)
            return
        }

        val rowPitch = denseBitmap.height.toFloat() / rowCount.coerceAtLeast(1).toFloat()

        // Uma faixa menor que uma linha inteira impede que a gaiola vizinha
        // entre no OCR. A largura pega Gaiola e um pedaco de AT/TO, mas nao Bairro.
        val halfHeight = maxOf(10, (rowPitch * 0.46f).toInt())
        val top = (centerY - halfHeight).coerceIn(0, denseBitmap.height - 1)
        val bottom = (centerY + halfHeight + 1).coerceIn(top + 1, denseBitmap.height)
        val sliceHeight = bottom - top
        val sliceWidth = maxOf(90, (denseBitmap.width * 0.20f).toInt())
            .coerceAtMost(denseBitmap.width)

        val slice = try {
            Bitmap.createBitmap(
                denseBitmap,
                0,
                top,
                sliceWidth,
                sliceHeight
            )
        } catch (_: Throwable) {
            null
        }

        try { denseBitmap.recycle() } catch (_: Throwable) {}

        if (slice == null) {
            readMediaEnhanced(media)
            return
        }

        // O recorte e minúsculo; ampliar forte custa pouco e ajuda J-16/I-10 etc.
        val wantedScale = 3.8f
        val maxByWidth = 900f / slice.width.toFloat().coerceAtLeast(1f)
        val scale = minOf(wantedScale, maxByWidth.coerceAtLeast(1f))

        var ocrSlice = if (scale > 1.05f) {
            try {
                Bitmap.createScaledBitmap(
                    slice,
                    (slice.width * scale).toInt().coerceAtLeast(1),
                    (slice.height * scale).toInt().coerceAtLeast(1),
                    true
                )
            } catch (_: Throwable) {
                slice
            }
        } else {
            slice
        }

        if (ocrSlice !== slice) {
            try { slice.recycle() } catch (_: Throwable) {}
        }

        val started = SystemClock.elapsedRealtime()
        val input = InputImage.fromBitmap(ocrSlice, 0)

        recognizer.process(input)
            .addOnSuccessListener { cageText ->
                val cageOcrMs = SystemClock.elapsedRealtime() - started

                if (!processing) {
                    try { ocrSlice.recycle() } catch (_: Throwable) {}
                    return@addOnSuccessListener
                }

                var cage: String? = RouteParser.extractCage(cageText.text)

                // Se o texto geral veio estranho, tenta cada linha/elemento.
                if (cage == null) {
                    outer@ for (block in cageText.textBlocks) {
                        for (line in block.lines) {
                            RouteParser.extractCage(line.text)?.let {
                                cage = it
                                break@outer
                            }
                            for (element in line.elements) {
                                RouteParser.extractCage(element.text)?.let {
                                    cage = it
                                    break@outer
                                }
                            }
                        }
                    }
                }

                val raw = cageText.text
                    .replace("\n", " ")
                    .replace(Regex("\\s+"), " ")
                    .trim()
                    .take(100)

                try { ocrSlice.recycle() } catch (_: Throwable) {}

                if (cage != null) {
                    val route = RouteResult(
                        neighborhood = lastDensePriorityNeighborhood,
                        cage = cage!!,
                        priorityIndex = lastDensePriorityIndex
                    )

                    if (isDuplicate(route)) {
                        finishFileOnlyFailure(
                            "Arquivo repetido ignorado | recovery gaiola=${cageOcrMs}ms"
                        )
                    } else {
                        Prefs.setStatus(
                            this,
                            "DENSA RECOVERY: ${route.neighborhood} -> ${route.cage} | " +
                                "denseOCR=${denseOcrMs}ms parse=${denseParseMs}ms " +
                                "gaiolaOCR=${cageOcrMs}ms | lido=[$raw] | enviando"
                        )
                        sendRouteInCurrentChat(route)
                    }
                } else {
                    Prefs.setStatus(
                        this,
                        "DENSA RECOVERY sem gaiola | bairro=$lastDensePriorityNeighborhood | " +
                            "y=$lastDensePriorityCenterY | gaiolaOCR=${cageOcrMs}ms | " +
                            "lido=[$raw] | reforcando arquivo inteiro..."
                    )
                    readMediaEnhanced(media)
                }
            }
            .addOnFailureListener { error ->
                try { ocrSlice.recycle() } catch (_: Throwable) {}
                if (!processing) return@addOnFailureListener

                Prefs.setStatus(
                    this,
                    "DENSA RECOVERY OCR gaiola falhou (${error.message ?: "sem detalhes"}). " +
                        "Reforcando arquivo inteiro..."
                )
                readMediaEnhanced(media)
            }
    }

'''
if helper_anchor not in s:
    raise SystemExit('dense recovery: ancora prepareEnhancedFileBitmap nao encontrada')
s = s.replace(helper_anchor, helper + helper_anchor, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 DENSE RECOVERY aplicado: bairro prioritario + OCR pequeno somente da Gaiola")
