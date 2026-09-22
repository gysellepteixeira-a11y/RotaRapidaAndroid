from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
gradle_path = Path("app/build.gradle.kts")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")
gradle = gradle_path.read_text(encoding="utf-8")

# v0.19 - DENSE SHORT IMAGE
# Caso real: recorte com 13 rotas e somente 226 px de altura.
# A Otimizacao 1 so tentava o detector colorido a partir de 300 px e a funcao
# detectLargeTableCrop ainda recusava h < 260. Resultado: a imagem ia para OCR
# completo/reforcado, que reconhecia dezenas de fragmentos mas nao conseguia
# fechar J-16 + Colina de Laranjeiras.
#
# Ajuste conservador:
# - tenta detector denso a partir de 180 px (133 px continua no caminho rapido
#   antigo que ja funciona muito bem);
# - detector aceita tabela a partir de 180 px;
# - recovery geometrico vale para qualquer tabela que passou no DENSE_MIN_ROWS=8,
#   nao somente 20+ linhas. O limite vertical continua baseado no passo real da
#   linha, portanto nao ampliamos a tolerancia entre linhas vizinhas.

old_dispatch = '''        if (media.height >= 300) {
            readMediaLargeColorCrop(media)
        } else {
            readMediaOriginalFull(media)
        }
'''
new_dispatch = '''        if (media.height >= 180) {
            readMediaLargeColorCrop(media)
        } else {
            readMediaOriginalFull(media)
        }
'''
if old_dispatch not in s:
    raise SystemExit("dense short: dispatch >=300 nao encontrado")
s = s.replace(old_dispatch, new_dispatch, 1)

old_guard = '        if (w < 500 || h < 260) return null\n'
new_guard = '        if (w < 500 || h < 180) return null\n'
if old_guard not in s:
    raise SystemExit("dense short: guard h<260 nao encontrado")
s = s.replace(old_guard, new_guard, 1)

old_recovery = '        if (expectedDenseRows < 20) {\n            return null\n        }\n'
new_recovery = '        if (expectedDenseRows < 8) {\n            return null\n        }\n'
if old_recovery not in s:
    raise SystemExit("dense short: limite recovery <20 nao encontrado")
s = s.replace(old_recovery, new_recovery, 1)

# Identificacao inequívoca no diagnostico.
prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 DENSA RECOVERY FAST =====',
    '===== DIAGNOSTICO IMAGEM v0.19 DENSA BAIXA ====='
)
prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 DENSA RECOVERY =====',
    '===== DIAGNOSTICO IMAGEM v0.19 DENSA BAIXA ====='
)

# Garante atualizacao por cima das builds anteriores.
gradle = gradle.replace('versionCode = 4', 'versionCode = 5')
gradle = gradle.replace(
    'versionName = "0.19-densa-recovery-fast"',
    'versionName = "0.19-densa-baixa"'
)
# Fallback caso o fast marker nao tenha alterado o versionName por alguma razao.
gradle = gradle.replace(
    'versionName = "0.19-densa-cage-fix"',
    'versionName = "0.19-densa-baixa"'
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")
gradle_path.write_text(gradle, encoding="utf-8")

print("Dense short aplicado: 180px+ usa detector denso; recovery liberado para 8+ linhas; versionCode 5")
