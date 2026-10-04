from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v27 | TEXT v6 + PRE CLICK DIAG + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v28 | TEXT v6 + EVENT DESC FAST + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'if (processing) return\n        if (rmPending) return',
    'private fun waitForReadMoreDescV20(startedAt:Long,poll:Int,generation:Long){',
    'val waitStart=SystemClock.elapsedRealtime()',
    'handler.postDelayed({waitForReadMoreDescV20(waitStart,1,waitGeneration)},5L)',
    'handler.postDelayed({waitForReadMoreDescV20(startedAt,poll+1,generation)},5L)',
    'directProofV26=used=$tdV26DirectUsed',
    'preClickV27=collect->tail=',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('EVENT DESC FAST v28 wrong base: '+m)

# v28 goal:
# When the truncated new bubble is already known but WhatsApp has not yet exposed
# the clickable contentDescription="Ler mais" in the first tree, do not hammer the
# entire accessibility root every 5 ms. Accessibility events are the natural signal
# that the inline control appeared. Search only event.source + a couple of parents,
# restricted to the vertical band of the same truncated bubble. Keep sparse full-root
# polling as a safety fallback for devices/frames that do not emit a useful event.

state_anchor='    private var tdV27RetryBandMs=0L\n'
state_insert=state_anchor+'''    private var rmV28WaitRect=Rect()
    private var rmV28WaitStartedAt=0L
    private var rmV28EventChecks=0
    private var rmV28EventSearchTotalMs=0L
    private var rmV28EventSearchMaxMs=0L
    private var rmV28EventHitAfterWait=-1L
    private var tdV28EventChecks=0
    private var tdV28EventSearchTotalMs=0L
    private var tdV28EventSearchMaxMs=0L
    private var tdV28EventHitAfterWait=-1L
'''
if state_anchor not in s:
    raise SystemExit('v28 state anchor not found')
s=s.replace(state_anchor,state_insert,1)

# Small event-local search. The whole-root helper is intentionally NOT used here.
helper_anchor='    private fun waitForReadMoreDescV20(startedAt:Long,poll:Int,generation:Long){\n'
helper=r'''    private fun findReadMoreDescNearEventV28(source:AccessibilityNodeInfo?,band:Rect):ReadMoreDescTargetV14? {
        if(source==null || band.isEmpty)return null
        val roots=ArrayList<AccessibilityNodeInfo>(3)
        var cur:AccessibilityNodeInfo?=source
        var up=0
        while(cur!=null && up<3){
            roots.add(cur)
            cur=try{cur.parent}catch(_:Throwable){null}
            up++
        }
        val minY=band.top-180
        val maxY=band.bottom+300
        var best:ReadMoreDescTargetV14?=null
        for(r0 in roots){
            val q=java.util.ArrayDeque<AccessibilityNodeInfo>()
            q.add(r0)
            var visited=0
            while(!q.isEmpty() && visited<64){
                val n=q.removeLast(); visited++
                val desc=try{n.contentDescription?.toString().orEmpty()}catch(_:Throwable){""}
                if(isExactReadMoreV12(desc)){
                    val r=Rect()
                    try{n.getBoundsInScreen(r)}catch(_:Throwable){}
                    val clickable=try{n.isClickable}catch(_:Throwable){false}
                    val enabled=try{n.isEnabled}catch(_:Throwable){false}
                    if(clickable && enabled && !r.isEmpty && r.bottom>=minY && r.top<=maxY){
                        val old=best
                        if(old==null || r.bottom>old.rect.bottom)best=ReadMoreDescTargetV14(n,r)
                    }
                }
                val cc=try{n.childCount}catch(_:Throwable){0}
                for(i in 0 until cc){
                    try{n.getChild(i)?.let{q.add(it)}}catch(_:Throwable){}
                }
            }
            if(best!=null)break
        }
        return best
    }

'''
if helper_anchor not in s:
    raise SystemExit('v28 helper anchor not found')
s=s.replace(helper_anchor,helper+helper_anchor,1)

