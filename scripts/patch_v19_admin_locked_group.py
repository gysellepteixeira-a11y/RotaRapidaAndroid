from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - GRUPO BLOQUEADO PELO ADMIN
#
# O WhatsApp pode deixar o grupo aberto/visivel, recebendo mensagens normalmente,
# mas sem campo de digitacao quando somente admins podem enviar. A versao anterior
# confundia isso com "nao estou numa conversa" e, por isso, nao analisava rotas de
# texto nesse estado. Imagens podiam ser vistas pelo watcher do MediaStore, mas a
# rota pendente dependia de um novo evento do WhatsApp para tentar enviar depois.
#
# Este patch:
# 1) reconhece o aviso de "somente/apenas admins podem enviar mensagens" como uma
#    conversa valida, mesmo sem editor;
# 2) le texto e imagem normalmente enquanto o grupo esta bloqueado;
# 3) ao achar a rota, mantem pendingRoute e NAO procura outra rota por cima;
# 4) verifica a cada 120 ms se o campo de mensagem reapareceu. Assim que o admin
#    liberar o grupo, envia a rota pendente imediatamente.

const_anchor = '        private const val CLOSED_GROUP_READ_DELAY_MS = 90L\n'
if 'PENDING_ROUTE_SEND_WATCH_MS' not in s:
    if const_anchor not in s:
        raise SystemExit('patch_v19_admin_locked_group: constantes do closed watcher nao encontradas')
    s = s.replace(
        const_anchor,
        const_anchor + '        private const val PENDING_ROUTE_SEND_WATCH_MS = 120L\n',
        1
    )

# Helper para reconhecer o estado de grupo bloqueado por admin.
helper_anchor = '    private fun checkForWhatsAppImageWhileChatClosed() {\n'
if 'private fun isAdminLockedGroup(' not in s:
    if helper_anchor not in s:
        raise SystemExit('patch_v19_admin_locked_group: helper do MediaStore watcher nao encontrado')

    helper = r'''    private fun isAdminLockedGroup(items: List<NodeItem>): Boolean {
        return items.any { item ->
            val t = RouteParser.normalize(item.text)
            if (t.isBlank()) return@any false

            val mentionsAdmin =
                t.contains("admin") ||
                t.contains("administrador")

            val onlyAdmins =
                t.contains("somente") ||
                t.contains("apenas") ||
                t.contains("so os") ||
                t.contains("so admin") ||
                t.contains("only")

            val sending =
                t.contains("enviar") ||
                t.contains("mensagem") ||
                t.contains("send") ||
                t.contains("message")

            mentionsAdmin && onlyAdmins && sending
        }
    }

'''
    s = s.replace(helper_anchor, helper + helper_anchor, 1)

# Enquanto existe rota pendente, tenta enviar periodicamente. Isso nao depende de
# o WhatsApp gerar um evento de acessibilidade exatamente no instante em que o
# admin reabre o envio de mensagens.
on_service = '\n    override fun onServiceConnected() {'
if 'pendingRouteSendWatchRunnable' not in s:
    pos = s.find(on_service)
    if pos < 0:
        raise SystemExit('patch_v19_admin_locked_group: onServiceConnected nao encontrado')

    runnable = r'''

    private val pendingRouteSendWatchRunnable = object : Runnable {
        override fun run() {
            try {
                if (
                    Prefs.isEnabled(this@WhatsRouteAccessibilityService) &&
                    pendingRoute != null &&
                    !processing &&
                    !alertSequenceRunning
                ) {
                    trySendPendingRouteIfChatOpen()
                }
            } catch (_: Throwable) {
                // A rota continua guardada para a proxima tentativa.
            } finally {
                handler.postDelayed(this, PENDING_ROUTE_SEND_WATCH_MS)
            }
        }
    }
'''
    s = s[:pos] + runnable + s[pos:]

