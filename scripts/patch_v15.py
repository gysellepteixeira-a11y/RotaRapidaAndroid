from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.15 - SOMENTE ARQUIVO + ENVIO ROBUSTO
#
# 1) A imagem NUNCA e aberta no WhatsApp. O APK so le o arquivo salvo no
#    MediaStore. Se a leitura normal nao achar a rota, faz uma segunda leitura
#    reforcada do MESMO arquivo (crop das colunas uteis + ampliacao).
# 2) Depois de colar a mensagem, tenta o botao Enviar varias vezes. Se o WhatsApp
#    ainda nao expuser o no do botao, toca na mesma altura do campo de mensagem,
#    no canto direito, onde o botao Enviar fica.

# -----------------------------------------------------------------------------
# IMPORT EXTRA PARA A SEGUNDA LEITURA DO ARQUIVO
# -----------------------------------------------------------------------------
bitmap_import = 'import android.graphics.Bitmap\n'
if 'import android.graphics.BitmapFactory' not in s:
    if bitmap_import not in s:
        raise SystemExit('Patch v0.15: import Bitmap nao encontrado')
    s = s.replace(
        bitmap_import,
        bitmap_import + 'import android.graphics.BitmapFactory\n',
        1
    )

# Da um pouco mais de tempo para o WhatsApp trocar microfone -> enviar.
s = s.replace(
    '        private const val SEND_BUTTON_DELAY_MS = 18L\n',
    '        private const val SEND_BUTTON_DELAY_MS = 65L\n',
    1
)

const_anchor = '        private const val MEDIASTORE_TRIGGER_TOLERANCE_MS = 2_500L\n'
const_extra = '''        private const val SEND_RETRY_DELAY_MS = 45L\n        private const val SEND_MAX_ATTEMPTS = 7\n'''
if 'SEND_MAX_ATTEMPTS' not in s:
    if const_anchor not in s:
        raise SystemExit('Patch v0.15: constantes MediaStore nao encontradas')
    s = s.replace(const_anchor, const_anchor + const_extra, 1)

# -----------------------------------------------------------------------------
# SUBSTITUI O FLUXO MEDIASTORE DA V0.14 POR UM FLUXO 100% FILE-ONLY.
# Mantemos a mesma assinatura para nao precisar mexer no bloco candidate.
# -----------------------------------------------------------------------------
start = s.find('    private fun readImageFromMediaStoreOrFallback(\n')
end = s.find('    private fun openImageFromSavedRect(\n', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'Patch v0.15: fluxo MediaStore v0.14 nao encontrado (start={start}, end={end})'
    )

