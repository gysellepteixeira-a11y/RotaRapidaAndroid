from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s = S.read_text(encoding='utf-8')

# This patch must run only after v3 TEXT FIRST + FAST SIGNATURE.
required = [
    '===== DIAGNOSTICO TEXTO v3 | OLD BASE + TEXT FIRST + FAST SIGNATURE =====',
    'val currentSignatures = LinkedHashSet<String>(items.size)',
    'val tfNewItems = ArrayList<NodeItem>(8)',
    'private var previousTexts: Set<String> = emptySet()',
]
for marker in required:
    if marker not in s:
        raise SystemExit('TEXT RAW DELTA v4 wrong base / missing marker: ' + marker)

# Keep a cheap exact-text baseline only for the TEXT-FIRST fast path.
# The original normalized previousTexts remains untouched for fallback/image behavior.
s = s.replace(
    '    private var previousTexts: Set<String> = emptySet()\n',
    '    private var previousTexts: Set<String> = emptySet()\n'
    '    private var previousFastTexts: Set<String> = emptySet()\n',
    1
)

# Whenever the old code establishes a fresh baseline, establish the cheap raw baseline too.
# These are non-critical priming / outside-chat paths, so allocation here does not affect the race.
old_baseline = '        previousTexts = textSignatures(items)\n'
count = s.count(old_baseline)
if count < 2:
    raise SystemExit(f'TEXT RAW DELTA v4 expected >=2 baseline assignments, found {count}')
s = s.replace(
    old_baseline,
    old_baseline +
    '        previousFastTexts = items.asSequence()\n'
    '            .map { it.text }\n'
    '            .filter { it.isNotBlank() }\n'
    '            .toSet()\n'
)

old_loop = '''        // TEXT FIRST + FAST SIGNATURE A/B:
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
'''
new_loop = '''        // TEXT RAW DELTA v4 A/B:
        // No caminho de uma rota textual valida, NAO normaliza a arvore inteira.
        // Primeiro calcula o delta por texto cru/exato (barato) e entrega somente
        // os novos itens ao parser, que ja faz a normalizacao necessaria.
        // Se nao houver rota textual, o fluxo antigo calcula currentSignatures
        // normalmente logo abaixo antes de continuar para imagem.
        val currentFastTexts = LinkedHashSet<String>(items.size)
        val tfNewItems = ArrayList<NodeItem>(8)
        for (item in items) {
            val key = item.text
            if (key.isBlank()) continue
            currentFastTexts.add(key)
            if (primed && key !in previousFastTexts) {
                tfNewItems.add(item)
            }
        }

        // Tenta a rota textual antes de qualquer normalizacao global ou preparo de imagem.
'''
if old_loop not in s:
    raise SystemExit('TEXT RAW DELTA v4 hot-loop anchor not found')
s = s.replace(old_loop, new_loop, 1)

# Successful text route: update only the cheap baseline. Do not pay textSignatures() here.
old_success = '''            if (tfRoute != null && !isDuplicate(tfRoute)) {
                previousTexts = currentSignatures
                currentStartedAt = SystemClock.elapsedRealtime()
'''
new_success = '''            if (tfRoute != null && !isDuplicate(tfRoute)) {
                previousFastTexts = currentFastTexts
                currentStartedAt = SystemClock.elapsedRealtime()
'''
if old_success not in s:
    raise SystemExit('TEXT RAW DELTA v4 success anchor not found')
s = s.replace(old_success, new_success, 1)

# Only if TEXT FIRST did not find a route do we pay the old normalized-signature cost.
old_fallback = '        val currentImageCandidates = findImageCandidates(items)\n'
new_fallback = '''        previousFastTexts = currentFastTexts
        val currentSignatures = textSignatures(items)
        val currentImageCandidates = findImageCandidates(items)
'''
if old_fallback not in s:
    raise SystemExit('TEXT RAW DELTA v4 image fallback anchor not found')
s = s.replace(old_fallback, new_fallback, 1)

old_header = '===== DIAGNOSTICO TEXTO v3 | OLD BASE + TEXT FIRST + FAST SIGNATURE ====='
new_header = '===== DIAGNOSTICO TEXTO v4 | OLD BASE + TEXT FIRST + RAW DELTA ====='
s = s.replace(old_header, new_header, 1)

checks = [
    'private var previousFastTexts: Set<String> = emptySet()',
    'val currentFastTexts = LinkedHashSet<String>(items.size)',
    'previousFastTexts = currentFastTexts',
    'val currentSignatures = textSignatures(items)',
    new_header,
]
for marker in checks:
    if marker not in s:
        raise SystemExit('TEXT RAW DELTA v4 verification failed: ' + marker)

# Strong safety check: the successful TEXT-FIRST block must no longer reference currentSignatures.
start = s.find('if (primed && Prefs.searchArmed(this) && tfNewItems.isNotEmpty())')
end = s.find('val currentImageCandidates = findImageCandidates(items)', start)
segment = s[start:end]
if start < 0 or end < 0:
    raise SystemExit('TEXT RAW DELTA v4 could not isolate text-first segment')
if 'RouteParser.normalize(item.text)' in segment:
    raise SystemExit('TEXT RAW DELTA v4 still normalizes every item in hot segment')
if 'previousTexts = currentSignatures' in segment:
    raise SystemExit('TEXT RAW DELTA v4 still updates normalized signatures in successful hot segment')

S.write_text(s, encoding='utf-8')
print('TEXT RAW DELTA v4 aplicado: rota textual evita normalizacao global; fallback de imagem preservado')
