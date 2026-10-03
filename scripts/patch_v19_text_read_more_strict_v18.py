from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

required=[
    '===== DIAGNOSTICO TEXTO v17 | TEXT v6 + READ MORE FRESH BUBBLE + DIRECT SEND =====',
    'private var rmTargetRectV17=Rect(); private var rmAnchorV17=""',
    'private fun rememberReadMoreChainV16(',
    'private fun parseExpandedReadMoreBubbleV16(',
    'private fun tapReadMoreRectV12(',
    'private fun waitForReadMoreExpansionV12(',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('READ MORE STRICT v18 wrong base: '+m)

# Extra strict-proof state. The key rule in v18 is that broad-band tree growth is
# NEVER enough to call the message expanded. We must reacquire the SAME message
# by a pre-click text anchor and prove that its accessible text got longer.
s=s.replace(
    '    private var rmTargetRectV17=Rect(); private var rmAnchorV17=""\n',
    '    private var rmTargetRectV17=Rect(); private var rmAnchorV17=""\n'
    '    private var rmBeforeAnchorLenV18=0; private var rmGestureStageV18=0; private var rmProofV18=""\n',
    1,
)
s=s.replace(
    '    private var tdReadMoreParseSourceV16=""; private var tdReadMoreParseItemsV16=0\n',
    '    private var tdReadMoreParseSourceV16=""; private var tdReadMoreParseItemsV16=0\n'
    '    private var tdReadMoreProofV18=""\n',
    1,
)

# Rebuild the remembered anchor. v17 chose the longest ancestor even when it could
# already be the chat container. v18 only accepts message-sized ancestors.
a=s.find('    private fun rememberReadMoreChainV16(')
b=s.find('    private fun parseExpandedReadMoreBubbleV16(',a)
if a<0 or b<0:
    raise SystemExit('v18 remember region not found')
remember=r'''    private fun rememberReadMoreChainV16(node:AccessibilityNodeInfo){
        val out=ArrayList<AccessibilityNodeInfo>(6)
        var cur:AccessibilityNodeInfo?=node
        var depth=0
        var bestAnchor=""
        val sw=resources.displayMetrics.widthPixels
        val sh=resources.displayMetrics.heightPixels
        while(cur!=null && depth<6){
            out.add(cur)
            val rr=Rect()
            try{cur?.getBoundsInScreen(rr)}catch(_:Throwable){}
            val raw=try{
                buildString{
                    cur?.text?.toString()?.let{append(it)}
                    cur?.contentDescription?.toString()?.let{if(isNotEmpty())append(' ');append(it)}
                }.trim()
            }catch(_:Throwable){""}
            val n=RouteParser.normalize(raw)
            val container=!rr.isEmpty && rr.width()>=(sw*0.965f).toInt() && rr.height()>=(sh*0.45f).toInt()
            if(!container && n.length>bestAnchor.length && !isExactReadMoreV12(n))bestAnchor=n
            cur=try{cur?.parent}catch(_:Throwable){null}
            depth++
        }
        rmNodeChainV16=out
        val r=Rect()
        try{node.getBoundsInScreen(r)}catch(_:Throwable){}
        rmTargetRectV17=Rect(r)
        rmBeforeAnchorLenV18=bestAnchor.length
        rmAnchorV17=if(bestAnchor.length>96)bestAnchor.substring(0,96) else bestAnchor
        rmGestureStageV18=0
        rmProofV18="anchorLen=${rmBeforeAnchorLenV18}"
        rmParseSourceV16=""
        rmParseItemsV16=0
        rmParseRetriesV16=0
    }

'''
s=s[:a]+remember+s[b:]

# Replace approximate gesture coordinates. If WhatsApp exposes a small Read-more
# rectangle we tap its center. For a whole message-text rectangle, probe a compact
# grid near the lower-right where inline "Ler mais" is drawn on Android.
a=s.find('    private fun tapReadMoreRectV12(')
b=s.find('    private fun clickReadMoreV12(',a)
if a<0 or b<0:
    raise SystemExit('v18 tap region not found')
tap=r'''    private fun tapReadMoreRectV18(r:Rect,stage:Int):Boolean {
        if(r.isEmpty)return false
        val dm=resources.displayMetrics
        val small=r.width()<(180f*dm.density).toInt() && r.height()<(90f*dm.density).toInt()
        val x:Float
        val y:Float
        if(small){
            x=r.exactCenterX(); y=r.exactCenterY()
        }else{
            val xDp=floatArrayOf(28f,58f,28f,72f,105f)
            val yDp=floatArrayOf(34f,34f,48f,48f,34f)
            val i=stage.coerceIn(0,xDp.lastIndex)
            x=(r.right-xDp[i]*dm.density).coerceIn(r.left+8f,dm.widthPixels-8f)
            y=(r.bottom-yDp[i]*dm.density).coerceIn(r.top+8f,dm.heightPixels-8f)
        }
        val p=Path().apply{moveTo(x,y)}
        return dispatchGesture(
            GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(p,0L,1L)).build(),
            null,
            null
        )
    }

    private fun tapReadMoreRectV12(r:Rect,alternate:Boolean=false):Boolean {
        val stage=if(alternate) 1 else 0
        rmGestureStageV18=maxOf(rmGestureStageV18,stage)
        return tapReadMoreRectV18(r,stage)
    }

'''
s=s[:a]+tap+s[b:]

# Make the final fallback in clickReadMoreV12 use the v18 stage-0 geometry.
s=s.replace(
    '        return tapReadMoreRectV12(item.rect,false) to "GESTURE"\n',
    '        rmGestureStageV18=0\n        return tapReadMoreRectV18(item.rect,0) to "GESTURE"\n',
    1,
)

# Strict proof from a FRESH tree. A candidate must match the pre-click message
# prefix and its accessible text must be materially longer than before. Changes in
# nearby timestamps/buttons/other messages can no longer produce a false positive.
anchor='    private fun waitForReadMoreExpansionV12('
pos=s.find(anchor)
if pos<0:
    raise SystemExit('v18 wait function not found')
end=s.find('    private fun waitForTextDirectSendReadyV5(',pos)
if end<0:
    raise SystemExit('v18 wait end anchor not found')
helpers=r'''    private data class ReadMoreProofV18(
        val expanded:Boolean,
        val matched:Boolean,
        val chars:Int,
        val stillTruncated:Boolean,
        val source:String
    )

    private fun freshReadMoreProofV18(target:Rect):ReadMoreProofV18 {
        val root=try{rootInActiveWindow}catch(_:Throwable){null}
            ?: return ReadMoreProofV18(false,false,0,true,"NO_ROOT")
        val sw=resources.displayMetrics.widthPixels
        val sh=resources.displayMetrics.heightPixels
        val anchor=rmAnchorV17
        val prefix=if(anchor.length>44)anchor.substring(0,44) else anchor
        if(prefix.length<12 || rmBeforeAnchorLenV18<12)
            return ReadMoreProofV18(false,false,0,true,"NO_ANCHOR")

        var bestLen=-1
        var bestTruncated=true
        var bestSource="MISS"
        var scanned=0
        val q=java.util.ArrayDeque<AccessibilityNodeInfo>()
        q.add(root)
        while(!q.isEmpty() && scanned<900){
            val n=q.removeLast(); scanned++
            val r=Rect()
            try{n.getBoundsInScreen(r)}catch(_:Throwable){}
            val container=!r.isEmpty && r.width()>=(sw*0.965f).toInt() && r.height()>=(sh*0.45f).toInt()
            if(!container){
                val raw=try{n.text?.toString().orEmpty()}catch(_:Throwable){""}
                val desc=try{n.contentDescription?.toString().orEmpty()}catch(_:Throwable){""}
                val joined=(raw+" "+desc).trim()
                if(joined.isNotEmpty()){
                    val norm=RouteParser.normalize(joined)
                    val match=norm.contains(prefix) || (norm.length>=24 && prefix.contains(norm.take(minOf(32,norm.length))))
                    if(match){
                        val trunc=hasReadMoreTextV12(joined) || joined.contains("...") || joined.contains("…")
                        if(norm.length>bestLen){
                            bestLen=norm.length
                            bestTruncated=trunc
                            bestSource="ANCHOR"
                        }
                    }
                }
            }
            val cc=try{n.childCount}catch(_:Throwable){0}
            for(i in 0 until cc){
                try{n.getChild(i)?.let{q.add(it)}}catch(_:Throwable){}
            }
        }
        if(bestLen<0)return ReadMoreProofV18(false,false,0,true,"MISS")
        val grew=bestLen>=rmBeforeAnchorLenV18+12
        val expanded=grew && !bestTruncated
        return ReadMoreProofV18(expanded,true,bestLen,bestTruncated,bestSource)
    }

    private fun absorbCurrentTextBaselineV18(){
        val root=try{rootInActiveWindow}catch(_:Throwable){null} ?: return
        val now=try{collectNodeItems(root)}catch(_:Throwable){emptyList<NodeItem>()}
        if(now.isNotEmpty()){
            previousFastTexts=now.asSequence().map{it.text}.filter{it.isNotBlank()}.toSet()
        }
    }

    private fun waitForReadMoreExpansionV12(
        target:Rect,
        before:ReadMoreBandStatsV12,
        startedAt:Long,
        poll:Int,
        retried:Boolean
    ){
        val proof=freshReadMoreProofV18(target)
        rmProofV18="${proof.source}:before=${rmBeforeAnchorLenV18},after=${proof.chars},trunc=${proof.stillTruncated},stage=${rmGestureStageV18}"
        if(proof.expanded){
            rmExpanded=SystemClock.elapsedRealtime(); rmPolls=poll; rmPending=false; rmCarry=true
            handler.post{analyzeCurrentWindow()}
            return
        }

        // Each retry is a DIFFERENT measured point near the inline Read-more label.
        // We verify the same message after every attempt, so an already-expanded
        // bubble is never tapped again.
        val nextStage=when(poll){
            2 -> 1
            5 -> 2
            8 -> 3
            11 -> 4
            else -> -1
        }
        if(nextStage>=0 && nextStage>rmGestureStageV18){
            val ok=tapReadMoreRectV18(target,nextStage)
            if(ok){
                rmGestureStageV18=nextStage
                rmMethod=rmMethod+"+G${nextStage+1}"
            }
        }

        if(poll<14){
            handler.postDelayed({waitForReadMoreExpansionV12(target,before,startedAt,poll+1,retried)},6L)
            return
        }

        // Crucial v18 safety: if expansion cannot be PROVEN, absorb this truncated
        // message into the baseline and STOP. Never release it to the route parser.
        rmPolls=poll
        absorbCurrentTextBaselineV18()
        rmPending=false; rmCarry=false
        val failProof=rmProofV18
        val failMethod=rmMethod
        rmUsed=false
        Prefs.setStatus(this,"TEXT v18: Ler mais NAO expandiu/nao foi comprovado | metodo=$failMethod | $failProof | nenhuma rota enviada.")
    }

'''
s=s[:pos]+helpers+s[end:]

# Carry the strict proof into the successful route diagnostic.
copy_old='tdReadMoreUsed=rmUsed; tdReadMoreClicked=rmClicked; tdReadMoreExpanded=rmExpanded; tdReadMoreClickMs=rmClickMs; tdReadMorePolls=rmPolls; tdReadMoreMethod=rmMethod; tdReadMoreParseSourceV16=rmParseSourceV16; tdReadMoreParseItemsV16=rmParseItemsV16'
copy_new=copy_old+'; tdReadMoreProofV18=rmProofV18'
if copy_old not in s:
    raise SystemExit('v18 td copy anchor not found')
s=s.replace(copy_old,copy_new,1)

report_old='appendLine("readMoreParse=$tdReadMoreParseSourceV16 | readMoreItems=$tdReadMoreParseItemsV16")'
report_new=report_old+'\n                appendLine("readMoreProof=$tdReadMoreProofV18")'
if report_old not in s:
    raise SystemExit('v18 report anchor not found')
s=s.replace(report_old,report_new,1)

# Extend reset state.
reset_old='rmNodeChainV16=emptyList(); rmParseSourceV16=""; rmParseItemsV16=0; rmParseRetriesV16=0; rmTargetRectV17=Rect(); rmAnchorV17=""'
reset_new=reset_old+'; rmBeforeAnchorLenV18=0; rmGestureStageV18=0; rmProofV18=""'
if reset_old not in s:
    raise SystemExit('v18 reset anchor not found')
s=s.replace(reset_old,reset_new,1)

old_header='===== DIAGNOSTICO TEXTO v17 | TEXT v6 + READ MORE FRESH BUBBLE + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v18 | TEXT v6 + READ MORE STRICT PROOF + DIRECT SEND ====='
s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'private data class ReadMoreProofV18(',
    'private fun freshReadMoreProofV18(',
    'private fun tapReadMoreRectV18(',
    'TEXT v18: Ler mais NAO expandiu/nao foi comprovado',
    'readMoreProof=$tdReadMoreProofV18',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('READ MORE STRICT v18 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('READ MORE STRICT v18 applied: same-message growth proof + targeted gesture grid + never parse unproven truncation; IMAGE v9 preserved')