new_media_flow = r'''    private fun finishFileOnlyFailure(message: String) {
        processing = false
        Prefs.setStatus(this, message)
        handler.postDelayed({ primeCurrentScreen() }, 120L)
    }

    private fun readImageFromMediaStoreOrFallback(
        targetRect: Rect,
        fingerprint: String,
        attempt: Int
    ) {
        // targetRect/fingerprint ficam na assinatura apenas para compatibilidade
        // com a v0.14. A v0.15 NAO abre mais a miniatura em nenhuma hipotese.
        if (!processing) return

        if (!hasImageReadPermission()) {
            finishFileOnlyFailure(
                "Sem permissao para Fotos. Leitura pela tela esta desativada; " +
                    "permita TODAS as fotos no app."
            )
            return
        }

        val media = findNewestWhatsAppImage()

        if (media == null) {
            if (attempt < MEDIASTORE_MAX_ATTEMPTS) {
                if (attempt == 0) {
                    Prefs.setStatus(
                        this,
                        "Imagem detectada; aguardando o arquivo aparecer nos arquivos..."
                    )
                }

                handler.postDelayed(
                    {
                        readImageFromMediaStoreOrFallback(
                            targetRect,
                            fingerprint,
                            attempt + 1
                        )
                    },
                    MEDIASTORE_RETRY_MS
                )
            } else {
                finishFileOnlyFailure(
                    "O arquivo da imagem nao apareceu no MediaStore. " +
                        "Nao abri a foto no WhatsApp."
                )
            }
            return
        }

        lastMediaImageId = media.id
        readMediaOriginal(media)
    }

    private fun readMediaOriginal(media: MediaImage) {
        if (!processing) return

        val ageMs = (System.currentTimeMillis() - media.dateAddedMs).coerceAtLeast(0L)
        Prefs.setStatus(
            this,
            "ARQUIVO encontrado em ${ageMs}ms: ${media.displayName}. OCR original..."
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
                                    "OCR=${elapsed}ms | enviando sem abrir foto"
                            )
                            sendRouteInCurrentChat(route)
                        }
                    } else {
                        Prefs.setStatus(
                            this,
                            "OCR original leu $totalLinhas linhas sem fechar a rota. " +
                                "Reforcando o MESMO arquivo..."
                        )
                        readMediaEnhanced(media)
                    }
                }
                .addOnFailureListener { error ->
                    if (!processing) return@addOnFailureListener
                    Prefs.setStatus(
                        this,
                        "OCR original falhou (${error.message ?: "sem detalhes"}). " +
                            "Tentando leitura reforcada do arquivo..."
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

    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {
        // As colunas Gaiola + Bairro ficam na parte esquerda/central da tabela.
        // Cortamos apenas a faixa direita que nao ajuda na escolha da rota e assim
        // conseguimos ampliar o texto sem criar um bitmap gigantesco.
        val usefulWidth = (source.width * 0.82f)
            .toInt()
            .coerceIn(1, source.width)

        val cropped = Bitmap.createBitmap(
            source,
            0,
            0,
            usefulWidth,
            source.height
        )

        val wantedScale = 1.65f
        val maxDimension = 3_000f
        val biggest = maxOf(cropped.width, cropped.height).toFloat()
        val maxAllowed = if (biggest > 0f) maxDimension / biggest else 1f
        val scale = minOf(wantedScale, maxAllowed.coerceAtLeast(1f))

        if (scale <= 1.01f) {
            if (cropped !== source) source.recycle()
            return cropped
        }

        val scaled = Bitmap.createScaledBitmap(
            cropped,
            (cropped.width * scale).toInt().coerceAtLeast(1),
            (cropped.height * scale).toInt().coerceAtLeast(1),
            true
        )

        if (cropped !== source) cropped.recycle()
        source.recycle()
        return scaled
    }

    private fun readMediaEnhanced(media: MediaImage) {
        if (!processing) return

        try {
            val decoded = contentResolver.openInputStream(media.uri)?.use { stream ->
                BitmapFactory.decodeStream(stream)
            }

            if (decoded == null) {
                finishFileOnlyFailure(
                    "Nao consegui decodificar o arquivo para a segunda leitura. " +
                        "Nao abri a foto no WhatsApp."
                )
                return
            }

            val enhanced = prepareEnhancedFileBitmap(decoded)
            val input = InputImage.fromBitmap(enhanced, 0)
            val started = SystemClock.elapsedRealtime()

            recognizer.process(input)
                .addOnSuccessListener { visionText ->
                    if (!processing) {
                        try { enhanced.recycle() } catch (_: Throwable) {}
                        return@addOnSuccessListener
                    }

                    val route = parseVisionText(visionText, enhanced.height)
                    val elapsed = SystemClock.elapsedRealtime() - started
                    val totalLinhas = contarLinhasVisionText(visionText)

                    try { enhanced.recycle() } catch (_: Throwable) {}

                    if (route != null) {
                        if (isDuplicate(route)) {
                            finishFileOnlyFailure(
                                "Arquivo repetido ignorado na leitura reforcada."
                            )
                        } else {
                            Prefs.setStatus(
                                this,
                                "ARQUIVO REFORCADO: ${route.neighborhood} -> ${route.cage} | " +
                                    "OCR=${elapsed}ms | enviando sem abrir foto"
                            )
                            sendRouteInCurrentChat(route)
                        }
                    } else {
                        finishFileOnlyFailure(
                            "Leitura reforcada leu $totalLinhas linhas, mas nao achou rota. " +
                                "Nao abri a imagem no WhatsApp."
                        )
                    }
                }
                .addOnFailureListener { error ->
                    try { enhanced.recycle() } catch (_: Throwable) {}
                    if (!processing) return@addOnFailureListener
                    finishFileOnlyFailure(
                        "OCR reforcado falhou: ${error.message ?: "sem detalhes"}. " +
                            "Nao abri a imagem no WhatsApp."
                    )
                }
        } catch (error: Throwable) {
            finishFileOnlyFailure(
                "Erro na leitura reforcada do arquivo: " +
                    (error.message ?: error.javaClass.simpleName) +
                    ". Nao abri a imagem no WhatsApp."
            )
        }
    }

'''

s = s[:start] + new_media_flow + s[end:]

