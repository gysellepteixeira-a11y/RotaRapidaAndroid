package com.gy.rotarapida

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.accessibilityservice.AccessibilityService.TakeScreenshotCallback
import android.accessibilityservice.AccessibilityService.ScreenshotResult
import android.graphics.Bitmap
import android.graphics.Path
import android.graphics.Rect
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.Display
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.Text
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import kotlin.math.abs

class WhatsRouteAccessibilityService : AccessibilityService() {

    companion object {
        private const val WHATSAPP = "com.whatsapp"
        private const val WHATSAPP_BUSINESS = "com.whatsapp.w4b"

        // Começamos conservador. Depois do primeiro teste no Poco F4
        // podemos reduzir esse valor.
        private const val IMAGE_OPEN_DELAY_MS = 140L

        private const val IMAGE_RETRY_DELAY_MS = 180L
        private const val SEND_BUTTON_DELAY_MS = 18L
        private const val DEDUP_MS = 8_000L
    }

    private data class NodeItem(
        val text: String,
        val rect: Rect,
        val className: String,
        val clickable: Boolean,
        val editable: Boolean,
        val node: AccessibilityNodeInfo
    )

    private val handler = Handler(Looper.getMainLooper())
    private val recognizer by lazy {
        TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
    }

    private var analyzeScheduled = false
    private var processing = false
    private var primed = false

    private var previousTexts: Set<String> = emptySet()
    private var previousImageFingerprints: Set<String> = emptySet()
    private var imageHintUntil = 0L

    private var lastSentSignature = ""
    private var lastSentAt = 0L
    private var currentStartedAt = 0L

    override fun onServiceConnected() {
        super.onServiceConnected()
        Prefs.setStatus(this, "Serviço de acessibilidade conectado.")
        handler.postDelayed({ primeCurrentScreen() }, 350)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        if (!Prefs.isEnabled(this)) return

        val pkg = event.packageName?.toString().orEmpty()
        if (pkg != WHATSAPP && pkg != WHATSAPP_BUSINESS) return

        inspectImageHint(event)

        if (processing) return
        scheduleAnalyze(12L)
    }

    override fun onInterrupt() {
        Prefs.setStatus(this, "Serviço de acessibilidade interrompido.")
    }

    override fun onDestroy() {
        recognizer.close()
        super.onDestroy()
    }

    private fun scheduleAnalyze(delayMs: Long) {
        if (analyzeScheduled) return
        analyzeScheduled = true

        handler.postDelayed({
            analyzeScheduled = false
            analyzeCurrentWindow()
        }, delayMs)
    }

    private fun primeCurrentScreen() {
        val root = rootInActiveWindow ?: return
        val items = collectNodeItems(root)

        previousTexts = textSignatures(items)
        previousImageFingerprints = findImageCandidates(items)
            .map(::imageFingerprint)
            .toSet()
        primed = true
    }

