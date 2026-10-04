from pathlib import Path

P=Path('app/src/main/java/com/gy/rotarapida/RouteParser.kt')
S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
p=P.read_text(encoding='utf-8')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v33 | TEXT v6 + LOCAL ANCHOR PROOF + SKIP BAND + TRUNC BEFORE ROOT + LAZY ADMIN + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v34 | TEXT v6 + PARSER SPLIT DIAG + LOCAL ANCHOR PROOF + SKIP BAND + TRUNC BEFORE ROOT + LAZY ADMIN + READ MORE v21 + DIRECT SEND ====='

required_service=[
    old_header,
    'RouteParser.parsePlainTexts(listOf(proof.text))',
    'directProofV26=used=$tdV26DirectUsed',
    'localProofV33=calls=$tdV33LocalCalls',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
]
for m in required_service:
    if m not in s:
        raise SystemExit('PARSER SPLIT DIAG v34 wrong service base: '+m)

required_parser=[
    'object RouteParser {',
    'fun normalize(value: String): String {',
    'fun extractCage(value: String): String? {',
    'private fun priorityFor(text: String): Pair<Int, String>? {',
    'fun parsePlainTexts(texts: List<String>): RouteResult? {',
]
for m in required_parser:
    if m not in p:
        raise SystemExit('PARSER SPLIT DIAG v34 wrong parser base: '+m)

# Pure diagnostics only: nanoTime probes and counters. Parsing order/results stay identical.
obj_anchor='''object RouteParser {\n\n'''
obj_insert='''object RouteParser {\n\n    data class PlainParseDiagV34(\n        val totalNs:Long=0L,\n        val linePrepNs:Long=0L,\n        val normalizeNs:Long=0L,\n        val priorityRulesNs:Long=0L,\n        val cageUpperNs:Long=0L,\n        val cageRegexNs:Long=0L,\n        val winnerNs:Long=0L,\n        val rawTexts:Int=0,\n        val lines:Int=0,\n        val priorityCalls:Int=0,\n        val cageCalls:Int=0,\n        val candidates:Int=0\n    )\n\n    @Volatile var lastPlainParseDiagV34=PlainParseDiagV34()\n        private set\n\n    private var diagPlainActiveV34=false\n    private var diagNormalizeNsV34=0L\n    private var diagPriorityRulesNsV34=0L\n    private var diagCageUpperNsV34=0L\n    private var diagCageRegexNsV34=0L\n    private var diagPriorityCallsV34=0\n    private var diagCageCallsV34=0\n\n'''
if obj_anchor not in p:
    raise SystemExit('v34 object anchor not found')
p=p.replace(obj_anchor,obj_insert,1)

normalize_old='''    fun normalize(value: String): String {\n        val decomposed = Normalizer.normalize(\n            value.lowercase(Locale.ROOT).trim(),\n            Normalizer.Form.NFD\n        )\n\n        return decomposed\n            .replace(Regex("""\\p{Mn}+"""), "")\n            .replace(Regex("""[^a-z0-9\\s]"""), " ")\n            .replace(Regex("""\\s+"""), " ")\n            .trim()\n    }\n'''
normalize_new='''    fun normalize(value: String): String {\n        val v34t=if(diagPlainActiveV34) System.nanoTime() else 0L\n        val decomposed = Normalizer.normalize(\n            value.lowercase(Locale.ROOT).trim(),\n            Normalizer.Form.NFD\n        )\n\n        val out=decomposed\n            .replace(Regex("""\\p{Mn}+"""), "")\n            .replace(Regex("""[^a-z0-9\\s]"""), " ")\n            .replace(Regex("""\\s+"""), " ")\n            .trim()\n        if(diagPlainActiveV34)diagNormalizeNsV34+=System.nanoTime()-v34t\n        return out\n    }\n'''
if normalize_old not in p:
    raise SystemExit('v34 normalize block not found')
p=p.replace(normalize_old,normalize_new,1)

cage_old='''    fun extractCage(value: String): String? {\n        val upper = value.uppercase(Locale.ROOT).trim()\n        val match = cageRegex.find(upper) ?: cageFallbackRegex.find(upper) ?: return null\n\n        var letter = match.groupValues[1]\n        if (letter == "1") letter = "I"\n\n        return letter.lowercase(Locale.ROOT) + match.groupValues[2]\n    }\n'''
cage_new='''    fun extractCage(value: String): String? {\n        if(diagPlainActiveV34)diagCageCallsV34++\n        val v34upperStart=if(diagPlainActiveV34) System.nanoTime() else 0L\n        val upper = value.uppercase(Locale.ROOT).trim()\n        if(diagPlainActiveV34)diagCageUpperNsV34+=System.nanoTime()-v34upperStart\n        val v34regexStart=if(diagPlainActiveV34) System.nanoTime() else 0L\n        val match = cageRegex.find(upper) ?: cageFallbackRegex.find(upper)\n        if(diagPlainActiveV34)diagCageRegexNsV34+=System.nanoTime()-v34regexStart\n        if(match==null)return null\n\n        var letter = match.groupValues[1]\n        if (letter == "1") letter = "I"\n\n        return letter.lowercase(Locale.ROOT) + match.groupValues[2]\n    }\n'''
if cage_old not in p:
    raise SystemExit('v34 cage block not found')
p=p.replace(cage_old,cage_new,1)

