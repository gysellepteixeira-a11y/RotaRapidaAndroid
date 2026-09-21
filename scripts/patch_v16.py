from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.16
# 1) PRIORIDADE REAL: nunca envia um bairro de prioridade menor se um bairro de
#    prioridade maior foi reconhecido na imagem. Ex.: se Valparaiso apareceu,
#    Praia da Baleia nao pode vencer so porque a gaiola dela ficou mais facil.
# 2) ROTAS PEQUENAS: a segunda leitura nao corta 18% da direita. Usa a imagem
#    inteira e amplia mais, porque esse corte podia remover parte do Bairro.
# 3) ENVIO: nao considera "enviado" so porque o gesto foi aceito. Depois do
#    clique/toque, confirma se o campo de mensagem esvaziou. Se nao esvaziou,
#    tenta de novo em posicoes seguras do botao Enviar.

# -----------------------------------------------------------------------------
# 1) PARSER DE IMAGEM - prioridade primeiro, gaiola depois.
# Substitui o parseVisionText injetado pela v0.12.
# -----------------------------------------------------------------------------
parse_start = s.find('    private fun parseVisionText(\n')
parse_end = s.find('\n    private fun closeImageWithoutSending(', parse_start)
if parse_start < 0 or parse_end < 0:
    raise SystemExit(
        f'Patch v0.16: parseVisionText nao encontrado '
        f'(start={parse_start}, end={parse_end})'
    )

new_parse = r'''    private fun parseVisionText(
        visionText: Text,
        screenHeight: Int
    ): RouteResult? {
        data class OcrPart(
            val text: String,
            val rect: Rect
        ) {
            val centerY: Int get() = (rect.top + rect.bottom) / 2
            val height: Int get() = (rect.bottom - rect.top).coerceAtLeast(1)
        }

        val parts = mutableListOf<OcrPart>()

        for (block in visionText.textBlocks) {
            for (line in block.lines) {
                var addedElement = false

                for (element in line.elements) {
                    val box = element.boundingBox ?: continue
                    val text = element.text.trim()
                    if (text.isBlank()) continue
                    parts += OcrPart(text, Rect(box))
                    addedElement = true
                }

                if (!addedElement) {
                    val box = line.boundingBox ?: continue
                    val text = line.text.trim()
                    if (text.isNotBlank()) {
                        parts += OcrPart(text, Rect(box))
                    }
                }
            }
        }

        if (parts.isEmpty()) return null

        val medianHeight = parts
            .map { it.height }
            .sorted()
            .let { heights -> heights[heights.size / 2] }
            .coerceAtLeast(5)

        // Mantem palavras/celulas da mesma linha juntas, sem juntar duas rotas.
        val rowTolerance = maxOf(5, (medianHeight * 0.66f).toInt())

        data class RowBucket(
            val parts: MutableList<OcrPart> = mutableListOf(),
            var centerY: Double = 0.0
        )

        val rows = mutableListOf<RowBucket>()

        for (part in parts.sortedBy { it.centerY }) {
            val nearest = rows
                .filter { kotlin.math.abs(it.centerY - part.centerY) <= rowTolerance }
                .minByOrNull { kotlin.math.abs(it.centerY - part.centerY) }

            if (nearest == null) {
                rows += RowBucket(
                    parts = mutableListOf(part),
                    centerY = part.centerY.toDouble()
                )
            } else {
                nearest.parts += part
                nearest.centerY = nearest.parts.map { it.centerY }.average()
            }
        }

        val screenItems = mutableListOf<ScreenText>()

        // Elementos originais: ajudam quando bairro e gaiola vieram fragmentados.
        for (part in parts) {
            screenItems += ScreenText(
                text = part.text,
                left = part.rect.left,
                top = part.rect.top,
                right = part.rect.right,
                bottom = part.rect.bottom
            )
        }

        // Tambem adiciona cada linha reconstruida como UM item completo.
        // O parseImageScreenTexts escolhe PRIMEIRO o bairro de menor indice de
        // prioridade entre TODOS os itens. So depois procura a gaiola da linha.
        for (row in rows) {
            val ordered = row.parts.sortedBy { it.rect.left }
            if (ordered.isEmpty()) continue

            val text = ordered
                .joinToString(" ") { it.text }
                .replace(Regex("\\s+"), " ")
                .trim()

            if (text.isBlank()) continue

            screenItems += ScreenText(
                text = text,
                left = ordered.minOf { it.rect.left },
                top = ordered.minOf { it.rect.top },
                right = ordered.maxOf { it.rect.right },
                bottom = ordered.maxOf { it.rect.bottom }
            )
        }

        // IMPORTANTE: nao usamos parsePlainTexts antes daqui. Na v0.15 ele podia
        // fechar Praia da Baleia com gaiola e retornar antes de perceber que havia
        // Valparaiso reconhecido em outra linha sem gaiola legivel.
        return RouteParser.parseImageScreenTexts(screenItems)
    }
'''

