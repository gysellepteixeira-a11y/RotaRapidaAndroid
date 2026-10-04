from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v22 | TEXT v6 + SCHEDULE DIAG + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v23 | TEXT v6 + READ MORE PROOF DIAG + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'private fun freshReadMoreProofV18(',
    'private fun waitForReadMoreExpansionV12(',
    'var scanned=0',
    'handler.postDelayed({waitForReadMoreExpansionV12(target,before,startedAt,poll+1,retried)},6L)',
    'scheduleV22=${tdV22RequestedDelay}ms',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('READ MORE PROOF DIAG v23 wrong base: '+m)

# Diagnostic-only primitive state. No parser, click, proof criterion, polling cadence,
# send path or image path is changed.
state_anchor='    private var tdV22MaxLate=0L\n'
state_insert=state_anchor+'''    private var rmV23CurrentScanned=0
    private var rmV23ProofCalls=0
    private var rmV23ProofTotalMs=0L
    private var rmV23ProofMaxMs=0L
    private var rmV23Proof0Ms=-1L
    private var rmV23Proof1Ms=-1L
    private var rmV23ScannedTotal=0
    private var rmV23ScannedMax=0
    private var rmV23Scanned0=-1
    private var rmV23Scanned1=-1
    private var rmV23LastPostAt=0L
    private var rmV23PollGap1=-1L
    private var rmV23PollLate1=-1L
    private var tdV23ProofCalls=0
    private var tdV23ProofTotalMs=0L
    private var tdV23ProofMaxMs=0L
    private var tdV23Proof0Ms=-1L
    private var tdV23Proof1Ms=-1L
    private var tdV23ScannedTotal=0
    private var tdV23ScannedMax=0
    private var tdV23Scanned0=-1
    private var tdV23Scanned1=-1
    private var tdV23PollGap1=-1L
    private var tdV23PollLate1=-1L
'''
if state_anchor not in s:
    raise SystemExit('v23 state anchor not found')
s=s.replace(state_anchor,state_insert,1)

# Count exactly how many accessibility nodes the strict-proof scan examines.
# This only writes one Int after the existing scan; matching/proof behavior is untouched.
scan_anchor='''        var scanned=0
        val q=java.util.ArrayDeque<AccessibilityNodeInfo>()
'''
scan_insert='''        var scanned=0
        rmV23CurrentScanned=0
        val q=java.util.ArrayDeque<AccessibilityNodeInfo>()
'''
if scan_anchor not in s:
    raise SystemExit('v23 scan anchor not found')
s=s.replace(scan_anchor,scan_insert,1)

miss_anchor='''        if(bestLen<0)return ReadMoreProofV18(false,false,0,true,"MISS")
        val grew=bestLen>=rmBeforeAnchorLenV18+12
'''
miss_insert='''        if(bestLen<0){
            rmV23CurrentScanned=scanned
            return ReadMoreProofV18(false,false,0,true,"MISS")
        }
        rmV23CurrentScanned=scanned
        val grew=bestLen>=rmBeforeAnchorLenV18+12
'''
if miss_anchor not in s:
    raise SystemExit('v23 proof end anchor not found')
s=s.replace(miss_anchor,miss_insert,1)

# Time each strict-proof call and the first 6ms repost interval. The existing proof
# call is still synchronous and the existing 6ms postDelayed remains exactly 6ms.
wait_anchor='''    ){
        val proof=freshReadMoreProofV18(target)
        rmProofV18="${proof.source}:before=${rmBeforeAnchorLenV18},after=${proof.chars},trunc=${proof.stillTruncated},stage=${rmGestureStageV18}"
'''
wait_insert='''    ){
        val rmV23Entry=SystemClock.elapsedRealtime()
        if(poll==1 && rmV23LastPostAt>0L){
            rmV23PollGap1=rmV23Entry-rmV23LastPostAt
            rmV23PollLate1=(rmV23PollGap1-6L).coerceAtLeast(0L)
        }
        val rmV23ProofStart=SystemClock.elapsedRealtime()
        val proof=freshReadMoreProofV18(target)
        val rmV23ProofCost=SystemClock.elapsedRealtime()-rmV23ProofStart
        val rmV23Scan=rmV23CurrentScanned
        rmV23ProofCalls++
        rmV23ProofTotalMs+=rmV23ProofCost
        if(rmV23ProofCost>rmV23ProofMaxMs)rmV23ProofMaxMs=rmV23ProofCost
        rmV23ScannedTotal+=rmV23Scan
        if(rmV23Scan>rmV23ScannedMax)rmV23ScannedMax=rmV23Scan
        if(poll==0){rmV23Proof0Ms=rmV23ProofCost;rmV23Scanned0=rmV23Scan}
        if(poll==1){rmV23Proof1Ms=rmV23ProofCost;rmV23Scanned1=rmV23Scan}
        rmProofV18="${proof.source}:before=${rmBeforeAnchorLenV18},after=${proof.chars},trunc=${proof.stillTruncated},stage=${rmGestureStageV18}"
'''
if wait_anchor not in s:
    raise SystemExit('v23 wait entry anchor not found')
