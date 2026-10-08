from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

required=[
    'private fun waitForReadMoreDescV20(startedAt:Long,poll:Int,generation:Long){',
    'private var rmDescWaitGenerationV21=0L; private var rmDescWaitActiveGenerationV21=0L',
    'private fun checkDirectMediaStoreImage() {',
    'val media = findNewestWhatsAppImage() ?: return',
    'Prefs.setSpeedDiagnosticReport(this,readMoreDumpV51)',
    'READ MORE TREE DIAG v51 | V48 FULL DIAG',
]
for m in required:
    if m not in s:
        raise SystemExit("v57 wrong base: "+m)

waiter_anchor='''    private fun waitForReadMoreDescV20(startedAt:Long,poll:Int,generation:Long){
'''
helper=r'''    private fun cancelReadMoreForImageV57() {
        rmDescWaitGenerationV21++
        rmDescWaitActiveGenerationV21=0L
        rmPending=false
        rmCarry=false
        rmUsed=false
        rmDescWaitMsV20=0L
        rmDescWaitPollsV20=0
    }

'''
if waiter_anchor not in s:
    raise SystemExit("v57 waiter anchor missing")
s=s.replace(waiter_anchor,helper+waiter_anchor,1)

media_anchor='''        val media = findNewestWhatsAppImage() ?: return

        // Reserva o arquivo antes de iniciar OCR para nenhum outro evento pegar o
        // mesmo ID em paralelo.
        lastMediaImageId = media.id
'''
media_new='''        val media = findNewestWhatsAppImage() ?: return

        // v57: arquivo real de imagem venceu a corrida.
        cancelReadMoreForImageV57()

        // Reserva o arquivo antes de iniciar OCR para nenhum outro evento pegar o
        // mesmo ID em paralelo.
        lastMediaImageId = media.id
'''
if media_anchor not in s:
    raise SystemExit("v57 MediaStore reserve anchor missing")
s=s.replace(media_anchor,media_new,1)

old_diag='''        val readMoreDumpV51=try{buildReadMoreTreeDumpV51()}catch(e:Throwable){
            "===== READ MORE TREE DIAG v51 =====\\nERRO: ${e.javaClass.simpleName}: ${e.message ?: "sem detalhes"}"
        }
        Prefs.setSpeedDiagnosticReport(this,readMoreDumpV51)
        Prefs.setStatus(this,"TEXT v21: rota truncada detectada, mas o botao Ler mais real nao apareceu em ${rmDescWaitMsV20}ms (${rmDescWaitPollsV20} polls). Diagnostico v51 salvo abaixo. Nenhuma rota parcial foi enviada.")
'''
new_diag='''        val timeoutGenerationV57=generation
        val timeoutMsV57=rmDescWaitMsV20
        val timeoutPollsV57=rmDescWaitPollsV20
        handler.postDelayed({
            if(timeoutGenerationV57!=rmDescWaitGenerationV21 || processing)return@postDelayed

            val readMoreDumpV51=try{buildReadMoreTreeDumpV51()}catch(e:Throwable){
                "===== READ MORE TREE DIAG v51 =====\\nERRO: ${e.javaClass.simpleName}: ${e.message ?: "sem detalhes"}"
            }
            Prefs.setSpeedDiagnosticReport(this,readMoreDumpV51)
            Prefs.setStatus(
                this,
                "TEXT v21: rota truncada detectada, mas o botao Ler mais real nao apareceu em ${timeoutMsV57}ms (${timeoutPollsV57} polls). Diagnostico v51 salvo abaixo. Nenhuma rota parcial foi enviada."
            )
        },250L)
'''
if old_diag not in s:
    raise SystemExit("v57 v51 timeout diagnostic block missing")
s=s.replace(old_diag,new_diag,1)

checks=[
    'private fun cancelReadMoreForImageV57()',
    'cancelReadMoreForImageV57()',
    'val timeoutGenerationV57=generation',
    'timeoutGenerationV57!=rmDescWaitGenerationV21 || processing',
    '},250L)',
    'readMediaOriginal(media)',
    'Prefs.setSpeedDiagnosticReport(this,readMoreDumpV51)',
]
for m in checks:
    if m not in s:
        raise SystemExit("v57 verify failed: "+m)

S.write_text(s,encoding="utf-8")
print("v57 IMAGE PRIORITY aplicado: MediaStore cancela DESC_WAIT; dump v51 recebe grace 250ms e nao sobrescreve OCR")

