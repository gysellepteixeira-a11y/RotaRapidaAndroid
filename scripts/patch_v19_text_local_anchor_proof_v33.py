from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v31 | TEXT v6 + SKIP OBSOLETE BAND + TRUNC BEFORE ROOT + LAZY ADMIN + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v33 | TEXT v6 + LOCAL ANCHOR PROOF + SKIP BAND + TRUNC BEFORE ROOT + LAZY ADMIN + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'private fun rememberReadMoreChainV16(node:AccessibilityNodeInfo)',
    'private fun freshReadMoreProofV18(target:Rect):ReadMoreProofV18 {',
    'private fun absorbCurrentTextBaselineV18()',
    'rmV23CurrentScanned=scanned',
    'bestText=joined',
    'obsoleteBandV31=skipped=true',
    'directProofV26=used=$tdV26DirectUsed',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
]
for m in required:
    if m not in s:
        raise SystemExit('LOCAL ANCHOR PROOF v33 wrong base: '+m)

# v33 only adds a fast proof path. The original v18 fresh-root BFS is copied
# unchanged below as fallback. A local success still requires the exact v18 rules:
# same pre-click message anchor, >=12 chars growth, and no truncation marker.
state_anchor='    private var tdV27RetryBandMs=0L\n'
state_insert=state_anchor+'''    private var rmV33AnchorDepth=-1
    private var rmV33LocalCalls=0
    private var rmV33LocalTotalMs=0L
    private var rmV33LocalMaxMs=0L
    private var rmV33LocalWins=0
    private var rmV33BfsFallbacks=0
    private var rmV33LocalRefreshOk=false
    private var rmV33LocalChars=0
    private var rmV33LocalTruncated=true
    private var tdV33AnchorDepth=-1
    private var tdV33LocalCalls=0
    private var tdV33LocalTotalMs=0L
    private var tdV33LocalMaxMs=0L
    private var tdV33LocalWins=0
    private var tdV33BfsFallbacks=0
    private var tdV33LocalRefreshOk=false
    private var tdV33LocalChars=0
    private var tdV33LocalTruncated=true
'''
if state_anchor not in s:
    raise SystemExit('v33 state anchor not found')
s=s.replace(state_anchor,state_insert,1)

# v18 already chooses the longest message-sized ancestor as its pre-click anchor.
# Remember which depth produced that anchor so proof can refresh that exact node.
remember_init='''        var bestAnchor=""
        val sw=resources.displayMetrics.widthPixels
'''
remember_init_new='''        var bestAnchor=""
        rmV33AnchorDepth=-1
        val sw=resources.displayMetrics.widthPixels
'''
if remember_init not in s:
    raise SystemExit('v33 remember init anchor not found')
s=s.replace(remember_init,remember_init_new,1)

remember_choice='''            if(!container && n.length>bestAnchor.length && !isExactReadMoreV12(n))bestAnchor=n
'''
remember_choice_new='''            if(!container && n.length>bestAnchor.length && !isExactReadMoreV12(n)){
                bestAnchor=n
                rmV33AnchorDepth=depth
            }
'''
if remember_choice not in s:
    raise SystemExit('v33 remember choice anchor not found')
s=s.replace(remember_choice,remember_choice_new,1)

# Replace ONLY freshReadMoreProofV18. Local path checks one remembered node first.
# If refresh/match/growth/truncation proof fails for any reason, the original v18
# fresh-root BFS executes with the same matching and safety criteria.
a=s.find('    private fun freshReadMoreProofV18(target:Rect):ReadMoreProofV18 {')
b=s.find('    private fun absorbCurrentTextBaselineV18()',a)
if a<0 or b<0:
    raise SystemExit('v33 proof region not found')
