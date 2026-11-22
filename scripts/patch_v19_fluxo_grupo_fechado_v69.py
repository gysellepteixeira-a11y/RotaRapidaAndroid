import os
import sys
import re

def get_balance(text):
    return text.count('{') - text.count('}')

def run_patch():
    S = "app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt"
    if not os.path.exists(S):
        sys.exit(f"Erro: {S} não encontrado.")
    
    with open(S, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 0. Inserir função auxiliar se não existir
    if "private fun findMessageEditorFastV48" not in content:
        fast_editor_func = "\n    private fun findMessageEditorFastV48(root: AccessibilityNodeInfo): NodeItem? {\n        val items = collectNodeItems(root)\n        return items.filter { it.editable || it.className == \"android.widget.EditText\" }\n                    .maxByOrNull { it.rect.bottom }\n    }\n"
        match = re.search(r'private fun findMessageEditor', content)
        if match:
            content = content[:match.start()] + fast_editor_func + content[match.start():]
        else:
            sys.exit("Erro: findMessageEditor não encontrado.")

    # 1. Substituir sendRouteWhenChatReady
    # Regex robusto para capturar toda a função, ignorando espaços e quebras
    pattern = re.compile(r'private fun sendRouteWhenChatReady\s*\(route: RouteResult, attempt: Int\)\s*\{.*?\}', re.DOTALL)
    new_loop = "private fun sendRouteWhenChatReady(route: RouteResult, attempt: Int) {\n        if (attempt >= 18) {\n            processing = false\n            Prefs.setStatus(this, \"Voltei ao grupo, mas o campo de mensagem não apareceu.\")\n            primeCurrentScreen()\n            return\n        }\n\n        val root = rootInActiveWindow\n        if (root == null) {\n            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)\n            return\n        }\n\n        val fastEditor = findMessageEditorFastV48(root)\n        if (fastEditor == null) {\n            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)\n            return\n        }\n\n        val group = Prefs.groupName(this)\n        val items = collectNodeItems(root)\n        if (!isTargetGroup(items, group)) {\n            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)\n            return\n        }\n\n        sendRouteInCurrentChat(route, fastEditor.node)\n    }"
    
    if not pattern.search(content):
        sys.exit("Erro: sendRouteWhenChatReady não encontrada para substituição.")
    content = pattern.sub(new_loop, content)
    
    # 2. Substituir sendRouteInCurrentChat
    pattern = re.compile(r'private fun sendRouteInCurrentChat\s*\(route: RouteResult\)\s*\{.*?\}', re.DOTALL)
    new_send = "private fun sendRouteInCurrentChat(route: RouteResult, editorNode: AccessibilityNodeInfo? = null) {\n        if (isDuplicate(route)) {\n            processing = false\n            primeCurrentScreen()\n            return\n        }\n\n        val root = rootInActiveWindow\n        if (root == null) {\n            processing = false\n            Prefs.setStatus(this, \"Não encontrei a janela do WhatsApp para enviar.\")\n            return\n        }\n\n        val editor = if (editorNode != null) {\n            val rect = Rect()\n            editorNode.getBoundsInScreen(rect)\n            NodeItem(\"\", rect, \"android.widget.EditText\", false, true, editorNode)\n        } else {\n            val items = collectNodeItems(root)\n            findMessageEditor(items)\n        }\n\n        if (editor == null) {\n            processing = false\n            Prefs.setStatus(this, \"Rota achada, mas não encontrei o campo de mensagem.\")\n            return\n        }\n\n        val message = buildMessage(route.cage)\n        val args = Bundle().apply {\n            putCharSequence(\n                AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,\n                message\n            )\n        }\n\n        val clickStarted = SystemClock.elapsedRealtime()\n        val setOk = editor.node.performAction(\n            AccessibilityNodeInfo.ACTION_SET_TEXT,\n            args\n        )\n\n        if (!setOk) {\n            processing = false\n            Prefs.setStatus(this, \"Rota achada, mas não consegui preencher a mensagem.\")\n            return\n        }\n\n        handler.postDelayed({\n            val newRoot = rootInActiveWindow\n            if (newRoot == null) {\n                processing = false\n                Prefs.setStatus(this, \"Mensagem preenchida, mas perdi a janela do WhatsApp.\")\n                return@postDelayed\n            }\n\n            val newItems = collectNodeItems(newRoot)\n            val send = findSendButton(newItems)\n\n            if (send == null || !clickNodeOrParent(send.node)) {\n                processing = false\n                Prefs.setStatus(this, \"Mensagem preenchida, mas não encontrei o botão Enviar.\")\n                return@postDelayed\n            }\n\n            val clickDuration = SystemClock.elapsedRealtime() - clickStarted\n            markSent(route, clickDuration)\n        }, SEND_BUTTON_DELAY_MS)\n    }"
    
    if not pattern.search(content):
        # Tenta a nova assinatura caso já tenha sido aplicada parcialmente
        pattern = re.compile(r'private fun sendRouteInCurrentChat\s*\(route: RouteResult, editorNode: AccessibilityNodeInfo\?\s*=\s*null\)\s*\{.*?\}', re.DOTALL)
        if not pattern.search(content):
            sys.exit("Erro: sendRouteInCurrentChat não encontrada.")
    content = pattern.sub(new_send, content)

    # 3. Substituir markSent
    pattern = re.compile(r'private fun markSent\s*\(route: RouteResult\)\s*\{.*?\}', re.DOTALL)
    new_mark = "private fun markSent(route: RouteResult, clickDuration: Long = -1L) {\n        lastSentSignature = \"${route.priorityIndex}:${route.cage}\"\n        lastSentAt = SystemClock.elapsedRealtime()\n\n        val elapsed = if (currentStartedAt > 0L) {\n            SystemClock.elapsedRealtime() - currentStartedAt\n        } else {\n            -1L\n        }\n\n        val log = if (elapsed >= 0) \"app=${elapsed}ms\" else \"\"\n        val clickLog = if (clickDuration >= 0) \" | click=${clickDuration}ms\" else \"\"\n\n        Prefs.setStatus(\n            this,\n            \"ENVIADO: ${route.neighborhood} -> ${route.cage} | $log$clickLog\"\n        )\n\n        handler.postDelayed({\n            processing = false\n            primeCurrentScreen()\n        }, 220L)\n    }"
    
    if not pattern.search(content):
        pattern = re.compile(r'private fun markSent\s*\(route: RouteResult, clickDuration: Long\s*=\s*-1L\)\s*\{.*?\}', re.DOTALL)
        if not pattern.search(content):
             sys.exit("Erro: markSent não encontrada.")
    content = pattern.sub(new_mark, content)

    # 4. Validação final
    count = content.count("fun sendRouteWhenChatReady")
    if count != 1:
        sys.exit(f"Erro: Duplicação ou erro em sendRouteWhenChatReady. Contagem: {count}")

    with open(S, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patch aplicado com sucesso.")

run_patch()
