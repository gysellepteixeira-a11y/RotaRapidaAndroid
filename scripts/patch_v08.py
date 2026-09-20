from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str):
    global s
    if old not in s:
        raise SystemExit(f"Patch v0.8: trecho nao encontrado: {label}")
    s = s.replace(old, new, 1)


replace_once(
    '        private const val IMAGE_REOPEN_COOLDOWN_MS = 15_000L\n',
    '        private const val IMAGE_REOPEN_COOLDOWN_MS = 15_000L\n'
    '        private const val IMAGE_MIN_DOWNLOAD_WAIT_MS = 450L\n'
    '        private const val IMAGE_DOWNLOAD_POLL_MS = 70L\n'
    '        private const val IMAGE_DOWNLOAD_TIMEOUT_MS = 8_000L\n',
    'constantes de espera do download',
)

image_section = s.find('// ---------------- IMAGEM ----------------')
start = s.find('        if (candidate != null) {', image_section)
end = s.find('\n    }\n\n    private fun inspectImageHint', start)
if start < 0 or end < 0:
    raise SystemExit('Patch v0.8: bloco candidate da imagem nao encontrado')

new_candidate = '''        if (candidate != null) {
            currentStartedAt = SystemClock.elapsedRealtime()
            processing = true

            Prefs.setStatus(
                this,
                "Imagem recebida. Aguardando terminar o download..."
            )

            waitForImageDownloadAndOpen(
                targetRect = Rect(candidate.rect),
                startedAt = currentStartedAt,
                stableChecks = 0
            )
            return
        }
'''

s = s[:start] + new_candidate + s[end:]

insert_at = s.find('    private fun inspectImageHint')
if insert_at < 0:
    raise SystemExit('Patch v0.8: ponto para helpers de download nao encontrado')