# -----------------------------------------------------------------------------
# DESATIVA TAMBEM O HELPER ANTIGO DE ABRIR FOTO, PARA GARANTIR QUE NENHUM CAMINHO
# LEGADO POSSA ABRIR O VISUALIZADOR ACIDENTALMENTE.
# -----------------------------------------------------------------------------
open_start = s.find('    private fun openImageFromSavedRect(\n')
open_end = s.find('    private fun waitForImageDownloadAndOpen(', open_start)
if open_start < 0 or open_end < 0:
    raise SystemExit(
        f'Patch v0.15: helper antigo de abertura nao encontrado '
        f'(start={open_start}, end={open_end})'
    )

no_open_helper = r'''    private fun openImageFromSavedRect(
        targetRect: Rect,
        fingerprint: String
    ) {
        // v0.15: visualizador de imagem desativado de proposito.
        finishFileOnlyFailure(
            "Leitura pela tela desativada. O APK so usa o arquivo original."
        )
    }

'''

s = s[:open_start] + no_open_helper + s[open_end:]

# -----------------------------------------------------------------------------
# ENVIO: TROCA A TENTATIVA UNICA POR RETENTATIVAS + TOQUE GEOMETRICO NO BOTAO.
# -----------------------------------------------------------------------------
send_block_start = s.find('        handler.postDelayed({\n            val newRoot = rootInActiveWindow\n', s.find('    private fun sendRouteInCurrentChat('))
send_block_end_marker = '        }, SEND_BUTTON_DELAY_MS)\n    }\n\n    private fun markSent('
send_block_end = s.find(send_block_end_marker, send_block_start)

if send_block_start < 0 or send_block_end < 0:
    raise SystemExit(
        f'Patch v0.15: bloco antigo de envio nao encontrado '
        f'(start={send_block_start}, end={send_block_end})'
    )

new_send_tail = '''        handler.postDelayed(\n            { tryClickSend(route, 0) },\n            SEND_BUTTON_DELAY_MS\n        )\n    }\n\n    private fun tryClickSend(route: RouteResult, attempt: Int) {\n        if (!processing) return\n\n        val root = rootInActiveWindow\n        if (root != null) {\n            val items = collectNodeItems(root)\n            val send = findSendButton(items)\n\n            if (send != null && clickNodeOrParent(send.node)) {\n                markSent(route)\n                return\n            }\n\n            if (attempt >= SEND_MAX_ATTEMPTS) {\n                val editor = findMessageEditor(items)\n                if (editor != null) {\n                    tapSendAtEditorHeight(route, editor.rect)\n                    return\n                }\n            }\n        }\n\n        if (attempt < SEND_MAX_ATTEMPTS) {\n            handler.postDelayed(\n                { tryClickSend(route, attempt + 1) },\n                SEND_RETRY_DELAY_MS\n            )\n        } else {\n            processing = false\n            Prefs.setStatus(\n                this,\n                "Mensagem preenchida, mas nao consegui acionar Enviar."\n            )\n            handler.postDelayed({ primeCurrentScreen() }, 120L)\n        }\n    }\n\n    private fun tapSendAtEditorHeight(route: RouteResult, editorRect: Rect) {\n        val w = resources.displayMetrics.widthPixels\n        val h = resources.displayMetrics.heightPixels\n\n        val x = (w * 0.93f).coerceIn(8f, (w - 8).toFloat())\n        val y = editorRect.centerY().toFloat().coerceIn(8f, (h - 8).toFloat())\n\n        val path = Path().apply { moveTo(x, y) }\n        val gesture = GestureDescription.Builder()\n            .addStroke(\n                GestureDescription.StrokeDescription(\n                    path,\n                    0L,\n                    45L\n                )\n            )\n            .build()\n\n        val accepted = dispatchGesture(\n            gesture,\n            object : GestureResultCallback() {\n                override fun onCompleted(gestureDescription: GestureDescription?) {\n                    markSent(route)\n                }\n\n                override fun onCancelled(gestureDescription: GestureDescription?) {\n                    processing = false\n                    Prefs.setStatus(\n                        this@WhatsRouteAccessibilityService,\n                        "Mensagem preenchida, mas o toque em Enviar foi cancelado."\n                    )\n                    handler.postDelayed({ primeCurrentScreen() }, 120L)\n                }\n            },\n            null\n        )\n\n        if (!accepted) {\n            processing = false\n            Prefs.setStatus(\n                this,\n                "Mensagem preenchida, mas o Android recusou o toque em Enviar."\n            )\n            handler.postDelayed({ primeCurrentScreen() }, 120L)\n        }\n    }\n\n    private fun markSent('''

s = (
    s[:send_block_start]
    + new_send_tail
    + s[send_block_end + len(send_block_end_marker):]
)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.15 aplicado: somente arquivos + OCR reforcado + envio com retentativas")
