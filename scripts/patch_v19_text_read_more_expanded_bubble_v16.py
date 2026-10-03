from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

required=[
    '===== DIAGNOSTICO TEXTO v15 | TEXT v6 + READ MORE NEWITEM GUARD + DIRECT SEND =====',
    'private fun findReadMoreDescFromNewItemsV15(',
    'private fun waitForReadMoreExpansionV12(',
    'val tfNewItems = tfNewItemsReverse.asReversed()',
    'private fun waitForTextDirectSendReadyV5(',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('READ MORE EXPANDED BUBBLE v16 wrong base: '+m)

# Keep the exact node/ancestor chain that belonged to the NEW truncated message.
# After WhatsApp expands it, parse this same message subtree instead of the v6
# global text-delta set. Repeated neighborhood/cage strings may already exist in
# previousFastTexts, which was exactly why v15 could expand correctly and still
# choose Rosario from only the surviving delta items.
state_anchor='    private var tdReadMoreClickMs=0L; private var tdReadMorePolls=0; private var tdReadMoreMethod=""\n'
state_insert='''    private var tdReadMoreClickMs=0L; private var tdReadMorePolls=0; private var tdReadMoreMethod=""
    private var rmNodeChainV16:List<AccessibilityNodeInfo> = emptyList()
    private var rmParseSourceV16=""; private var rmParseItemsV16=0; private var rmParseRetriesV16=0
    private var tdReadMoreParseSourceV16=""; private var tdReadMoreParseItemsV16=0
'''
if state_anchor not in s:
    raise SystemExit('v16 state anchor not found')
s=s.replace(state_anchor,state_insert,1)

helper_anchor='    private fun findReadMoreDescFromNewItemsV15(newItems:List<NodeItem>):ReadMoreDescTargetV14? {'
helpers=r'''    private fun rememberReadMoreChainV16(node:AccessibilityNodeInfo){
        val out=ArrayList<AccessibilityNodeInfo>(4)
        var cur:AccessibilityNodeInfo?=node
        var depth=0
        while(cur!=null && depth<4){
            out.add(cur)
            cur=try{cur.parent}catch(_:Throwable){null}
            depth++
        }
        rmNodeChainV16=out
        rmParseSourceV16=""
        rmParseItemsV16=0
        rmParseRetriesV16=0
    }

    private fun parseExpandedReadMoreBubbleV16(screenHeight:Int):RouteResult? {
        if(rmNodeChainV16.isEmpty())return null
        val screenWidth=resources.displayMetrics.widthPixels
        var best:RouteResult?=null
        var bestDepth=-1
        var bestCount=0

        // depth 0 can be only the inline text/span. Parents 1..3 are normally
        // wrappers + the actual WhatsApp message bubble. Stop before chat/recycler.
        for(depth in 1 until rmNodeChainV16.size){
            val root=rmNodeChainV16[depth]
            try{root.refresh()}catch(_:Throwable){}
            val rr=Rect()
            try{root.getBoundsInScreen(rr)}catch(_:Throwable){}
            if(rr.isEmpty)continue
            // A near-full-screen ancestor is the conversation container, not the
            // message. Never parse it: that could mix an older Valparaiso route.
            if(rr.width()>=(screenWidth*0.97f).toInt() && rr.height()>=(screenHeight*0.72f).toInt())break

            val q=java.util.ArrayDeque<AccessibilityNodeInfo>()
            q.add(root)
            val texts=ArrayList<ScreenText>(24)
            val seen=HashSet<String>()
            var visited=0
            var truncated=false
            while(!q.isEmpty() && visited<180){
                val n=q.removeLast(); visited++
                val r=Rect()
                try{n.getBoundsInScreen(r)}catch(_:Throwable){}
                val raw=try{n.text?.toString().orEmpty()}catch(_:Throwable){""}
                if(raw.isNotBlank()){
                    if(hasReadMoreTextV12(raw) || raw.contains("...") || raw.contains("…"))truncated=true
                    val key=raw+"|"+r.left+","+r.top+","+r.right+","+r.bottom
                    if(seen.add(key))texts.add(ScreenText(raw,r.left,r.top,r.right,r.bottom))
                }
                val cc=try{n.childCount}catch(_:Throwable){0}
                for(i in 0 until cc){
                    try{n.getChild(i)?.let{q.add(it)}}catch(_:Throwable){}
                }
            }
            // Do not trust a subtree that still visibly contains the truncation.
            if(truncated || texts.isEmpty())continue
            val route=RouteParser.parseScreenTexts(texts,screenHeight)
                ?: RouteParser.parsePlainTexts(texts.map{it.text})
            if(route!=null && (best==null || route.priorityIndex<best!!.priorityIndex)){
                best=route; bestDepth=depth; bestCount=texts.size
            }
        }

        if(best!=null){
            rmParseSourceV16="PARENT"+bestDepth
            rmParseItemsV16=bestCount
        }
        return best
    }

'''
if helper_anchor not in s:
    raise SystemExit('v16 helper anchor not found')
s=s.replace(helper_anchor,helpers+helper_anchor,1)

# Remember the exact message chain before either direct-desc click or the v12
# gesture fallback. The current M52 trace used GESTURE+GESTURE2, so both matter.
direct_old='''            if(descTarget!=null){
                val before=freshReadMoreBandStatsV12(descTarget.rect)
'''
direct_new='''            if(descTarget!=null){
                rememberReadMoreChainV16(descTarget.node)
                val before=freshReadMoreBandStatsV12(descTarget.rect)
'''
if direct_old not in s:
    raise SystemExit('v16 direct target anchor not found')
s=s.replace(direct_old,direct_new,1)

fallback_old='''            if(readMoreTarget!=null){
                val before=freshReadMoreBandStatsV12(readMoreTarget.rect)
'''
fallback_new='''            if(readMoreTarget!=null){
                rememberReadMoreChainV16(readMoreTarget.node)
                val before=freshReadMoreBandStatsV12(readMoreTarget.rect)
'''
if fallback_old not in s:
    raise SystemExit('v16 fallback target anchor not found')
s=s.replace(fallback_old,fallback_new,1)

# After a verified expansion, rmCarry=true. In that one analysis, do NOT derive
# the route from tfNewItems (which intentionally removes texts seen before).
# Parse the remembered expanded message bubble itself. If its tree is one frame
# late, retry briefly; never fall through and send Rosario from a partial delta.
parse_old=r'''            val tfParseStart = SystemClock.elapsedRealtime()
            val tfRoute =
                RouteParser.parseScreenTexts(
                    tfNewItems.map {
                        ScreenText(
                            text = it.text,
                            left = it.rect.left,
                            top = it.rect.top,
                            right = it.rect.right,
                            bottom = it.rect.bottom
                        )
                    },
                    tfScreenHeight
                ) ?: RouteParser.parsePlainTexts(tfNewItems.map { it.text })
            val tfParseDone = SystemClock.elapsedRealtime()
'''
parse_new=r'''            val tfParseStart = SystemClock.elapsedRealtime()
            val tfRoute = if(rmCarry){
                parseExpandedReadMoreBubbleV16(tfScreenHeight)
            }else{
                RouteParser.parseScreenTexts(
                    tfNewItems.map {
                        ScreenText(
                            text = it.text,
                            left = it.rect.left,
                            top = it.rect.top,
                            right = it.rect.right,
                            bottom = it.rect.bottom
                        )
                    },
                    tfScreenHeight
                ) ?: RouteParser.parsePlainTexts(tfNewItems.map { it.text })
            }
            val tfParseDone = SystemClock.elapsedRealtime()

            if(rmCarry && tfRoute==null){
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
if parse_old not in s:
    raise SystemExit('v16 parser block anchor not found')
s=s.replace(parse_old,parse_new,1)

# Carry the source of the expanded-bubble parse into the existing RAM diagnostic.
tdbegin_old='tdReadMoreUsed=rmUsed; tdReadMoreClicked=rmClicked; tdReadMoreExpanded=rmExpanded; tdReadMoreClickMs=rmClickMs; tdReadMorePolls=rmPolls; tdReadMoreMethod=rmMethod'
tdbegin_new='tdReadMoreUsed=rmUsed; tdReadMoreClicked=rmClicked; tdReadMoreExpanded=rmExpanded; tdReadMoreClickMs=rmClickMs; tdReadMorePolls=rmPolls; tdReadMoreMethod=rmMethod; tdReadMoreParseSourceV16=rmParseSourceV16; tdReadMoreParseItemsV16=rmParseItemsV16'
if tdbegin_old not in s:
    raise SystemExit('v16 tdBegin copy anchor not found')
s=s.replace(tdbegin_old,tdbegin_new,1)

reset_old='rmPending=false; rmCarry=false; rmUsed=false; rmStarted=0L; rmClicked=0L; rmExpanded=0L; rmClickMs=0L; rmPolls=0; rmMethod=""'
reset_new='rmPending=false; rmCarry=false; rmUsed=false; rmStarted=0L; rmClicked=0L; rmExpanded=0L; rmClickMs=0L; rmPolls=0; rmMethod=""; rmNodeChainV16=emptyList(); rmParseSourceV16=""; rmParseItemsV16=0; rmParseRetriesV16=0'
if reset_old not in s:
    raise SystemExit('v16 reset anchor not found')
s=s.replace(reset_old,reset_new,1)

report_old='if(tdReadMoreUsed) appendLine("readMore=${tdD(tdReadMoreClicked,tdReadMoreExpanded)} | readMoreAction=${tdReadMoreClickMs}ms | readMorePolls=$tdReadMorePolls")'
report_new='''if(tdReadMoreUsed){
                appendLine("readMore=${tdD(tdReadMoreClicked,tdReadMoreExpanded)} | readMoreAction=${tdReadMoreClickMs}ms | readMorePolls=$tdReadMorePolls")
                appendLine("readMoreParse=$tdReadMoreParseSourceV16 | readMoreItems=$tdReadMoreParseItemsV16")
            }'''
if report_old not in s:
    raise SystemExit('v16 report anchor not found')
s=s.replace(report_old,report_new,1)

old_header='===== DIAGNOSTICO TEXTO v15 | TEXT v6 + READ MORE NEWITEM GUARD + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v16 | TEXT v6 + READ MORE EXPANDED BUBBLE + DIRECT SEND ====='
s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'private fun rememberReadMoreChainV16(',
    'private fun parseExpandedReadMoreBubbleV16(',
    'parseExpandedReadMoreBubbleV16(tfScreenHeight)',
    'Nao enviei rota parcial.',
    'readMoreParse=$tdReadMoreParseSourceV16',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('READ MORE EXPANDED BUBBLE v16 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('READ MORE EXPANDED BUBBLE v16 applied: parse same expanded message subtree, never partial v6 delta; IMAGE v9 preserved')