    private fun analyzeCurrentWindow() {
        if (processing || !Prefs.isEnabled(this)) return

        val group = Prefs.groupName(this)
        if (group.isBlank()) {
            Prefs.setStatus(this, "Configure o nome exato do grupo no app.")
            return
        }

        val root = rootInActiveWindow ?: return
        val items = collectNodeItems(root)

        if (!isTargetGroup(items, group)) {
            previousTexts = textSignatures(items)
            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
            primed = true
            return
        }

        val currentSignatures = textSignatures(items)
        val currentImageCandidates = findImageCandidates(items)
        val currentImageFingerprints = currentImageCandidates
            .map(::imageFingerprint)
            .toSet()

        if (!primed) {
            previousTexts = currentSignatures
            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
            primed = true
            Prefs.setStatus(this, "Grupo confirmado. Aguardando uma nova rota.")
            return
        }

        val newItems = items.filter { item ->
            val signature = RouteParser.normalize(item.text)
            signature.isNotBlank() && signature !in previousTexts
        }

        previousTexts = currentSignatures

        // ---------------- TEXTO ----------------
        val screenHeight = resources.displayMetrics.heightPixels

        val textRoute =
            RouteParser.parseScreenTexts(
                newItems.map {
                    ScreenText(
                        text = it.text,
                        left = it.rect.left,
                        top = it.rect.top,
                        right = it.rect.right,
                        bottom = it.rect.bottom
                    )
                },
                screenHeight
            )
                ?: RouteParser.parsePlainTexts(newItems.map { it.text })

        if (textRoute != null && !isDuplicate(textRoute)) {
            previousImageFingerprints = currentImageFingerprints
            currentStartedAt = SystemClock.elapsedRealtime()
            processing = true
            Prefs.setStatus(
                this,
                "Texto: ${textRoute.neighborhood} -> ${textRoute.cage}. Enviando..."
            )
            sendRouteInCurrentChat(textRoute)
            return
        }

        // ---------------- IMAGEM ----------------
        //
        // v0.2:
        // No M52 o WhatsApp não expôs a miniatura com o texto "foto/imagem".
        // Por isso não dependemos mais do imageHintUntil.
        //
        // Agora detectamos também um NOVO bloco visual grande, sem texto,
        // dentro da região da conversa. Isso cobre miniaturas expostas como
        // android.view.View / FrameLayout, algo comum no WhatsApp/Samsung.
        val newImageCandidates = currentImageCandidates.filter { candidate ->
            imageFingerprint(candidate) !in previousImageFingerprints
        }

        val candidate = newImageCandidates.maxWithOrNull(
            compareBy<NodeItem>(
                { imageCandidateScore(it) },
                { it.rect.bottom }
            )
        )

        // Atualiza a referência ANTES de qualquer clique.
        previousImageFingerprints = currentImageFingerprints

        if (candidate != null) {
            currentStartedAt = SystemClock.elapsedRealtime()
            processing = true

            val hintAtivo = SystemClock.elapsedRealtime() <= imageHintUntil
            Prefs.setStatus(
                this,
                "Imagem candidata x=${candidate.rect.left}, y=${candidate.rect.top}, " +
                    "w=${candidate.rect.width()}, h=${candidate.rect.height()}. Tocando..."
            )

            if (clickImageCandidateSafely(candidate)) {
                handler.postDelayed(
                    { verifyImageViewerAndRead(attempt = 0) },
                    IMAGE_OPEN_DELAY_MS
                )
            } else {
                processing = false
                Prefs.setStatus(
                    this,
                    "Imagem candidata detectada, mas não achei um alvo de clique seguro."
                )
                handler.postDelayed({ primeCurrentScreen() }, 100L)
            }
            return
        }
    }

    private fun inspectImageHint(event: AccessibilityEvent) {
        val merged = buildString {
            event.text?.forEach {
                append(it?.toString().orEmpty())
                append(' ')
            }
            append(event.contentDescription?.toString().orEmpty())
            append(' ')
            append(event.source?.contentDescription?.toString().orEmpty())
        }

        val n = RouteParser.normalize(merged)
        val textHint =
            "foto" in n ||
            "imagem" in n ||
            "photo" in n ||
            "image" in n

        var largeImageSource = false

        event.source?.let { source ->
            val rect = Rect()
            source.getBoundsInScreen(rect)

            val w = resources.displayMetrics.widthPixels
            val h = resources.displayMetrics.heightPixels
            val className = source.className?.toString().orEmpty()

            largeImageSource =
                className.contains("Image", ignoreCase = true) &&
                rect.width() >= (w * 0.18).toInt() &&
                rect.height() >= (h * 0.06).toInt() &&
                rect.top >= (h * 0.12).toInt()
        }

        if (textHint || largeImageSource) {
            imageHintUntil = SystemClock.elapsedRealtime() + 900L
        }
    }

    private fun verifyImageViewerAndRead(attempt: Int) {
        if (!processing) return

        val root = rootInActiveWindow
        if (root == null) {
            processing = false
            Prefs.setStatus(this, "Não consegui confirmar se a imagem abriu.")
            return
        }

        val items = collectNodeItems(root)

        // No grupo normal existe o campo de mensagem.
        // No visualizador de imagem do WhatsApp esse campo desaparece.
        val editorStillVisible = findMessageEditor(items) != null

        if (editorStillVisible) {
            // MUITO IMPORTANTE:
            // não usa GLOBAL_ACTION_BACK aqui.
            // Se o clique não abriu a imagem, voltar tiraria a pessoa do grupo.
            processing = false
            Prefs.setStatus(
                this,
                "Imagem detectada, mas o toque não abriu o visualizador. Não voltei do grupo."
            )
            handler.postDelayed({ primeCurrentScreen() }, 120L)
            return
        }

        Prefs.setStatus(this, "Imagem aberta. Preparando OCR...")
        handler.postDelayed(
            { captureAndReadImage(attempt) },
            70L
        )
    }


