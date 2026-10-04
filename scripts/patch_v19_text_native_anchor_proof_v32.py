from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v31 | TEXT v6 + SKIP OBSOLETE BAND + TRUNC BEFORE ROOT + LAZY ADMIN + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v32 | TEXT v6 + NATIVE ANCHOR PROOF + SKIP BAND + TRUNC BEFORE ROOT + LAZY ADMIN + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'private fun freshReadMoreProofV18(target:Rect):ReadMoreProofV18 {',
    'val prefix=if(anchor.length>44)anchor.substring(0,44) else anchor',
    'var bestLen=-1',
    'bestText=joined',
    'return ReadMoreProofV18(expanded,true,bestLen,bestTruncated,bestSource,bestText)',
    'obsoleteBandV31=skipped=true',
    'directProofV26=used=$tdV26DirectUsed',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
]
for m in required:
    if m not in s:
        raise SystemExit('NATIVE ANCHOR PROOF v32 wrong base: '+m)

# Diagnostics for the native fast path. The original strict BFS remains the fallback.
state_anchor='    private var tdV27RetryBandMs=0L\n'
state_insert=state_anchor+'''    private var rmV32NativeCalls=0
    private var rmV32NativeTotalMs=0L
    private var rmV32NativeMaxMs=0L
    private var rmV32NativeCandidates=0
    private var rmV32NativeWins=0
    private var rmV32BfsFallbacks=0
    private var tdV32NativeCalls=0
    private var tdV32NativeTotalMs=0L
    private var tdV32NativeMaxMs=0L
    private var tdV32NativeCandidates=0
    private var tdV32NativeWins=0
    private var tdV32BfsFallbacks=0
'''
if state_anchor not in s:
    raise SystemExit('v32 state anchor not found')
s=s.replace(state_anchor,state_insert,1)

# Native prefix search may return early only when it proves the exact same v18
# conditions: same message, >=12 char growth and no Read-more/ellipsis truncation.
# Otherwise the untouched strict BFS below remains the authoritative fallback.
anchor='''        if(prefix.length<12 || rmBeforeAnchorLenV18<12)
            return ReadMoreProofV18(false,false,0,true,"NO_ANCHOR","")

        var bestLen=-1
'''
insert='''        if(prefix.length<12 || rmBeforeAnchorLenV18<12)
            return ReadMoreProofV18(false,false,0,true,"NO_ANCHOR","")

        val v32NativeStart=SystemClock.elapsedRealtime()
        var v32BestLen=-1
        var v32BestText=""
        var v32BestTruncated=true
        val v32Nodes=try{root.findAccessibilityNodeInfosByText(prefix)}catch(_:Throwable){emptyList<AccessibilityNodeInfo>()}
        rmV32NativeCandidates+=v32Nodes.size
        for(n in v32Nodes){
            val r=Rect()
            try{n.getBoundsInScreen(r)}catch(_:Throwable){}
            val container=!r.isEmpty && r.width()>=(sw*0.965f).toInt() && r.height()>=(sh*0.45f).toInt()
            if(container)continue
            val raw=try{n.text?.toString().orEmpty()}catch(_:Throwable){""}
            val desc=try{n.contentDescription?.toString().orEmpty()}catch(_:Throwable){""}
            val joined=(raw+" "+desc).trim()
            if(joined.isEmpty())continue
            val norm=RouteParser.normalize(joined)
            val match=norm.contains(prefix) || (norm.length>=24 && prefix.contains(norm.take(minOf(32,norm.length))))
            if(!match)continue
            val trunc=hasReadMoreTextV12(joined) || joined.contains("...") || joined.contains("…")
            if(norm.length>v32BestLen){
                v32BestLen=norm.length
                v32BestText=joined
                v32BestTruncated=trunc
            }
        }
        val v32NativeCost=SystemClock.elapsedRealtime()-v32NativeStart
        rmV32NativeCalls++
        rmV32NativeTotalMs+=v32NativeCost
        if(v32NativeCost>rmV32NativeMaxMs)rmV32NativeMaxMs=v32NativeCost
        if(v32BestLen>=rmBeforeAnchorLenV18+12 && !v32BestTruncated){
            rmV32NativeWins++
            rmV23CurrentScanned=0
            return ReadMoreProofV18(true,true,v32BestLen,false,"ANCHOR_NATIVE",v32BestText)
        }
        rmV32BfsFallbacks++

        var bestLen=-1
'''
if anchor not in s:
    raise SystemExit('v32 proof insertion anchor not found')
s=s.replace(anchor,insert,1)

# Snapshot native proof metrics with the existing v27/v23 proof snapshot.
copy_anchor='tdV27RetryBandMs=rmV27RetryBandMs'
copy_insert=copy_anchor+'''; tdV32NativeCalls=rmV32NativeCalls; tdV32NativeTotalMs=rmV32NativeTotalMs; tdV32NativeMaxMs=rmV32NativeMaxMs; tdV32NativeCandidates=rmV32NativeCandidates; tdV32NativeWins=rmV32NativeWins; tdV32BfsFallbacks=rmV32BfsFallbacks'''
if copy_anchor not in s:
    raise SystemExit('v32 snapshot anchor not found')
s=s.replace(copy_anchor,copy_insert,1)

# Reset only in the existing per-attempt v27 reset chain. Do not match the class
# field declaration with the same rmV27RetryBandMs text.
reset_anchor='rmV27RetrySearchTotalMs=0L; rmV27RetrySearchMaxMs=0L; rmV27RetryBandMs=0L'
reset_insert=reset_anchor+'''; rmV32NativeCalls=0; rmV32NativeTotalMs=0L; rmV32NativeMaxMs=0L; rmV32NativeCandidates=0; rmV32NativeWins=0; rmV32BfsFallbacks=0'''
if reset_anchor not in s:
    raise SystemExit('v32 contextual reset anchor not found')
s=s.replace(reset_anchor,reset_insert,1)

report_anchor='''                    appendLine("obsoleteBandV31=skipped=true | immediateBand=${tdV27BandMs}ms | retryBand=${tdV27RetryBandMs}ms | strictSameMessageProof=preserved")
'''
report_insert=report_anchor+'''                    appendLine("nativeProofV32=calls=$tdV32NativeCalls | total=${tdV32NativeTotalMs}ms | max=${tdV32NativeMaxMs}ms | candidates=$tdV32NativeCandidates | wins=$tdV32NativeWins | bfsFallbacks=$tdV32BfsFallbacks | strictCriteria=same")
'''
if report_anchor not in s:
    raise SystemExit('v32 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'root.findAccessibilityNodeInfosByText(prefix)',
    'ReadMoreProofV18(true,true,v32BestLen,false,"ANCHOR_NATIVE",v32BestText)',
    'rmV32BfsFallbacks++',
    'nativeProofV32=calls=',
    'strictCriteria=same',
    'obsoleteBandV31=skipped=true',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('NATIVE ANCHOR PROOF v32 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('NATIVE ANCHOR PROOF v32 applied: native prefix lookup may short-circuit only with identical v18 same-message growth + no-truncation proof; original BFS preserved as fallback')
