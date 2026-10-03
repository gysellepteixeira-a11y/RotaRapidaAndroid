from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
P = Path('app/src/main/java/com/gy/rotarapida/Prefs.kt')
s = S.read_text(encoding='utf-8')
p = P.read_text(encoding='utf-8')

required_service = [
    'private var tdCandidate=0L',
    'private fun tdBegin(',
    'private const val DIRECT_MEDIASTORE_WATCH_MS = 10L',
    'private const val PENDING_ROUTE_SEND_WATCH_MS = 10L',
    'private fun findAdminUltraSendNodeFast(',
]
for marker in required_service:
    if marker not in s:
        raise SystemExit('TEXT FIRST wrong base / missing service marker: ' + marker)
if 'MEDIA10 STATUSLEAN ADMIN ULTRA DIRECT FAST' not in p:
    raise SystemExit('TEXT FIRST wrong base / missing Prefs marker')

anchor = '''        val currentSignatures = textSignatures(items)
        val currentImageCandidates = findImageCandidates(items)
'''
if anchor not in s:
    raise SystemExit('TEXT FIRST anchor currentSignatures/imageCandidates not found')

insert = '''        val currentSignatures = textSignatures(items)

        // TEXT FIRST A/B: tenta somente a rota textual antes de qualquer
        // preparacao/fingerprint de imagem. Se nao houver rota textual, o fluxo
        // antigo continua exatamente abaixo, inclusive toda a logica de imagem.
        if (primed && Prefs.searchArmed(this)) {
            val tfNewItems = items.filter { item ->
                val signature = RouteParser.normalize(item.text)
                signature.isNotBlank() && signature !in previousTexts
            }

            if (tfNewItems.isNotEmpty()) {
                val tfScreenHeight = resources.displayMetrics.heightPixels
                val tfParseStart = SystemClock.elapsedRealtime()
                val tfRoute =
                    RouteParser.parseScreenTexts(
                        tfNewItems.map {
                            ScreenText(
                                text = it.text,
                                left = it.rect.left,
                                top = it.rect.top,
                                right = it.rect.right,
                                bottom = it.rect.bottom
                            )
                        },
                        tfScreenHeight
                    ) ?: RouteParser.parsePlainTexts(tfNewItems.map { it.text })
                val tfParseDone = SystemClock.elapsedRealtime()

                if (tfRoute != null && !isDuplicate(tfRoute)) {
                    previousTexts = currentSignatures
                    currentStartedAt = SystemClock.elapsedRealtime()
                    tdBegin(
                        if (tdCandidate > 0L) tdCandidate else tdAnalyzeLocal,
                        tdAnalyzeLocal,
                        tdCollectDoneLocal,
                        tdCollectLocal,
                        tfParseDone - tfParseStart,
                        currentStartedAt,
                        tfNewItems.size
                    )
                    processing = true
                    val tdSt = SystemClock.elapsedRealtime()
                    Prefs.setStatus(
                        this,
                        "Texto: ${tfRoute.neighborhood} -> ${tfRoute.cage}. Enviando..."
                    )
                    if (tdOn) {
                        tdStatusTexto += SystemClock.elapsedRealtime() - tdSt
                        tdStatusTextoDone = SystemClock.elapsedRealtime()
                    }
                    sendRouteInCurrentChat(tfRoute)
                    return
                }
            }
        }

        val currentImageCandidates = findImageCandidates(items)
'''

s = s.replace(anchor, insert, 1)
s = s.replace(
    '===== DIAGNOSTICO TEXTO v1 | OLD BASE =====',
    '===== DIAGNOSTICO TEXTO v2 | OLD BASE + TEXT FIRST ====='
)

S.write_text(s, encoding='utf-8')
print('TEXT FIRST A/B aplicado: texto antes do preparo de imagem; envio inalterado')