    private fun captureAndReadImage(attempt: Int) {
        if (!processing) return

        takeScreenshot(
            Display.DEFAULT_DISPLAY,
            mainExecutor,
            object : TakeScreenshotCallback {
                override fun onSuccess(screenshot: ScreenshotResult) {
                    val hardwareBuffer = screenshot.hardwareBuffer

                    val wrapped = Bitmap.wrapHardwareBuffer(
                        hardwareBuffer,
                        screenshot.colorSpace
                    )

                    val bitmap = wrapped?.copy(Bitmap.Config.ARGB_8888, false)
                    hardwareBuffer.close()

                    if (bitmap == null) {
                        imageFailed("Não consegui converter a captura da imagem.")
                        return
                    }

                    val ocrBitmap = prepararBitmapImagemParaOcr(
                        bitmap = bitmap,
                        attempt = attempt
                    )

                    val input = InputImage.fromBitmap(ocrBitmap, 0)

                    recognizer.process(input)
                        .addOnSuccessListener { visionText ->
                            val route = parseVisionText(
                                visionText,
                                ocrBitmap.height
                            )

                            val totalLinhas = contarLinhasVisionText(visionText)
                            val amostra = resumirVisionText(visionText)

                            if (ocrBitmap !== bitmap) {
                                ocrBitmap.recycle()
                            }
                            bitmap.recycle()

                            if (route != null) {
                                if (isDuplicate(route)) {
                                    closeImageWithoutSending("Imagem repetida ignorada.")
                                } else {
                                    Prefs.setStatus(
                                        this@WhatsRouteAccessibilityService,
                                        "Imagem: ${route.neighborhood} -> ${route.cage}. Voltando ao grupo..."
                                    )

                                    performGlobalAction(GLOBAL_ACTION_BACK)
                                    handler.postDelayed(
                                        { sendRouteWhenChatReady(route, 0) },
                                        40L
                                    )
                                }
                            } else if (attempt == 0) {
                                Prefs.setStatus(
                                    this@WhatsRouteAccessibilityService,
                                    "OCR imagem 1: $totalLinhas linhas, sem rota. " +
                                        "Reforçando imagem e tentando de novo..."
                                )

                                handler.postDelayed(
                                    { captureAndReadImage(attempt = 1) },
                                    IMAGE_RETRY_DELAY_MS
                                )
                            } else {
                                closeImageWithoutSending(
                                    if (totalLinhas == 0)
                                        "OCR da imagem não conseguiu ler nenhum texto."
                                    else
                                        "OCR imagem leu $totalLinhas linhas, mas não fechou a rota. " +
                                            "Amostra: $amostra"
                                )
                            }
                        }
                        .addOnFailureListener { error ->
                            if (ocrBitmap !== bitmap) {
                                ocrBitmap.recycle()
                            }
                            bitmap.recycle()

                            if (attempt == 0) {
                                handler.postDelayed(
                                    { captureAndReadImage(attempt = 1) },
                                    IMAGE_RETRY_DELAY_MS
                                )
                            } else {
                                imageFailed("Erro no OCR: ${error.message}")
                            }
                        }
                }

                override fun onFailure(errorCode: Int) {
                    if (attempt == 0) {
                        handler.postDelayed(
                            { captureAndReadImage(attempt = 1) },
                            IMAGE_RETRY_DELAY_MS
                        )
                    } else {
                        imageFailed("Falha ao capturar a tela. Código: $errorCode")
                    }
                }
            }
        )
    }

    private fun prepararBitmapImagemParaOcr(
        bitmap: Bitmap,
        attempt: Int
    ): Bitmap {
        val w = bitmap.width
        val h = bitmap.height

        // Retira principalmente barra superior e controles inferiores do
        // visualizador. A tabela permanece inteira na largura.
        val top = (h * 0.07f).toInt().coerceAtLeast(0)
        val bottom = (h * 0.08f).toInt().coerceAtLeast(0)
        val cropHeight = (h - top - bottom).coerceAtLeast(1)

        val cropped = Bitmap.createBitmap(
            bitmap,
            0,
            top,
            w,
            cropHeight
        )

        // O problema no M52 é que a tabela aberta fica legível ao olho,
        // mas o texto é pequeno para o ML Kit. Em vez de dar zoom físico
        // (que poderia cortar a coluna Bairro), ampliamos a captura inteira.
        val scale = if (attempt == 0) 1.60f else 2.10f

        val scaled = Bitmap.createScaledBitmap(
            cropped,
            (cropped.width * scale).toInt().coerceAtLeast(1),
            (cropped.height * scale).toInt().coerceAtLeast(1),
            true
        )

        if (scaled !== cropped) {
            cropped.recycle()
        }

        return scaled
    }

