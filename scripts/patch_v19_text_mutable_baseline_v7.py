from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s = S.read_text(encoding='utf-8')

old_header = '===== DIAGNOSTICO TEXTO v6 | OLD BASE + TEXT TAIL DELTA + DIRECT SEND ====='
new_header = '===== DIAGNOSTICO TEXTO v7 | OLD BASE + TEXT TAIL DELTA + MUTABLE BASELINE + DIRECT SEND ====='

required = [
    old_header,
    'private var previousFastTexts: Set<String> = emptySet()',
    'previousFastTexts = previousFastTexts + tfNewKeys',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
]
for marker in required:
    if marker not in s:
        raise SystemExit('TEXT MUTABLE BASELINE v7 wrong base / missing marker: ' + marker)

# v7 A/B: o v6 ainda copiava TODO o baseline de textos depois do parser:
# previousFastTexts + tfNewKeys. Isso acontece antes de currentStartedAt e antes
# do envio, portanto entra diretamente no tempo da corrida.
# Mantemos exatamente os mesmos dados, mas garantimos que os baselines criados
# fora do caminho critico sejam MutableSet e adicionamos somente as 5~ novas
# chaves in-place no sucesso.
old_baseline = '''previousFastTexts = items.asSequence()
            .map { it.text }
            .filter { it.isNotBlank() }
            .toSet()'''
new_baseline = '''previousFastTexts = items.asSequence()
            .map { it.text }
            .filter { it.isNotBlank() }
            .toMutableSet()'''
count = s.count(old_baseline)
if count < 2:
    raise SystemExit(f'TEXT MUTABLE BASELINE v7 expected >=2 raw baseline blocks, found {count}')
s = s.replace(old_baseline, new_baseline)

old_success = '''                if (tfNewKeys.isNotEmpty()) {
                    previousFastTexts = previousFastTexts + tfNewKeys
                }
                currentStartedAt = SystemClock.elapsedRealtime()
'''
new_success = '''                if (tfNewKeys.isNotEmpty()) {
                    val tfMutableBaseline = previousFastTexts as? MutableSet<String>
                    if (tfMutableBaseline != null) {
                        tfMutableBaseline.addAll(tfNewKeys)
                    } else {
                        // Fallback defensivo; normalmente nao entra porque os baselines
                        // do v7 sao criados como MutableSet fora do caminho critico.
                        previousFastTexts = previousFastTexts.toMutableSet().also {
                            it.addAll(tfNewKeys)
                        }
                    }
                }
                currentStartedAt = SystemClock.elapsedRealtime()
'''
if old_success not in s:
    raise SystemExit('TEXT MUTABLE BASELINE v7 success anchor not found')
s = s.replace(old_success, new_success, 1)

s = s.replace(old_header, new_header, 1)

checks = [
    new_header,
    '.toMutableSet()',
    'val tfMutableBaseline = previousFastTexts as? MutableSet<String>',
    'tfMutableBaseline.addAll(tfNewKeys)',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
]
for marker in checks:
    if marker not in s:
        raise SystemExit('TEXT MUTABLE BASELINE v7 verification failed: ' + marker)

# A/B safety: nao pode restar a uniao que copia o baseline inteiro no sucesso.
if 'previousFastTexts = previousFastTexts + tfNewKeys' in s:
    raise SystemExit('TEXT MUTABLE BASELINE v7 full-set copy still present')
if 'waitForTextDirectSendReadyV5(' not in s:
    raise SystemExit('TEXT MUTABLE BASELINE v7 lost DIRECT SEND v5')

S.write_text(s, encoding='utf-8')
print('TEXT MUTABLE BASELINE v7 aplicado: baseline bruto mutavel + addAll pequeno in-place; DIRECT SEND v5 e imagem preservados')
