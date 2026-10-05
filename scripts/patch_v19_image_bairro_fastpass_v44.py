from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

required=[
    '===== DIAGNOSTICO IMAGEM v14 | BAIRRO FAST PASS v43 + V37 FALLBACK + GAIOLA NARROW =====',
    'val fastScale=0.82f',
    'bairroFastV43=used=$idV43Used',
    'private fun readDenseBairroFirstV37(',
    '===== DIAGNOSTICO TEXTO v37 |',
]
for m in required:
    if m not in s:
        raise SystemExit('v44 wrong base: '+m)

# Isolated experiment: change ONLY the fast Bairro OCR scale.
# Crop geometry, matching, Y mapping, Gaiola Narrow, send path and exact v37 fallback stay unchanged.
s=s.replace('private var idV43Ocr=0L; private var idV43Scale=0.82f; private var idV43Width=0',
            'private var idV43Ocr=0L; private var idV43Scale=0.70f; private var idV43Width=0',1)
s=s.replace('idV43Ocr=0L; idV43Scale=0.82f; idV43Width=0',
            'idV43Ocr=0L; idV43Scale=0.70f; idV43Width=0',1)
s=s.replace('// v43 FAST PASS: narrower Bairro-only crop + 0.82x OCR bitmap.',
            '// v44 FAST PASS: same Bairro-only crop, more aggressive 0.70x OCR bitmap.',1)
s=s.replace('val fastScale=0.82f','val fastScale=0.70f',1)

old_header='===== DIAGNOSTICO IMAGEM v14 | BAIRRO FAST PASS v43 + V37 FALLBACK + GAIOLA NARROW ====='
new_header='===== DIAGNOSTICO IMAGEM v15 | BAIRRO FAST PASS 0.70x v44 + V37 FALLBACK + GAIOLA NARROW ====='
s=s.replace(old_header,new_header,1)
s=s.replace('bairroFastV43=used=$idV43Used', 'bairroFastV44=used=$idV43Used',1)
s=s.replace('lastDenseRecoveryDebug="bairro-fast-v43=$rowCount;', 'lastDenseRecoveryDebug="bairro-fast-v44=$rowCount;',1)

for m in [
    new_header,
    'val fastScale=0.70f',
    'bairroFastV44=used=$idV43Used',
    'private fun readDenseBairroFirstV37(',
    'readDenseBairroFirstV37(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)',
    'speedDiagnosticSendMethod = "IMAGE_DIRECT_V8"',
    '===== DIAGNOSTICO TEXTO v37 |',
]:
    if m not in s:
        raise SystemExit('v44 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('IMAGE v44 applied: Bairro fast pass scale 0.82x -> 0.70x; v37 fallback and Gaiola Narrow preserved')
