from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v18 | TEXT v6 + READ MORE STRICT PROOF + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v20 | TEXT v6 + READ MORE DESC WAIT + STRICT PROOF + DIRECT SEND ====='
required=[
    old_header,
    'private fun findReadMoreDescFromNewItemsV15(',
    'private fun findNewestReadMoreDescTargetV14()',
    'private fun freshReadMoreProofV18(',
    'private fun absorbCurrentTextBaselineV18()',
    'private fun waitForReadMoreExpansionV12(',
    'val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)',
    'TEXT v18: Ler mais NAO expandiu/nao foi comprovado',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('READ MORE DESC WAIT v20 wrong base: '+m)

# v20 fixes the remaining race seen on the M52: the truncated message/ellipsis can
# be present a few milliseconds BEFORE WhatsApp exposes the real clickable
# android.view.View whose contentDescription is "Ler mais". v18 immediately fell
# back to blind gestures in that window. v20 never gestures on a truncated route:
# it briefly polls for the real desc node and clicks ACTION_CLICK only.

state_anchor='    private var tdReadMoreProofV18=""\n'
state_insert='''    private var tdReadMoreProofV18=""
    private var rmDescWaitMsV20=0L; private var rmDescWaitPollsV20=0
    private var tdReadMoreDescWaitMsV20=0L; private var tdReadMoreDescWaitPollsV20=0
'''
if state_anchor not in s:
    raise SystemExit('v20 state anchor not found')
s=s.replace(state_anchor,state_insert,1)

# Add the retry helper immediately before the send-ready helper. Polling is only
# entered when a NEW truncated bubble exists but no real Read-more desc node was
# available in the first accessibility frame. Normal routes do not pass here.
helper_anchor='    private fun waitForTextDirectSendReadyV5('
helper=r'''    private fun waitForReadMoreDescV20(startedAt:Long,poll:Int){
        if(!rmPending)return

        val descTarget=try{findNewestReadMoreDescTargetV14()}catch(_:Throwable){null}
        if(descTarget!=null){
            rememberReadMoreChainV16(descTarget.node)
            val before=freshReadMoreBandStatsV12(descTarget.rect)
            val t=SystemClock.elapsedRealtime()
            val ok=try{descTarget.node.performAction(AccessibilityNodeInfo.ACTION_CLICK)}catch(_:Throwable){false}
            val done=SystemClock.elapsedRealtime()
            if(ok){
                rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done
                rmClickMs=done-t; rmExpanded=0L; rmPolls=0; rmMethod="DESC_RETRY"
                rmDescWaitMsV20=t-startedAt; rmDescWaitPollsV20=poll
                waitForReadMoreExpansionV12(descTarget.rect,before,t,0,false)
                return
            }
        }

        val now=SystemClock.elapsedRealtime()
        if(now-startedAt<120L){
            handler.postDelayed({waitForReadMoreDescV20(startedAt,poll+1)},5L)
            return
        }

        // Safety: after ~120 ms without a real clickable desc node, never parse
        // the visible partial route. Absorb the current truncated text. If WhatsApp
        // exposes the desc node later as a new accessibility item, the normal
        // DESC_NEWITEM path can still open it and parse the full expanded bubble.
        rmDescWaitMsV20=now-startedAt; rmDescWaitPollsV20=poll
        absorbCurrentTextBaselineV18()
        rmPending=false; rmCarry=false; rmUsed=false
        Prefs.setStatus(this,"TEXT v20: rota truncada detectada, mas o botao Ler mais real nao apareceu em ${rmDescWaitMsV20}ms (${rmDescWaitPollsV20} polls). Nenhuma rota parcial foi enviada.")
    }

'''
if helper_anchor not in s:
    raise SystemExit('v20 helper anchor not found')
s=s.replace(helper_anchor,helper+helper_anchor,1)

# Replace only the old gesture fallback. The fast direct-desc path immediately
# above remains untouched. When ellipsis/read-more text is visible but the desc
# node is not ready, block the analyzer and wait for the real node instead.
old_fallback=r'''            val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)
            if(readMoreTarget!=null){
                rememberReadMoreChainV16(readMoreTarget.node)
                val before=freshReadMoreBandStatsV12(readMoreTarget.rect)
                val t=SystemClock.elapsedRealtime()
                val click=clickReadMoreV12(readMoreTarget)
                val done=SystemClock.elapsedRealtime()
                if(click.first){
                    rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done
                    rmClickMs=done-t; rmExpanded=0L; rmPolls=0; rmMethod=click.second
                    waitForReadMoreExpansionV12(readMoreTarget.rect,before,t,0,false)
                    return
                }
                // A visible truncated bubble must never reach the parser.
                handler.postDelayed({analyzeCurrentWindow()},20L)
                return
            }
'''
new_fallback=r'''            val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)
            if(readMoreTarget!=null){
                // Do NOT use GESTURE/G2/G3/G4/G5. The M52 trace proved those can
                // miss the inline label. Wait briefly for WhatsApp to expose the
                // actual clickable contentDescription="Ler mais" node instead.
                val waitStart=SystemClock.elapsedRealtime()
                rmPending=true; rmCarry=false; rmUsed=false
                rmDescWaitMsV20=0L; rmDescWaitPollsV20=0
                handler.postDelayed({waitForReadMoreDescV20(waitStart,1)},5L)
                return
            }
'''
if old_fallback not in s:
    raise SystemExit('v20 old gesture fallback block not found')
s=s.replace(old_fallback,new_fallback,1)

# Copy retry timing into the successful RAM diagnostic.
copy_old='tdReadMoreUsed=rmUsed; tdReadMoreClicked=rmClicked; tdReadMoreExpanded=rmExpanded; tdReadMoreClickMs=rmClickMs; tdReadMorePolls=rmPolls; tdReadMoreMethod=rmMethod; tdReadMoreParseSourceV16=rmParseSourceV16; tdReadMoreParseItemsV16=rmParseItemsV16; tdReadMoreProofV18=rmProofV18'
copy_new=copy_old+'; tdReadMoreDescWaitMsV20=rmDescWaitMsV20; tdReadMoreDescWaitPollsV20=rmDescWaitPollsV20'
if copy_old not in s:
    raise SystemExit('v20 diagnostic copy anchor not found')
s=s.replace(copy_old,copy_new,1)

report_old='                appendLine("readMoreProof=$tdReadMoreProofV18")\n'
report_new=report_old+'                if(tdReadMoreDescWaitMsV20>0L) appendLine("readMoreDescWait=${tdReadMoreDescWaitMsV20}ms | descWaitPolls=$tdReadMoreDescWaitPollsV20")\n'
if report_old not in s:
    raise SystemExit('v20 report anchor not found')
s=s.replace(report_old,report_new,1)

# Reset v20 retry state with the existing v18 Read-more state.
reset_old='rmBeforeAnchorLenV18=0; rmGestureStageV18=0; rmProofV18=""'
reset_new=reset_old+'; rmDescWaitMsV20=0L; rmDescWaitPollsV20=0'
if reset_old not in s:
    raise SystemExit('v20 reset anchor not found')
s=s.replace(reset_old,reset_new,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'private fun waitForReadMoreDescV20(',
    'rmMethod="DESC_RETRY"',
    'now-startedAt<120L',
    'handler.postDelayed({waitForReadMoreDescV20(waitStart,1)},5L)',
    'Nenhuma rota parcial foi enviada.',
    'readMoreDescWait=${tdReadMoreDescWaitMsV20}ms',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('READ MORE DESC WAIT v20 verify failed: '+m)

# The hot path must no longer invoke clickReadMoreV12 on the truncated target.
if 'val click=clickReadMoreV12(readMoreTarget)' in s:
    raise SystemExit('v20 verify failed: old gesture hot path still present')

S.write_text(s,encoding='utf-8')
print('READ MORE DESC WAIT v20 applied: no blind gestures; 5ms polling up to ~120ms for real contentDescription node; v18 strict proof/TEXT v6/IMAGE v9 preserved')