helpers = '''    private fun waitForImageDownloadAndOpen(
        targetRect: Rect,
        startedAt: Long,
        stableChecks: Int
    ) {
        if (!processing) return

        val now = SystemClock.elapsedRealtime()
        val elapsed = now - startedAt

        val root = rootInActiveWindow
        if (root == null) {
            if (elapsed < IMAGE_DOWNLOAD_TIMEOUT_MS) {
                handler.postDelayed(
                    {
                        waitForImageDownloadAndOpen(
                            targetRect,
                            startedAt,
                            stableChecks
                        )
                    },
                    IMAGE_DOWNLOAD_POLL_MS
                )
            } else {
                processing = false
                previousImageFingerprints = emptySet()
                Prefs.setStatus(this, "Nao consegui acompanhar o download da imagem.")
            }
            return
        }

        val items = collectNodeItems(root)
        val group = Prefs.groupName(this)

        if (group.isNotBlank() && !isTargetGroup(items, group)) {
            processing = false
            Prefs.setStatus(this, "Saiu do grupo antes de abrir a imagem.")
            return
        }

        val candidates = findImageCandidates(items)
        val candidate = candidates.minByOrNull { item ->
            abs(item.rect.centerX() - targetRect.centerX()) +
                abs(item.rect.centerY() - targetRect.centerY()) +
                abs(item.rect.width() - targetRect.width()) / 2 +
                abs(item.rect.height() - targetRect.height()) / 2
        }

        if (candidate == null) {
            if (elapsed < IMAGE_DOWNLOAD_TIMEOUT_MS) {
                handler.postDelayed(
                    {
                        waitForImageDownloadAndOpen(
                            targetRect,
                            startedAt,
                            0
                        )
                    },
                    IMAGE_DOWNLOAD_POLL_MS
                )
            } else {
                processing = false
                previousImageFingerprints = emptySet()
                Prefs.setStatus(this, "A miniatura sumiu antes de terminar o download.")
            }
            return
        }

        val sameRect =
            abs(candidate.rect.left - targetRect.left) <= 24 &&
            abs(candidate.rect.top - targetRect.top) <= 24 &&
            abs(candidate.rect.right - targetRect.right) <= 24 &&
            abs(candidate.rect.bottom - targetRect.bottom) <= 24

        val nextStable = if (sameRect) stableChecks + 1 else 0
        val pending = hasMediaDownloadIndicator(items, candidate.rect)

        val ready =
            !pending &&
            elapsed >= IMAGE_MIN_DOWNLOAD_WAIT_MS &&
            nextStable >= 3

        if (ready) {
            lastOpenedImageFingerprint = imageFingerprint(candidate)
            lastOpenedImageAt = SystemClock.elapsedRealtime()

            Prefs.setStatus(this, "Download pronto. Abrindo imagem...")

            if (clickImageCandidateSafely(candidate)) {
                handler.postDelayed(
                    { verifyImageViewerAndRead(attempt = 0) },
                    IMAGE_OPEN_DELAY_MS
                )
            } else {
                processing = false
                Prefs.setStatus(this, "Download pronto, mas nao consegui tocar na imagem.")
                handler.postDelayed({ primeCurrentScreen() }, 120L)
            }
            return
        }

        if (elapsed >= IMAGE_DOWNLOAD_TIMEOUT_MS) {
            processing = false
            previousImageFingerprints = emptySet()
            Prefs.setStatus(
                this,
                if (pending)
                    "A imagem ainda estava baixando; nao abri incompleta."
                else
                    "A imagem nao ficou estavel a tempo; vou aguardar novo evento."
            )
            return
        }

        if (pending) {
            Prefs.setStatus(this, "Imagem ainda baixando...")
        }

        handler.postDelayed(
            {
                waitForImageDownloadAndOpen(
                    Rect(candidate.rect),
                    startedAt,
                    nextStable
                )
            },
            IMAGE_DOWNLOAD_POLL_MS
        )
    }

    private fun hasMediaDownloadIndicator(
        items: List<NodeItem>,
        imageRect: Rect
    ): Boolean {
        val margin = 36
        val region = Rect(
            imageRect.left - margin,
            imageRect.top - margin,
            imageRect.right + margin,
            imageRect.bottom + margin
        )

        val pendingWords = listOf(
            "baixar",
            "baixando",
            "download",
            "downloading",
            "carregando",
            "loading",
            "tentar novamente",
            "retry"
        )

        return items.any { item ->
            val overlaps =
                item.rect.left < region.right &&
                item.rect.right > region.left &&
                item.rect.top < region.bottom &&
                item.rect.bottom > region.top

            if (!overlaps) {
                false
            } else {
                val n = RouteParser.normalize(item.text)
                pendingWords.any { word -> n.contains(word) }
            }
        }
    }

'''

s = s[:insert_at] + helpers + s[insert_at:]
service_path.write_text(s, encoding="utf-8")

# -------- OCR DA GAIOLA --------
# O regex antigo tinha um fallback que aceitava letra+2 digitos DENTRO do AT/TO.
# Ex.: um final X23 podia ser confundido com gaiola. Agora a gaiola precisa ser
# um token isolado e a letra fica limitada ao intervalo usado pelas gaiolas.
parser_path = Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
r = parser_path.read_text(encoding="utf-8")

old_regex = '''    private val cageRegex =
        Regex("""(?<![A-Z0-9])([A-Z1])[-.\\s]?(\\d{2})(?!\\d)""")

    private val cageFallbackRegex =
        Regex("""([A-Z1])[-.\\s]?(\\d{2})(?!\\d)""")
'''
new_regex = '''    private val cageRegex =
        Regex("""(?<![A-Z0-9])([A-I1])[-.\\s]?(\\d{2})(?![A-Z0-9])""")
'''
if old_regex not in r:
    raise SystemExit('Patch v0.8: regex antigo da gaiola nao encontrado')
r = r.replace(old_regex, new_regex, 1)

old_match = '        val match = cageRegex.find(upper) ?: cageFallbackRegex.find(upper) ?: return null\n'
new_match = '        val match = cageRegex.find(upper) ?: return null\n'
if old_match not in r:
    raise SystemExit('Patch v0.8: fallback antigo da gaiola nao encontrado')
r = r.replace(old_match, new_match, 1)

parser_path.write_text(r, encoding="utf-8")

print("Patch v0.8 aplicado: espera download/estabilidade + gaiola isolada do AT/TO")
