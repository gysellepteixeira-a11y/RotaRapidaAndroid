from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - GRUPO FECHADO PELO ADMIN
#
# Aqui "fechado" significa: a conversa continua aberta e recebendo mensagens,
# mas o WhatsApp remove o campo de digitacao porque somente admins podem enviar.
#
# Comportamento desejado:
# - enquanto o grupo estiver fechado pelo admin, continua lendo rota de TEXTO e IMAGEM;
# - achou a rota: guarda em pendingRoute e para de procurar outra;
# - quando o admin liberar o grupo e o campo de mensagem reaparecer, envia imediatamente;
# - nao depende de nome de grupo configurado;
# - nao usa watcher global de MediaStore fora da conversa.

const_anchor = '        private const val KEEP_OCR_WARM_INTERVAL_MS = 15_000L\n'
if 'PENDING_ROUTE_SEND_WATCH_MS' not in s:
    if const_anchor not in s:
        raise SystemExit('patch_v19_admin_locked_group: KEEP_OCR_WARM_INTERVAL_MS nao encontrada')
    s = s.replace(
        const_anchor,
        const_anchor + '        private const val PENDING_ROUTE_SEND_WATCH_MS = 120L\n',
        1
    )

# Reconhece a faixa que o WhatsApp mostra quando somente admins podem enviar.
# RouteParser.normalize remove acentos/variacoes simples.
helper_anchor = '    private fun keepOcrEngineWarm() {\n'
if 'private fun isAdminLockedGroup(' not in s:
    if helper_anchor not in s:
        raise SystemExit('patch_v19_admin_locked_group: keepOcrEngineWarm nao encontrado')

    helper = r'''    private fun isAdminLockedGroup(items: List<NodeItem>): Boolean {
        return items.any { item ->
            val t = RouteParser.normalize(item.text)
            if (t.isBlank()) return@any false

            val admin =
                t.contains("admin") ||
                t.contains("administrador")

            val restrictive =
                t.contains("somente") ||
                t.contains("apenas") ||
                t.contains("so admin") ||
                t.contains("so os admin") ||
                t.contains("only admin")

            val sendMessage =
                t.contains("enviar") ||
                t.contains("mensagem") ||
                t.contains("send") ||
                t.contains("message")

            admin && restrictive && sendMessage
        }
    }

'''
    s = s.replace(helper_anchor, helper + helper_anchor, 1)

# Rota pendente: verifica rapidamente se o campo voltou a existir.
# Assim nao dependemos de o WhatsApp gerar um evento exatamente quando o admin
# troca a permissao do grupo.
on_service_anchor = '\n    override fun onServiceConnected() {'
if 'pendingRouteSendWatchRunnable' not in s:
    pos = s.find(on_service_anchor)
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
                // Nunca perde pendingRoute por causa do watcher.
            } finally {
                handler.postDelayed(this, PENDING_ROUTE_SEND_WATCH_MS)
            }
        }
    }
'''
    s = s[:pos] + runnable + s[pos:]

# Inicia o watcher de pendingRoute junto do aquecimento de OCR.
old_connect = '''        warmUpRecognizer()
        handler.removeCallbacks(keepOcrWarmRunnable)
        handler.postDelayed(keepOcrWarmRunnable, KEEP_OCR_WARM_INTERVAL_MS)
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
new_connect = '''        warmUpRecognizer()
        handler.removeCallbacks(keepOcrWarmRunnable)
        handler.postDelayed(keepOcrWarmRunnable, KEEP_OCR_WARM_INTERVAL_MS)
        handler.removeCallbacks(pendingRouteSendWatchRunnable)
        handler.postDelayed(pendingRouteSendWatchRunnable, PENDING_ROUTE_SEND_WATCH_MS)
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
if old_connect not in s:
    raise SystemExit('patch_v19_admin_locked_group: bloco onServiceConnected aquecido nao encontrado')
s = s.replace(old_connect, new_connect, 1)

# patch_v19_any_group considera conversa valida apenas quando existe editor.
# Para grupo fechado pelo admin isso e errado: o editor some, mas as mensagens
# continuam chegando. Nesse caso deixamos analyzeCurrentWindow seguir normalmente.
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
new_analyze = '''        // Conversa normal: tem editor. Grupo fechado pelo admin: nao tem editor,
        // mas exibe a faixa dizendo que somente admins podem enviar. Nos dois casos
        // a tela e uma conversa valida e deve continuar lendo TEXTO e IMAGEM.
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
    raise SystemExit('patch_v19_admin_locked_group: bloco inicial de analyzeCurrentWindow nao encontrado')
s = s.replace(old_analyze, new_analyze, 1)

# Se uma rota ja foi lida no grupo fechado, ela tem prioridade absoluta.
# Enquanto espera o admin liberar, nao tenta ler/substituir por outra rota.
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
    raise SystemExit('patch_v19_admin_locked_group: pendingRoute em onAccessibilityEvent nao encontrado')
s = s.replace(old_event, new_event, 1)

# Mensagem de estado coerente com grupo bloqueado pelo admin.
old_hold = '''            "Rota pronta: ${route.neighborhood} -> ${route.cage}. " +
                "$reason Abra uma conversa/grupo do WhatsApp e eu envio automaticamente."
'''
new_hold = '''            "Rota pronta: ${route.neighborhood} -> ${route.cage}. " +
                "$reason Aguardando o admin liberar o envio; assim que o campo aparecer, envio automaticamente."
'''
if old_hold in s:
    s = s.replace(old_hold, new_hold, 1)

# Desliga watcher ao destruir o servico.
old_destroy = '''    override fun onDestroy() {
        handler.removeCallbacks(keepOcrWarmRunnable)
        recognizer.close()
        super.onDestroy()
    }
'''
new_destroy = '''    override fun onDestroy() {
        handler.removeCallbacks(keepOcrWarmRunnable)
        handler.removeCallbacks(pendingRouteSendWatchRunnable)
        recognizer.close()
        super.onDestroy()
    }
'''
if old_destroy not in s:
    raise SystemExit('patch_v19_admin_locked_group: onDestroy da versao aquecida nao encontrado')
s = s.replace(old_destroy, new_destroy, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 ADMIN LOCK aplicado: le texto/imagem com grupo fechado pelo admin e envia ao liberar")
