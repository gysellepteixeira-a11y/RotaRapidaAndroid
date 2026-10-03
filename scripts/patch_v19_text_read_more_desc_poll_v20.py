from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v18 | TEXT v6 + READ MORE STRICT PROOF + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v20 | TEXT v6 + READ MORE DESC POLL + DIRECT SEND ====='
required=[
    old_header,
    'private fun findReadMoreDescFromNewItemsV15(',
    'private fun findNewestReadMoreDescTargetV14()',
    'private fun freshReadMoreProofV18(',
    'private fun absorbCurrentTextBaselineV18()',
    'private fun waitForReadMoreExpansionV12(',
    'val descTargetNew=findReadMoreDescFromNewItemsV15(tfNewItems)',
    'val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('READ MORE DESC POLL v20 wrong base: '+m)

# v20 goal: never use coordinate gestures for a truncated WhatsApp message.
# If the ellipsis/message arrives before the real contentDescription='Ler mais'
# control, wait briefly for that exact clickable node and ACTION_CLICK it.
# Normal messages and an already-available Read-more node pay no extra delay.
state_anchor='    private var tdReadMoreProofV18=""\n'
state_insert='''    private var tdReadMoreProofV18=""
    private var rmDescWaitMsV20=0L; private var rmDescWaitPollsV20=0
    private var tdReadMoreDescWaitMsV20=0L; private var tdReadMoreDescWaitPollsV20=0
'''
if state_anchor not in s:
    raise SystemExit('v20 state anchor not found')
s=s.replace(state_anchor,state_insert,1)

# Replace the entire Read-more discovery block inside the !rmCarry hot path.
# Direct-desc stays first. If the truncated bubble exists but the desc node is one
# accessibility frame late, arm the guard and poll only for the real node.
hs=s.find('            val descTargetNew=findReadMoreDescFromNewItemsV15(tfNewItems)')
he=s.find('        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.',hs)
if hs<0 or he<0:
    raise SystemExit('v20 hot region not found')
hot=r'''            val descTargetNew=findReadMoreDescFromNewItemsV15(tfNewItems)
            val descTarget=descTargetNew ?: findNewestReadMoreDescTargetV14()
            if(descTarget!=null){
                rememberReadMoreChainV16(descTarget.node)
                val before=freshReadMoreBandStatsV12(descTarget.rect)
                val t=SystemClock.elapsedRealtime()
                val ok=try{descTarget.node.performAction(AccessibilityNodeInfo.ACTION_CLICK)}catch(_:Throwable){false}
                val done=SystemClock.elapsedRealtime()
                if(ok){
                    rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done
                    rmClickMs=done-t; rmExpanded=0L; rmPolls=0
                    rmMethod=if(descTargetNew!=null) "DESC_NEWITEM" else "DESC_ROOT"
                    rmDescWaitMsV20=0L; rmDescWaitPollsV20=0
                    waitForReadMoreExpansionV12(descTarget.rect,before,t,0,false)
                    return
                }
            }

            val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)
            if(readMoreTarget!=null){
                rememberReadMoreChainV16(readMoreTarget.node)
                rmUsed=true; rmPending=true; rmCarry=true
                rmStarted=SystemClock.elapsedRealtime(); rmClicked=0L; rmExpanded=0L
                rmClickMs=0L; rmPolls=0; rmMethod="DESC_WAIT"
                rmDescWaitMsV20=0L; rmDescWaitPollsV20=0
                waitForReadMoreDescV20(readMoreTarget.rect,rmStarted,0)
                return
            }
        }

'''
s=s[:hs]+hot+s[he:]

# Replace v18's expansion waiter (which retried by gesture) with two direct-node
# waiters. Both have a ~120 ms ceiling (24 x 5 ms nominal), but return immediately
# as soon as the exact WhatsApp Read-more node is available/expansion is proven.
a=s.find('    private fun waitForReadMoreExpansionV12(')
b=s.find('    private fun waitForTextDirectSendReadyV5(',a)
if a<0 or b<0:
    raise SystemExit('v20 wait region not found')
waiters=r'''    private fun waitForReadMoreDescV20(target:Rect,startedAt:Long,poll:Int){
        if(!rmPending)return
        val desc=findNewestReadMoreDescTargetV14()
        if(desc!=null){
            // Re-anchor on the fresh real control; the original ellipsis node may
            // already have been rebuilt by WhatsApp.
            rememberReadMoreChainV16(desc.node)
            val before=freshReadMoreBandStatsV12(desc.rect)
            val t=SystemClock.elapsedRealtime()
            val ok=try{desc.node.performAction(AccessibilityNodeInfo.ACTION_CLICK)}catch(_:Throwable){false}
            val done=SystemClock.elapsedRealtime()
            if(ok){
                rmDescWaitMsV20=t-startedAt; rmDescWaitPollsV20=poll
                rmClicked=done; rmClickMs=done-t; rmMethod="DESC_POLL"
                waitForReadMoreExpansionV12(desc.rect,before,t,0,false)
                return
            }
        }
        if(poll<24){
            handler.postDelayed({waitForReadMoreDescV20(target,startedAt,poll+1)},5L)
            return
        }

        rmDescWaitMsV20=SystemClock.elapsedRealtime()-startedAt; rmDescWaitPollsV20=poll
        absorbCurrentTextBaselineV18()
        rmPending=false; rmCarry=false
        val waited=rmDescWaitMsV20
        rmUsed=false
        Prefs.setStatus(this,"TEXT v20: mensagem truncada, mas o botao real Ler mais nao apareceu em ${waited}ms. Nenhuma rota parcial foi enviada.")
    }

    private fun waitForReadMoreExpansionV12(
        target:Rect,
        before:ReadMoreBandStatsV12,
        startedAt:Long,
        poll:Int,
        retried:Boolean
    ){
        val proof=freshReadMoreProofV18(target)
        rmProofV18="${proof.source}:before=${rmBeforeAnchorLenV18},after=${proof.chars},trunc=${proof.stillTruncated},stage=DESC_ONLY"
        if(proof.expanded){
            rmExpanded=SystemClock.elapsedRealtime(); rmPolls=poll; rmPending=false; rmCarry=true
            handler.post{analyzeCurrentWindow()}
            return
        }

        // If ACTION_CLICK returned true but WhatsApp did not expand, reacquire the
        // exact contentDescription node and retry ACTION_CLICK. Never gesture.
        if(poll==5 || poll==12){
            val desc=findNewestReadMoreDescTargetV14()
            if(desc!=null){
                val ok=try{desc.node.performAction(AccessibilityNodeInfo.ACTION_CLICK)}catch(_:Throwable){false}
                if(ok)rmMethod=rmMethod+"+DESC_RETRY"
            }
        }

        if(poll<24){
            handler.postDelayed({waitForReadMoreExpansionV12(target,before,startedAt,poll+1,retried)},5L)
            return
        }

        // Strict safety is preserved: never release a still-truncated message to
        // the route parser.
        rmPolls=poll
        absorbCurrentTextBaselineV18()
        rmPending=false; rmCarry=false
        val failProof=rmProofV18
        val failMethod=rmMethod
        rmUsed=false
        Prefs.setStatus(this,"TEXT v20: Ler mais nao expandiu/nao foi comprovado | metodo=$failMethod | $failProof | nenhuma rota enviada.")
    }

'''
s=s[:a]+waiters+s[b:]

# Carry the desc-wait timing into the successful diagnostic.
copy_old='tdReadMoreUsed=rmUsed; tdReadMoreClicked=rmClicked; tdReadMoreExpanded=rmExpanded; tdReadMoreClickMs=rmClickMs; tdReadMorePolls=rmPolls; tdReadMoreMethod=rmMethod; tdReadMoreParseSourceV16=rmParseSourceV16; tdReadMoreParseItemsV16=rmParseItemsV16; tdReadMoreProofV18=rmProofV18'
copy_new=copy_old+'; tdReadMoreDescWaitMsV20=rmDescWaitMsV20; tdReadMoreDescWaitPollsV20=rmDescWaitPollsV20'
if copy_old not in s:
    raise SystemExit('v20 diagnostic copy anchor not found')
s=s.replace(copy_old,copy_new,1)

report_old='appendLine("readMoreProof=$tdReadMoreProofV18")'
report_new=report_old+'\n                appendLine("readMoreDescWait=${tdReadMoreDescWaitMsV20}ms | readMoreDescPolls=$tdReadMoreDescWaitPollsV20")'
if report_old not in s:
    raise SystemExit('v20 diagnostic report anchor not found')
s=s.replace(report_old,report_new,1)

reset_old='rmNodeChainV16=emptyList(); rmParseSourceV16=""; rmParseItemsV16=0; rmParseRetriesV16=0; rmTargetRectV17=Rect(); rmAnchorV17=""; rmBeforeAnchorLenV18=0; rmGestureStageV18=0; rmProofV18=""'
reset_new=reset_old+'; rmDescWaitMsV20=0L; rmDescWaitPollsV20=0'
if reset_old not in s:
    raise SystemExit('v20 reset anchor not found')
s=s.replace(reset_old,reset_new,1)

s=s.replace(old_header,new_header,1)

# Verification: the active hot path and active expansion waiter must be desc-only.
for m in [
    new_header,
    'private fun waitForReadMoreDescV20(',
    'rmMethod="DESC_POLL"',
    'stage=DESC_ONLY',
    'readMoreDescWait=${tdReadMoreDescWaitMsV20}ms',
    'TEXT v20: mensagem truncada, mas o botao real Ler mais nao apareceu',
    'TEXT v20: Ler mais nao expandiu/nao foi comprovado',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('READ MORE DESC POLL v20 verify failed: '+m)

# The old gesture helper may remain in source for compatibility, but neither the
# Read-more hot path nor the expansion waiter may call it anymore.
hot_now=s[hs:s.find('        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.',hs)]
wait_now=s[s.find('    private fun waitForReadMoreDescV20('):s.find('    private fun waitForTextDirectSendReadyV5(',s.find('    private fun waitForReadMoreDescV20('))]
for forbidden in ['clickReadMoreV12(', 'tapReadMoreRectV18(', 'tapReadMoreRectV12(']:
    if forbidden in hot_now or forbidden in wait_now:
        raise SystemExit('v20 active path still contains gesture fallback: '+forbidden)

S.write_text(s,encoding='utf-8')
print('READ MORE DESC POLL v20 applied: exact desc node polling, ACTION_CLICK only, ~120ms ceiling, no coordinate gestures; v18 proof + TEXT v6 + IMAGE v9 preserved')
