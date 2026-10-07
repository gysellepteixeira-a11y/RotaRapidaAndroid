from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

required=[
    '===== DIAGNOSTICO IMAGEM v19 | V48 EDITOR FAST PATH + V47 CLEAN FAST =====',
    'private fun waitForReadMoreDescV20(startedAt:Long,poll:Int,generation:Long){',
    'if(now-startedAt<120L){',
    'TEXT v21: rota truncada detectada, mas o botao Ler mais real nao apareceu em',
]
for m in required:
    if m not in s:
        raise SystemExit("v49 wrong base: "+m)

s=s.replace('if(now-startedAt<120L){','if(now-startedAt<400L){',1)

old_status='''        Prefs.setStatus(this,"TEXT v21: rota truncada detectada, mas o botao Ler mais real nao apareceu em ${rmDescWaitMsV20}ms (${rmDescWaitPollsV20} polls). Nenhuma rota parcial foi enviada.")
'''
new_status='''        Prefs.setStatus(this,"TEXT v49: rota truncada detectada, mas o botao Ler mais real nao apareceu em ${rmDescWaitMsV20}ms (${rmDescWaitPollsV20} polls). Nenhuma rota parcial foi enviada.")
'''
if old_status not in s:
    raise SystemExit("v49 timeout status anchor missing")
s=s.replace(old_status,new_status,1)

# Keep the same exact-node ACTION_CLICK and generation safety.
for m in [
    'findNewestReadMoreDescTargetV14()',
    'performAction(AccessibilityNodeInfo.ACTION_CLICK)',
    'generation!=rmDescWaitActiveGenerationV21',
    'waitForReadMoreExpansionV12(descTarget.rect,before,t,0,false)',
    'if(now-startedAt<400L){',
    'TEXT v49: rota truncada detectada',
]:
    if m not in s:
        raise SystemExit("v49 verify failed: "+m)

S.write_text(s,encoding="utf-8")
print("v49 READ MORE WAIT400 applied: real contentDescription only; timeout 120ms -> 400ms; strict proof and no-partial-send preserved")
