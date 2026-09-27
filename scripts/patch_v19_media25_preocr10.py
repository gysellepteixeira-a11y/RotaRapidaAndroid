from pathlib import Path
import re

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# Mantem os timings da base MEDIA25 + PREOCR10 usados no teste do M52.

# 1) Watcher direto do MediaStore: 100 ms -> 25 ms.
s, n_media = re.subn(
    r'private const val DIRECT_MEDIASTORE_WATCH_MS = \d+L',
    'private const val DIRECT_MEDIASTORE_WATCH_MS = 25L',
    s,
    count=1
)
if n_media != 1:
    raise SystemExit('MEDIA25: DIRECT_MEDIASTORE_WATCH_MS nao encontrado')

# 2) Espera imediatamente anterior a captura/OCR do visualizador.
# O caminho principal atual usa MediaStore, mas preservamos o PREOCR10 tambem
# para o fallback visual. Aceita tanto o texto antigo quanto o marcador novo.
patched_preocr = False

markers = [
    'Visualizador confirmado. Iniciando OCR...',
    'Imagem aberta. Preparando OCR...'
]

for marker in markers:
    pos = s.find(marker)
    if pos < 0:
        continue

    # Limita a troca a uma janela curta depois do status para nao alterar retries.
    win_end = min(len(s), pos + 700)
    window = s[pos:win_end]

    # Preferencia: delay explicitamente 60/70 ms imediatamente no handler.
    new_window, count = re.subn(
        r'(handler\.postDelayed\([\s\S]{0,260}?)(?:60|70)L(\s*\))',
        r'\g<1>10L\2',
        window,
        count=1
    )

    if count == 1:
        s = s[:pos] + new_window + s[win_end:]
        patched_preocr = True
        break

# Se a versao final ja tiver sido reduzida por outro patch, nao falha.
if not patched_preocr:
    # Confirma que existe pelo menos um 10L perto de um dos marcadores.
    for marker in markers:
        pos = s.find(marker)
        if pos >= 0 and '10L' in s[pos:min(len(s), pos + 700)]:
            patched_preocr = True
            break

if not patched_preocr:
    print('PREOCR10: marcador visual nao encontrado/nao aplicavel; caminho MediaStore continua intacto')

service_path.write_text(s, encoding="utf-8")
print('MEDIA25 + PREOCR10 aplicados')
