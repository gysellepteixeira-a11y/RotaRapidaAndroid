from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s = S.read_text(encoding='utf-8')

required = [
    '===== DIAGNOSTICO TEXTO v5 | OLD BASE + TEXT FIRST + RAW DELTA + DIRECT SEND =====',
    'private var previousFastTexts: Set<String> = emptySet()',
    'val currentFastTexts = LinkedHashSet<String>(items.size)',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
]
for marker in required:
    if marker not in s:
        raise SystemExit('TEXT TAIL DELTA v6 wrong base / missing marker: ' + marker)

old_loop = '''        // TEXT RAW DELTA v4 A/B:
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

new_loop = '''        // TEXT TAIL DELTA v6 A/B:
        // Uma mensagem nova do WhatsApp aparece no fim da conversa. Para uma rota
        // textual valida, evita percorrer/hashear TODA a arvore: varre de baixo para
        // cima e para depois de encontrar o bloco novo + 6 textos antigos consecutivos.
        // Se nao achar rota, o fallback logo abaixo reconstrui o baseline completo.
        val tfNewItemsReverse = ArrayList<NodeItem>(8)
        val tfNewKeys = LinkedHashSet<String>(8)
        var tfSawNew = false
        var tfOldAfterNew = 0
        if (primed) {
            for (i in items.indices.reversed()) {
                val item = items[i]
                val key = item.text
                if (key.isBlank()) continue

                if (key !in previousFastTexts) {
                    tfSawNew = true
                    tfOldAfterNew = 0
                    tfNewItemsReverse.add(item)
                    tfNewKeys.add(key)
                    // Limite defensivo: uma rota textual normal usa poucos nos.
                    if (tfNewItemsReverse.size >= 32) break
                } else if (tfSawNew) {
                    tfOldAfterNew++
                    if (tfOldAfterNew >= 6) break
                }
            }
        }
        val tfNewItems = tfNewItemsReverse.asReversed()

        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.
'''

if old_loop not in s:
    raise SystemExit('TEXT TAIL DELTA v6 hot-loop anchor not found')
s = s.replace(old_loop, new_loop, 1)

old_success = '''            if (tfRoute != null && !isDuplicate(tfRoute)) {
                previousFastTexts = currentFastTexts
                currentStartedAt = SystemClock.elapsedRealtime()
'''
new_success = '''            if (tfRoute != null && !isDuplicate(tfRoute)) {
                // Durante a corrida, atualiza somente com o pequeno bloco novo.
                // O app para apos enviar; ao rearmar, o baseline completo e refeito.
                if (tfNewKeys.isNotEmpty()) {
                    previousFastTexts = previousFastTexts + tfNewKeys
                }
                currentStartedAt = SystemClock.elapsedRealtime()
'''
if old_success not in s:
    raise SystemExit('TEXT TAIL DELTA v6 success anchor not found')
s = s.replace(old_success, new_success, 1)

old_fallback = '''        previousFastTexts = currentFastTexts
        val currentSignatures = textSignatures(items)
        val currentImageCandidates = findImageCandidates(items)
'''
new_fallback = '''        // Apenas quando o TAIL FAST nao produziu uma rota valida pagamos a
        // varredura completa. Assim imagem/fallback conservam o comportamento antigo.
        previousFastTexts = items.asSequence()
            .map { it.text }
            .filter { it.isNotBlank() }
            .toSet()
        val currentSignatures = textSignatures(items)
        val currentImageCandidates = findImageCandidates(items)
'''
if old_fallback not in s:
    raise SystemExit('TEXT TAIL DELTA v6 fallback anchor not found')
s = s.replace(old_fallback, new_fallback, 1)

old_header = '===== DIAGNOSTICO TEXTO v5 | OLD BASE + TEXT FIRST + RAW DELTA + DIRECT SEND ====='
new_header = '===== DIAGNOSTICO TEXTO v6 | OLD BASE + TEXT TAIL DELTA + DIRECT SEND ====='
s = s.replace(old_header, new_header, 1)

checks = [
    'val tfNewItemsReverse = ArrayList<NodeItem>(8)',
    'if (tfOldAfterNew >= 6) break',
    'previousFastTexts = previousFastTexts + tfNewKeys',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    new_header,
]
for marker in checks:
    if marker not in s:
        raise SystemExit('TEXT TAIL DELTA v6 verification failed: ' + marker)

# Strong A/B safety checks: successful text hot path must not rebuild the full set,
# and DIRECT SEND v5 must remain present and untouched.
start = s.find('if (primed && Prefs.searchArmed(this) && tfNewItems.isNotEmpty())')
end = s.find('val currentSignatures = textSignatures(items)', start)
if start < 0 or end < 0:
    raise SystemExit('TEXT TAIL DELTA v6 could not isolate hot segment')
segment = s[start:end]
if 'items.asSequence()' in segment:
    raise SystemExit('TEXT TAIL DELTA v6 full baseline leaked into successful hot segment')
if 'waitForTextDirectSendReadyV5(' not in s:
    raise SystemExit('TEXT TAIL DELTA v6 lost DIRECT SEND v5')

S.write_text(s, encoding='utf-8')
print('TEXT TAIL DELTA v6 aplicado: rota textual varre apenas cauda nova; DIRECT SEND v5 e imagem preservados')
