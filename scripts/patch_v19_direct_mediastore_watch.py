from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - DIRECT MEDIASTORE WATCH
#
# Problema observado no WhatsApp: quando existem muitos avisos de sistema do tipo
# "mudou as configuracoes do grupo...", a arvore de acessibilidade fica cheia de
# containers grandes. Mesmo filtrando esses avisos, o detector visual de miniatura
# continua podendo ficar inconsistente.
#
# A v0.19 ja le a FOTO pelo arquivo original do MediaStore. Portanto nao precisamos
# depender de reconhecer a miniatura na arvore do WhatsApp para disparar o OCR.
#
# Esta correcao:
# - enquanto PROCURAR ROTA estiver armado e a tela for uma conversa valida,
#   consulta o MediaStore a cada 100 ms;
# - achou um arquivo novo do WhatsApp: usa exatamente readMediaOriginal() da v0.19;
# - funciona com conversa normal e com grupo fechado pelo admin;
# - desativa SOMENTE o gatilho visual de miniatura, que era a parte contaminada
#   pelos avisos de configuracao;
# - texto continua pelo fluxo de acessibilidade normal;
# - OCR, parser, prioridade, crop denso e envio nao sao alterados.

const_anchor = '        private const val PENDING_ROUTE_SEND_WATCH_MS = 120L\n'
if 'DIRECT_MEDIASTORE_WATCH_MS' not in s:
    if const_anchor not in s:
        raise SystemExit('patch_v19_direct_mediastore_watch: PENDING_ROUTE_SEND_WATCH_MS nao encontrada')
    s = s.replace(
        const_anchor,
        const_anchor + '        private const val DIRECT_MEDIASTORE_WATCH_MS = 100L\n',
        1
    )

# Runnable independente da deteccao visual de miniatura.
on_service_anchor = '\n    override fun onServiceConnected() {'
if 'directMediaStoreWatchRunnable' not in s:
    pos = s.find(on_service_anchor)
    if pos < 0:
        raise SystemExit('patch_v19_direct_mediastore_watch: onServiceConnected nao encontrado')

    runnable = r'''

    private val directMediaStoreWatchRunnable = object : Runnable {
        override fun run() {
            try {
                checkDirectMediaStoreImage()
            } catch (_: Throwable) {
                // O watcher nunca pode derrubar o AccessibilityService.
            } finally {
                handler.postDelayed(this, DIRECT_MEDIASTORE_WATCH_MS)
            }
        }
    }
'''
    s = s[:pos] + runnable + s[pos:]

# Inicia junto dos watchers ja existentes.
connect_anchor = '''        handler.removeCallbacks(pendingRouteSendWatchRunnable)
        handler.postDelayed(pendingRouteSendWatchRunnable, PENDING_ROUTE_SEND_WATCH_MS)
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
connect_new = '''        handler.removeCallbacks(pendingRouteSendWatchRunnable)
        handler.postDelayed(pendingRouteSendWatchRunnable, PENDING_ROUTE_SEND_WATCH_MS)
        handler.removeCallbacks(directMediaStoreWatchRunnable)
        handler.postDelayed(directMediaStoreWatchRunnable, 80L)
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
if connect_anchor not in s:
    raise SystemExit('patch_v19_direct_mediastore_watch: bloco de inicio dos watchers nao encontrado')
s = s.replace(connect_anchor, connect_new, 1)

# Helper direto. Usa os mesmos findNewestWhatsAppImage/readMediaOriginal da v0.19.
helper_anchor = '    private fun keepOcrEngineWarm() {\n'
if 'private fun checkDirectMediaStoreImage()' not in s:
    if helper_anchor not in s:
        raise SystemExit('patch_v19_direct_mediastore_watch: keepOcrEngineWarm nao encontrado')

    helper = r'''    private fun checkDirectMediaStoreImage() {
        if (
            !Prefs.isEnabled(this) ||
            !Prefs.searchArmed(this) ||
            processing ||
            pendingRoute != null ||
            alertSequenceRunning ||
            !hasImageReadPermission()
        ) return

        val root = rootInActiveWindow ?: return
        val items = collectNodeItems(root)

        // Conversa comum: editor presente.
        // Grupo fechado pelo admin: editor ausente, mas o detector/sticky de admin
        // identifica que ainda estamos dentro da conversa recebendo mensagens.
        val editorAvailable = findMessageEditor(items) != null
        val adminLockedNow = isAdminLockedGroup(items)

        if (editorAvailable) {
            adminLockedConversationActive = false
        } else if (adminLockedNow) {
            adminLockedConversationActive = true
        }

        if (!editorAvailable && !adminLockedConversationActive) return

        // A janela de findNewestWhatsAppImage e curta de proposito. Atualizando o
        // horario em cada tick, pegamos somente arquivo realmente recente.
        currentImageWallTimeMs = System.currentTimeMillis()
        val media = findNewestWhatsAppImage() ?: return

        // Reserva o arquivo antes de iniciar OCR para nenhum outro evento pegar o
        // mesmo ID em paralelo.
        lastMediaImageId = media.id
        currentStartedAt = SystemClock.elapsedRealtime()
        processing = true
        analyzeScheduled = false

        Prefs.setStatus(
            this,
            "Imagem nova detectada direto nos arquivos do WhatsApp. OCR v0.19..."
        )

        readMediaOriginal(media)
    }

'''
    s = s.replace(helper_anchor, helper + helper_anchor, 1)

# Desativa o gatilho VISUAL de miniatura. A foto agora e disparada exclusivamente
# pelo arquivo novo no MediaStore, portanto mensagens de sistema/containers nao
# conseguem mais tomar o lugar da rota.
start = s.find('        val candidate = newImageCandidates.maxWithOrNull(')
end_marker = '\n\n        // Atualiza a referência ANTES de qualquer clique.'
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit(
        f'patch_v19_direct_mediastore_watch: bloco candidate nao encontrado (start={start}, end={end})'
    )

s = s[:start] + '        val candidate: NodeItem? = null\n' + s[end:]

# Para o watcher no destroy.
destroy_anchor = '''        handler.removeCallbacks(keepOcrWarmRunnable)
        handler.removeCallbacks(pendingRouteSendWatchRunnable)
        recognizer.close()
'''
destroy_new = '''        handler.removeCallbacks(keepOcrWarmRunnable)
        handler.removeCallbacks(pendingRouteSendWatchRunnable)
        handler.removeCallbacks(directMediaStoreWatchRunnable)
        recognizer.close()
'''
if destroy_anchor not in s:
    raise SystemExit('patch_v19_direct_mediastore_watch: onDestroy nao encontrado')
s = s.replace(destroy_anchor, destroy_new, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 DIRECT MEDIASTORE WATCH aplicado: imagem nao depende mais da arvore visual do WhatsApp")
