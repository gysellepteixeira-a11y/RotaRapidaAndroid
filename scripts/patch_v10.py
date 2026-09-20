from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.10: a v0.9 podia ficar esperando estabilidade para sempre porque o WhatsApp
# recria/animava a miniatura. Guardamos o retangulo original e fazemos um toque
# por coordenada depois de um atraso curto e fixo, sem precisar reencontrar o no.
image_section = s.find('// ---------------- IMAGEM ----------------')
start = s.find('        if (candidate != null) {', image_section)
end = s.find('\n    }\n\n    private fun waitForImageDownloadAndOpen', start)
if start < 0 or end < 0:
    raise SystemExit('Patch v0.10: bloco candidate pos-v0.9 nao encontrado')

new_candidate = '''        if (candidate != null) {
            currentStartedAt = SystemClock.elapsedRealtime()
            processing = true

            val savedRect = Rect(candidate.rect)
            val savedFingerprint = imageFingerprint(candidate)

            Prefs.setStatus(
                this,
                "Imagem recebida. Aguardando 700 ms para carregar..."
            )

            handler.postDelayed(
                {
                    openImageFromSavedRect(
                        savedRect,
                        savedFingerprint
                    )
                },
                700L
            )
            return
        }
'''

s = s[:start] + new_candidate + s[end:]

insert_at = s.find('    private fun waitForImageDownloadAndOpen(')
if insert_at < 0:
    raise SystemExit('Patch v0.10: helper de espera nao encontrado')

helper = '''    private fun openImageFromSavedRect(
        targetRect: Rect,
        fingerprint: String
    ) {
        if (!processing) return

        val root = rootInActiveWindow
        if (root == null) {
            processing = false
            Prefs.setStatus(this, "Nao consegui acessar o WhatsApp para abrir a imagem.")
            return
        }

        val items = collectNodeItems(root)
        val group = Prefs.groupName(this)
        if (group.isNotBlank() && !isTargetGroup(items, group)) {
            processing = false
            Prefs.setStatus(this, "O grupo nao esta mais aberto.")
            return
        }

        val screenWidth = resources.displayMetrics.widthPixels
        val screenHeight = resources.displayMetrics.heightPixels

        val tapX = targetRect.centerX().coerceIn(8, screenWidth - 8)
        val tapY = (targetRect.top + (targetRect.height() * 0.42f)).toInt()
            .coerceIn(
                (screenHeight * 0.14).toInt(),
                (screenHeight * 0.88).toInt()
            )

        val path = Path().apply {
            moveTo(tapX.toFloat(), tapY.toFloat())
        }

        val gesture = GestureDescription.Builder()
            .addStroke(
                GestureDescription.StrokeDescription(
                    path,
                    0L,
                    45L
                )
            )
            .build()

        lastOpenedImageFingerprint = fingerprint
        lastOpenedImageAt = SystemClock.elapsedRealtime()

        Prefs.setStatus(this, "Imagem carregada. Abrindo...")

        val accepted = dispatchGesture(
            gesture,
            object : GestureResultCallback() {
                override fun onCompleted(gestureDescription: GestureDescription?) {
                    handler.postDelayed(
                        { verifyImageViewerAndRead(attempt = 0) },
                        IMAGE_OPEN_DELAY_MS + 80L
                    )
                }

                override fun onCancelled(gestureDescription: GestureDescription?) {
                    processing = false
                    Prefs.setStatus(
                        this@WhatsRouteAccessibilityService,
                        "O toque para abrir a imagem foi cancelado."
                    )
                }
            },
            null
        )

        if (!accepted) {
            processing = false
            Prefs.setStatus(this, "O Android nao aceitou o toque na imagem.")
        }
    }

'''

s = s[:insert_at] + helper + s[insert_at:]
service_path.write_text(s, encoding="utf-8")
print("Patch v0.10 aplicado: espera 700 ms e abre pela coordenada salva da miniatura")
