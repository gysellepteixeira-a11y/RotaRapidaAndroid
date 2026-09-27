from pathlib import Path
import re

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

# A/B LIMPO SOBRE BAIRRO FIRST GAIOLA NARROW SEND READY
# 1) MediaStore 25ms -> 10ms
# 2) Mantem scan original (step=4)
# 3) Mantem zoom adaptativo original do Bairro (ex.: x1.55)
# 4) Remove somente dois Prefs.setStatus do caminho critico ANTES dos OCRs
# 5) Nao altera envio, parser, prioridade, crop, zoom ou fallbacks

s, n_media = re.subn(
    r'private const val DIRECT_MEDIASTORE_WATCH_MS = 25L',
    'private const val DIRECT_MEDIASTORE_WATCH_MS = 10L',
    s,
    count=1,
)
if n_media != 1:
    raise SystemExit('MEDIA10 STATUSLEAN: DIRECT_MEDIASTORE_WATCH_MS=25L nao encontrado')

# Remove o status "DENSA ... iniciando Bairro..." imediatamente antes de
# readDenseBairroFirst(). O diagnostico final continua trazendo OCR Bairro,
# Gaiola, envio e app total.
pattern_dense = re.compile(
    r'''\n\s*Prefs\.setStatus\(\n\s*this,\n\s*"DENSA \$\{detected\.rowCount\} BAIRRO->GAIOLA \| crop " \+\n\s*"\$\{\(detected\.widthRatio \* 100\)\.toInt\(\)\}% \| " \+\n\s*"x\$\{String\.format\(java\.util\.Locale\.US, "%.2f", scale\)\} \| iniciando Bairro\.\.\."\n\s*\)\n''',
    re.MULTILINE,
)
s, n_dense = pattern_dense.subn('\n', s, count=1)
if n_dense != 1:
    # Compatibilidade com pequenas variacoes de formatacao: remove por janela.
    marker = 'BAIRRO->GAIOLA | crop '
    pos = s.find(marker)
    if pos < 0:
        raise SystemExit('MEDIA10 STATUSLEAN: status DENSA pre-Bairro nao encontrado')
    start = s.rfind('        Prefs.setStatus(', 0, pos)
    end = s.find('\n        readDenseBairroFirst(', pos)
    if start < 0 or end < 0:
        raise SystemExit('MEDIA10 STATUSLEAN: limites do status DENSA nao encontrados')
    s = s[:start] + s[end + 1:]

# Remove o status "BAIRRO PRIMEIRO: ... OCR Bairro..." entre started e
# recognizer.process(). Isso evita SharedPreferences/log antes do ML Kit.
marker_bairro = '"BAIRRO PRIMEIRO: $rowCount linhas | faixa ${bairroWidth}px | OCR Bairro..."'
pos = s.find(marker_bairro)
if pos < 0:
    raise SystemExit('MEDIA10 STATUSLEAN: status pre-OCR Bairro nao encontrado')
start = s.rfind('        Prefs.setStatus(', 0, pos)
end = s.find('\n\n        recognizer.process(', pos)
if start < 0 or end < 0:
    raise SystemExit('MEDIA10 STATUSLEAN: limites do status pre-OCR Bairro nao encontrados')
s = s[:start] + s[end + 2:]

prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND READY =====',
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND READY MEDIA10 STATUSLEAN ====='
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")
print('SEND READY MEDIA10 STATUSLEAN aplicado: MediaStore10 + 2 status pre-OCR removidos; zoom/scan/envio intactos')
