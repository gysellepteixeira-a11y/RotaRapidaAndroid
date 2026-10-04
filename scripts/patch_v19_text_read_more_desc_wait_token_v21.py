from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v20 | TEXT v6 + READ MORE DESC WAIT + STRICT PROOF + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v21 | TEXT v6 + READ MORE DESC WAIT TOKEN + STRICT PROOF + DIRECT SEND ====='
required=[
    old_header,
    'private var rmDescWaitMsV20=0L; private var rmDescWaitPollsV20=0',
    'private fun waitForReadMoreDescV20(startedAt:Long,poll:Int)',
    'rmMethod=if(descTargetNew!=null) "DESC_NEWITEM" else "DESC_ROOT"',
    'handler.postDelayed({waitForReadMoreDescV20(waitStart,1)},5L)',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('READ MORE DESC WAIT TOKEN v21 wrong base: '+m)

# Generation token for the short DESC wait. A callback from an older accessibility
# frame is ignored as soon as another path resolves the same Read-more message.
state_old='''    private var rmDescWaitMsV20=0L; private var rmDescWaitPollsV20=0
    private var tdReadMoreDescWaitMsV20=0L; private var tdReadMoreDescWaitPollsV20=0
'''
state_new='''    private var rmDescWaitMsV20=0L; private var rmDescWaitPollsV20=0
    private var tdReadMoreDescWaitMsV20=0L; private var tdReadMoreDescWaitPollsV20=0
    private var rmDescWaitGenerationV21=0L; private var rmDescWaitActiveGenerationV21=0L
'''
if state_old not in s:
    raise SystemExit('v21 state anchor not found')
s=s.replace(state_old,state_new,1)

# Replace the v20 waiter with a generation-aware version. Only the generation that
# started the current wait may update timing, click, time out, or schedule another poll.
a=s.find('    private fun waitForReadMoreDescV20(startedAt:Long,poll:Int){')
b=s.find('    private fun waitForTextDirectSendReadyV5(',a)
if a<0 or b<0:
    raise SystemExit('v21 waiter region not found')
waiter=r'''    private fun waitForReadMoreDescV20(startedAt:Long,poll:Int,generation:Long){
        if(generation!=rmDescWaitActiveGenerationV21 || !rmPending)return

        val descTarget=try{findNewestReadMoreDescTargetV14()}catch(_:Throwable){null}
        if(descTarget!=null){
            rememberReadMoreChainV16(descTarget.node)
            val before=freshReadMoreBandStatsV12(descTarget.rect)
            val t=SystemClock.elapsedRealtime()
            val ok=try{descTarget.node.performAction(AccessibilityNodeInfo.ACTION_CLICK)}catch(_:Throwable){false}
            val done=SystemClock.elapsedRealtime()
            if(generation!=rmDescWaitActiveGenerationV21)return
            if(ok){
                // Resolve this generation BEFORE expansion polling starts. Any old
                // handler callback carrying the same/older token becomes inert.
                rmDescWaitActiveGenerationV21=0L
                rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done
                rmClickMs=done-t; rmExpanded=0L; rmPolls=0; rmMethod="DESC_RETRY"
                rmDescWaitMsV20=t-startedAt; rmDescWaitPollsV20=poll
                waitForReadMoreExpansionV12(descTarget.rect,before,t,0,false)
                return
            }
        }

        if(generation!=rmDescWaitActiveGenerationV21)return
        val now=SystemClock.elapsedRealtime()
        if(now-startedAt<120L){
            handler.postDelayed({waitForReadMoreDescV20(startedAt,poll+1,generation)},5L)
            return
        }

        // This generation expired. Retire it before releasing rmPending so a later
        // DESC_NEWITEM event starts clean and cannot inherit this wait's metrics.
        rmDescWaitMsV20=now-startedAt; rmDescWaitPollsV20=poll
        rmDescWaitActiveGenerationV21=0L
        absorbCurrentTextBaselineV18()
        rmPending=false; rmCarry=false; rmUsed=false
        Prefs.setStatus(this,"TEXT v21: rota truncada detectada, mas o botao Ler mais real nao apareceu em ${rmDescWaitMsV20}ms (${rmDescWaitPollsV20} polls). Nenhuma rota parcial foi enviada.")
    }

'''
s=s[:a]+waiter+s[b:]

# If the normal analyzer gets the real desc node directly, it wins immediately.
# Invalidate any previous waiter and clear its timing so the diagnostic cannot show
# a phantom readMoreDescWait on a DESC_NEWITEM/DESC_ROOT success.
direct_old='''                    rmClickMs=done-t; rmExpanded=0L; rmPolls=0
                    rmMethod=if(descTargetNew!=null) "DESC_NEWITEM" else "DESC_ROOT"
'''
direct_new='''                    rmClickMs=done-t; rmExpanded=0L; rmPolls=0
                    rmDescWaitGenerationV21++
                    rmDescWaitActiveGenerationV21=0L
                    rmDescWaitMsV20=0L; rmDescWaitPollsV20=0
                    rmMethod=if(descTargetNew!=null) "DESC_NEWITEM" else "DESC_ROOT"
'''
if direct_old not in s:
    raise SystemExit('v21 direct desc success anchor not found')
s=s.replace(direct_old,direct_new,1)

# Starting a short wait now allocates a unique token.
start_old='''                val waitStart=SystemClock.elapsedRealtime()
                rmPending=true; rmCarry=false; rmUsed=false
                rmDescWaitMsV20=0L; rmDescWaitPollsV20=0
                handler.postDelayed({waitForReadMoreDescV20(waitStart,1)},5L)
                return
'''
start_new='''                val waitStart=SystemClock.elapsedRealtime()
                rmDescWaitGenerationV21++
                val waitGeneration=rmDescWaitGenerationV21
                rmDescWaitActiveGenerationV21=waitGeneration
                rmPending=true; rmCarry=false; rmUsed=false
                rmDescWaitMsV20=0L; rmDescWaitPollsV20=0
                handler.postDelayed({waitForReadMoreDescV20(waitStart,1,waitGeneration)},5L)
                return
'''
if start_old not in s:
    raise SystemExit('v21 wait start anchor not found')
s=s.replace(start_old,start_new,1)

# Reset token state with the existing read-more reset. Incrementing generation also
# invalidates any callback that was already queued on Handler.
reset_old='rmBeforeAnchorLenV18=0; rmGestureStageV18=0; rmProofV18=""; rmDescWaitMsV20=0L; rmDescWaitPollsV20=0'
reset_new=reset_old+'; rmDescWaitGenerationV21++; rmDescWaitActiveGenerationV21=0L'
if reset_old not in s:
    raise SystemExit('v21 reset anchor not found')
s=s.replace(reset_old,reset_new,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'private var rmDescWaitGenerationV21=0L',
    'generation!=rmDescWaitActiveGenerationV21',
    'waitForReadMoreDescV20(startedAt,poll+1,generation)',
    'rmDescWaitActiveGenerationV21=waitGeneration',
    'rmDescWaitMsV20=0L; rmDescWaitPollsV20=0',
    'TEXT v21: rota truncada detectada',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('READ MORE DESC WAIT TOKEN v21 verify failed: '+m)

if 'waitForReadMoreDescV20(waitStart,1)' in s:
    raise SystemExit('v21 verify failed: old un-tokenized wait call still present')

S.write_text(s,encoding='utf-8')
print('READ MORE DESC WAIT TOKEN v21 applied: generation guard + stale waiter cancellation + clean wait metrics; v20 behavior/TEXT v6/IMAGE v9 preserved')