s=s.replace(wait_anchor,wait_insert,1)

post_anchor='''            handler.postDelayed({waitForReadMoreExpansionV12(target,before,startedAt,poll+1,retried)},6L)
            return
'''
post_insert='''            rmV23LastPostAt=SystemClock.elapsedRealtime()
            handler.postDelayed({waitForReadMoreExpansionV12(target,before,startedAt,poll+1,retried)},6L)
            return
'''
if post_anchor not in s:
    raise SystemExit('v23 repost anchor not found')
s=s.replace(post_anchor,post_insert,1)

# Snapshot the proof diagnostics alongside the existing successful Read-more snapshot.
copy_anchor='tdReadMoreProofV18=rmProofV18'
copy_insert='''tdReadMoreProofV18=rmProofV18; tdV23ProofCalls=rmV23ProofCalls; tdV23ProofTotalMs=rmV23ProofTotalMs; tdV23ProofMaxMs=rmV23ProofMaxMs; tdV23Proof0Ms=rmV23Proof0Ms; tdV23Proof1Ms=rmV23Proof1Ms; tdV23ScannedTotal=rmV23ScannedTotal; tdV23ScannedMax=rmV23ScannedMax; tdV23Scanned0=rmV23Scanned0; tdV23Scanned1=rmV23Scanned1; tdV23PollGap1=rmV23PollGap1; tdV23PollLate1=rmV23PollLate1'''
if copy_anchor not in s:
    raise SystemExit('v23 snapshot anchor not found')
s=s.replace(copy_anchor,copy_insert,1)

# Add a compact line after the existing readMoreProof line.
report_anchor='''                appendLine("readMoreProof=$tdReadMoreProofV18")
'''
report_insert=report_anchor+'''                appendLine("proofV23=calls=$tdV23ProofCalls | proof0=${tdV23Proof0Ms}ms/${tdV23Scanned0}nodes | proof1=${tdV23Proof1Ms}ms/${tdV23Scanned1}nodes | proofTotal=${tdV23ProofTotalMs}ms | proofMax=${tdV23ProofMaxMs}ms | scannedTotal=$tdV23ScannedTotal | scannedMax=$tdV23ScannedMax | poll1Gap=${tdV23PollGap1}ms | poll1Late=${tdV23PollLate1}ms")
'''
if report_anchor not in s:
    raise SystemExit('v23 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

# Reset only diagnostic counters with the existing Read-more state reset.
reset_anchor='rmBeforeAnchorLenV18=0; rmGestureStageV18=0; rmProofV18=""'
reset_insert=reset_anchor+'''; rmV23CurrentScanned=0; rmV23ProofCalls=0; rmV23ProofTotalMs=0L; rmV23ProofMaxMs=0L; rmV23Proof0Ms=-1L; rmV23Proof1Ms=-1L; rmV23ScannedTotal=0; rmV23ScannedMax=0; rmV23Scanned0=-1; rmV23Scanned1=-1; rmV23LastPostAt=0L; rmV23PollGap1=-1L; rmV23PollLate1=-1L'''
if reset_anchor not in s:
    raise SystemExit('v23 reset anchor not found')
s=s.replace(reset_anchor,reset_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'proofV23=calls=$tdV23ProofCalls',
    'poll1Late=${tdV23PollLate1}ms',
    'rmV23CurrentScanned=scanned',
    'handler.postDelayed({waitForReadMoreExpansionV12(target,before,startedAt,poll+1,retried)},6L)',
    'scheduleV22=${tdV22RequestedDelay}ms',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('READ MORE PROOF DIAG v23 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('READ MORE PROOF DIAG v23 applied: proof cost/node count + first repost lateness only; v22/v21 behavior, TEXT v6 and IMAGE v9 preserved')