# While a DESC wait is active, use the arriving WhatsApp event itself as the fast
# discovery path. Once a click is accepted, retire the v21 generation before
# starting the unchanged strict expansion proof.
event_old='''        if (processing) return
        if (rmPending) return
'''
event_new=r'''        if (processing) return
        if (rmPending) {
            val v28Generation=rmDescWaitActiveGenerationV21
            if(v28Generation!=0L && !rmV28WaitRect.isEmpty){
                val v28SearchStart=SystemClock.elapsedRealtime()
                val v28Target=try{findReadMoreDescNearEventV28(event.source,rmV28WaitRect)}catch(_:Throwable){null}
                val v28SearchCost=SystemClock.elapsedRealtime()-v28SearchStart
                rmV28EventChecks++
                rmV28EventSearchTotalMs+=v28SearchCost
                if(v28SearchCost>rmV28EventSearchMaxMs)rmV28EventSearchMaxMs=v28SearchCost
                if(v28Target!=null && v28Generation==rmDescWaitActiveGenerationV21){
                    rememberReadMoreChainV16(v28Target.node)
                    val before=freshReadMoreBandStatsV12(v28Target.rect)
                    val t=SystemClock.elapsedRealtime()
                    val ok=try{v28Target.node.performAction(AccessibilityNodeInfo.ACTION_CLICK)}catch(_:Throwable){false}
                    val done=SystemClock.elapsedRealtime()
                    if(v28Generation!=rmDescWaitActiveGenerationV21)return
                    if(ok){
                        rmDescWaitActiveGenerationV21=0L
                        rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done
                        rmClickMs=done-t; rmExpanded=0L; rmPolls=0; rmMethod="DESC_EVENT_V28"
                        rmDescWaitMsV20=if(rmV28WaitStartedAt>0L) t-rmV28WaitStartedAt else 0L
                        rmDescWaitPollsV20=0
                        rmV28EventHitAfterWait=rmDescWaitMsV20
                        waitForReadMoreExpansionV12(v28Target.rect,before,t,0,false)
                        return
                    }
                }
            }
            return
        }
'''
if event_old not in s:
    raise SystemExit('v28 event rmPending anchor not found')
s=s.replace(event_old,event_new,1)

# Remember the same truncated bubble band that caused DESC_WAIT. This is the safety
# fence used by the event-local search above.
wait_start_old='''                val waitStart=SystemClock.elapsedRealtime()
                rmDescWaitGenerationV21++
'''
wait_start_new='''                val waitStart=SystemClock.elapsedRealtime()
                rmV28WaitRect=Rect(readMoreTarget.rect)
                rmV28WaitStartedAt=waitStart
                rmDescWaitGenerationV21++
'''
if wait_start_old not in s:
    raise SystemExit('v28 wait-start anchor not found')
s=s.replace(wait_start_old,wait_start_new,1)

# If the normal DESC_NEWITEM/DESC_ROOT path wins, retire any old event-wait band.
direct_clear_old='''                    rmDescWaitMsV20=0L; rmDescWaitPollsV20=0
                    rmMethod=if(descTargetNew!=null) "DESC_NEWITEM" else "DESC_ROOT"
'''
direct_clear_new='''                    rmDescWaitMsV20=0L; rmDescWaitPollsV20=0
                    rmV28WaitRect.setEmpty(); rmV28WaitStartedAt=0L
                    rmMethod=if(descTargetNew!=null) "DESC_NEWITEM" else "DESC_ROOT"
'''
if direct_clear_old not in s:
    raise SystemExit('v28 direct-clear anchor not found')
s=s.replace(direct_clear_old,direct_clear_new,1)

# Full-root polling remains as a fallback, but no longer runs every 5ms and monopolizes
# the main Looper. Event-source discovery should normally win before these scans.
s=s.replace('handler.postDelayed({waitForReadMoreDescV20(waitStart,1,waitGeneration)},5L)',
            'handler.postDelayed({waitForReadMoreDescV20(waitStart,1,waitGeneration)},20L)',1)
s=s.replace('handler.postDelayed({waitForReadMoreDescV20(startedAt,poll+1,generation)},5L)',
            'handler.postDelayed({waitForReadMoreDescV20(startedAt,poll+1,generation)},20L)',1)

