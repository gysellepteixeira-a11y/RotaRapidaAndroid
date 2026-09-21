from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - WATCH MEDIASTORE COM GRUPO FECHADO
#
# Problema: quando nenhuma conversa do WhatsApp estava aberta, o AccessibilityService
# nao via a miniatura da nova imagem. Assim nao existia pendingRoute para enviar quando
# a pessoa abrisse o grupo depois.
#
# Solucao: enquanto PROCURAR ROTA estiver armado, consulta somente o MediaStore do
# WhatsApp em intervalo curto. Se surgir uma imagem nova, usa exatamente o MESMO fluxo
# OCR da v0.19 (incluindo crop denso). Se encontrar rota sem conversa aberta,
# sendRouteInCurrentChat() ja a guarda em pendingRoute. Ao abrir qualquer conversa,
# o fluxo existente envia automaticamente.

const_anchor = '        private const val KEEP_OCR_WARM_INTERVAL_MS = 15_000L\n'
if 'CLOSED_GROUP_WATCH_INTERVAL_MS' not in s:
    if const_anchor not in s:
        raise SystemExit('patch_v19_closed_group_watch: constante KEEP_OCR_WARM_INTERVAL_MS nao encontrada')
    s = s.replace(
        const_anchor,
        const_anchor +
        '        private const val CLOSED_GROUP_WATCH_INTERVAL_MS = 350L\n'
        '        private const val CLOSED_GROUP_READ_DELAY_MS = 90L\n',
        1
    )

# Estado/runnable inseridos depois do runnable de aquecimento.
anchor = '''    private val keepOcrWarmRunnable = object : Runnable {
'''
start = s.find(anchor)
if start < 0:
    raise SystemExit('patch_v19_closed_group_watch: keepOcrWarmRunnable nao encontrado')

# acha o final do objeto Runnable por ancora seguinte do codigo atual
end_anchor = '\n    override fun onServiceConnected() {'
end = s.find(end_anchor, start)
if end < 0:
    raise SystemExit('patch_v19_closed_group_watch: onServiceConnected nao encontrado')

if 'closedGroupWatchRunnable' not in s:
    watcher = r'''

    private val closedGroupWatchRunnable = object : Runnable {
        override fun run() {
            try {
                if (
                    Prefs.isEnabled(this@WhatsRouteAccessibilityService) &&
                    Prefs.searchArmed(this@WhatsRouteAccessibilityService) &&
                    !processing &&
                    pendingRoute == null &&
                    hasImageReadPermission()
                ) {
                    checkForWhatsAppImageWhileChatClosed()
                }
            } catch (_: Throwable) {
                // O watcher nunca pode derrubar o service.
            } finally {
                handler.postDelayed(this, CLOSED_GROUP_WATCH_INTERVAL_MS)
            }
        }
    }
'''
    s = s[:end] + watcher + s[end:]

# Inicia watcher junto do aquecimento.
old_connect = '''        warmUpRecognizer()
        handler.removeCallbacks(keepOcrWarmRunnable)
        handler.postDelayed(keepOcrWarmRunnable, KEEP_OCR_WARM_INTERVAL_MS)
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
new_connect = '''        warmUpRecognizer()
        handler.removeCallbacks(keepOcrWarmRunnable)
        handler.postDelayed(keepOcrWarmRunnable, KEEP_OCR_WARM_INTERVAL_MS)
        handler.removeCallbacks(closedGroupWatchRunnable)
        handler.postDelayed(closedGroupWatchRunnable, CLOSED_GROUP_WATCH_INTERVAL_MS)
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
if old_connect not in s:
    raise SystemExit('patch_v19_closed_group_watch: bloco onServiceConnected aquecido nao encontrado')
s = s.replace(old_connect, new_connect, 1)

# Funcao que observa o MediaStore sem depender de evento/tela do WhatsApp.
# Reaproveita findNewestWhatsAppImage e readMediaOriginal, portanto nao muda OCR.
insert_anchor = '    private fun keepOcrEngineWarm() {\n'
if 'private fun checkForWhatsAppImageWhileChatClosed()' not in s:
    if insert_anchor not in s:
        raise SystemExit('patch_v19_closed_group_watch: keepOcrEngineWarm nao encontrado')

    helper = r'''    private fun checkForWhatsAppImageWhileChatClosed() {
        if (
            processing ||
            pendingRoute != null ||
            !Prefs.searchArmed(this) ||
            !Prefs.isEnabled(this)
        ) return

        // A busca existente considera apenas arquivos adicionados perto deste horario.
        // Como este watcher roda continuamente, uma imagem velha nunca vira rota nova.
        currentImageWallTimeMs = System.currentTimeMillis()
        val media = findNewestWhatsAppImage() ?: return

        // Marca imediatamente para nenhum evento de acessibilidade processar o mesmo
        // arquivo em paralelo.
        lastMediaImageId = media.id
        processing = true
        currentStartedAt = SystemClock.elapsedRealtime()

        Prefs.setStatus(
            this,
            "Imagem nova detectada pelos arquivos do WhatsApp. OCR..."
        )

        handler.postDelayed(
            {
                if (!processing) return@postDelayed
                readMediaOriginal(media)
            },
            CLOSED_GROUP_READ_DELAY_MS
        )
    }

'''
    s = s.replace(insert_anchor, helper + insert_anchor, 1)

# Para watcher ao destruir o service.
old_destroy = '''    override fun onDestroy() {
        handler.removeCallbacks(keepOcrWarmRunnable)
        recognizer.close()
        super.onDestroy()
    }
'''
new_destroy = '''    override fun onDestroy() {
        handler.removeCallbacks(keepOcrWarmRunnable)
        handler.removeCallbacks(closedGroupWatchRunnable)
        recognizer.close()
        super.onDestroy()
    }
'''
if old_destroy not in s:
    raise SystemExit('patch_v19_closed_group_watch: onDestroy da versao aquecida nao encontrado')
s = s.replace(old_destroy, new_destroy, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 CLOSED GROUP WATCH aplicado: rota e lida pelo MediaStore mesmo sem grupo aberto")