    private fun contarLinhasVisionText(visionText: Text): Int =
        visionText.textBlocks.sumOf { it.lines.size }

    private fun resumirVisionText(visionText: Text): String {
        val linhas = visionText.textBlocks
            .flatMap { it.lines }
            .map { it.text.trim() }
            .filter { it.isNotBlank() }

        if (linhas.isEmpty()) {
            return "nenhum texto"
        }

        val prioridade = linhas.firstOrNull { linha ->
            val n = RouteParser.normalize(linha)
            listOf(
                "valparaiso",
                "colina",
                "baleia",
                "morada",
                "eurico",
                "plaza",
                "rosario",
                "helio",
                "ferraz",
                "barcelona",
                "maringa"
            ).any { it in n }
        }

        val amostra = prioridade ?: linhas.takeLast(3).joinToString(" | ")

        return amostra
            .replace("\n", " ")
            .take(120)
    }


    private fun parseVisionText(
        visionText: Text,
        screenHeight: Int
    ): RouteResult? {
        val items = mutableListOf<ScreenText>()

        for (block in visionText.textBlocks) {
            for (line in block.lines) {
                val box = line.boundingBox ?: continue
                items += ScreenText(
                    text = line.text,
                    left = box.left,
                    top = box.top,
                    right = box.right,
                    bottom = box.bottom
                )

                // Os elementos ajudam quando a tabela separa a gaiola do bairro.
                for (element in line.elements) {
                    val eb = element.boundingBox ?: continue
                    items += ScreenText(
                        text = element.text,
                        left = eb.left,
                        top = eb.top,
                        right = eb.right,
                        bottom = eb.bottom
                    )
                }
            }
        }

        return RouteParser.parseScreenTexts(items, screenHeight)
    }

    private fun closeImageWithoutSending(message: String) {
        backOnlyIfImageViewerOpen()
        Prefs.setStatus(this, message)

        handler.postDelayed({
            processing = false
            primeCurrentScreen()
        }, 180L)
    }

    private fun imageFailed(message: String) {
        backOnlyIfImageViewerOpen()
        Prefs.setStatus(this, message)

        handler.postDelayed({
            processing = false
            primeCurrentScreen()
        }, 180L)
    }

    private fun backOnlyIfImageViewerOpen() {
        val root = rootInActiveWindow ?: return
        val items = collectNodeItems(root)

        // Se o campo de mensagem ainda existe, continuamos no grupo.
        // Nesse caso NÃO VOLTA.
        if (findMessageEditor(items) != null) {
            return
        }

        performGlobalAction(GLOBAL_ACTION_BACK)
    }

    private fun sendRouteWhenChatReady(route: RouteResult, attempt: Int) {
        if (attempt >= 18) {
            processing = false
            Prefs.setStatus(this, "Voltei ao grupo, mas o campo de mensagem não apareceu.")
            primeCurrentScreen()
            return
        }

        val root = rootInActiveWindow
        if (root == null) {
            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)
            return
        }

        val items = collectNodeItems(root)
        val group = Prefs.groupName(this)

