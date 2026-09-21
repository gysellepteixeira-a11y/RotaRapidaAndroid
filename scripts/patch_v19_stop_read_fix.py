from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
activity_path = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")

s = service_path.read_text(encoding="utf-8")
a = activity_path.read_text(encoding="utf-8")

# Corrige regressao introduzida pelo modo STOP:
# ao tocar em PROCURAR NOVAMENTE, a versao anterior marcava needsPrime=true e
# ignorava completamente a primeira tela/evento do WhatsApp. Em testes rapidos,
# esse primeiro evento podia ser justamente a nova rota, dando a impressao de que
# imagens/textos que a v0.19 lia antes tinham parado de funcionar.
#
# Agora rearmar apenas libera a busca. Nao muda parser, OCR, MediaStore nem a
# leitura densa da v0.19. A referencia anterior ja contem a rota que acabou de ser
# enviada, entao ela nao e reenviada; qualquer rota nova visivel pode ser lida.

old_listener = '''        searchAgain.setOnClickListener {
            Prefs.setSearchArmed(this, true)
            Prefs.setNeedsPrime(this, true)
            Prefs.setStatus(
                this,
                "Procurar novamente ativado. Abra o grupo configurado; a partir da tela atual, vou aguardar uma NOVA rota."
            )
        }
'''
new_listener = '''        searchAgain.setOnClickListener {
            Prefs.setSearchArmed(this, true)
            Prefs.setNeedsPrime(this, false)
            Prefs.setStatus(
                this,
                "Procurar novamente ativado. Aguardando rota no grupo configurado."
            )
        }
'''
if old_listener not in a:
    raise SystemExit('patch_v19_stop_read_fix: listener PROCURAR NOVAMENTE nao encontrado')
a = a.replace(old_listener, new_listener, 1)
activity_path.write_text(a, encoding="utf-8")

old_prime = '''        if (!Prefs.searchArmed(this)) return

        if (Prefs.needsPrime(this)) {
            previousTexts = textSignatures(items)
            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
            primed = true
            Prefs.setNeedsPrime(this, false)
            Prefs.setStatus(this, "Pronto. Aguardando uma NOVA rota.")
            return
        }

        val currentSignatures = textSignatures(items)
'''
new_prime = '''        if (!Prefs.searchArmed(this)) return

        val currentSignatures = textSignatures(items)
'''
if old_prime not in s:
    raise SystemExit('patch_v19_stop_read_fix: bloco needsPrime nao encontrado')
s = s.replace(old_prime, new_prime, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 STOP READ FIX aplicado: rearmar nao engole mais a primeira rota")
