from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

for m in [
 '===== DIAGNOSTICO TEXTO v10 | TEXT v6 + READ MORE FAST + DIRECT SEND =====',
 'private fun findNewestReadMoreV10(',
 'private fun waitForReadMoreExpansionV10(',
 'val readMoreNode = findNewestReadMoreV10(root, tfNewItems)',
 'private fun waitForTextDirectSendReadyV5(',
 '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====']:
    if m not in s: raise SystemExit('READ MORE SPAN v11 wrong base: '+m)

a=s.find('    private fun findNewestReadMoreV10(')
b=s.find('    private fun waitForTextDirectSendReadyV5(',a)
if a<0 or b<0: raise SystemExit('READ MORE SPAN v11 helper region not found')
helpers=r'''    private fun isReadMoreLabelV11(raw:String):Boolean {
        val n=RouteParser.normalize(raw)
        return n=="ler mais" || n=="read more" || " ler mais" in n || " read more" in n || n.startsWith("ler mais ") || n.startsWith("read more ")
    }

    private fun clickNewestReadMoreSpanV11(newItems:List<NodeItem>):Pair<AccessibilityNodeInfo,String>? {
        for(item in newItems.sortedByDescending{it.rect.bottom}){
            val cs=item.node.text ?: continue
            val sp=cs as? android.text.Spanned ?: continue
            val raw=cs.toString()
            val spans=sp.getSpans(0,sp.length,android.text.style.ClickableSpan::class.java)
            for(span in spans.reversed()){
                val x=sp.getSpanStart(span).coerceAtLeast(0)
                val y=sp.getSpanEnd(span).coerceAtMost(sp.length)
                val label=if(y>x) sp.subSequence(x,y).toString() else ""
                val tail=(raw.contains("...")||raw.contains("…")) && y>=sp.length-2
                if(!isReadMoreLabelV11(label) && !tail) continue
                try { span.onClick(android.view.View(this)); return item.node to raw } catch(_:Throwable){}
            }
        }
        return null
    }

    private fun findNewestReadMoreItemV11(items:List<NodeItem>,newItems:List<NodeItem>):NodeItem? {
        if(newItems.isEmpty()) return null
        val rr=newItems.map{it.rect}.filter{!it.isEmpty}; if(rr.isEmpty()) return null
        val top=rr.minOf{it.top}; val bottom=rr.maxOf{it.bottom}
        val extra=maxOf(220,(resources.displayMetrics.heightPixels*0.10f).toInt())
        return items.asSequence().filter{!it.rect.isEmpty}.filter{it.rect.bottom>=top && it.rect.top<=bottom+extra}.filter{isReadMoreLabelV11(it.text)}.maxByOrNull{it.rect.bottom}
    }

    private fun findNewestEllipsisV11(newItems:List<NodeItem>):NodeItem? =
        newItems.asSequence().filter{!it.rect.isEmpty}.filter{it.text.contains("...")||it.text.contains("…")}.maxByOrNull{it.rect.bottom}

    private fun tapReadMoreFallbackV11(item:NodeItem):Boolean {
        val r=item.rect; if(r.isEmpty) return false
        val dm=resources.displayMetrics
        val x=(r.right-56f*dm.density).coerceIn(r.left+8f,dm.widthPixels-8f)
        val y=(r.bottom-18f*dm.density).coerceIn(r.top+8f,dm.heightPixels-8f)
        val p=Path().apply{moveTo(x,y)}
        return dispatchGesture(GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(p,0L,1L)).build(),null,null)
    }

    private fun waitForReadMoreExpansionV11(node:AccessibilityNodeInfo,before:String,startedAt:Long,poll:Int){
        val delay=4L; val max=45
        var changed=false
        try{
            if(!node.refresh()) changed=true else {
                val now=node.text?.toString().orEmpty()
                changed=now!=before || (!now.contains("...") && !now.contains("…") && !isReadMoreLabelV11(now))
            }
        }catch(_:Throwable){changed=true}
        if(changed){
            rmExpanded=SystemClock.elapsedRealtime(); rmPolls=poll; rmPending=false; rmCarry=true
            handler.post{analyzeCurrentWindow()}; return
        }
        if(poll<max){ handler.postDelayed({waitForReadMoreExpansionV11(node,before,startedAt,poll+1)},delay); return }
        rmPending=false; rmCarry=false
        handler.postDelayed({analyzeCurrentWindow()},20L)
    }

'''
s=s[:a]+helpers+s[b:]

hs=s.find('            val readMoreNode = findNewestReadMoreV10(root, tfNewItems)')
he=s.find('        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.',hs)
if hs<0 or he<0: raise SystemExit('READ MORE SPAN v11 hot region not found')
hot=r'''            val spanClick=clickNewestReadMoreSpanV11(tfNewItems)
            if(spanClick!=null){
                val t=SystemClock.elapsedRealtime()
                rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=t; rmClickMs=0L; rmExpanded=0L; rmPolls=0
                waitForReadMoreExpansionV11(spanClick.first,spanClick.second,t,0)
                return
            }

            val readMoreItem=findNewestReadMoreItemV11(items,tfNewItems)
            if(readMoreItem!=null){
                val before=readMoreItem.node.text?.toString().orEmpty(); val t=SystemClock.elapsedRealtime()
                val ok=clickNodeOrParent(readMoreItem.node); val done=SystemClock.elapsedRealtime()
                if(ok){
                    rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done; rmClickMs=done-t; rmExpanded=0L; rmPolls=0
                    waitForReadMoreExpansionV11(readMoreItem.node,before,t,0)
                    return
                }
            }

            val ellipsisItem=findNewestEllipsisV11(tfNewItems)
            if(ellipsisItem!=null){
                val before=ellipsisItem.node.text?.toString().orEmpty(); val t=SystemClock.elapsedRealtime()
                val ok=tapReadMoreFallbackV11(ellipsisItem); val done=SystemClock.elapsedRealtime()
                if(ok){
                    rmUsed=true; rmPending=true; rmCarry=true; rmStarted=t; rmClicked=done; rmClickMs=done-t; rmExpanded=0L; rmPolls=0
                    waitForReadMoreExpansionV11(ellipsisItem.node,before,t,0)
                    return
                }
                handler.postDelayed({analyzeCurrentWindow()},12L)
                return
            }
        }

'''
s=s[:hs]+hot+s[he:]

old='===== DIAGNOSTICO TEXTO v10 | TEXT v6 + READ MORE FAST + DIRECT SEND ====='
new='===== DIAGNOSTICO TEXTO v11 | TEXT v6 + READ MORE SPAN + DIRECT SEND ====='
s=s.replace(old,new,1)
for m in [new,'private fun clickNewestReadMoreSpanV11(','private fun waitForReadMoreExpansionV11(','val spanClick=clickNewestReadMoreSpanV11(tfNewItems)','speedDiagnosticSendMethod = "TEXT_DIRECT_V5"','===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====']:
    if m not in s: raise SystemExit('READ MORE SPAN v11 verify failed: '+m)
S.write_text(s,encoding='utf-8')
print('READ MORE SPAN v11 applied: clickable span first, node second, gesture fallback; TEXT v6 + IMAGE v9 preserved')
