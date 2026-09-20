from pathlib import Path

p = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = p.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str):
    global s
    if old not in s:
        raise SystemExit(f"Patch v0.7: trecho nao encontrado: {label}")
    s = s.replace(old, new, 1)


replace_once(
    '        private const val DEDUP_MS = 8_000L\n',
    '        private const val DEDUP_MS = 8_000L\n'
    '        private const val IMAGE_REOPEN_COOLDOWN_MS = 15_000L\n',
    'constante cooldown',
)

replace_once(
    '    private var imageHintUntil = 0L\n\n'
    '    private var lastSentSignature',
    '    private var imageHintUntil = 0L\n'
    '    private var lastOpenedImageFingerprint = ""\n'
    '    private var lastOpenedImageAt = 0L\n\n'
    '    private var lastSentSignature',
    'estado da ultima imagem',
)

replace_once(
    '''        val newImageCandidates = currentImageCandidates.filter { candidate ->
            imageFingerprint(candidate) !in previousImageFingerprints
        }
''',
    '''        val imageNow = SystemClock.elapsedRealtime()
        val newImageCandidates = currentImageCandidates.filter { candidate ->
            val fp = imageFingerprint(candidate)
            val isNew = fp !in previousImageFingerprints
            val wasJustOpened =
                fp == lastOpenedImageFingerprint &&
                imageNow - lastOpenedImageAt < IMAGE_REOPEN_COOLDOWN_MS

            isNew && !wasJustOpened
        }
''',
    'filtro de imagens novas',
)

replace_once(
    '''        if (candidate != null) {
            currentStartedAt = SystemClock.elapsedRealtime()
            processing = true

            val hintAtivo = SystemClock.elapsedRealtime() <= imageHintUntil
''',
    '''        if (candidate != null) {
            currentStartedAt = SystemClock.elapsedRealtime()
            processing = true
            lastOpenedImageFingerprint = imageFingerprint(candidate)
            lastOpenedImageAt = currentStartedAt

            val hintAtivo = SystemClock.elapsedRealtime() <= imageHintUntil
''',
    'marcar imagem aberta',
)

start = s.find('    private fun verifyImageViewerAndRead(attempt: Int) {')
end_marker = '\n\n    private fun captureAndReadImage(attempt: Int) {'
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('Patch v0.7: funcao verifyImageViewerAndRead nao encontrada')

new_verify = '''    private fun verifyImageViewerAndRead(
        attempt: Int,
        verifyTry: Int = 0
    ) {
        if (!processing) return

        val root = rootInActiveWindow
        if (root == null) {
            if (verifyTry < 4) {
                handler.postDelayed(
                    { verifyImageViewerAndRead(attempt, verifyTry + 1) },
                    80L
                )
            } else {
                processing = false
                Prefs.setStatus(this, "Nao consegui confirmar a tela da imagem.")
            }
            return
        }

        val items = collectNodeItems(root)
        val group = Prefs.groupName(this)

        // v0.7: o visualizador de midia do WhatsApp no M52 pode expor
        // um EditText proprio. Por isso EditText nao serve para decidir
        // se a imagem abriu. Confirmamos pela ausencia do grupo-alvo.
        val stillInTargetGroup =
            group.isNotBlank() && isTargetGroup(items, group)

        if (stillInTargetGroup) {
            if (verifyTry < 4) {
                handler.postDelayed(
                    { verifyImageViewerAndRead(attempt, verifyTry + 1) },
                    80L
                )
            } else {
                processing = false
                Prefs.setStatus(
                    this,
                    "O toque foi feito, mas o visualizador nao abriu."
                )
                handler.postDelayed({ primeCurrentScreen() }, 120L)
            }
            return
        }

        Prefs.setStatus(this, "Visualizador confirmado. Iniciando OCR...")
        handler.postDelayed(
            { captureAndReadImage(attempt) },
            60L
        )
    }
'''

s = s[:start] + new_verify + s[end:]

replace_once(
    '''    private fun backOnlyIfImageViewerOpen() {
        val root = rootInActiveWindow ?: return
        val items = collectNodeItems(root)

        // Se o campo de mensagem ainda existe, continuamos no grupo.
        // Nesse caso NAO VOLTA.
        if (findMessageEditor(items) != null) {
            return
        }

        performGlobalAction(GLOBAL_ACTION_BACK)
    }
'''.replace('NAO VOLTA', 'NÃO VOLTA'),
    '''    private fun backOnlyIfImageViewerOpen() {
        val root = rootInActiveWindow ?: return
        val items = collectNodeItems(root)
        val group = Prefs.groupName(this)

        // Se o cabecalho do grupo-alvo esta visivel, ja estamos no chat.
        // Nao usa EditText como teste porque o visualizador do WhatsApp
        // no M52 tambem pode expor um campo editavel.
        if (group.isNotBlank() && isTargetGroup(items, group)) {
            return
        }

        performGlobalAction(GLOBAL_ACTION_BACK)
    }
''',
    'retorno seguro da imagem',
)

p.write_text(s, encoding="utf-8")
print("Patch v0.7 aplicado ao APK: viewer por cabecalho do grupo + cooldown de reabertura")
