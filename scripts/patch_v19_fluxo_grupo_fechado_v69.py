from pathlib import Path
import sys

S = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = S.read_text(encoding="utf-8")

# 1. Otimizar loop de espera sendRouteWhenChatReady
old_loop = '''    private fun sendRouteWhenChatReady(route: RouteResult, attempt: Int) {
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
    }'''

new_loop = '''    private fun sendRouteWhenChatReady(route: RouteResult, attempt: Int) {
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

        val fastEditor = findMessageEditorFastV48(root)
        if (fastEditor == null) {
            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)
            return
        }

        val group = Prefs.groupName(this)
        val items = collectNodeItems(root)
        if (!isTargetGroup(items, group)) {
            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)
            return
        }

        sendRouteInCurrentChat(route, fastEditor.node)
    }'''

# 2. Atualizar assinatura e corpo de sendRouteInCurrentChat
old_send = '''    private fun sendRouteInCurrentChat(route: RouteResult) {
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
    }'''

new_send = '''    private fun sendRouteInCurrentChat(route: RouteResult, editorNode: AccessibilityNodeInfo? = null) {
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

        val editor = if (editorNode != null) {
            val rect = Rect()
            editorNode.getBoundsInScreen(rect)
            NodeItem("", rect, "android.widget.EditText", false, true, editorNode)
        } else {
            val items = collectNodeItems(root)
            findMessageEditor(items)
        }

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

        val clickStarted = SystemClock.elapsedRealtime()
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

            val clickDuration = SystemClock.elapsedRealtime() - clickStarted
            markSent(route, clickDuration)
        }, SEND_BUTTON_DELAY_MS)
    }'''

# 3. Atualizar markSent
old_mark = '''    private fun markSent(route: RouteResult) {
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
    }'''

new_mark = '''    private fun markSent(route: RouteResult, clickDuration: Long = -1L) {
        lastSentSignature = "${route.priorityIndex}:${route.cage}"
        lastSentAt = SystemClock.elapsedRealtime()

        val elapsed = if (currentStartedAt > 0L) {
            SystemClock.elapsedRealtime() - currentStartedAt
        } else {
            -1L
        }

        val log = if (elapsed >= 0) "app=${elapsed}ms" else ""
        val clickLog = if (clickDuration >= 0) " | click=${clickDuration}ms" else ""

        Prefs.setStatus(
            this,
            "ENVIADO: ${route.neighborhood} -> ${route.cage} | $log$clickLog"
        )

        handler.postDelayed({
            processing = false
            primeCurrentScreen()
        }, 220L)
    }'''

if old_loop not in s or old_send not in s or old_mark not in s:
    sys.exit("Erro: blocos de código originais não encontrados para patch")

s = s.replace(old_loop, new_loop, 1)
s = s.replace(old_send, new_send, 1)
s = s.replace(old_mark, new_mark, 1)

S.write_text(s, encoding="utf-8")
print("Patch aplicado com sucesso: otimização de fluxo de grupo fechado")
''',file_path: