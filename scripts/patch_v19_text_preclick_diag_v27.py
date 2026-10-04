from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v26 | TEXT v6 + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v27 | TEXT v6 + PRE CLICK DIAG + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'val tfNewItems = tfNewItemsReverse.asReversed()',
    'val descTargetNew=findReadMoreDescFromNewItemsV15(tfNewItems)',
    'val descTarget=descTargetNew ?: findNewestReadMoreDescTargetV14()',
    'val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)',
    'private fun waitForReadMoreDescV20(startedAt:Long,poll:Int){',
    'val descTarget=try{findNewestReadMoreDescTargetV14()}catch(_:Throwable){null}',
    'directProofV26=used=$tdV26DirectUsed',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('PRE CLICK DIAG v27 wrong base: '+m)

# Diagnostic only. No delay, proof rule, click target, parser, send path or image
# behavior changes. These fields split the time between the first collected tree
# and the actual Read-more ACTION_CLICK.
state_anchor='    private var tdV26Fallback=false\n'
state_insert=state_anchor+'''    private var rmV27TailReadyAt=0L
    private var rmV27DescStartAt=0L
    private var rmV27DescNewMs=0L
    private var rmV27DescRootMs=0L
    private var rmV27TargetScanMs=0L
    private var rmV27BandMs=0L
    private var rmV27ClickDoneAt=0L
    private var rmV27RetrySearchCalls=0
    private var rmV27RetrySearchTotalMs=0L
    private var rmV27RetrySearchMaxMs=0L
    private var rmV27RetryBandMs=0L
    private var tdV27CollectDoneAt=0L
    private var tdV27TailReadyAt=0L
    private var tdV27DescStartAt=0L
    private var tdV27DescNewMs=0L
    private var tdV27DescRootMs=0L
    private var tdV27TargetScanMs=0L
    private var tdV27BandMs=0L
    private var tdV27ClickDoneAt=0L
    private var tdV27RetrySearchCalls=0
    private var tdV27RetrySearchTotalMs=0L
    private var tdV27RetrySearchMaxMs=0L
    private var tdV27RetryBandMs=0L
'''
if state_anchor not in s:
    raise SystemExit('v27 state anchor not found')
s=s.replace(state_anchor,state_insert,1)

# Mark when the cheap TEXT v6 tail delta is ready.
tail_old='''        val tfNewItems = tfNewItemsReverse.asReversed()

        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.
'''
tail_new='''        val tfNewItems = tfNewItemsReverse.asReversed()
        if(primed && tfNewItems.isNotEmpty()) rmV27TailReadyAt=SystemClock.elapsedRealtime()

        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.
'''
if tail_old not in s:
    raise SystemExit('v27 tail anchor not found')
s=s.replace(tail_old,tail_new,1)

# Time the already-collected DESC_NEWITEM lookup and, only on a miss, the fresh-root
# desc lookup. Semantics are identical to the original Elvis expression.
desc_old='''            val descTargetNew=findReadMoreDescFromNewItemsV15(tfNewItems)
            val descTarget=descTargetNew ?: findNewestReadMoreDescTargetV14()
            if(descTarget!=null){
'''
desc_new='''            rmV27DescStartAt=SystemClock.elapsedRealtime()
            val v27DescNewStart=SystemClock.elapsedRealtime()
            val descTargetNew=findReadMoreDescFromNewItemsV15(tfNewItems)
            rmV27DescNewMs=SystemClock.elapsedRealtime()-v27DescNewStart
            val descTarget=if(descTargetNew!=null){
                descTargetNew
            }else{
                val v27RootStart=SystemClock.elapsedRealtime()
                val v27RootTarget=findNewestReadMoreDescTargetV14()
                rmV27DescRootMs=SystemClock.elapsedRealtime()-v27RootStart
                v27RootTarget
            }
            if(descTarget!=null){
'''
if desc_old not in s:
    raise SystemExit('v27 desc lookup block not found')
s=s.replace(desc_old,desc_new,1)

# Time the band snapshot directly before ACTION_CLICK on the immediate desc path.
# v26 timing state is left exactly where it was.
immediate_band_old='''                rememberReadMoreChainV16(descTarget.node)
                val before=freshReadMoreBandStatsV12(descTarget.rect)
                val t=SystemClock.elapsedRealtime()
'''
immediate_band_new='''                rememberReadMoreChainV16(descTarget.node)
                val v27BandStart=SystemClock.elapsedRealtime()
                val before=freshReadMoreBandStatsV12(descTarget.rect)
                rmV27BandMs=SystemClock.elapsedRealtime()-v27BandStart
                val t=SystemClock.elapsedRealtime()
'''
if immediate_band_old not in s:
    raise SystemExit('v27 immediate band anchor not found')
s=s.replace(immediate_band_old,immediate_band_new,1)

# Capture successful click completion on the immediate path.
immediate_ok_old='''                if(ok){
                    rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done
'''
immediate_ok_new='''                if(ok){
                    rmV27ClickDoneAt=done
                    rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done
'''
if immediate_ok_old not in s:
    raise SystemExit('v27 immediate click anchor not found')
s=s.replace(immediate_ok_old,immediate_ok_new,1)

# If no desc node exists yet, time the cheap visible-truncation target lookup before
# entering the existing v20 DESC_RETRY wait.
target_old='''            val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)
            if(readMoreTarget!=null){
'''
target_new='''            val v27TargetStart=SystemClock.elapsedRealtime()
            val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)
            rmV27TargetScanMs=SystemClock.elapsedRealtime()-v27TargetStart
            if(readMoreTarget!=null){
'''
if target_old not in s:
    raise SystemExit('v27 truncated target anchor not found')
s=s.replace(target_old,target_new,1)

# In DESC_RETRY, measure how much of the wall-clock wait is actually spent scanning
# a fresh accessibility root. This distinguishes tree-scan cost from node exposure /
# Handler scheduling delay.
retry_search_old='''        val descTarget=try{findNewestReadMoreDescTargetV14()}catch(_:Throwable){null}
        if(descTarget!=null){
'''
retry_search_new='''        val v27RetrySearchStart=SystemClock.elapsedRealtime()
        val descTarget=try{findNewestReadMoreDescTargetV14()}catch(_:Throwable){null}
        val v27RetrySearchCost=SystemClock.elapsedRealtime()-v27RetrySearchStart
        rmV27RetrySearchCalls++
        rmV27RetrySearchTotalMs+=v27RetrySearchCost
        if(v27RetrySearchCost>rmV27RetrySearchMaxMs) rmV27RetrySearchMaxMs=v27RetrySearchCost
        if(descTarget!=null){
'''
if retry_search_old not in s:
    raise SystemExit('v27 retry search anchor not found')
s=s.replace(retry_search_old,retry_search_new,1)

# This occurrence is inside waitForReadMoreDescV20 because the immediate occurrence
# was already replaced above.
retry_band_old='''            rememberReadMoreChainV16(descTarget.node)
            val before=freshReadMoreBandStatsV12(descTarget.rect)
            val t=SystemClock.elapsedRealtime()
'''
retry_band_new='''            rememberReadMoreChainV16(descTarget.node)
            val v27RetryBandStart=SystemClock.elapsedRealtime()
            val before=freshReadMoreBandStatsV12(descTarget.rect)
            rmV27RetryBandMs=SystemClock.elapsedRealtime()-v27RetryBandStart
            val t=SystemClock.elapsedRealtime()
'''
if retry_band_old not in s:
    raise SystemExit('v27 retry band anchor not found')
s=s.replace(retry_band_old,retry_band_new,1)

# The remaining identical success block belongs to DESC_RETRY. Capture click end.
if immediate_ok_old not in s:
    raise SystemExit('v27 retry click anchor not found')
retry_ok_new='''            if(ok){
                rmV27ClickDoneAt=done
                rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done
'''
s=s.replace(immediate_ok_old,retry_ok_new,1)