# Inicia o watcher de envio pendente junto dos demais watchers.
old_connect = '''        handler.removeCallbacks(closedGroupWatchRunnable)
        handler.postDelayed(closedGroupWatchRunnable, CLOSED_GROUP_WATCH_INTERVAL_MS)
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
new_connect = '''        handler.removeCallbacks(closedGroupWatchRunnable)
        handler.postDelayed(closedGroupWatchRunnable, CLOSED_GROUP_WATCH_INTERVAL_MS)
        handler.removeCallbacks(pendingRouteSendWatchRunnable)
        handler.postDelayed(pendingRouteSendWatchRunnable, PENDING_ROUTE_SEND_WATCH_MS)
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
if old_connect not in s:
    raise SystemExit('patch_v19_admin_locked_group: bloco onServiceConnected do watcher nao encontrado')
s = s.replace(old_connect, new_connect, 1)

# Um grupo bloqueado continua sendo uma conversa valida para ANALISAR a rota.
# So nao ha editor para enviar naquele momento.
old_analyze = '''        // So trabalha dentro de uma conversa normal. Na lista inicial do
        // WhatsApp nao existe o editor de mensagem da conversa.
        if (findMessageEditor(items) == null) {
            previousTexts = textSignatures(items)
            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
            primed = true
            return
        }
'''
new_analyze = '''        // Uma conversa normal tem editor. Quando o admin bloqueia o grupo,
        // o editor some, mas o proprio WhatsApp mostra o aviso de que somente
        // admins podem enviar. Nesse caso CONTINUAMOS lendo as rotas recebidas.
        val messageEditorAvailable = findMessageEditor(items) != null
        val adminLockedGroup = isAdminLockedGroup(items)

        if (!messageEditorAvailable && !adminLockedGroup) {
            previousTexts = textSignatures(items)
            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
            primed = true
            return
        }
'''
if old_analyze not in s:
    raise SystemExit('patch_v19_admin_locked_group: bloqueio de analyzeCurrentWindow nao encontrado')
s = s.replace(old_analyze, new_analyze, 1)

# Se ja ha uma rota aguardando o grupo ser liberado, nao continua procurando e
# nao corre o risco de substituir a rota pendente por outra.
old_event = '''        if (!processing && pendingRoute != null) {
            if (trySendPendingRouteIfChatOpen()) return
        }

        // Depois de um envio confirmado, o bot fica PARADO indefinidamente.
'''
new_event = '''        if (!processing && pendingRoute != null) {
            trySendPendingRouteIfChatOpen()
            return
        }

        // Depois de um envio confirmado, o bot fica PARADO indefinidamente.
'''
if old_event not in s:
    raise SystemExit('patch_v19_admin_locked_group: bloco pendingRoute do evento nao encontrado')
s = s.replace(old_event, new_event, 1)

# Status mais claro quando a rota foi lida, mas o grupo esta bloqueado pelo admin.
old_hold_status = '''            "Rota pronta: ${route.neighborhood} -> ${route.cage}. " +
                "$reason Abra uma conversa/grupo do WhatsApp e eu envio automaticamente."
'''
new_hold_status = '''            "Rota pronta: ${route.neighborhood} -> ${route.cage}. " +
                "$reason Aguardando o campo de mensagem ser liberado; envio automatico assim que aparecer."
'''
if old_hold_status in s:
    s = s.replace(old_hold_status, new_hold_status, 1)

# Para o watcher adicional junto dos demais.
old_destroy = '''        handler.removeCallbacks(keepOcrWarmRunnable)
        handler.removeCallbacks(closedGroupWatchRunnable)
        recognizer.close()
'''
new_destroy = '''        handler.removeCallbacks(keepOcrWarmRunnable)
        handler.removeCallbacks(closedGroupWatchRunnable)
        handler.removeCallbacks(pendingRouteSendWatchRunnable)
        recognizer.close()
'''
if old_destroy not in s:
    raise SystemExit('patch_v19_admin_locked_group: onDestroy dos watchers nao encontrado')
s = s.replace(old_destroy, new_destroy, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 ADMIN LOCK aplicado: le rota com grupo bloqueado e envia assim que admin liberar")
