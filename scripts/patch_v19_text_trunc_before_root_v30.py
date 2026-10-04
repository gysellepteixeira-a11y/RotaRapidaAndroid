from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v29 | TEXT v6 + LAZY ADMIN CHECK + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v30 | TEXT v6 + TRUNC BEFORE ROOT + LAZY ADMIN + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'val descTargetNew=findReadMoreDescFromNewItemsV15(tfNewItems)',
    'val v27TargetStart=SystemClock.elapsedRealtime()',
    'val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)',
    'val v27RootTarget=findNewestReadMoreDescTargetV14()',
    'lazyAdminV29=collect->editor=',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
]
for m in required:
    if m not in s:
        raise SystemExit('TRUNC BEFORE ROOT v30 wrong base: '+m)

# Reorder only the expensive lookup sequence:
# 1) exact DESC in already-collected new items (unchanged primary path)
# 2) cheap visible truncation check in the same new items
# 3) if truncated, enter the existing safe DESC_WAIT immediately
# 4) full fresh-root DESC scan is retained only when no truncation target exists
# This never sends a partial route and does not relax strict proof.
old_desc='''            rmV27DescStartAt=SystemClock.elapsedRealtime()
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
new_desc='''            rmV27DescStartAt=SystemClock.elapsedRealtime()
            rmV27DescRootMs=0L
            rmV27TargetScanMs=0L
            val v27DescNewStart=SystemClock.elapsedRealtime()
            val descTargetNew=findReadMoreDescFromNewItemsV15(tfNewItems)
            rmV27DescNewMs=SystemClock.elapsedRealtime()-v27DescNewStart

            val v30TargetStart=SystemClock.elapsedRealtime()
            val readMoreTarget=if(descTargetNew==null){
                findNewestReadMoreTargetV12(tfNewItems)
            }else null
            rmV27TargetScanMs=SystemClock.elapsedRealtime()-v30TargetStart

            val descTarget=if(descTargetNew!=null){
                descTargetNew
            }else if(readMoreTarget!=null){
                // v30: message is visibly truncated; skip the expensive whole-root
                // scan and enter the existing tokenized DESC_WAIT below.
                null
            }else{
                val v27RootStart=SystemClock.elapsedRealtime()
                val v27RootTarget=findNewestReadMoreDescTargetV14()
                rmV27DescRootMs=SystemClock.elapsedRealtime()-v27RootStart
                v27RootTarget
            }
            if(descTarget!=null){
'''
if old_desc not in s:
    raise SystemExit('v30 desc ordering block not found')
s=s.replace(old_desc,new_desc,1)

old_target='''            val v27TargetStart=SystemClock.elapsedRealtime()
            val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)
            rmV27TargetScanMs=SystemClock.elapsedRealtime()-v27TargetStart
            if(readMoreTarget!=null){
'''
new_target='''            if(readMoreTarget!=null){
'''
if old_target not in s:
    raise SystemExit('v30 duplicate target block not found')
s=s.replace(old_target,new_target,1)

# Add explicit A/B marker to final report. Existing v27 descRoot/targetScan now refer
# only to the current successful analysis because they are reset before the lookup.
report_anchor='''                    appendLine("lazyAdminV29=collect->editor=${tdD(tdV27CollectDoneAt,tdV29EditorStartAt)} | editor=${tdV29EditorMs}ms | adminCheck=${tdV29AdminMs}ms | adminSkipped=$tdV29AdminSkipped | editorDone->tailStart=${tdD(tdV29EditorDoneAt,tdV29TailLoopStartAt)} | tailLoop=${tdV29TailLoopMs}ms | tailDone->desc=${tdD(tdV29TailLoopDoneAt,tdV27DescStartAt)}")
'''
report_insert=report_anchor+'''                    appendLine("truncBeforeRootV30=enabled | currentDescRoot=${tdV27DescRootMs}ms | currentTargetScan=${tdV27TargetScanMs}ms | strictProof=preserved")
'''
if report_anchor not in s:
    raise SystemExit('v30 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'val readMoreTarget=if(descTargetNew==null)',
    'else if(readMoreTarget!=null)',
    'rmV27DescRootMs=0L',
    'truncBeforeRootV30=enabled',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('TRUNC BEFORE ROOT v30 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('TRUNC BEFORE ROOT v30 applied: DESC_NEWITEM first; visible truncation enters safe DESC_WAIT before whole-root scan; strict proof preserved')