# Snapshot v27 diagnostics at the same point the existing Read-more diagnostics are
# copied into td* state, before tdBegin clears temporary state.
copy_anchor='tdV23PollLate1=rmV23PollLate1'
copy_insert=copy_anchor+'''; tdV27CollectDoneAt=rmV26CollectDoneAt; tdV27TailReadyAt=rmV27TailReadyAt; tdV27DescStartAt=rmV27DescStartAt; tdV27DescNewMs=rmV27DescNewMs; tdV27DescRootMs=rmV27DescRootMs; tdV27TargetScanMs=rmV27TargetScanMs; tdV27BandMs=rmV27BandMs; tdV27ClickDoneAt=rmV27ClickDoneAt; tdV27RetrySearchCalls=rmV27RetrySearchCalls; tdV27RetrySearchTotalMs=rmV27RetrySearchTotalMs; tdV27RetrySearchMaxMs=rmV27RetrySearchMaxMs; tdV27RetryBandMs=rmV27RetryBandMs'''
if copy_anchor not in s:
    raise SystemExit('v27 diagnostic snapshot anchor not found')
s=s.replace(copy_anchor,copy_insert,1)

# Reset temporary v27 state alongside v26 state. td* values intentionally survive
# until the final diagnostic is persisted after confirmation.
reset_anchor='''rmV26AnalyzeAt=0L; rmV26CollectDoneAt=0L; rmV26CollectMs=0L; rmV26NewItems=0; rmV26DirectParseMs=0L; rmV26ProofTextChars=0; rmV26Fallback=false'''
reset_insert=reset_anchor+'''; rmV27TailReadyAt=0L; rmV27DescStartAt=0L; rmV27DescNewMs=0L; rmV27DescRootMs=0L; rmV27TargetScanMs=0L; rmV27BandMs=0L; rmV27ClickDoneAt=0L; rmV27RetrySearchCalls=0; rmV27RetrySearchTotalMs=0L; rmV27RetrySearchMaxMs=0L; rmV27RetryBandMs=0L'''
if reset_anchor not in s:
    raise SystemExit('v27 reset anchor not found')
s=s.replace(reset_anchor,reset_insert,1)

# Add compact lines after the v26 A/B line. No WhatsApp message contents are logged.
report_anchor='''                    appendLine("directProofV26=used=$tdV26DirectUsed | proofTextChars=$tdV26ProofTextChars | directParse=${tdV26DirectParseMs}ms | fallbackReanalyze=$tdV26Fallback")
'''
report_insert=report_anchor+'''                    appendLine("preClickV27=collect->tail=${tdD(tdV27CollectDoneAt,tdV27TailReadyAt)} | tail->desc=${tdD(tdV27TailReadyAt,tdV27DescStartAt)} | descNew=${tdV27DescNewMs}ms | descRoot=${tdV27DescRootMs}ms | targetScan=${tdV27TargetScanMs}ms | band=${tdV27BandMs}ms | collect->click=${tdD(tdV27CollectDoneAt,tdV27ClickDoneAt)}")
                    if(tdV27RetrySearchCalls>0){
                        appendLine("descRetryV27=wait=${tdReadMoreDescWaitMsV20}ms | polls=$tdReadMoreDescWaitPollsV20 | rootSearchCalls=$tdV27RetrySearchCalls | rootSearchTotal=${tdV27RetrySearchTotalMs}ms | rootSearchMax=${tdV27RetrySearchMaxMs}ms | finalBand=${tdV27RetryBandMs}ms")
                    }
'''
if report_anchor not in s:
    raise SystemExit('v27 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'rmV27TailReadyAt=SystemClock.elapsedRealtime()',
    'rmV27DescNewMs=SystemClock.elapsedRealtime()-v27DescNewStart',
    'rmV27DescRootMs=SystemClock.elapsedRealtime()-v27RootStart',
    'rmV27TargetScanMs=SystemClock.elapsedRealtime()-v27TargetStart',
    'rmV27RetrySearchTotalMs+=v27RetrySearchCost',
    'preClickV27=collect->tail=',
    'descRetryV27=wait=',
    'directProofV26=used=$tdV26DirectUsed',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('PRE CLICK DIAG v27 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('PRE CLICK DIAG v27 applied: collect->tail->desc lookup->band->click + DESC_RETRY root-scan timing only; v26 behavior preserved')
