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
        raise SystemExit('TEXT FAST SIGNATURE wrong base / missing service marker: ' + marker)
if 'MEDIA10 STATUSLEAN ADMIN ULTRA DIRECT FAST' not in p:
    raise SystemExit('TEXT FAST SIGNATURE wrong base / missing Prefs marker')

anchor = '''        val currentSignatures = textSignatures(items)
        val currentImageCandidates = findImageCandidates(items)
'''
if anchor not in s:
    raise SystemExit('TEXT FAST SIGNATURE anchor currentSignatures/imageCandidates not found')

insert = '''        // TEXT FIRST + FAST SIGNATURE A/B:
        // normaliza cada texto apenas UMA vez e, na mesma passagem, monta
        // currentSignatures + tfNewItems. Antes o caminho textual normalizava
        // todos os itens em textSignatures() e depois normalizava tudo de novo
        // no filter de newItems.
        val currentSignatures = LinkedHashSet<String>(items.size)
        val tfNewItems = ArrayList<NodeItem>(8)
        for (item in items) {
            val signature = RouteParser.normalize(item.text)
            if (signature.isBlank()) continue
            currentSignatures.add(signature)
            if (primed && signature !in previousTexts) {
                tfNewItems.add(item)
            }
        }

        // Tenta a rota textual antes de qualquer preparo/fingerprint de imagem.
        // Se nao houver rota textual valida, o fluxo antigo de imagem continua
        // exatamente abaixo.
        if (primed && Prefs.searchArmed(this) && tfNewItems.isNotEmpty()) {
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

        val currentImageCandidates = findImageCandidates(items)
'''

s = s.replace(anchor, insert, 1)

old_header = '===== DIAGNOSTICO TEXTO v1 | OLD BASE ====='
new_header = '===== DIAGNOSTICO TEXTO v3 | OLD BASE + TEXT FIRST + FAST SIGNATURE ====='
if old_header not in s:
    raise SystemExit('TEXT FAST SIGNATURE diagnostic header v1 not found')
s = s.replace(old_header, new_header, 1)

checks = [
    'val currentSignatures = LinkedHashSet<String>(items.size)',
    'val tfNewItems = ArrayList<NodeItem>(8)',
    new_header,
]
for marker in checks:
    if marker not in s:
        raise SystemExit('TEXT FAST SIGNATURE verification failed: ' + marker)

S.write_text(s, encoding='utf-8')
print('TEXT FIRST + FAST SIGNATURE aplicado: uma normalizacao por item; envio inalterado')

import runpy

# v4: successful text routes use a cheap exact-text delta and skip global normalization.
runpy.run_path('scripts/patch_v19_text_raw_delta_v4.py', run_name='__main__')

# v5: direct named Enviar/Send lookup every 4ms for text routes.
runpy.run_path('scripts/patch_v19_text_direct_send_v5.py', run_name='__main__')

# v6: scan only the newest tail of the chat before the parser.
runpy.run_path('scripts/patch_v19_text_tail_delta_v6.py', run_name='__main__')

# v7: keep the same v6 tail/parser/direct-send behavior, but stop copying the
# entire raw baseline before sending; add only the new keys in-place.
runpy.run_path('scripts/patch_v19_text_mutable_baseline_v7.py', run_name='__main__')
