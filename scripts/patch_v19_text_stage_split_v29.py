from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v27 | TEXT v6 + PRE CLICK DIAG + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v29 | TEXT v6 + STAGE SPLIT DIAG + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'if (!isTargetGroup(items, group)) {',
    'val tfNewItemsReverse = ArrayList<NodeItem>(8)',
    'val tfNewItems = tfNewItemsReverse.asReversed()',
    'tdV27RetryBandMs=rmV27RetryBandMs',
    'preClickV27=collect->tail=',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('STAGE SPLIT v29 wrong base: '+m)

state_anchor='    private var tdV27RetryBandMs=0L\n'
state_insert=state_anchor+'''    private var rmV29GroupStartAt=0L
    private var rmV29GroupDoneAt=0L
    private var rmV29GroupCheckMs=0L
    private var rmV29TailLoopStartAt=0L
    private var rmV29TailLoopDoneAt=0L
    private var rmV29TailLoopMs=0L
    private var tdV29GroupStartAt=0L
    private var tdV29GroupDoneAt=0L
    private var tdV29GroupCheckMs=0L
    private var tdV29TailLoopStartAt=0L
    private var tdV29TailLoopDoneAt=0L
    private var tdV29TailLoopMs=0L
'''
if state_anchor not in s:
    raise SystemExit('v29 state anchor not found')
s=s.replace(state_anchor,state_insert,1)

# Split the first expensive region after collectNodeItems: target-group validation.
group_old='''        if (!isTargetGroup(items, group)) {
'''
group_new='''        rmV29GroupStartAt=SystemClock.elapsedRealtime()
        val v29TargetGroup=isTargetGroup(items, group)
        rmV29GroupDoneAt=SystemClock.elapsedRealtime()
        rmV29GroupCheckMs=rmV29GroupDoneAt-rmV29GroupStartAt
        if (!v29TargetGroup) {
'''
if group_old not in s:
    raise SystemExit('v29 group-check anchor not found')
s=s.replace(group_old,group_new,1)

# Time only the actual TEXT v6 tail-delta loop, excluding validation before it.
tail_start_old='''        val tfNewItemsReverse = ArrayList<NodeItem>(8)
'''
tail_start_new='''        rmV29TailLoopStartAt=SystemClock.elapsedRealtime()
        val tfNewItemsReverse = ArrayList<NodeItem>(8)
'''
if tail_start_old not in s:
    raise SystemExit('v29 tail start anchor not found')
s=s.replace(tail_start_old,tail_start_new,1)

tail_done_old='''        val tfNewItems = tfNewItemsReverse.asReversed()
'''
tail_done_new='''        val tfNewItems = tfNewItemsReverse.asReversed()
        rmV29TailLoopDoneAt=SystemClock.elapsedRealtime()
        rmV29TailLoopMs=rmV29TailLoopDoneAt-rmV29TailLoopStartAt
'''
if tail_done_old not in s:
    raise SystemExit('v29 tail done anchor not found')
s=s.replace(tail_done_old,tail_done_new,1)

# Snapshot alongside v27 diagnostic state before Read-more temp state is cleared.
copy_anchor='tdV27RetryBandMs=rmV27RetryBandMs'
copy_insert=copy_anchor+'''; tdV29GroupStartAt=rmV29GroupStartAt; tdV29GroupDoneAt=rmV29GroupDoneAt; tdV29GroupCheckMs=rmV29GroupCheckMs; tdV29TailLoopStartAt=rmV29TailLoopStartAt; tdV29TailLoopDoneAt=rmV29TailLoopDoneAt; tdV29TailLoopMs=rmV29TailLoopMs'''
if copy_anchor not in s:
    raise SystemExit('v29 copy anchor not found')
s=s.replace(copy_anchor,copy_insert,1)

reset_anchor='''rmV27TailReadyAt=0L; rmV27DescStartAt=0L; rmV27DescNewMs=0L; rmV27DescRootMs=0L; rmV27TargetScanMs=0L; rmV27BandMs=0L; rmV27ClickDoneAt=0L; rmV27RetrySearchCalls=0; rmV27RetrySearchTotalMs=0L; rmV27RetrySearchMaxMs=0L; rmV27RetryBandMs=0L'''
reset_insert=reset_anchor+'''; rmV29GroupStartAt=0L; rmV29GroupDoneAt=0L; rmV29GroupCheckMs=0L; rmV29TailLoopStartAt=0L; rmV29TailLoopDoneAt=0L; rmV29TailLoopMs=0L'''
if reset_anchor not in s:
    raise SystemExit('v29 reset anchor not found')
s=s.replace(reset_anchor,reset_insert,1)

report_anchor='''                    appendLine("preClickV27=collect->tail=${tdD(tdV27CollectDoneAt,tdV27TailReadyAt)} | tail->desc=${tdD(tdV27TailReadyAt,tdV27DescStartAt)} | descNew=${tdV27DescNewMs}ms | descRoot=${tdV27DescRootMs}ms | targetScan=${tdV27TargetScanMs}ms | band=${tdV27BandMs}ms | collect->click=${tdD(tdV27CollectDoneAt,tdV27ClickDoneAt)}")
'''
report_insert=report_anchor+'''                    appendLine("stageV29=collect->group=${tdD(tdV27CollectDoneAt,tdV29GroupStartAt)} | groupCheck=${tdV29GroupCheckMs}ms | groupDone->tailStart=${tdD(tdV29GroupDoneAt,tdV29TailLoopStartAt)} | tailLoop=${tdV29TailLoopMs}ms | tailDone->desc=${tdD(tdV29TailLoopDoneAt,tdV27DescStartAt)} | collect->desc=${tdD(tdV27CollectDoneAt,tdV27DescStartAt)}")
'''
if report_anchor not in s:
    raise SystemExit('v29 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'val v29TargetGroup=isTargetGroup(items, group)',
    'rmV29GroupCheckMs=rmV29GroupDoneAt-rmV29GroupStartAt',
    'rmV29TailLoopStartAt=SystemClock.elapsedRealtime()',
    'rmV29TailLoopMs=rmV29TailLoopDoneAt-rmV29TailLoopStartAt',
    'stageV29=collect->group=',
    'preClickV27=collect->tail=',
    'directProofV26=used=$tdV26DirectUsed',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('STAGE SPLIT v29 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('STAGE SPLIT v29 applied: diagnostic-only split of collect -> group check -> tail loop -> Read-more lookup; v27 behavior preserved')
