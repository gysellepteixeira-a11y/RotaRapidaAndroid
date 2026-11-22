import os
import sys
import re

def normalize_text(text):
    return text.replace('\r\n', '\n').strip()

def run_patch():
    S = "app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt"
    if not os.path.exists(S):
        print(f"Erro: Arquivo {S} não encontrado.")
        sys.exit(1)

    with open(S, "r", encoding="utf-8") as f:
        content = f.read()

    content = normalize_text(content)

    # Adicionar findMessageEditorFastV48 se necessário
    if "private fun findMessageEditorFastV48" not in content:
        fast_editor_func = '''    private fun findMessageEditorFastV48(root: AccessibilityNodeInfo): NodeItem? {
        val items = collectNodeItems(root)
        return items.filter { it.editable || it.className == "android.widget.EditText" }
                    .maxByOrNull { it.rect.bottom }
    }'''
        # Inserir antes de findMessageEditor
        match = re.search(r'private fun findMessageEditor', content)
        if match:
            content = content[:match.start()] + fast_editor_func + "\n\n" + content[match.start():]
        else:
            print("Erro crítico: função findMessageEditor não encontrada para âncora.")
            sys.exit(1)

    # Regra 2b: Localizar usando âncoras e regex
    # sendRouteWhenChatReady
    # sendRouteInCurrentChat
    # markSent

    # 1. Ajustar sendRouteWhenChatReady
    # Regex para encontrar a função inteira e substituir
    loop_pattern = re.compile(r'private fun sendRouteWhenChatReady\(route: RouteResult, attempt: Int\) \{.*?\}', re.DOTALL)
    if not loop_pattern.search(content):
        print("Erro: função sendRouteWhenChatReady não encontrada.")
        # Debug: imprimir trecho próximo
        print(content[:1000])
        sys.exit(1)

    new_loop = '''private fun sendRouteWhenChatReady(route: RouteResult, attempt: Int) {
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
    content = loop_pattern.sub(new_loop, content)

    # 2. Ajustar sendRouteInCurrentChat
    send_pattern = re.compile(r'private fun sendRouteInCurrentChat\(route: RouteResult\) \{.*?\}', re.DOTALL)
    if not send_pattern.search(content):
        # Tenta com assinatura já alterada se rodar mais de uma vez, mas não deveria acontecer
        print("Erro: função sendRouteInCurrentChat original não encontrada.")
        sys.exit(1)

    new_send = '''private fun sendRouteInCurrentChat(route: RouteResult, editorNode: AccessibilityNodeInfo? = null) {
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
    content = send_pattern.sub(new_send, content)

    # 3. Ajustar markSent
    mark_pattern = re.compile(r'private fun markSent\(route: RouteResult\) \{.*?\}', re.DOTALL)
    if not mark_pattern.search(content):
        print("Erro: função markSent original não encontrada.")
        sys.exit(1)

    new_mark = '''private fun markSent(route: RouteResult, clickDuration: Long = -1L) {
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
    content = mark_pattern.sub(new_mark, content)

    with open(S, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patch aplicado com sucesso.")

if __name__ == "__main__":
    run_patch()
'''
with open("scripts/patch_v19_fluxo_grupo_fechado_v69.py", "w", encoding="utf-8") as f:
    f.write(content)
