from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v27 | TEXT v6 + PRE CLICK DIAG + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v29 | TEXT v6 + LAZY ADMIN CHECK + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'val messageEditorAvailable = findMessageEditor(items) != null',
    'val adminLockedGroupNow = isAdminLockedGroup(items)',
    'val tfNewItemsReverse = ArrayList<NodeItem>(8)',
    'val tfNewItems = tfNewItemsReverse.asReversed()',
    'tdV27RetryBandMs=rmV27RetryBandMs',
    'preClickV27=collect->tail=',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('LAZY ADMIN CHECK v29 wrong base: '+m)

state_anchor='    private var tdV27RetryBandMs=0L\n'
state_insert=state_anchor+'''    private var rmV29EditorStartAt=0L
    private var rmV29EditorDoneAt=0L
    private var rmV29EditorMs=0L
    private var rmV29AdminMs=0L
    private var rmV29AdminSkipped=false
    private var rmV29TailLoopStartAt=0L
    private var rmV29TailLoopDoneAt=0L
    private var rmV29TailLoopMs=0L
    private var tdV29EditorStartAt=0L
    private var tdV29EditorDoneAt=0L
    private var tdV29EditorMs=0L
    private var tdV29AdminMs=0L
    private var tdV29AdminSkipped=false
    private var tdV29TailLoopStartAt=0L
    private var tdV29TailLoopDoneAt=0L
    private var tdV29TailLoopMs=0L
'''
if state_anchor not in s:
    raise SystemExit('v29 state anchor not found')
s=s.replace(state_anchor,state_insert,1)

# A/B operational change: if the editor exists, the conversation is already known
# to be writable. The expensive admin-lock detector is only relevant when editor is
# absent. Existing state semantics remain identical: editor present clears the
# remembered admin lock; editor absent still executes the full stable detector.
admin_old='''        val messageEditorAvailable = findMessageEditor(items) != null
        val adminLockedGroupNow = isAdminLockedGroup(items)

        if (messageEditorAvailable) {
'''
admin_new='''        rmV29EditorStartAt=SystemClock.elapsedRealtime()
        val messageEditorAvailable = findMessageEditor(items) != null
        rmV29EditorDoneAt=SystemClock.elapsedRealtime()
        rmV29EditorMs=rmV29EditorDoneAt-rmV29EditorStartAt

        val v29AdminStart=SystemClock.elapsedRealtime()
        val adminLockedGroupNow = if(messageEditorAvailable){
            rmV29AdminSkipped=true
            false
        }else{
            rmV29AdminSkipped=false
            isAdminLockedGroup(items)
        }
        rmV29AdminMs=SystemClock.elapsedRealtime()-v29AdminStart

        if (messageEditorAvailable) {
'''
if admin_old not in s:
    raise SystemExit('v29 admin block anchor not found')
s=s.replace(admin_old,admin_new,1)

# Time only the actual TEXT v6 tail-delta loop.
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

copy_anchor='tdV27RetryBandMs=rmV27RetryBandMs'
copy_insert=copy_anchor+'''; tdV29EditorStartAt=rmV29EditorStartAt; tdV29EditorDoneAt=rmV29EditorDoneAt; tdV29EditorMs=rmV29EditorMs; tdV29AdminMs=rmV29AdminMs; tdV29AdminSkipped=rmV29AdminSkipped; tdV29TailLoopStartAt=rmV29TailLoopStartAt; tdV29TailLoopDoneAt=rmV29TailLoopDoneAt; tdV29TailLoopMs=rmV29TailLoopMs'''
if copy_anchor not in s:
    raise SystemExit('v29 copy anchor not found')
s=s.replace(copy_anchor,copy_insert,1)

reset_anchor='''rmV27TailReadyAt=0L; rmV27DescStartAt=0L; rmV27DescNewMs=0L; rmV27DescRootMs=0L; rmV27TargetScanMs=0L; rmV27BandMs=0L; rmV27ClickDoneAt=0L; rmV27RetrySearchCalls=0; rmV27RetrySearchTotalMs=0L; rmV27RetrySearchMaxMs=0L; rmV27RetryBandMs=0L'''
reset_insert=reset_anchor+'''; rmV29EditorStartAt=0L; rmV29EditorDoneAt=0L; rmV29EditorMs=0L; rmV29AdminMs=0L; rmV29AdminSkipped=false; rmV29TailLoopStartAt=0L; rmV29TailLoopDoneAt=0L; rmV29TailLoopMs=0L'''
if reset_anchor not in s:
    raise SystemExit('v29 reset anchor not found')
s=s.replace(reset_anchor,reset_insert,1)

report_anchor='''                    appendLine("preClickV27=collect->tail=${tdD(tdV27CollectDoneAt,tdV27TailReadyAt)} | tail->desc=${tdD(tdV27TailReadyAt,tdV27DescStartAt)} | descNew=${tdV27DescNewMs}ms | descRoot=${tdV27DescRootMs}ms | targetScan=${tdV27TargetScanMs}ms | band=${tdV27BandMs}ms | collect->click=${tdD(tdV27CollectDoneAt,tdV27ClickDoneAt)}")
'''
report_insert=report_anchor+'''                    appendLine("lazyAdminV29=collect->editor=${tdD(tdV27CollectDoneAt,tdV29EditorStartAt)} | editor=${tdV29EditorMs}ms | adminCheck=${tdV29AdminMs}ms | adminSkipped=$tdV29AdminSkipped | editorDone->tailStart=${tdD(tdV29EditorDoneAt,tdV29TailLoopStartAt)} | tailLoop=${tdV29TailLoopMs}ms | tailDone->desc=${tdD(tdV29TailLoopDoneAt,tdV27DescStartAt)}")
'''
if report_anchor not in s:
    raise SystemExit('v29 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'val adminLockedGroupNow = if(messageEditorAvailable)',
    'rmV29AdminSkipped=true',
    'isAdminLockedGroup(items)',
    'rmV29TailLoopMs=rmV29TailLoopDoneAt-rmV29TailLoopStartAt',
    'lazyAdminV29=collect->editor=',
    'adminSkipped=$tdV29AdminSkipped',
    'preClickV27=collect->tail=',
    'directProofV26=used=$tdV26DirectUsed',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('LAZY ADMIN CHECK v29 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('LAZY ADMIN CHECK v29 applied: skip full admin text normalization when editor exists; stage diagnostics + v27/v26 safety preserved')
