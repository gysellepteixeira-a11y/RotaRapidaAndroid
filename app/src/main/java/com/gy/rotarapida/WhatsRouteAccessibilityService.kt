package com.gy.rotarapida

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityService.TakeScreenshotCallback
import android.accessibilityservice.AccessibilityService.ScreenshotResult
import android.graphics.Bitmap
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

        private const val IMAGE_RETRY_DELAY_MS = 380L
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
    private var lastImageFingerprint = ""
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
        lastImageFingerprint = findImageCandidate(items)?.let(::imageFingerprint).orEmpty()
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
            lastImageFingerprint = findImageCandidate(items)?.let(::imageFingerprint).orEmpty()
            primed = true
            return
        }

        val currentSignatures = textSignatures(items)

        if (!primed) {
            previousTexts = currentSignatures
            lastImageFingerprint = findImageCandidate(items)?.let(::imageFingerprint).orEmpty()
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
        if (SystemClock.elapsedRealtime() <= imageHintUntil) {
            val candidate = findImageCandidate(items)
            if (candidate != null) {
                val fingerprint = imageFingerprint(candidate)

                if (fingerprint != lastImageFingerprint) {
                    lastImageFingerprint = fingerprint
                    currentStartedAt = SystemClock.elapsedRealtime()
                    processing = true

                    Prefs.setStatus(this, "Nova imagem detectada. Abrindo...")

                    if (clickNodeOrParent(candidate.node)) {
                        handler.postDelayed(
                            { captureAndReadImage(attempt = 0) },
                            IMAGE_OPEN_DELAY_MS
                        )
                    } else {
                        processing = false
                        Prefs.setStatus(this, "Imagem detectada, mas não consegui abrir.")
                    }
                    return
                }
            }
        }

        // Mantém a referência atual das imagens sem clicar em imagem antiga.
        findImageCandidate(items)?.let {
            lastImageFingerprint = imageFingerprint(it)
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

                    val input = InputImage.fromBitmap(bitmap, 0)

                    recognizer.process(input)
                        .addOnSuccessListener { visionText ->
                            val route = parseVisionText(
                                visionText,
                                bitmap.height
                            )

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
                                    "Primeiro OCR da imagem não fechou a rota. Tentando mais uma vez..."
                                )

                                handler.postDelayed(
                                    { captureAndReadImage(attempt = 1) },
                                    IMAGE_RETRY_DELAY_MS
                                )
                            } else {
                                closeImageWithoutSending(
                                    "Imagem lida, mas não encontrei bairro prioritário + gaiola."
                                )
                            }
                        }
                        .addOnFailureListener { error ->
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
        performGlobalAction(GLOBAL_ACTION_BACK)
        Prefs.setStatus(this, message)

        handler.postDelayed({
            processing = false
            primeCurrentScreen()
        }, 180L)
    }

    private fun imageFailed(message: String) {
        performGlobalAction(GLOBAL_ACTION_BACK)
        Prefs.setStatus(this, message)

        handler.postDelayed({
            processing = false
            primeCurrentScreen()
        }, 180L)
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

    private fun findImageCandidate(items: List<NodeItem>): NodeItem? {
        val screenWidth = resources.displayMetrics.widthPixels
        val screenHeight = resources.displayMetrics.heightPixels

        val badWords = listOf(
            "perfil",
            "avatar",
            "emoji",
            "camera",
            "camera",
            "anexar",
            "sticker"
        )

        return items
            .filter { item ->
                val classLooksLikeImage =
                    item.className.contains("Image", ignoreCase = true)

                val n = RouteParser.normalize(item.text)
                val descriptionLooksLikeImage =
                    "foto" in n ||
                    "imagem" in n ||
                    "photo" in n ||
                    "image" in n

                val notToolbar =
                    item.rect.top >= (screenHeight * 0.14).toInt() &&
                    item.rect.bottom <= (screenHeight * 0.90).toInt()

                val largeEnough =
                    item.rect.width() >= (screenWidth * 0.20).toInt() &&
                    item.rect.height() >= (screenHeight * 0.055).toInt()

                val safeDescription = badWords.none { it in n }

                (classLooksLikeImage || descriptionLooksLikeImage) &&
                    notToolbar &&
                    largeEnough &&
                    safeDescription
            }
            .maxByOrNull { it.rect.bottom }
    }

    private fun imageFingerprint(item: NodeItem): String =
        buildString {
            append(RouteParser.normalize(item.text))
            append('|')
            append(item.rect.left)
            append(',')
            append(item.rect.top)
            append(',')
            append(item.rect.right)
            append(',')
            append(item.rect.bottom)
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
