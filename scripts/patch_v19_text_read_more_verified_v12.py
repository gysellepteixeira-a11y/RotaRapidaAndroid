from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

for m in [
    '===== DIAGNOSTICO TEXTO v11 | TEXT v6 + READ MORE SPAN + DIRECT SEND =====',
    'private fun isReadMoreLabelV11(',
    'private fun clickNewestReadMoreSpanV11(',
    'private fun waitForReadMoreExpansionV11(',
    'val spanClick=clickNewestReadMoreSpanV11(tfNewItems)',
    'private fun waitForTextDirectSendReadyV5(',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('READ MORE VERIFIED v12 wrong base: '+m)

# Add a diagnostic field telling us which opening method was attempted.
s=s.replace(
    '    private var rmClickMs=0L; private var rmPolls=0\n',
    '    private var rmClickMs=0L; private var rmPolls=0; private var rmMethod=""\n',
    1,
)
s=s.replace(
    '    private var tdReadMoreClickMs=0L; private var tdReadMorePolls=0\n',
    '    private var tdReadMoreClickMs=0L; private var tdReadMorePolls=0; private var tdReadMoreMethod=""\n',
    1,
)
s=s.replace(
    'rmUsed=false; rmStarted=0L; rmClicked=0L; rmExpanded=0L; rmClickMs=0L; rmPolls=0',
    'rmUsed=false; rmStarted=0L; rmClicked=0L; rmExpanded=0L; rmClickMs=0L; rmPolls=0; rmMethod=""',
    1,
)
s=s.replace(
    'tdReadMoreUsed=rmUsed; tdReadMoreClicked=rmClicked; tdReadMoreExpanded=rmExpanded; tdReadMoreClickMs=rmClickMs; tdReadMorePolls=rmPolls',
    'tdReadMoreUsed=rmUsed; tdReadMoreClicked=rmClicked; tdReadMoreExpanded=rmExpanded; tdReadMoreClickMs=rmClickMs; tdReadMorePolls=rmPolls; tdReadMoreMethod=rmMethod',
    1,
)
s=s.replace(
    'rmPending=false; rmCarry=false; rmUsed=false; rmStarted=0L; rmClicked=0L; rmExpanded=0L; rmClickMs=0L; rmPolls=0',
    'rmPending=false; rmCarry=false; rmUsed=false; rmStarted=0L; rmClicked=0L; rmExpanded=0L; rmClickMs=0L; rmPolls=0; rmMethod=""',
    1,
)

# Replace v11 helper region with v12. v12 never treats refresh()/stale-node failure
# as expansion. It measures a FRESH WhatsApp accessibility tree and requires real
# text growth before the parser is released.
a=s.find('    private fun isReadMoreLabelV11(')
b=s.find('    private fun waitForTextDirectSendReadyV5(',a)
if a<0 or b<0:
    raise SystemExit('READ MORE VERIFIED v12 helper region not found')

helpers=r'''    private data class ReadMoreBandStatsV12(
        val chars:Int,
        val maxLen:Int,
        val hasReadMore:Boolean,
        val hasEllipsis:Boolean
    )

    private fun hasReadMoreTextV12(raw:String):Boolean {
        val n=RouteParser.normalize(raw)
        return n=="ler mais" || n=="read more" || n.contains(" ler mais") || n.contains(" read more") || n.startsWith("ler mais ") || n.startsWith("read more ")
    }

    private fun isExactReadMoreV12(raw:String):Boolean {
        val n=RouteParser.normalize(raw).trim()
        return n=="ler mais" || n=="read more"
    }

    private fun freshReadMoreBandStatsV12(target:Rect):ReadMoreBandStatsV12 {
        val root=try{rootInActiveWindow}catch(_:Throwable){null}
            ?: return ReadMoreBandStatsV12(0,0,false,false)
        val h=resources.displayMetrics.heightPixels
        val top=maxOf(0,target.top-220)
        val bottom=minOf(h,target.bottom+300)
        val seen=HashSet<String>()
        var chars=0
        var maxLen=0
        var hasReadMore=false
        var hasEllipsis=false
        val q=java.util.ArrayDeque<AccessibilityNodeInfo>()
        q.add(root)
        while(!q.isEmpty()){
            val n=q.removeLast()
            val r=Rect()
            try{n.getBoundsInScreen(r)}catch(_:Throwable){}
            if(!r.isEmpty && r.bottom>=top && r.top<=bottom){
                val raw=buildString{
                    n.text?.toString()?.let{append(it)}
                    n.contentDescription?.toString()?.let{if(isNotEmpty())append(' ');append(it)}
                }.trim()
                if(raw.isNotEmpty() && seen.add(raw)){
                    chars+=raw.length
                    if(raw.length>maxLen)maxLen=raw.length
                    if(hasReadMoreTextV12(raw))hasReadMore=true
                    if(raw.contains("...")||raw.contains("…"))hasEllipsis=true
                }
            }
            val cc=try{n.childCount}catch(_:Throwable){0}
            for(i in 0 until cc){
                try{n.getChild(i)?.let{q.add(it)}}catch(_:Throwable){}
            }
        }
        return ReadMoreBandStatsV12(chars,maxLen,hasReadMore,hasEllipsis)
    }

    private fun findNewestReadMoreTargetV12(newItems:List<NodeItem>):NodeItem? {
        if(newItems.isEmpty())return null
        val sorted=newItems.filter{!it.rect.isEmpty}.sortedByDescending{it.rect.bottom}
        return sorted.firstOrNull{isExactReadMoreV12(it.text)}
            ?: sorted.firstOrNull{hasReadMoreTextV12(it.text)}
            ?: sorted.firstOrNull{it.text.contains("...")||it.text.contains("…")}
    }

    private fun tapReadMoreRectV12(r:Rect,alternate:Boolean=false):Boolean {
        if(r.isEmpty)return false
        val dm=resources.displayMetrics
        val dx=(if(alternate) 105f else 52f)*dm.density
        val dy=18f*dm.density
        val x=(r.right-dx).coerceIn(r.left+8f,dm.widthPixels-8f)
        val y=(r.bottom-dy).coerceIn(r.top+8f,dm.heightPixels-8f)
        val p=Path().apply{moveTo(x,y)}
        return dispatchGesture(
            GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(p,0L,1L)).build(),
            null,
            null
        )
    }

    private fun clickReadMoreV12(item:NodeItem):Pair<Boolean,String> {
        val cs=item.node.text
        val sp=cs as? android.text.Spanned
        if(sp!=null){
            val spans=sp.getSpans(0,sp.length,android.text.style.ClickableSpan::class.java)
            for(span in spans.reversed()){
                val x=sp.getSpanStart(span).coerceAtLeast(0)
                val y=sp.getSpanEnd(span).coerceAtMost(sp.length)
                val label=if(y>x)sp.subSequence(x,y).toString() else ""
                if(!isExactReadMoreV12(label) && !hasReadMoreTextV12(label))continue
                try{
                    span.onClick(android.view.View(this))
                    return true to "SPAN"
                }catch(_:Throwable){}
            }
        }

        // Only trust ACTION_CLICK when the accessibility node itself IS the
        // small Read-more label. Never click a whole message/parent and call it success.
        if(isExactReadMoreV12(item.text)){
            try{
                if(item.node.isClickable && item.node.performAction(AccessibilityNodeInfo.ACTION_CLICK))
                    return true to "NODE"
            }catch(_:Throwable){}
            val r=item.rect
            if(!r.isEmpty){
                val p=Path().apply{moveTo(r.exactCenterX(),r.exactCenterY())}
                val ok=dispatchGesture(
                    GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(p,0L,1L)).build(),
                    null,
                    null
                )
                if(ok)return true to "GESTURE_CENTER"
            }
        }

        // WhatsApp often exposes "Ler mais" only as part of the message text.
        // In that case tap its visual position at the end of the last line.
        return tapReadMoreRectV12(item.rect,false) to "GESTURE"
    }

    private fun waitForReadMoreExpansionV12(
        target:Rect,
        before:ReadMoreBandStatsV12,
        startedAt:Long,
        poll:Int,
        retried:Boolean
    ){
        val now=freshReadMoreBandStatsV12(target)
        val grew=(now.chars>=before.chars+12)||(now.maxLen>=before.maxLen+12)
        val cleared=(before.hasReadMore&&!now.hasReadMore)||(before.hasEllipsis&&!now.hasEllipsis)
        val stronglyGrew=(now.chars>=before.chars+28)||(now.maxLen>=before.maxLen+28)
        val expanded=grew&&(cleared||stronglyGrew)
        if(expanded){
            rmExpanded=SystemClock.elapsedRealtime(); rmPolls=poll; rmPending=false; rmCarry=true
            handler.post{analyzeCurrentWindow()}
            return
        }

        // First click can miss when WhatsApp puts the inline label further left.
        // One measured retry only; no repeated blind taps.
        if(!retried && poll>=18){
            val ok=tapReadMoreRectV12(target,true)
            if(ok){
                rmMethod=rmMethod+"+GESTURE2"
                handler.postDelayed({waitForReadMoreExpansionV12(target,before,startedAt,poll+1,true)},4L)
                return
            }
        }

        if(poll<55){
            handler.postDelayed({waitForReadMoreExpansionV12(target,before,startedAt,poll+1,retried)},4L)
            return
        }

        // Never release a still-truncated message to the route parser.
        rmPending=false; rmCarry=false
        handler.postDelayed({analyzeCurrentWindow()},60L)
    }

'''
s=s[:a]+helpers+s[b:]

# Replace the v11 hot block. Capture fresh-tree stats BEFORE the click, then only
# continue to the parser after fresh-tree growth has been verified.
hs=s.find('            val spanClick=clickNewestReadMoreSpanV11(tfNewItems)')
he=s.find('        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.',hs)
if hs<0 or he<0:
    raise SystemExit('READ MORE VERIFIED v12 hot region not found')

hot=r'''            val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)
            if(readMoreTarget!=null){
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
        }

'''
s=s[:hs]+hot+s[he:]

old='===== DIAGNOSTICO TEXTO v11 | TEXT v6 + READ MORE SPAN + DIRECT SEND ====='
new='===== DIAGNOSTICO TEXTO v12 | TEXT v6 + READ MORE VERIFIED + DIRECT SEND ====='
s=s.replace(old,new,1)

# Make the next phone diagnostic tell us the exact opening method.
s=s.replace(
    'appendLine("[${tdA(tdReadMoreClicked)}] Ler mais clicado | action=${tdReadMoreClickMs}ms")',
    'appendLine("[${tdA(tdReadMoreClicked)}] Ler mais acionado | action=${tdReadMoreClickMs}ms | metodo=$tdReadMoreMethod")',
    1,
)

for m in [
    new,
    'private fun freshReadMoreBandStatsV12(',
    'private fun clickReadMoreV12(',
    'private fun waitForReadMoreExpansionV12(',
    'val readMoreTarget=findNewestReadMoreTargetV12(tfNewItems)',
    'metodo=$tdReadMoreMethod',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('READ MORE VERIFIED v12 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('READ MORE VERIFIED v12 applied: fresh-tree growth confirmation + precise click + one gesture retry; TEXT v6 + IMAGE v9 preserved')