priority_old='''    private fun priorityFor(text: String): Pair<Int, String>? {\n        val normalized = normalize(text)\n        if (normalized.isBlank()) return null\n\n        priorities.forEachIndexed { index, rule ->\n            if (rule.requiredTokens.all { normalized.contains(it) }) {\n                return index to rule.name\n            }\n        }\n\n        return null\n    }\n'''
priority_new='''    private fun priorityFor(text: String): Pair<Int, String>? {\n        if(diagPlainActiveV34)diagPriorityCallsV34++\n        val normalized = normalize(text)\n        if (normalized.isBlank()) return null\n\n        val v34rulesStart=if(diagPlainActiveV34) System.nanoTime() else 0L\n        for ((index, rule) in priorities.withIndex()) {\n            if (rule.requiredTokens.all { normalized.contains(it) }) {\n                if(diagPlainActiveV34)diagPriorityRulesNsV34+=System.nanoTime()-v34rulesStart\n                return index to rule.name\n            }\n        }\n        if(diagPlainActiveV34)diagPriorityRulesNsV34+=System.nanoTime()-v34rulesStart\n        return null\n    }\n'''
if priority_old not in p:
    raise SystemExit('v34 priority block not found')
p=p.replace(priority_old,priority_new,1)

parse_start=p.find('    fun parsePlainTexts(texts: List<String>): RouteResult? {')
parse_end=p.find('\n    /**\n     * Fallback visual:',parse_start)
if parse_start<0 or parse_end<0:
    raise SystemExit('v34 parsePlainTexts region not found')
parse_new=r'''    fun parsePlainTexts(texts: List<String>): RouteResult? {
        val v34totalStart=System.nanoTime()
        diagPlainActiveV34=true
        diagNormalizeNsV34=0L
        diagPriorityRulesNsV34=0L
        diagCageUpperNsV34=0L
        diagCageRegexNsV34=0L
        diagPriorityCallsV34=0
        diagCageCallsV34=0
        var v34linePrepNs=0L
        var v34winnerNs=0L
        var v34lines=0
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
                val priority = priorityFor(line) ?: continue
                val cage = extractCage(line) ?: continue
                candidates += Triple(priority.first, priority.second, cage)
            }
        }

        val v34winnerStart=System.nanoTime()
        val result=if(candidates.isEmpty()){
            null
        }else{
            val winner = candidates.minByOrNull { it.first }
            if(winner==null) null else RouteResult(winner.second, winner.third, winner.first)
        }
        v34winnerNs=System.nanoTime()-v34winnerStart
        val v34totalNs=System.nanoTime()-v34totalStart
        lastPlainParseDiagV34=PlainParseDiagV34(
            totalNs=v34totalNs,
            linePrepNs=v34linePrepNs,
            normalizeNs=diagNormalizeNsV34,
            priorityRulesNs=diagPriorityRulesNsV34,
            cageUpperNs=diagCageUpperNsV34,
            cageRegexNs=diagCageRegexNsV34,
            winnerNs=v34winnerNs,
            rawTexts=texts.size,
            lines=v34lines,
            priorityCalls=diagPriorityCallsV34,
            cageCalls=diagCageCallsV34,
            candidates=candidates.size
        )
        diagPlainActiveV34=false
        return result
    }
'''
p=p[:parse_start]+parse_new+p[parse_end:]

# Snapshot parser internals immediately after the v26 direct parse, before any other parser call.
state_anchor='    private var tdV33LocalTruncated=true\n'
state_insert=state_anchor+'    private var tdV34ParserDiag=""\n'
if state_anchor not in s:
    raise SystemExit('v34 service state anchor not found')
s=s.replace(state_anchor,state_insert,1)

snap_anchor='''            val v26ParseDone=SystemClock.elapsedRealtime()\n            rmV26DirectParseMs=v26ParseDone-v26ParseStart\n            rmV26ProofTextChars=proof.text.length\n'''
snap_insert='''            val v26ParseDone=SystemClock.elapsedRealtime()\n            rmV26DirectParseMs=v26ParseDone-v26ParseStart\n            rmV26ProofTextChars=proof.text.length\n            val v34pd=RouteParser.lastPlainParseDiagV34\n            val v34sum=v34pd.linePrepNs+v34pd.normalizeNs+v34pd.priorityRulesNs+v34pd.cageUpperNs+v34pd.cageRegexNs+v34pd.winnerNs\n            val v34other=(v34pd.totalNs-v34sum).coerceAtLeast(0L)\n            fun v34us(ns:Long)=ns/1000L\n            tdV34ParserDiag="total=${v34us(v34pd.totalNs)}us | lines=${v34pd.lines} | linePrep=${v34us(v34pd.linePrepNs)}us | normalize=${v34us(v34pd.normalizeNs)}us | priorityRules=${v34us(v34pd.priorityRulesNs)}us | cageUpper=${v34us(v34pd.cageUpperNs)}us | cageRegex=${v34us(v34pd.cageRegexNs)}us | winner=${v34us(v34pd.winnerNs)}us | other=${v34us(v34other)}us | priorityCalls=${v34pd.priorityCalls} | cageCalls=${v34pd.cageCalls} | candidates=${v34pd.candidates}"\n'''
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
    'diagNormalizeNsV34',
    'diagPriorityRulesNsV34',
    'diagCageRegexNsV34',
    'parserV34=$tdV34ParserDiag',
    'localProofV33=calls=$tdV33LocalCalls',
    'strictCriteria=same',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in (p+s):
        raise SystemExit('PARSER SPLIT DIAG v34 verify failed: '+m)

P.write_text(p,encoding='utf-8')
S.write_text(s,encoding='utf-8')
print('PARSER SPLIT DIAG v34 applied: diagnostic-only line prep/normalize/priority/cage/winner timing; v33 proof and parser behavior preserved')
