from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

v15_header='===== DIAGNOSTICO TEXTO v15 | TEXT v6 + READ MORE NEWITEM GUARD + DIRECT SEND ====='
if v15_header in s:
    print('READ MORE NEWITEM GUARD v15 already applied; keeping current source')
    raise SystemExit(0)

required=[
    '===== DIAGNOSTICO TEXTO v14 | TEXT v6 + READ MORE DESC DIRECT + DIRECT SEND =====',
    'private data class ReadMoreDescTargetV14(',
    'private fun findNewestReadMoreDescTargetV14()',
    'val descTarget=findNewestReadMoreDescTargetV14()',
    'rmMethod="DESC_NODE"',
    'private fun analyzeCurrentWindow() {',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('READ MORE NEWITEM GUARD v15 wrong base: '+m)

# The probe proved that the real WhatsApp control is already inside the SAME
# collected tail as a NodeItem: text may be empty, contentDescription='Ler mais',
# clickable=true, ACTION_CLICK available. Prefer that exact already-collected node
# instead of asking a second fresh root which can briefly lag one accessibility frame.
anchor='    private fun findNewestReadMoreDescTargetV14():ReadMoreDescTargetV14? {'
helper=r'''    private fun findReadMoreDescFromNewItemsV15(newItems:List<NodeItem>):ReadMoreDescTargetV14? {
        var best:ReadMoreDescTargetV14?=null
        for(item in newItems){
            val n=item.node
            val desc=try{n.contentDescription?.toString().orEmpty()}catch(_:Throwable){""}
            if(!isExactReadMoreV12(desc))continue
            val r=Rect()
            try{n.getBoundsInScreen(r)}catch(_:Throwable){}
            val clickable=try{n.isClickable}catch(_:Throwable){false}
            val enabled=try{n.isEnabled}catch(_:Throwable){false}
            if(!clickable || !enabled || r.isEmpty)continue
            val cur=best
            if(cur==null || r.bottom>cur.rect.bottom){
                best=ReadMoreDescTargetV14(n,r)
            }
        }
        return best
    }

'''
s=s.replace(anchor,helper+anchor,1)

# Critical race fix: v10 only ignored NEW accessibility events while rmPending.
# A handler analyzeCurrentWindow() that had already been queued could still run and
# parse the truncated Rosario route before expansion completed. Guard the analyzer
# itself too, so no parser can pass while Read More is pending.
fn='    private fun analyzeCurrentWindow() {'
pos=s.find(fn)
if pos<0:
    raise SystemExit('analyzeCurrentWindow not found')
insert_at=pos+len(fn)
if 'if (rmPending) return' not in s[insert_at:insert_at+140]:
    s=s[:insert_at]+'\n        if (rmPending) return'+s[insert_at:]

old=r'''            val descTarget=findNewestReadMoreDescTargetV14()
            if(descTarget!=null){
                val before=freshReadMoreBandStatsV12(descTarget.rect)
                val t=SystemClock.elapsedRealtime()
                val ok=try{descTarget.node.performAction(AccessibilityNodeInfo.ACTION_CLICK)}catch(_:Throwable){false}
                val done=SystemClock.elapsedRealtime()
                if(ok){
                    rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done
                    rmClickMs=done-t; rmExpanded=0L; rmPolls=0; rmMethod="DESC_NODE"
                    waitForReadMoreExpansionV12(descTarget.rect,before,t,0,false)
                    return
                }
            }
'''
new=r'''            val descTargetNew=findReadMoreDescFromNewItemsV15(tfNewItems)
            val descTarget=descTargetNew ?: findNewestReadMoreDescTargetV14()
            if(descTarget!=null){
                val before=freshReadMoreBandStatsV12(descTarget.rect)
                val t=SystemClock.elapsedRealtime()
                val ok=try{descTarget.node.performAction(AccessibilityNodeInfo.ACTION_CLICK)}catch(_:Throwable){false}
                val done=SystemClock.elapsedRealtime()
                if(ok){
                    rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done
                    rmClickMs=done-t; rmExpanded=0L; rmPolls=0
                    rmMethod=if(descTargetNew!=null) "DESC_NEWITEM" else "DESC_ROOT"
                    waitForReadMoreExpansionV12(descTarget.rect,before,t,0,false)
                    return
                }
            }
'''
if old not in s:
    raise SystemExit('v15 hot block not found')
s=s.replace(old,new,1)

old_header='===== DIAGNOSTICO TEXTO v14 | TEXT v6 + READ MORE DESC DIRECT + DIRECT SEND ====='
new_header=v15_header
s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'private fun findReadMoreDescFromNewItemsV15(',
    'if (rmPending) return',
    'rmMethod=if(descTargetNew!=null) "DESC_NEWITEM" else "DESC_ROOT"',
    'waitForReadMoreExpansionV12(descTarget.rect,before,t,0,false)',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('READ MORE NEWITEM GUARD v15 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('READ MORE NEWITEM GUARD v15 applied: collected contentDescription node first + hard rmPending analyzer guard; TEXT v6 + IMAGE v9 preserved')