s = s[:parse_start] + new_parse + s[parse_end:]

# -----------------------------------------------------------------------------
# 2) LEITURA REFORCADA - imagem inteira, sem cortar Bairro.
# -----------------------------------------------------------------------------
prep_start = s.find('    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {')
prep_end = s.find('\n    private fun readMediaEnhanced(', prep_start)
if prep_start < 0 or prep_end < 0:
    raise SystemExit(
        f'Patch v0.16: prepareEnhancedFileBitmap nao encontrado '
        f'(start={prep_start}, end={prep_end})'
    )

new_prepare = r'''    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {
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

s = s[:prep_start] + new_prepare + s[prep_end:]

# -----------------------------------------------------------------------------
# 3) ENVIO VERIFICADO.
# Troca tryClickSend + tapSendAtEditorHeight da v0.15.
# -----------------------------------------------------------------------------
s = s.replace(
    '        private const val SEND_RETRY_DELAY_MS = 45L\n',
    '        private const val SEND_RETRY_DELAY_MS = 90L\n',
    1
)
s = s.replace(
    '        private const val SEND_MAX_ATTEMPTS = 7\n',
    '        private const val SEND_MAX_ATTEMPTS = 9\n',
    1
)

send_start = s.find('    private fun tryClickSend(route: RouteResult, attempt: Int) {')
send_end = s.find('    private fun markSent(route: RouteResult) {', send_start)
if send_start < 0 or send_end < 0:
    raise SystemExit(
        f'Patch v0.16: funcoes de envio v0.15 nao encontradas '
        f'(start={send_start}, end={send_end})'
    )

new_send = r'''    private fun currentEditorText(items: List<NodeItem>): String {
        val editor = findMessageEditor(items) ?: return ""
        return editor.node.text?.toString().orEmpty()
    }

    private fun messageStillInEditor(items: List<NodeItem>): Boolean {
        val text = currentEditorText(items)
        if (text.isBlank()) return false

        val n = RouteParser.normalize(text)
        return "felipe lima de castilho" in n ||
            "1347515" in n ||
            "gaiola" in n
    }

    private fun findStrictSendCandidate(
        items: List<NodeItem>,
        editorRect: Rect
    ): NodeItem? {
        val w = resources.displayMetrics.widthPixels
        val h = resources.displayMetrics.heightPixels
        val editorY = editorRect.centerY()
        val yTolerance = maxOf(70, (h * 0.06f).toInt())

        val named = items
            .filter { item ->
                val n = RouteParser.normalize(item.text)
                "enviar" in n || n == "send" || "send message" in n
            }
            .filter { item ->
                item.rect.right >= (w * 0.78f).toInt() &&
                    kotlin.math.abs(item.rect.centerY() - editorY) <= yTolerance
            }
            .maxByOrNull { it.rect.right }

        if (named != null) return named

        // Sem descricao: procura somente um alvo pequeno imediatamente a direita
        // do campo de mensagem, na MESMA altura. Evita clicar em emoji/anexo.
        return items
            .filter { it.clickable }
            .filter { item ->
                item.rect.left >= (w * 0.80f).toInt() &&
                    kotlin.math.abs(item.rect.centerY() - editorY) <= yTolerance &&
                    item.rect.width() in 28..220 &&
                    item.rect.height() in 28..220
            }
            .maxByOrNull { it.rect.right }
    }

    private fun tryClickSend(route: RouteResult, attempt: Int) {
        if (!processing) return

        val root = rootInActiveWindow
        if (root == null) {
            if (attempt < SEND_MAX_ATTEMPTS) {
                handler.postDelayed(
                    { tryClickSend(route, attempt + 1) },
                    SEND_RETRY_DELAY_MS
                )
            } else {
                processing = false
                Prefs.setStatus(this, "Mensagem preenchida, mas perdi a janela do WhatsApp.")
            }
            return
        }

        val items = collectNodeItems(root)

        // Se o campo ja esvaziou, a tentativa anterior realmente enviou.
        if (!messageStillInEditor(items)) {
            markSent(route)
            return
        }

        val editor = findMessageEditor(items)
        if (editor == null) {
            if (attempt < SEND_MAX_ATTEMPTS) {
                handler.postDelayed(
                    { tryClickSend(route, attempt + 1) },
                    SEND_RETRY_DELAY_MS
                )
            } else {
                processing = false
                Prefs.setStatus(this, "Mensagem preenchida, mas nao achei mais o campo de mensagem.")
            }
            return
        }

        val candidate = findStrictSendCandidate(items, editor.rect)

        // Primeiro tenta ACTION_CLICK no proprio botao/pai.
        if (candidate != null && clickNodeOrParent(candidate.node)) {
            handler.postDelayed(
                { verifySendResult(route, attempt) },
                140L
            )
            return
        }

        // Se ACTION_CLICK nao funcionar, toca no centro real do no. Se o no nao
        // existir, usa coordenadas ligeiramente diferentes a cada tentativa.
        val w = resources.displayMetrics.widthPixels
        val h = resources.displayMetrics.heightPixels

        val fallbackXs = floatArrayOf(0.935f, 0.955f, 0.915f, 0.945f)
        val x = if (candidate != null && !candidate.rect.isEmpty) {
            candidate.rect.centerX().toFloat()
        } else {
            w * fallbackXs[attempt % fallbackXs.size]
        }.coerceIn(8f, (w - 8).toFloat())

        val yOffset = when (attempt % 3) {
            1 -> -8f
            2 -> 8f
            else -> 0f
        }

        val y = (editor.rect.centerY().toFloat() + yOffset)
            .coerceIn(8f, (h - 8).toFloat())

        tapSendAndVerify(route, attempt, x, y)
    }

    private fun tapSendAndVerify(
        route: RouteResult,
        attempt: Int,
        x: Float,
        y: Float
    ) {
        val path = Path().apply { moveTo(x, y) }
        val gesture = GestureDescription.Builder()
            .addStroke(
                GestureDescription.StrokeDescription(
                    path,
                    0L,
                    55L
                )
            )
            .build()

        val accepted = dispatchGesture(
            gesture,
            object : GestureResultCallback() {
                override fun onCompleted(gestureDescription: GestureDescription?) {
                    handler.postDelayed(
                        { verifySendResult(route, attempt) },
                        150L
                    )
                }

                override fun onCancelled(gestureDescription: GestureDescription?) {
                    scheduleNextSendAttempt(route, attempt)
                }
            },
            null
        )

        if (!accepted) {
            scheduleNextSendAttempt(route, attempt)
        }
    }

    private fun verifySendResult(route: RouteResult, attempt: Int) {
        if (!processing) return

        val root = rootInActiveWindow
        if (root == null) {
            scheduleNextSendAttempt(route, attempt)
            return
        }

        val items = collectNodeItems(root)

        if (!messageStillInEditor(items)) {
            markSent(route)
        } else {
            scheduleNextSendAttempt(route, attempt)
        }
    }

    private fun scheduleNextSendAttempt(route: RouteResult, attempt: Int) {
        if (!processing) return

        if (attempt < SEND_MAX_ATTEMPTS) {
            handler.postDelayed(
                { tryClickSend(route, attempt + 1) },
                SEND_RETRY_DELAY_MS
            )
        } else {
            processing = false
            Prefs.setStatus(
                this,
                "Mensagem ficou no campo: nao consegui confirmar o clique em Enviar."
            )
            handler.postDelayed({ primeCurrentScreen() }, 150L)
        }
    }

'''

s = s[:send_start] + new_send + s[send_end:]

service_path.write_text(s, encoding="utf-8")
print("Patch v0.16 aplicado: prioridade estrita + rotas pequenas full-width + envio confirmado")
