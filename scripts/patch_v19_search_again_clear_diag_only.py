from pathlib import Path

prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
activity_path = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")

prefs = prefs_path.read_text(encoding="utf-8")
a = activity_path.read_text(encoding="utf-8")

# A/B isolado: NAO altera timers, watchers, MediaStore, parser, OCR nem envio.
# Apenas limpa o estado persistido do diagnostico quando a usuaria toca
# PROCURAR NOVAMENTE.

required = [
    'KEY_SPEED_DIAGNOSTIC',
    'KEY_SPEED_DIAGNOSTIC_ACTIVE',
    'KEY_SPEED_DIAGNOSTIC_START',
]
for item in required:
    if item not in prefs:
        raise SystemExit(f"clear_diag_only: {item} nao encontrado em Prefs.kt")

if 'fun clearSpeedDiagnosticOnly(context: Context)' not in prefs:
    insert = '''

    fun clearSpeedDiagnosticOnly(context: Context) {
        prefs(context).edit()
            .remove(KEY_SPEED_DIAGNOSTIC)
            .remove(KEY_SPEED_DIAGNOSTIC_ACTIVE)
            .remove(KEY_SPEED_DIAGNOSTIC_START)
            .apply()
    }
'''
    pos = prefs.rfind('\n}')
    if pos < 0:
        raise SystemExit('clear_diag_only: fim de Prefs.kt nao encontrado')
    prefs = prefs[:pos] + insert + prefs[pos:]

old_listener = '''        searchAgain.setOnClickListener {
            Prefs.setSearchArmed(this, true)
            Prefs.setNeedsPrime(this, false)
            Prefs.setStatus(
                this,
                "Procurar novamente ativado. Aguardando rota no grupo configurado."
            )
        }
'''
new_listener = '''        searchAgain.setOnClickListener {
            Prefs.clearSpeedDiagnosticOnly(this)
            Prefs.setSearchArmed(this, true)
            Prefs.setNeedsPrime(this, false)
            Prefs.setStatus(
                this,
                "Procurar novamente ativado. Aguardando rota no grupo configurado."
            )
        }
'''

if old_listener not in a:
    raise SystemExit('clear_diag_only: listener PROCURAR NOVAMENTE final nao encontrado')

a = a.replace(old_listener, new_listener, 1)

prefs_path.write_text(prefs, encoding="utf-8")
activity_path.write_text(a, encoding="utf-8")

print('A/B CLEAR DIAG ONLY aplicado: somente diagnostico persistido e limpo no PROCURAR NOVAMENTE')