proof=r'''    private fun freshReadMoreProofV18(target:Rect):ReadMoreProofV18 {
        val sw=resources.displayMetrics.widthPixels
        val sh=resources.displayMetrics.heightPixels
        val anchor=rmAnchorV17
        val prefix=if(anchor.length>44)anchor.substring(0,44) else anchor
        if(prefix.length<12 || rmBeforeAnchorLenV18<12)
            return ReadMoreProofV18(false,false,0,true,"NO_ANCHOR","")

        // v33 fast path: refresh the exact ancestor that supplied the pre-click
        // same-message anchor. This avoids walking the whole accessibility tree
        // when WhatsApp keeps that virtual node alive across the expansion.
        val localStart=SystemClock.elapsedRealtime()
        rmV33LocalCalls++
        var localRefresh=false
        var localChars=0
        var localTruncated=true
        var localText=""
        var localMatch=false
        val localNode=if(rmV33AnchorDepth>=0 && rmV33AnchorDepth<rmNodeChainV16.size){
            rmNodeChainV16[rmV33AnchorDepth]
        }else null
        if(localNode!=null){
            localRefresh=try{localNode.refresh()}catch(_:Throwable){false}
            if(localRefresh){
                val rr=Rect()
                try{localNode.getBoundsInScreen(rr)}catch(_:Throwable){}
                val container=!rr.isEmpty && rr.width()>=(sw*0.965f).toInt() && rr.height()>=(sh*0.45f).toInt()
                if(!container){
                    val raw=try{localNode.text?.toString().orEmpty()}catch(_:Throwable){""}
                    val desc=try{localNode.contentDescription?.toString().orEmpty()}catch(_:Throwable){""}
                    val joined=(raw+" "+desc).trim()
                    if(joined.isNotEmpty()){
                        val norm=RouteParser.normalize(joined)
                        localMatch=norm.contains(prefix) || (norm.length>=24 && prefix.contains(norm.take(minOf(32,norm.length))))
                        if(localMatch){
                            localChars=norm.length
                            localText=joined
                            localTruncated=hasReadMoreTextV12(joined) || joined.contains("...") || joined.contains("…")
                        }
                    }
                }
            }
        }
        val localCost=SystemClock.elapsedRealtime()-localStart
        rmV33LocalTotalMs+=localCost
        if(localCost>rmV33LocalMaxMs)rmV33LocalMaxMs=localCost
        rmV33LocalRefreshOk=localRefresh
        rmV33LocalChars=localChars
        rmV33LocalTruncated=localTruncated
        val localGrew=localMatch && localChars>=rmBeforeAnchorLenV18+12
        if(localGrew && !localTruncated){
            rmV33LocalWins++
            rmV23CurrentScanned=1
            return ReadMoreProofV18(true,true,localChars,false,"ANCHOR_LOCAL",localText)
        }
        rmV33BfsFallbacks++

        // Original v18 strict proof fallback: fresh active root + full BFS.
        val root=try{rootInActiveWindow}catch(_:Throwable){null}
            ?: return ReadMoreProofV18(false,false,0,true,"NO_ROOT","")
        var bestLen=-1
        var bestTruncated=true
        var bestSource="MISS"
        var bestText=""
        var scanned=0
        rmV23CurrentScanned=0
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
                            bestText=joined
                        }
                    }
                }
            }
            val cc=try{n.childCount}catch(_:Throwable){0}
            for(i in 0 until cc){
                try{n.getChild(i)?.let{q.add(it)}}catch(_:Throwable){}
            }
        }
        if(bestLen<0){
            rmV23CurrentScanned=scanned
            return ReadMoreProofV18(false,false,0,true,"MISS","")
        }
        rmV23CurrentScanned=scanned
        val grew=bestLen>=rmBeforeAnchorLenV18+12
        val expanded=grew && !bestTruncated
        return ReadMoreProofV18(expanded,true,bestLen,bestTruncated,bestSource,bestText)
    }

'''
s=s[:a]+proof+s[b:]

# Snapshot diagnostics alongside the existing v27 proof/click diagnostics.
copy_anchor='tdV27RetryBandMs=rmV27RetryBandMs'
copy_insert=copy_anchor+'''; tdV33AnchorDepth=rmV33AnchorDepth; tdV33LocalCalls=rmV33LocalCalls; tdV33LocalTotalMs=rmV33LocalTotalMs; tdV33LocalMaxMs=rmV33LocalMaxMs; tdV33LocalWins=rmV33LocalWins; tdV33BfsFallbacks=rmV33BfsFallbacks; tdV33LocalRefreshOk=rmV33LocalRefreshOk; tdV33LocalChars=rmV33LocalChars; tdV33LocalTruncated=rmV33LocalTruncated'''
if copy_anchor not in s:
    raise SystemExit('v33 snapshot anchor not found')
s=s.replace(copy_anchor,copy_insert,1)

# Temporary state resets only after successful diagnostics are copied to td*.
reset_anchor='rmV27RetryBandMs=0L'
reset_insert=reset_anchor+'''; rmV33AnchorDepth=-1; rmV33LocalCalls=0; rmV33LocalTotalMs=0L; rmV33LocalMaxMs=0L; rmV33LocalWins=0; rmV33BfsFallbacks=0; rmV33LocalRefreshOk=false; rmV33LocalChars=0; rmV33LocalTruncated=true'''
if reset_anchor not in s:
    raise SystemExit('v33 reset anchor not found')
s=s.replace(reset_anchor,reset_insert,1)

report_anchor='''                    appendLine("obsoleteBandV31=skipped=true | immediateBand=${tdV27BandMs}ms | retryBand=${tdV27RetryBandMs}ms | strictSameMessageProof=preserved")
'''
report_insert=report_anchor+'''                    appendLine("localProofV33=calls=$tdV33LocalCalls | total=${tdV33LocalTotalMs}ms | max=${tdV33LocalMaxMs}ms | anchorDepth=$tdV33AnchorDepth | refresh=$tdV33LocalRefreshOk | chars=$tdV33LocalChars | trunc=$tdV33LocalTruncated | wins=$tdV33LocalWins | bfsFallbacks=$tdV33BfsFallbacks | strictCriteria=same")
'''
if report_anchor not in s:
    raise SystemExit('v33 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'rmV33AnchorDepth=depth',
    'localNode.refresh()',
    'ReadMoreProofV18(true,true,localChars,false,"ANCHOR_LOCAL",localText)',
    'rmV33BfsFallbacks++',
    'localProofV33=calls=',
    'strictCriteria=same',
    'obsoleteBandV31=skipped=true',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'directProofV26=used=$tdV26DirectUsed',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('LOCAL ANCHOR PROOF v33 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('LOCAL ANCHOR PROOF v33 applied: exact remembered anchor node refreshed first; identical v18 growth/no-truncation criteria; original fresh-root BFS preserved as fallback')
