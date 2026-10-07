from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

old='''        if(next){
            primed=false
            Prefs.setStatus(
                this,
                if(Prefs.groupName(this).isBlank())
                    "Automacao ligada pelo botao flutuante, mas falta configurar o grupo."
                else
                    "Automacao ligada pelo botao flutuante."
            )
            handler.postDelayed({
                if(Prefs.isEnabled(this)) primeCurrentScreen()
            },80L)
        }else{
'''
new='''        if(next){
            // Mesmo efeito funcional de PROCURAR NOVAMENTE do app:
            // rearma a busca apos uma rota ter sido enviada.
            Prefs.setSearchArmed(this,true)
            Prefs.setNeedsPrime(this,false)

            primed=false
            Prefs.setStatus(
                this,
                if(Prefs.groupName(this).isBlank())
                    "Automacao ligada pelo botao flutuante, mas falta configurar o grupo."
                else
                    "Automacao ligada pelo botao flutuante. Aguardando nova rota."
            )
            handler.postDelayed({
                if(Prefs.isEnabled(this) && Prefs.searchArmed(this)) primeCurrentScreen()
            },80L)
        }else{
            Prefs.setSearchArmed(this,false)
'''
if old not in s:
    raise SystemExit("v53 floating ON block not found")
s=s.replace(old,new,1)

for m in [
    'Prefs.setSearchArmed(this,true)',
    'Prefs.setNeedsPrime(this,false)',
    'Prefs.setSearchArmed(this,false)',
    'Prefs.isEnabled(this) && Prefs.searchArmed(this)',
]:
    if m not in s:
        raise SystemExit("v53 verify failed: "+m)

S.write_text(s,encoding="utf-8")
print("v53 FLOATING REARM aplicado: ON flutuante agora equivale a PROCURAR NOVAMENTE; OFF desarma busca")
