from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v23 | TEXT v6 + READ MORE PROOF DIAG + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v24 | TEXT v6 + SKIP IMMEDIATE PROOF + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'private fun freshReadMoreProofV18(',
    'private fun waitForReadMoreExpansionV12(',
    'val rmV23Entry=SystemClock.elapsedRealtime()',
    'proofV23=calls=$tdV23ProofCalls',
    'handler.postDelayed({waitForReadMoreExpansionV12(target,before,startedAt,poll+1,retried)},6L)',
    'scheduleV22=${tdV22RequestedDelay}ms',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('SKIP IMMEDIATE PROOF v24 wrong base: '+m)

# Isolated A/B: v23 proved that the immediate post-click proof (poll 0) never won
# in the measured samples; it only spent 11-20+ ms scanning the same 25 nodes.
# v24 does NOT change the strict proof criterion, anchor, parser, click, DESC wait,
# send path, image path or later polling. It only skips that synchronous poll-0
# scan and lets the already-existing 6 ms delayed proof become the first proof.
wait_anchor='''    ){
        val rmV23Entry=SystemClock.elapsedRealtime()
'''
wait_insert='''    ){
        if(poll==0){
            // Keep the exact pre-click anchor captured by rememberReadMoreChainV16.
            // Skip only the immediate full-tree proof scan; first real proof runs
            // after the same 6 ms cadence already used between v23 proof polls.
            rmV23LastPostAt=SystemClock.elapsedRealtime()
            handler.postDelayed({waitForReadMoreExpansionV12(target,before,startedAt,1,retried)},6L)
            return
        }
        val rmV23Entry=SystemClock.elapsedRealtime()
'''
if wait_anchor not in s:
    raise SystemExit('v24 wait entry anchor not found')
s=s.replace(wait_anchor,wait_insert,1)

# Add one explicit A/B marker; preserve all v23 proof timing counters so we can
# compare proof calls/costs directly against the previous build.
report_anchor='''                appendLine("proofV23=calls=$tdV23ProofCalls | proof0=${tdV23Proof0Ms}ms/${tdV23Scanned0}nodes | proof1=${tdV23Proof1Ms}ms/${tdV23Scanned1}nodes | proofTotal=${tdV23ProofTotalMs}ms | proofMax=${tdV23ProofMaxMs}ms | scannedTotal=$tdV23ScannedTotal | scannedMax=$tdV23ScannedMax | poll1Gap=${tdV23PollGap1}ms | poll1Late=${tdV23PollLate1}ms")
'''
report_insert=report_anchor+'''                appendLine("proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved")
'''
if report_anchor not in s:
    raise SystemExit('v24 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'if(poll==0){',
    'waitForReadMoreExpansionV12(target,before,startedAt,1,retried)',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'proofV23=calls=$tdV23ProofCalls',
    'scheduleV22=${tdV22RequestedDelay}ms',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('SKIP IMMEDIATE PROOF v24 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('SKIP IMMEDIATE PROOF v24 applied: poll-0 proof scan skipped; first strict proof after existing 6ms cadence; v23 diagnostics, v21 safety, TEXT v6 and IMAGE v9 preserved')
