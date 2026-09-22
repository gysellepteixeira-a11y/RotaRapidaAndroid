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
# - recovery especial (bairro prioritario + OCR pequeno somente da Gaiola) passa
#   a valer para qualquer tabela que ja foi classificada como densa: 8+ linhas.

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

old_prepare_recovery = '        if (expectedDenseRows < 20) return null\n'
new_prepare_recovery = '        if (expectedDenseRows < 8) return null\n'
if old_prepare_recovery not in s:
    raise SystemExit("dense short: limite expectedDenseRows <20 nao encontrado")
s = s.replace(old_prepare_recovery, new_prepare_recovery, 1)

old_trigger_recovery = '                        detected.rowCount >= 20 &&\n'
new_trigger_recovery = '                        detected.rowCount >= 8 &&\n'
if old_trigger_recovery not in s:
    raise SystemExit("dense short: gatilho detected.rowCount >=20 nao encontrado")
s = s.replace(old_trigger_recovery, new_trigger_recovery, 1)

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
gradle = gradle.replace(
    'versionName = "0.19-densa-cage-fix"',
    'versionName = "0.19-densa-baixa"'
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")
gradle_path.write_text(gradle, encoding="utf-8")

print("Dense short aplicado: 180px+ usa detector denso; recovery OCR Gaiola liberado para 8+ linhas; versionCode 5")
