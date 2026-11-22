import os
import sys
import re

def get_balance(text):
    return text.count('{') - text.count('}')

def run_patch():
    S = "app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt"
    with open(S, "r", encoding="utf-8") as f:
        content = f.read()
    
    b_before = get_balance(content)
    
    # 0. Adicionar findMessageEditorFastV48
    if "private fun findMessageEditorFastV48" not in content:
        fast_editor_func = "\n    private fun findMessageEditorFastV48(root: AccessibilityNodeInfo): NodeItem? {\n        val items = collectNodeItems(root)\n        return items.filter { it.editable || it.className == \"android.widget.EditText\" }\n                    .maxByOrNull { it.rect.bottom }\n    }\n"
        match = re.search(r'private fun findMessageEditor', content)
        if match:
            content = content[:match.start()] + fast_editor_func + content[match.start():]
        else:
            sys.exit("Erro: findMessageEditor não encontrado.")

    # 1. Ajustar sendRouteWhenChatReady
    m_loop = re.search(r'private fun sendRouteWhenChatReady\(route: RouteResult, attempt: Int\) \{', content)
    if not m_loop: sys.exit("Erro: sendRouteWhenChatReady não encontrada.")
    start = m_loop.start()
    balance = 0
    end = -1
    for i in range(start, len(content)):
        if content[i] == '{': balance += 1
        elif content[i] == '}': balance -= 1
        if balance == 0 and i > start:
            end = i + 1
            break
            
    new_loop = "private fun sendRouteWhenChatReady(route: RouteResult, attempt: Int) {\n        if (attempt >= 18) {\n            processing = false\n            Prefs.setStatus(this, \"Voltei ao grupo, mas o campo de mensagem não apareceu.\")\n            primeCurrentScreen()\n            return\n        }\n\n        val root = rootInActiveWindow\n        if (root == null) {\n            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)\n            return\n        }\n\n        val fastEditor = findMessageEditorFastV48(root)\n        if (fastEditor == null) {\n            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)\n            return\n        }\n\n        val group = Prefs.groupName(this)\n        val items = collectNodeItems(root)\n        if (!isTargetGroup(items, group)) {\n            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)\n            return\n        }\n\n        sendRouteInCurrentChat(route, fastEditor.node)\n    }"
    content = content[:start] + new_loop + content[end:]

    # 2. Ajustar sendRouteInCurrentChat
    m_send = re.search(r'private fun sendRouteInCurrentChat\(route: RouteResult\) \{', content)
    if not m_send: sys.exit("Erro: sendRouteInCurrentChat original não encontrada.")
    start = m_send.start()
    balance = 0
    end = -1
    for i in range(start, len(content)):
        if content[i] == '{': balance += 1
        elif content[i] == '}': balance -= 1
        if balance == 0 and i > start:
            end = i + 1
            break
            
    new_send = "private fun sendRouteInCurrentChat(route: RouteResult, editorNode: AccessibilityNodeInfo? = null) {\n        if (isDuplicate(route)) {\n            processing = false\n            primeCurrentScreen()\n            return\n        }\n\n        val root = rootInActiveWindow\n        if (root == null) {\n            processing = false\n            Prefs.setStatus(this, \"Não encontrei a janela do WhatsApp para enviar.\")\n            return\n        }\n\n        val editor = if (editorNode != null) {\n            val rect = Rect()\n            editorNode.getBoundsInScreen(rect)\n            NodeItem(\"\", rect, \"android.widget.EditText\", false, true, editorNode)\n        } else {\n            val items = collectNodeItems(root)\n            findMessageEditor(items)\n        }\n\n        if (editor == null) {\n            processing = false\n            Prefs.setStatus(this, \"Rota achada, mas não encontrei o campo de mensagem.\")\n            return\n        }\n\n        val message = buildMessage(route.cage)\n        val args = Bundle().apply {\n            putCharSequence(\n                AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,\n                message\n            )\n        }\n\n        val clickStarted = SystemClock.elapsedRealtime()\n        val setOk = editor.node.performAction(\n            AccessibilityNodeInfo.ACTION_SET_TEXT,\n            args\n        )\n\n        if (!setOk) {\n            processing = false\n            Prefs.setStatus(this, \"Rota achada, mas não consegui preencher a mensagem.\")\n            return\n        }\n\n        handler.postDelayed({\n            val newRoot = rootInActiveWindow\n            if (newRoot == null) {\n                processing = false\n                Prefs.setStatus(this, \"Mensagem preenchida, mas perdi a janela do WhatsApp.\")\n                return@postDelayed\n            }\n\n            val newItems = collectNodeItems(newRoot)\n            val send = findSendButton(newItems)\n\n            if (send == null || !clickNodeOrParent(send.node)) {\n                processing = false\n                Prefs.setStatus(this, \"Mensagem preenchida, mas não encontrei o botão Enviar.\")\n                return@postDelayed\n            }\n\n            val clickDuration = SystemClock.elapsedRealtime() - clickStarted\n            markSent(route, clickDuration)\n        }, SEND_BUTTON_DELAY_MS)\n    }"
    content = content[:start] + new_send + content[end:]
    
    # 3. Ajustar markSent
    m_mark = re.search(r'private fun markSent\(route: RouteResult\) \{', content)
    if not m_mark: sys.exit("Erro: markSent original não encontrada.")
    start = m_mark.start()
    balance = 0
    end = -1
    for i in range(start, len(content)):
        if content[i] == '{': balance += 1
        elif content[i] == '}': balance -= 1
        if balance == 0 and i > start:
            end = i + 1
            break

    new_mark = "private fun markSent(route: RouteResult, clickDuration: Long = -1L) {\n        lastSentSignature = \"${route.priorityIndex}:${route.cage}\"\n        lastSentAt = SystemClock.elapsedRealtime()\n\n        val elapsed = if (currentStartedAt > 0L) {\n            SystemClock.elapsedRealtime() - currentStartedAt\n        } else {\n            -1L\n        }\n\n        val log = if (elapsed >= 0) \"app=${elapsed}ms\" else \"\"\n        val clickLog = if (clickDuration >= 0) \" | click=${clickDuration}ms\" else \"\"\n\n        Prefs.setStatus(\n            this,\n            \"ENVIADO: ${route.neighborhood} -> ${route.cage} | $log$clickLog\"\n        )\n\n        handler.postDelayed({\n            processing = false\n            primeCurrentScreen()\n        }, 220L)\n    }"
    content = content[:start] + new_mark + content[end:]
    
    b_after = get_balance(content)
    if b_before != b_after:
        sys.exit(f"Erro: Saldo de chaves incorreto! Antes: {b_before}, Depois: {b_after}")
    
    with open(S, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patch aplicado com sucesso.")

run_patch()
