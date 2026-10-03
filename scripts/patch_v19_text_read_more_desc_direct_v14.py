from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

required=[
    '===== DIAGNOSTICO TEXTO v12 | TEXT v6 + READ MORE VERIFIED + DIRECT SEND =====',
    'private fun freshReadMoreBandStatsV12(',
    'private fun findNewestReadMoreTargetV12(',
    'private fun waitForReadMoreExpansionV12(',
    'val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)',
    'private fun waitForTextDirectSendReadyV5(',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('READ MORE DESC DIRECT v14 wrong base: '+m)

needle='    private fun findNewestReadMoreTargetV12(newItems:List<NodeItem>):NodeItem? {'
helper=r'''    private data class ReadMoreDescTargetV14(
        val node:AccessibilityNodeInfo,
        val rect:Rect
    )

    private fun findNewestReadMoreDescTargetV14():ReadMoreDescTargetV14? {
        val root=try{rootInActiveWindow}catch(_:Throwable){null} ?: return null
        val q=java.util.ArrayDeque<AccessibilityNodeInfo>()
        q.add(root)
        var best:ReadMoreDescTargetV14?=null
        while(!q.isEmpty()){
            val n=q.removeLast()
            val desc=try{n.contentDescription?.toString().orEmpty()}catch(_:Throwable){""}
            if(isExactReadMoreV12(desc)){
                val r=Rect()
                try{n.getBoundsInScreen(r)}catch(_:Throwable){}
                val clickable=try{n.isClickable}catch(_:Throwable){false}
                val enabled=try{n.isEnabled}catch(_:Throwable){false}
                if(clickable && enabled && !r.isEmpty){
                    val cur=best
                    if(cur==null || r.bottom>cur.rect.bottom){
                        best=ReadMoreDescTargetV14(n,r)
                    }
                }
            }
            val cc=try{n.childCount}catch(_:Throwable){0}
            for(i in 0 until cc){
                try{n.getChild(i)?.let{q.add(it)}}catch(_:Throwable){}
            }
        }
        return best
    }

'''
s=s.replace(needle,helper+needle,1)

needle_hot='            val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)\n'
hot=r'''            val descTarget=findNewestReadMoreDescTargetV14()
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
            val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)
'''
s=s.replace(needle_hot,hot,1)

old='===== DIAGNOSTICO TEXTO v12 | TEXT v6 + READ MORE VERIFIED + DIRECT SEND ====='
new='===== DIAGNOSTICO TEXTO v14 | TEXT v6 + READ MORE DESC DIRECT + DIRECT SEND ====='
s=s.replace(old,new,1)

for m in [
    new,
    'private fun findNewestReadMoreDescTargetV14()',
    'rmMethod="DESC_NODE"',
    'performAction(AccessibilityNodeInfo.ACTION_CLICK)',
    'waitForReadMoreExpansionV12(descTarget.rect,before,t,0,false)',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('READ MORE DESC DIRECT v14 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('READ MORE DESC DIRECT v14 applied: exact contentDescription node + ACTION_CLICK + verified expansion; TEXT v6 + IMAGE v9 preserved')

# Immediately layer the v15 race fix on top when this build step runs.
exec(Path('scripts/patch_v19_text_read_more_newitem_guard_v15.py').read_text(encoding='utf-8'), {'__name__':'__main__'})
