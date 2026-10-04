from pathlib import Path

P=Path('app/src/main/java/com/gy/rotarapida/RouteParser.kt')
S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
p=P.read_text(encoding='utf-8')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v33 | TEXT v6 + LOCAL ANCHOR PROOF + SKIP BAND + TRUNC BEFORE ROOT + LAZY ADMIN + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v34 | TEXT v6 + PARSER SPLIT DIAG + LOCAL ANCHOR PROOF + SKIP BAND + TRUNC BEFORE ROOT + LAZY ADMIN + READ MORE v21 + DIRECT SEND ====='

for m in [
    old_header,
    'RouteParser.parsePlainTexts(listOf(proof.text))',
    'directProofV26=used=$tdV26DirectUsed',
    'localProofV33=calls=$tdV33LocalCalls',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
]:
    if m not in s:
        raise SystemExit('PARSER SPLIT DIAG v34 wrong service base: '+m)

for m in [
    'object RouteParser {',
    'private fun priorityFor(text: String): Pair<Int, String>? {',
    'fun extractCage(value: String): String? {',
    'fun parsePlainTexts(texts: List<String>): RouteResult? {',
]:
    if m not in p:
        raise SystemExit('PARSER SPLIT DIAG v34 wrong parser base: '+m)

# Diagnostic only. Do not rewrite normalize/priority/extractCage internals: simply
# measure the existing calls exactly as they are in the current parser.
obj_anchor='object RouteParser {\n\n'
obj_insert='''object RouteParser {\n\n    data class PlainParseDiagV34(\n        val totalNs:Long=0L,\n        val linePrepNs:Long=0L,\n        val priorityNs:Long=0L,\n        val cageNs:Long=0L,\n        val winnerNs:Long=0L,\n        val rawTexts:Int=0,\n        val lines:Int=0,\n        val priorityCalls:Int=0,\n        val cageCalls:Int=0,\n        val candidates:Int=0\n    )\n\n    @Volatile var lastPlainParseDiagV34=PlainParseDiagV34()\n        private set\n\n'''
if obj_anchor not in p:
    raise SystemExit('v34 object anchor not found')
p=p.replace(obj_anchor,obj_insert,1)

parse_start=p.find('    fun parsePlainTexts(texts: List<String>): RouteResult? {')
parse_end=p.find('\n    /**\n     * Fallback visual:',parse_start)
if parse_start<0 or parse_end<0:
    raise SystemExit('v34 parsePlainTexts region not found')

parse_new=r'''    fun parsePlainTexts(texts: List<String>): RouteResult? {
        val v34totalStart=System.nanoTime()
        var v34linePrepNs=0L
        var v34priorityNs=0L
        var v34cageNs=0L
        var v34winnerNs=0L
        var v34lines=0
        var v34priorityCalls=0
        var v34cageCalls=0
        val candidates = mutableListOf<Triple<Int, String, String>>()

        for (raw in texts) {
            val v34lineStart=System.nanoTime()
            val lines = raw
                .replace("\r", "\n")
                .split("\n")
                .map { it.trim() }
                .filter { it.isNotBlank() }
            v34linePrepNs+=System.nanoTime()-v34lineStart
            v34lines+=lines.size

            for (line in lines) {
                val v34priorityStart=System.nanoTime()
                val priority = priorityFor(line)
                v34priorityNs+=System.nanoTime()-v34priorityStart
                v34priorityCalls++
                if(priority==null)continue

                val v34cageStart=System.nanoTime()
                val cage = extractCage(line)
                v34cageNs+=System.nanoTime()-v34cageStart
                v34cageCalls++
                if(cage==null)continue
                candidates += Triple(priority.first, priority.second, cage)
            }
        }

        val v34winnerStart=System.nanoTime()
        val result=if(candidates.isEmpty()){
            null
        }else{
            val winner=candidates.minByOrNull { it.first }
            if(winner==null) null else RouteResult(winner.second,winner.third,winner.first)
        }
        v34winnerNs=System.nanoTime()-v34winnerStart
        val v34totalNs=System.nanoTime()-v34totalStart
        lastPlainParseDiagV34=PlainParseDiagV34(
            totalNs=v34totalNs,
            linePrepNs=v34linePrepNs,
            priorityNs=v34priorityNs,
            cageNs=v34cageNs,
            winnerNs=v34winnerNs,
            rawTexts=texts.size,
            lines=v34lines,
            priorityCalls=v34priorityCalls,
            cageCalls=v34cageCalls,
            candidates=candidates.size
        )
        return result
    }
'''
p=p[:parse_start]+parse_new+p[parse_end:]

state_anchor='    private var tdV33LocalTruncated=true\n'
state_insert=state_anchor+'    private var tdV34ParserDiag=""\n'
if state_anchor not in s:
    raise SystemExit('v34 service state anchor not found')
s=s.replace(state_anchor,state_insert,1)

snap_anchor='''            val v26ParseDone=SystemClock.elapsedRealtime()\n            rmV26DirectParseMs=v26ParseDone-v26ParseStart\n            rmV26ProofTextChars=proof.text.length\n'''
snap_insert='''            val v26ParseDone=SystemClock.elapsedRealtime()\n            rmV26DirectParseMs=v26ParseDone-v26ParseStart\n            rmV26ProofTextChars=proof.text.length\n            val v34pd=RouteParser.lastPlainParseDiagV34\n            val v34sum=v34pd.linePrepNs+v34pd.priorityNs+v34pd.cageNs+v34pd.winnerNs\n            val v34other=(v34pd.totalNs-v34sum).coerceAtLeast(0L)\n            fun v34us(ns:Long)=ns/1000L\n            tdV34ParserDiag="total=${v34us(v34pd.totalNs)}us | lines=${v34pd.lines} | linePrep=${v34us(v34pd.linePrepNs)}us | priority=${v34us(v34pd.priorityNs)}us | cage=${v34us(v34pd.cageNs)}us | winner=${v34us(v34pd.winnerNs)}us | other=${v34us(v34other)}us | priorityCalls=${v34pd.priorityCalls} | cageCalls=${v34pd.cageCalls} | candidates=${v34pd.candidates}"\n'''
if snap_anchor not in s:
    raise SystemExit('v34 direct parse snapshot anchor not found')
s=s.replace(snap_anchor,snap_insert,1)

report_anchor='''                    appendLine("directProofV26=used=$tdV26DirectUsed | proofTextChars=$tdV26ProofTextChars | directParse=${tdV26DirectParseMs}ms | fallbackReanalyze=$tdV26Fallback")\n'''
report_insert=report_anchor+'''                    appendLine("parserV34=$tdV34ParserDiag")\n'''
if report_anchor not in s:
    raise SystemExit('v34 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'data class PlainParseDiagV34(',
    'lastPlainParseDiagV34=PlainParseDiagV34(',
    'parserV34=$tdV34ParserDiag',
    'priority=${v34us(v34pd.priorityNs)}us',
    'cage=${v34us(v34pd.cageNs)}us',
    'localProofV33=calls=$tdV33LocalCalls',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in (p+s):
        raise SystemExit('PARSER SPLIT DIAG v34 verify failed: '+m)

P.write_text(p,encoding='utf-8')
S.write_text(s,encoding='utf-8')
print('PARSER SPLIT DIAG v34 applied: diagnostic-only line prep + existing priorityFor + existing extractCage + winner timing; v33 behavior preserved')