        if (!isTargetGroup(items, group)) {
            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)
            return
        }

        if (findMessageEditor(items) == null) {
            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)
            return
        }

        sendRouteInCurrentChat(route)
    }

    private fun sendRouteInCurrentChat(route: RouteResult) {
        if (isDuplicate(route)) {
            processing = false
            primeCurrentScreen()
            return
        }

        val root = rootInActiveWindow
        if (root == null) {
            processing = false
            Prefs.setStatus(this, "Não encontrei a janela do WhatsApp para enviar.")
            return
        }

        val items = collectNodeItems(root)
        val editor = findMessageEditor(items)

        if (editor == null) {
            processing = false
            Prefs.setStatus(this, "Rota achada, mas não encontrei o campo de mensagem.")
            return
        }

        val message = buildMessage(route.cage)

        val args = Bundle().apply {
            putCharSequence(
                AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                message
            )
        }

        val setOk = editor.node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        )

        if (!setOk) {
            processing = false
            Prefs.setStatus(this, "Rota achada, mas não consegui preencher a mensagem.")
            return
        }

        handler.postDelayed({
            val newRoot = rootInActiveWindow
            if (newRoot == null) {
                processing = false
                Prefs.setStatus(this, "Mensagem preenchida, mas perdi a janela do WhatsApp.")
                return@postDelayed
            }

            val newItems = collectNodeItems(newRoot)
            val send = findSendButton(newItems)

            if (send == null || !clickNodeOrParent(send.node)) {
                processing = false
                Prefs.setStatus(this, "Mensagem preenchida, mas não encontrei o botão Enviar.")
                return@postDelayed
            }

            markSent(route)
        }, SEND_BUTTON_DELAY_MS)
    }

    private fun markSent(route: RouteResult) {
        lastSentSignature = "${route.priorityIndex}:${route.cage}"
        lastSentAt = SystemClock.elapsedRealtime()

        val elapsed = if (currentStartedAt > 0L) {
            SystemClock.elapsedRealtime() - currentStartedAt
        } else {
            -1L
        }

        Prefs.setStatus(
            this,
            if (elapsed >= 0)
                "ENVIADO: ${route.neighborhood} -> ${route.cage} | app=${elapsed}ms"
            else
                "ENVIADO: ${route.neighborhood} -> ${route.cage}"
        )

        handler.postDelayed({
            processing = false
            primeCurrentScreen()
        }, 220L)
    }

    private fun isDuplicate(route: RouteResult): Boolean {
        val signature = "${route.priorityIndex}:${route.cage}"
        return signature == lastSentSignature &&
            SystemClock.elapsedRealtime() - lastSentAt < DEDUP_MS
    }

    private fun buildMessage(cage: String): String =
        """
        Felipe lima de Castilho
        1347515
        Passeio
        Gaiola: $cage
        """.trimIndent()

    private fun isTargetGroup(items: List<NodeItem>, wanted: String): Boolean {
        val target = RouteParser.normalize(wanted)
        if (target.isBlank()) return false

        val screenHeight = resources.displayMetrics.heightPixels
        val topLimit = (screenHeight * 0.25).toInt()

        return items.any { item ->
            item.rect.top <= topLimit &&
                RouteParser.normalize(item.text).contains(target)
        }
    }

    private fun findMessageEditor(items: List<NodeItem>): NodeItem? =
        items
            .filter { item ->
                item.editable ||
                    item.className == "android.widget.EditText"
            }
            .maxByOrNull { it.rect.bottom }

    private fun findSendButton(items: List<NodeItem>): NodeItem? {
        val screenWidth = resources.displayMetrics.widthPixels
        val screenHeight = resources.displayMetrics.heightPixels

        val named = items
            .filter { it.clickable }
            .filter { item ->
                val n = RouteParser.normalize(item.text)
                "enviar" in n || n == "send" || "send message" in n
            }
            .maxByOrNull { it.rect.bottom }

        if (named != null) return named

        // Fallback: depois de preencher o texto, o botão de enviar fica
        // no canto inferior direito do WhatsApp.
        return items
            .filter { it.clickable }
            .filter { item ->
                item.rect.left >= (screenWidth * 0.72).toInt() &&
                    item.rect.top >= (screenHeight * 0.72).toInt() &&
                    item.rect.width() in 24..240 &&
                    item.rect.height() in 24..240
            }
            .maxWithOrNull(
                compareBy<NodeItem>({ it.rect.bottom }, { it.rect.right })
            )
    }

    private fun findImageCandidates(items: List<NodeItem>): List<NodeItem> {
        val screenWidth = resources.displayMetrics.widthPixels
        val screenHeight = resources.displayMetrics.heightPixels

        val badWords = listOf(
            "perfil",
            "avatar",
            "emoji",
            "camera",
            "anexar",
            "sticker",
            "microfone",
            "enviar",
            "menu",
            "voltar",
            "chamada",
            "videochamada"
        )

        return items
            .filter { item ->
                if (item.rect.isEmpty) return@filter false
                if (item.editable) return@filter false

                val n = RouteParser.normalize(item.text)

                val notToolbar =
                    item.rect.top >= (screenHeight * 0.13).toInt() &&
                    item.rect.bottom <= (screenHeight * 0.89).toInt()

                val widthOk =
                    item.rect.width() >= (screenWidth * 0.20).toInt() &&
                    item.rect.width() <= (screenWidth * 0.96).toInt()

                val heightOk =
                    item.rect.height() >= (screenHeight * 0.055).toInt() &&
                    item.rect.height() <= (screenHeight * 0.48).toInt()

                if (!notToolbar || !widthOk || !heightOk) {
                    return@filter false
                }

                if (badWords.any { it in n }) {
                    return@filter false
                }

                val classLooksLikeImage =
                    item.className.contains("Image", ignoreCase = true) ||
                    item.className.contains("Photo", ignoreCase = true)

                val descriptionLooksLikeImage =
                    "foto" in n ||
                    "imagem" in n ||
                    "photo" in n ||
                    "image" in n

                // Fallback importante para o WhatsApp no M52:
                // a miniatura pode aparecer apenas como View/FrameLayout,
                // sem descrição "imagem". Nesse caso exigimos:
                // - bloco visual grande;
                // - sem texto próprio;
                // - sem texto útil nos descendentes;
                // - ele próprio ou algum pai próximo precisa ser clicável.
                val blankVisualCandidate =
                    n.isBlank() &&
                    item.rect.width() >= (screenWidth * 0.24).toInt() &&
                    item.rect.height() >= (screenHeight * 0.060).toInt()

                // Alguns WhatsApps/Samsung expõem a miniatura como View/FrameLayout
                // sem texto e sem ACTION_CLICK. O toque por coordenada da v0.4
                // permite usar esses nós também.
                val genericVisualCandidate =
                    n.length <= 12 &&
                    (
                        item.className.contains("View", ignoreCase = true) ||
                        item.className.contains("Frame", ignoreCase = true) ||
                        item.className.contains("Layout", ignoreCase = true)
                    ) &&
                    item.rect.width() >= (screenWidth * 0.26).toInt() &&
                    item.rect.height() >= (screenHeight * 0.070).toInt()

                classLooksLikeImage ||
                    descriptionLooksLikeImage ||
                    blankVisualCandidate ||
                    genericVisualCandidate
            }
            // Remove duplicações de filho/pai ocupando praticamente o mesmo retângulo.
            .distinctBy { item ->
                listOf(
                    item.rect.left / 8,
                    item.rect.top / 8,
                    item.rect.right / 8,
                    item.rect.bottom / 8
                ).joinToString(":")
            }
    }

    private fun hasClickableNodeOrParent(
        start: AccessibilityNodeInfo,
        maxDepth: Int
    ): Boolean {
        var current: AccessibilityNodeInfo? = start
        var depth = 0

        while (current != null && depth <= maxDepth) {
            if (current.isClickable) return true
            current = current.parent
            depth++
        }

        return false
    }

    private fun hasMeaningfulDescendantText(
        node: AccessibilityNodeInfo,
        maxDepth: Int,
        depth: Int = 0
    ): Boolean {
        if (depth > maxDepth) return false

        val own = buildString {
            node.text?.toString()?.let { append(it) }
            node.contentDescription?.toString()?.let {
                if (isNotEmpty()) append(' ')
                append(it)
            }
        }

        val normalized = RouteParser.normalize(own)

        if (
            normalized.length >= 3 &&
            "foto" !in normalized &&
            "imagem" !in normalized &&
            "photo" !in normalized &&
            "image" !in normalized
        ) {
            return true
        }

        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            if (hasMeaningfulDescendantText(child, maxDepth, depth + 1)) {
                return true
            }
        }

        return false
    }

    private fun imageCandidateScore(item: NodeItem): Long {
        val area = item.rect.width().toLong() * item.rect.height().toLong()
        val classBonus =
            if (item.className.contains("Image", ignoreCase = true)) 1_000_000_000L
            else 0L
        val textBonus = if (
            RouteParser.normalize(item.text).let {
                "foto" in it || "imagem" in it || "photo" in it || "image" in it
            }
        ) 500_000_000L else 0L

        // Dá preferência ao candidato mais baixo quando a pontuação é próxima.
        return classBonus + textBonus + area + item.rect.bottom.toLong()
    }

    private fun imageFingerprint(item: NodeItem): String =
        buildString {
            append(item.className)
            append('|')
            append(RouteParser.normalize(item.text))
            append('|')
            append(item.rect.left)
            append(',')
            append(item.rect.top)
            append(',')
            append(item.rect.right)
            append(',')
            append(item.rect.bottom)
            append('|')
            append(item.node.hashCode())
        }

    private fun textSignatures(items: List<NodeItem>): Set<String> =
        items
            .map { RouteParser.normalize(it.text) }
            .filter { it.isNotBlank() }
            .toSet()

    private fun collectNodeItems(root: AccessibilityNodeInfo): List<NodeItem> {
        val result = ArrayList<NodeItem>(96)
        collectNodeItemsRecursive(root, result, depth = 0)
        return result
    }

    private fun collectNodeItemsRecursive(
        node: AccessibilityNodeInfo,
        out: MutableList<NodeItem>,
        depth: Int
    ) {
        if (depth > 80) return

        val rect = Rect()
        node.getBoundsInScreen(rect)

        val mergedText = buildString {
            node.text?.toString()?.takeIf { it.isNotBlank() }?.let {
                append(it)
            }

            node.contentDescription?.toString()?.takeIf { it.isNotBlank() }?.let {
                if (isNotEmpty()) append(" | ")
                append(it)
            }
        }

        out += NodeItem(
            text = mergedText,
            rect = rect,
            className = node.className?.toString().orEmpty(),
            clickable = node.isClickable,
            editable = node.isEditable,
            node = node
        )

        for (index in 0 until node.childCount) {
            val child = node.getChild(index) ?: continue
            collectNodeItemsRecursive(child, out, depth + 1)
        }
    }

    private fun clickImageCandidateSafely(candidate: NodeItem): Boolean {
        val screenWidth = resources.displayMetrics.widthPixels
        val screenHeight = resources.displayMetrics.heightPixels
        val r = candidate.rect

        if (r.isEmpty) return false

        // Toca dentro da miniatura por COORDENADA, sem depender de o WhatsApp
        // marcar aquele nó como "clickable". Isso é mais confiável no M52.
        val tapX = r.centerX()
            .coerceIn(8, screenWidth - 8)

        // 42% da altura tende a cair no conteúdo da foto, evitando timestamp/caption.
        val tapY = (r.top + (r.height() * 0.42f)).toInt()
            .coerceIn(
                (screenHeight * 0.14).toInt(),
                (screenHeight * 0.88).toInt()
            )

        val path = Path().apply {
            moveTo(tapX.toFloat(), tapY.toFloat())
        }

        val gesture = GestureDescription.Builder()
            .addStroke(
                GestureDescription.StrokeDescription(
                    path,
                    0L,
                    45L
                )
            )
            .build()

        val gestureAccepted = dispatchGesture(
            gesture,
            object : GestureResultCallback() {
                override fun onCompleted(gestureDescription: GestureDescription?) {
                    Prefs.setStatus(
                        this@WhatsRouteAccessibilityService,
                        "Toque na imagem executado em ($tapX,$tapY). Confirmando abertura..."
                    )
                }

                override fun onCancelled(gestureDescription: GestureDescription?) {
                    Prefs.setStatus(
                        this@WhatsRouteAccessibilityService,
                        "Toque por coordenada foi cancelado."
                    )
                }
            },
            null
        )

        if (gestureAccepted) {
            return true
        }

        // Fallback: tenta ACTION_CLICK somente se o Android não aceitou o gesto.
        var current: AccessibilityNodeInfo? = candidate.node
        var depth = 0

        while (current != null && depth <= 5) {
            val rect = Rect()
            current.getBoundsInScreen(rect)

            val notWholeChat =
                rect.width() <= (screenWidth * 0.98).toInt() &&
                rect.height() <= (screenHeight * 0.70).toInt()

            if (
                current.isClickable &&
                notWholeChat &&
                current.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            ) {
                return true
            }

            current = current.parent
            depth++
        }

        return false
    }


    private fun clickNodeOrParent(start: AccessibilityNodeInfo): Boolean {
        var current: AccessibilityNodeInfo? = start
        var depth = 0

        while (current != null && depth < 6) {
            if (current.isClickable &&
                current.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            ) {
                return true
            }

            current = current.parent
            depth++
        }

        return start.performAction(AccessibilityNodeInfo.ACTION_CLICK)
    }
}
