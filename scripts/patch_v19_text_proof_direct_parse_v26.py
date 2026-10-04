from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v25 | TEXT v6 + POST PROOF DIAG + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v26 | TEXT v6 + PROOF DIRECT PARSE + READ MORE v21 + DIRECT SEND ====='
required=[
    old_header,
    'private data class ReadMoreProofV18(',
    'private fun freshReadMoreProofV18(',
    'if(proof.expanded){',
    'rmV25ProofConfirmedAt=rmExpanded',
    'postProofV25=proof->reanalyze=',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('PROOF DIRECT PARSE v26 wrong base: '+m)

# v26 A/B goal:
# the strict proof already walks a FRESH tree, reacquires the SAME message, proves
# that it grew and proves truncation disappeared. Keep the exact full accessible
# text from that winning proof node and feed it straight to the same plain-text
# parser. If that direct parse does not produce a valid non-duplicate route, fall
# back to the untouched v25 reanalysis/subtree path.

# Per-attempt origin timing lets the normal diagnostic keep the ORIGINAL analysis
# and collection timestamps even though the successful v26 route bypasses the
# second analyzeCurrentWindow() call entirely.
state_anchor='    private var tdV25RouteAt=0L\n'
state_insert=state_anchor+'''    private var rmV26AnalyzeAt=0L
    private var rmV26CollectDoneAt=0L
    private var rmV26CollectMs=0L
    private var rmV26NewItems=0
    private var rmV26DirectParseMs=0L
    private var rmV26ProofTextChars=0
    private var rmV26Fallback=false
    private var tdV26DirectUsed=false
    private var tdV26DirectParseMs=0L
    private var tdV26ProofTextChars=0
    private var tdV26Fallback=false
'''
if state_anchor not in s:
    raise SystemExit('v26 state anchor not found')
s=s.replace(state_anchor,state_insert,1)

# Carry the exact winning message text out of the already-required strict proof.
data_old='''    private data class ReadMoreProofV18(
        val expanded:Boolean,
        val matched:Boolean,
        val chars:Int,
        val stillTruncated:Boolean,
        val source:String
    )
'''
data_new='''    private data class ReadMoreProofV18(
        val expanded:Boolean,
        val matched:Boolean,
        val chars:Int,
        val stillTruncated:Boolean,
        val source:String,
        val text:String
    )
'''
if data_old not in s:
    raise SystemExit('v26 ReadMoreProof data class anchor not found')
s=s.replace(data_old,data_new,1)

# Constructors that return without a matched message carry an empty text.
for old,new in [
    ('ReadMoreProofV18(false,false,0,true,"NO_ROOT")','ReadMoreProofV18(false,false,0,true,"NO_ROOT","")'),
    ('ReadMoreProofV18(false,false,0,true,"NO_ANCHOR")','ReadMoreProofV18(false,false,0,true,"NO_ANCHOR","")'),
    ('ReadMoreProofV18(false,false,0,true,"MISS")','ReadMoreProofV18(false,false,0,true,"MISS","")'),
]:
    if old not in s:
        raise SystemExit('v26 proof constructor anchor not found: '+old)
    s=s.replace(old,new)

best_anchor='''        var bestLen=-1
        var bestTruncated=true
        var bestSource="MISS"
        var scanned=0
'''
best_insert='''        var bestLen=-1
        var bestTruncated=true
        var bestSource="MISS"
        var bestText=""
        var scanned=0
'''
if best_anchor not in s:
    raise SystemExit('v26 best proof state anchor not found')
s=s.replace(best_anchor,best_insert,1)

best_update_old='''                            bestLen=norm.length
                            bestTruncated=trunc
                            bestSource="ANCHOR"
'''
best_update_new='''                            bestLen=norm.length
                            bestTruncated=trunc
                            bestSource="ANCHOR"
                            bestText=joined
'''
if best_update_old not in s:
    raise SystemExit('v26 winning proof text anchor not found')
s=s.replace(best_update_old,best_update_new,1)

final_old='''        return ReadMoreProofV18(expanded,true,bestLen,bestTruncated,bestSource)
'''
final_new='''        return ReadMoreProofV18(expanded,true,bestLen,bestTruncated,bestSource,bestText)
'''
if final_old not in s:
    raise SystemExit('v26 final proof constructor anchor not found')
s=s.replace(final_old,final_new,1)

# Remember the first analysis/collection timing for immediate DESC_NEWITEM/DESC_ROOT.
desc_old='''            if(descTarget!=null){
                rememberReadMoreChainV16(descTarget.node)
'''
desc_new='''            if(descTarget!=null){
                rmV26AnalyzeAt=tdAnalyzeLocal
                rmV26CollectDoneAt=tdCollectDoneLocal
                rmV26CollectMs=tdCollectLocal
                rmV26NewItems=tfNewItems.size
                rememberReadMoreChainV16(descTarget.node)
'''
if desc_old not in s:
    raise SystemExit('v26 immediate desc timing anchor not found')
s=s.replace(desc_old,desc_new,1)

# If the real desc node appears a few ms later (DESC_RETRY), keep the timing from
# the original analysis that detected the truncated bubble.
wait_old='''            if(readMoreTarget!=null){
                // Do NOT use GESTURE/G2/G3/G4/G5. The M52 trace proved those can
'''
wait_new='''            if(readMoreTarget!=null){
                rmV26AnalyzeAt=tdAnalyzeLocal
                rmV26CollectDoneAt=tdCollectDoneLocal
                rmV26CollectMs=tdCollectLocal
                rmV26NewItems=tfNewItems.size
                // Do NOT use GESTURE/G2/G3/G4/G5. The M52 trace proved those can
'''
if wait_old not in s:
    raise SystemExit('v26 desc-wait timing anchor not found')
s=s.replace(wait_old,wait_new,1)

# Replace only the SUCCESS action after strict proof. Proof criteria and polling
# are unchanged. Direct parser uses the exact full text from the proof. A miss or
# duplicate falls back to v25 handler.post{analyzeCurrentWindow()} unchanged.
proof_old='''        if(proof.expanded){
            rmExpanded=SystemClock.elapsedRealtime(); rmV25ProofConfirmedAt=rmExpanded; rmPolls=poll; rmPending=false; rmCarry=true
            handler.post{analyzeCurrentWindow()}
            return
        }
'''
proof_new='''        if(proof.expanded){
            rmExpanded=SystemClock.elapsedRealtime(); rmV25ProofConfirmedAt=rmExpanded; rmPolls=poll; rmPending=false; rmCarry=true

            val v26ParseStart=SystemClock.elapsedRealtime()
            val v26Route=if(proof.text.isNotBlank()){
                RouteParser.parsePlainTexts(listOf(proof.text))
            }else null
            val v26ParseDone=SystemClock.elapsedRealtime()
            rmV26DirectParseMs=v26ParseDone-v26ParseStart
            rmV26ProofTextChars=proof.text.length

            if(v26Route!=null && !isDuplicate(v26Route)){
                rmV26Fallback=false
                rmParseSourceV16="PROOF_DIRECT"
                rmParseItemsV16=1

                // Same cheap TEXT v6 baseline philosophy: only absorb the new
                // expanded message. Full baseline is rebuilt when search rearms.
                if(proof.text.isNotBlank()){
                    previousFastTexts=previousFastTexts+proof.text
                }

                currentStartedAt=SystemClock.elapsedRealtime()

                // Keep v25 timing visible. There is intentionally no reanalysis
                // or second collection in this successful v26 path.
                tdV25ProofConfirmedAt=rmV25ProofConfirmedAt
                tdV25ReanalyzeAt=0L
                tdV25CollectDoneAt=0L
                tdV25ParserStartAt=v26ParseStart
                tdV25ParserDoneAt=v26ParseDone
                tdV25RouteAt=currentStartedAt

                tdV26DirectUsed=true
                tdV26DirectParseMs=rmV26DirectParseMs
                tdV26ProofTextChars=rmV26ProofTextChars
                tdV26Fallback=false

                val v26Analyze=if(rmV26AnalyzeAt>0L) rmV26AnalyzeAt else rmV25ProofConfirmedAt
                val v26CollectDone=if(rmV26CollectDoneAt>0L) rmV26CollectDoneAt else v26Analyze
                val v26Event=if(tdCandidate>0L) tdCandidate else v26Analyze
                tdBegin(
                    v26Event,
                    v26Analyze,
                    v26CollectDone,
                    rmV26CollectMs,
                    rmV26DirectParseMs,
                    currentStartedAt,
                    if(rmV26NewItems>0) rmV26NewItems else 1
                )
                processing=true
                val tdSt=SystemClock.elapsedRealtime()
                Prefs.setStatus(
                    this,
                    "Texto: ${v26Route.neighborhood} -> ${v26Route.cage}. Enviando..."
                )
                if(tdOn){
                    tdStatusTexto+=SystemClock.elapsedRealtime()-tdSt
                    tdStatusTextoDone=SystemClock.elapsedRealtime()
                }
                sendRouteInCurrentChat(v26Route)
                return
            }

            rmV26Fallback=true
            handler.post{analyzeCurrentWindow()}
            return
        }
'''
if proof_old not in s:
    raise SystemExit('v26 proof-success block anchor not found')
s=s.replace(proof_old,proof_new,1)

# If direct parsing could not be used and v25 reanalysis later succeeds, snapshot
# that fact before tdBegin resets the temporary Read-more state.
fallback_snapshot_old='''                    tdV25RouteAt=currentStartedAt
                }
                tdBegin(
'''
fallback_snapshot_new='''                    tdV25RouteAt=currentStartedAt
                }
                if(rmV26Fallback){
                    tdV26DirectUsed=false
                    tdV26DirectParseMs=rmV26DirectParseMs
                    tdV26ProofTextChars=rmV26ProofTextChars
                    tdV26Fallback=true
                }
                tdBegin(
'''
if fallback_snapshot_old not in s:
    raise SystemExit('v26 fallback snapshot anchor not found')
s=s.replace(fallback_snapshot_old,fallback_snapshot_new,1)

# Reset only temporary v26 state with the existing v25 Read-more reset.
reset_anchor='''rmV25ProofConfirmedAt=0L; rmV25ReanalyzeAt=0L; rmV25CollectDoneAt=0L; rmV25ParserStartAt=0L; rmV25ParserDoneAt=0L'''
reset_insert=reset_anchor+'''; rmV26AnalyzeAt=0L; rmV26CollectDoneAt=0L; rmV26CollectMs=0L; rmV26NewItems=0; rmV26DirectParseMs=0L; rmV26ProofTextChars=0; rmV26Fallback=false'''
if reset_anchor not in s:
    raise SystemExit('v26 reset anchor not found')
s=s.replace(reset_anchor,reset_insert,1)

# One explicit A/B line. Never print the actual WhatsApp text; only its char count.
report_anchor='''                    appendLine("postProofV25=proof->reanalyze=${tdD(tdV25ProofConfirmedAt,tdV25ReanalyzeAt)} | reanalyze->collect=${tdD(tdV25ReanalyzeAt,tdV25CollectDoneAt)} | collect->parser=${tdD(tdV25CollectDoneAt,tdV25ParserStartAt)} | parser=${tdD(tdV25ParserStartAt,tdV25ParserDoneAt)} | parserDone->route=${tdD(tdV25ParserDoneAt,tdV25RouteAt)} | proof->route=${tdD(tdV25ProofConfirmedAt,tdV25RouteAt)}")
'''
report_insert=report_anchor+'''                    appendLine("directProofV26=used=$tdV26DirectUsed | proofTextChars=$tdV26ProofTextChars | directParse=${tdV26DirectParseMs}ms | fallbackReanalyze=$tdV26Fallback")
'''
if report_anchor not in s:
    raise SystemExit('v26 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'val text:String',
    'bestText=joined',
    'RouteParser.parsePlainTexts(listOf(proof.text))',
    'rmParseSourceV16="PROOF_DIRECT"',
    'directProofV26=used=$tdV26DirectUsed',
    'fallbackReanalyze=$tdV26Fallback',
    'handler.post{analyzeCurrentWindow()}',
    'proofV24=skipImmediate=true | firstProofDelay=6ms | strictProof=preserved',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('PROOF DIRECT PARSE v26 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('PROOF DIRECT PARSE v26 applied: strict-proof winning text -> direct parser; v25 reanalysis retained as fallback; TEXT_DIRECT_V5 and IMAGE v9 preserved')
