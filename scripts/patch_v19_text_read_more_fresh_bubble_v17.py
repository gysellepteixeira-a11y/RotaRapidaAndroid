from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

required=[
    '===== DIAGNOSTICO TEXTO v16 | TEXT v6 + READ MORE EXPANDED BUBBLE + DIRECT SEND =====',
    'private fun rememberReadMoreChainV16(',
    'private fun parseExpandedReadMoreBubbleV16(',
    'rmNodeChainV16:List<AccessibilityNodeInfo>',
    'rmParseRetriesV16<=12',
    'previousFastTexts: Set<String>',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('READ MORE FRESH BUBBLE v17 wrong base: '+m)

# v16 kept AccessibilityNodeInfo/parent objects from BEFORE expansion. On WhatsApp
# those objects can become stale after the bubble is rebuilt, leaving the parser
# with no usable subtree and (worse) v16 could keep rmPending=true forever.
# v17 only keeps a rectangle + short text anchor, then reacquires the bubble from
# a FRESH rootInActiveWindow after expansion.
state_old='''    private var rmNodeChainV16:List<AccessibilityNodeInfo> = emptyList()
    private var rmParseSourceV16=""; private var rmParseItemsV16=0; private var rmParseRetriesV16=0
    private var tdReadMoreParseSourceV16=""; private var tdReadMoreParseItemsV16=0
'''
state_new='''    private var rmNodeChainV16:List<AccessibilityNodeInfo> = emptyList()
    private var rmParseSourceV16=""; private var rmParseItemsV16=0; private var rmParseRetriesV16=0
    private var rmTargetRectV17=Rect(); private var rmAnchorV17=""
    private var tdReadMoreParseSourceV16=""; private var tdReadMoreParseItemsV16=0
'''
if state_old not in s:
    raise SystemExit('v17 state anchor not found')
s=s.replace(state_old,state_new,1)

# Replace the v16 remember helper. Keep the old chain only for compatibility with
# the existing reset/report fields, but do not depend on stale nodes for parsing.
a=s.find('    private fun rememberReadMoreChainV16(')
b=s.find('    private fun parseExpandedReadMoreBubbleV16(',a)
if a<0 or b<0:
    raise SystemExit('v17 remember function region not found')
remember=r'''    private fun rememberReadMoreChainV16(node:AccessibilityNodeInfo){
        val out=ArrayList<AccessibilityNodeInfo>(4)
        var cur:AccessibilityNodeInfo?=node
        var depth=0
        var bestAnchor=""
        while(cur!=null && depth<5){
            out.add(cur)
            val raw=try{
                buildString{
                    cur?.text?.toString()?.let{append(it)}
                    cur?.contentDescription?.toString()?.let{if(isNotEmpty())append(' ');append(it)}
                }.trim()
            }catch(_:Throwable){""}
            val n=RouteParser.normalize(raw)
            if(n.length>bestAnchor.length && !isExactReadMoreV12(n))bestAnchor=n
            cur=try{cur?.parent}catch(_:Throwable){null}
            depth++
        }
        rmNodeChainV16=out
        val r=Rect()
        try{node.getBoundsInScreen(r)}catch(_:Throwable){}
        rmTargetRectV17=Rect(r)
        rmAnchorV17=if(bestAnchor.length>72)bestAnchor.substring(0,72) else bestAnchor
        rmParseSourceV16=""
        rmParseItemsV16=0
        rmParseRetriesV16=0
    }

'''
s=s[:a]+remember+s[b:]

# Replace stale-chain parser with fresh-root reacquisition. Candidate nodes must
# either cover the old Ler-mais position or match the pre-click text anchor. Full
# chat/recycler containers are rejected. Among message-sized candidates we prefer
# the best route priority; for equal priority the richer subtree wins.
a=s.find('    private fun parseExpandedReadMoreBubbleV16(')
b=s.find('    private fun findReadMoreDescFromNewItemsV15(',a)
if a<0 or b<0:
    raise SystemExit('v17 parser function region not found')
parser=r'''    private fun parseExpandedReadMoreBubbleV16(screenHeight:Int):RouteResult? {
        val root=try{rootInActiveWindow}catch(_:Throwable){null} ?: return null
        val screenWidth=resources.displayMetrics.widthPixels
        val target=rmTargetRectV17
        val tx=if(target.isEmpty) -1 else target.centerX()
        val ty=if(target.isEmpty) -1 else target.centerY()
        val anchor=rmAnchorV17
        val anchorShort=if(anchor.length>36)anchor.substring(0,36) else anchor

        val candidates=ArrayList<AccessibilityNodeInfo>(16)
        val q=java.util.ArrayDeque<AccessibilityNodeInfo>()
        q.add(root)
        var scanned=0
        while(!q.isEmpty() && scanned<900){
            val n=q.removeLast(); scanned++
            val r=Rect()
            try{n.getBoundsInScreen(r)}catch(_:Throwable){}
            if(!r.isEmpty){
                val coversTarget=tx>=0 && ty>=0 && tx>=r.left && tx<=r.right && ty>=r.top && ty<=r.bottom
                val raw=try{
                    buildString{
                        n.text?.toString()?.let{append(it)}
                        n.contentDescription?.toString()?.let{if(isNotEmpty())append(' ');append(it)}
                    }.trim()
                }catch(_:Throwable){""}
                val norm=if(raw.isNotEmpty())RouteParser.normalize(raw) else ""
                val anchorMatch=anchorShort.length>=12 && norm.length>=12 &&
                    (norm.contains(anchorShort) || anchorShort.contains(norm.take(minOf(28,norm.length))))

                // Recycler/chat containers are essentially full width and tall.
                // A long message bubble can be tall, but it is still narrower.
                val looksLikeChatContainer=r.width()>=(screenWidth*0.965f).toInt() &&
                    r.height()>=(screenHeight*0.45f).toInt()
                if((coversTarget || anchorMatch) && !looksLikeChatContainer){
                    candidates.add(n)
                }
            }
            val cc=try{n.childCount}catch(_:Throwable){0}
            for(i in 0 until cc){
                try{n.getChild(i)?.let{q.add(it)}}catch(_:Throwable){}
            }
        }

        var best:RouteResult?=null
        var bestPriority=Int.MAX_VALUE
        var bestChars=-1
        var bestCount=0
        var bestMode=""

        for((idx,cand) in candidates.withIndex()){
            val cq=java.util.ArrayDeque<AccessibilityNodeInfo>()
            cq.add(cand)
            val texts=ArrayList<ScreenText>(32)
            val seen=HashSet<String>()
            var chars=0
            var visited=0
            var stillReadMore=false
            while(!cq.isEmpty() && visited<220){
                val n=cq.removeLast(); visited++
                val r=Rect()
                try{n.getBoundsInScreen(r)}catch(_:Throwable){}
                val raw=try{n.text?.toString().orEmpty()}catch(_:Throwable){""}
                val desc=try{n.contentDescription?.toString().orEmpty()}catch(_:Throwable){""}
                if(hasReadMoreTextV12(raw) || isExactReadMoreV12(desc))stillReadMore=true
                if(raw.isNotBlank()){
                    val key=raw+"|"+r.left+","+r.top+","+r.right+","+r.bottom
                    if(seen.add(key)){
                        texts.add(ScreenText(raw,r.left,r.top,r.right,r.bottom))
                        chars+=raw.length
                    }
                }
                val cc=try{n.childCount}catch(_:Throwable){0}
                for(i in 0 until cc){
                    try{n.getChild(i)?.let{cq.add(it)}}catch(_:Throwable){}
                }
            }
            if(stillReadMore || texts.isEmpty())continue

            val route=RouteParser.parseScreenTexts(texts,screenHeight)
                ?: RouteParser.parsePlainTexts(texts.map{it.text})
                ?: continue

            val p=route.priorityIndex
            if(p<bestPriority || (p==bestPriority && chars>bestChars)){
                best=route
                bestPriority=p
                bestChars=chars
                bestCount=texts.size
                bestMode="FRESH"+idx
            }
        }

        if(best!=null){
            rmParseSourceV16=bestMode
            rmParseItemsV16=bestCount
        }
        return best
    }

'''
s=s[:a]+parser+s[b:]

# Replace the v16 failure branch. Retry a little longer to let WhatsApp rebuild the
# fresh accessibility tree. If it still cannot isolate the expanded message, DO
# NOT freeze the service and DO NOT fall through to the partial delta. Baseline the
# current texts, report the failure visibly, and remain armed for the NEXT route.
old=r'''            if(rmCarry && tfRoute==null){
                rmParseRetriesV16++
                if(rmParseRetriesV16<=12){
                    handler.postDelayed({analyzeCurrentWindow()},8L)
                }else{
                    // Safety first: a Read-more route must never be sent from the
                    // incomplete v6 delta. Keep the analyzer blocked until rearm.
                    rmPending=true; rmCarry=false
                    Prefs.setStatus(this,"Ler mais expandiu, mas nao consegui isolar a mensagem completa. Nao enviei rota parcial.")
                }
                return
            }
'''
new=r'''            if(rmCarry && tfRoute==null){
                rmParseRetriesV16++
                if(rmParseRetriesV16<=25){
                    handler.postDelayed({analyzeCurrentWindow()},8L)
                }else{
                    // Never freeze on a failed Read-more parse. Also absorb the
                    // expanded message into the baseline so a later accessibility
                    // event cannot send Rosario (or another partial tail) by mistake.
                    previousFastTexts = items.asSequence()
                        .map { it.text }
                        .filter { it.isNotBlank() }
                        .toSet()
                    rmPending=false; rmCarry=false
                    val anchorInfo=if(rmAnchorV17.isBlank()) "sem-anchor" else "anchor-ok"
                    Prefs.setStatus(this,"TEXT v17: Ler mais abriu, mas a mensagem completa nao foi isolada apos ${rmParseRetriesV16} tentativas ($anchorInfo). Nenhuma rota parcial foi enviada; aguardando a proxima rota.")
                }
                return
            }
'''
if old not in s:
    raise SystemExit('v17 failure branch anchor not found')
s=s.replace(old,new,1)

# Reset v17 state together with existing Read-more state.
reset_old='rmNodeChainV16=emptyList(); rmParseSourceV16=""; rmParseItemsV16=0; rmParseRetriesV16=0'
reset_new='rmNodeChainV16=emptyList(); rmParseSourceV16=""; rmParseItemsV16=0; rmParseRetriesV16=0; rmTargetRectV17=Rect(); rmAnchorV17=""'
if reset_old not in s:
    raise SystemExit('v17 reset anchor not found')
s=s.replace(reset_old,reset_new,1)

old_header='===== DIAGNOSTICO TEXTO v16 | TEXT v6 + READ MORE EXPANDED BUBBLE + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v17 | TEXT v6 + READ MORE FRESH BUBBLE + DIRECT SEND ====='
s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'private var rmTargetRectV17=Rect()',
    'val root=try{rootInActiveWindow}',
    'looksLikeChatContainer',
    'rmParseSourceV16=bestMode',
    'rmParseRetriesV16<=25',
    'Nenhuma rota parcial foi enviada',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('READ MORE FRESH BUBBLE v17 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('READ MORE FRESH BUBBLE v17 applied: fresh root reacquisition; no stale-node freeze; IMAGE v9 preserved')