# Clear the event band if the existing v21 timeout gives up this generation.
timeout_old='''        rmDescWaitActiveGenerationV21=0L
        absorbCurrentTextBaselineV18()
        rmPending=false; rmCarry=false; rmUsed=false
'''
timeout_new='''        rmDescWaitActiveGenerationV21=0L
        rmV28WaitRect.setEmpty(); rmV28WaitStartedAt=0L
        absorbCurrentTextBaselineV18()
        rmPending=false; rmCarry=false; rmUsed=false
'''
if timeout_old not in s:
    raise SystemExit('v28 timeout anchor not found')
s=s.replace(timeout_old,timeout_new,1)

# Snapshot event-fast diagnostics before tdBegin clears operational Read-more state.
copy_anchor='tdV27RetryBandMs=rmV27RetryBandMs'
copy_insert=copy_anchor+'''; tdV28EventChecks=rmV28EventChecks; tdV28EventSearchTotalMs=rmV28EventSearchTotalMs; tdV28EventSearchMaxMs=rmV28EventSearchMaxMs; tdV28EventHitAfterWait=rmV28EventHitAfterWait'''
if copy_anchor not in s:
    raise SystemExit('v28 diagnostic snapshot anchor not found')
s=s.replace(copy_anchor,copy_insert,1)

# Reset v28 temporary metrics with the existing v27 temporary reset.
reset_anchor='''rmV27TailReadyAt=0L; rmV27DescStartAt=0L; rmV27DescNewMs=0L; rmV27DescRootMs=0L; rmV27TargetScanMs=0L; rmV27BandMs=0L; rmV27ClickDoneAt=0L; rmV27RetrySearchCalls=0; rmV27RetrySearchTotalMs=0L; rmV27RetrySearchMaxMs=0L; rmV27RetryBandMs=0L'''
reset_insert=reset_anchor+'''; rmV28WaitRect.setEmpty(); rmV28WaitStartedAt=0L; rmV28EventChecks=0; rmV28EventSearchTotalMs=0L; rmV28EventSearchMaxMs=0L; rmV28EventHitAfterWait=-1L'''
if reset_anchor not in s:
    raise SystemExit('v28 reset anchor not found')
s=s.replace(reset_anchor,reset_insert,1)

# Add a compact A/B line after the v27 pre-click line.
report_anchor='''                    appendLine("preClickV27=collect->tail=${tdD(tdV27CollectDoneAt,tdV27TailReadyAt)} | tail->desc=${tdD(tdV27TailReadyAt,tdV27DescStartAt)} | descNew=${tdV27DescNewMs}ms | descRoot=${tdV27DescRootMs}ms | targetScan=${tdV27TargetScanMs}ms | band=${tdV27BandMs}ms | collect->click=${tdD(tdV27CollectDoneAt,tdV27ClickDoneAt)}")
'''
report_insert=report_anchor+'''                    appendLine("eventDescV28=checks=$tdV28EventChecks | searchTotal=${tdV28EventSearchTotalMs}ms | searchMax=${tdV28EventSearchMaxMs}ms | hitAfterWait=${tdV28EventHitAfterWait}ms | fallbackPoll=20ms | method=$tdReadMoreMethod")
'''
if report_anchor not in s:
    raise SystemExit('v28 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'private fun findReadMoreDescNearEventV28(',
    'rmMethod="DESC_EVENT_V28"',
    'rmV28WaitRect=Rect(readMoreTarget.rect)',
    'waitForReadMoreDescV20(waitStart,1,waitGeneration)},20L',
    'waitForReadMoreDescV20(startedAt,poll+1,generation)},20L',
    'eventDescV28=checks=',
    'fallbackPoll=20ms',
    'directProofV26=used=$tdV26DirectUsed',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('EVENT DESC FAST v28 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('EVENT DESC FAST v28 applied: event.source exact Read-more fast path + 20ms sparse full-root fallback; v26 proof/direct parser and IMAGE v9 preserved')
