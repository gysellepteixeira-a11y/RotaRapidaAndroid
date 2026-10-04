from pathlib import Path

P=Path('app/src/main/java/com/gy/rotarapida/RouteParser.kt')
S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
p=P.read_text(encoding='utf-8')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v34 | TEXT v6 + PARSER SPLIT DIAG + LOCAL ANCHOR PROOF + SKIP BAND + TRUNC BEFORE ROOT + LAZY ADMIN + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v36 | TEXT v6 + ASCII NORMALIZE FAST + PARSER SPLIT DIAG + LOCAL ANCHOR PROOF + SKIP BAND + TRUNC BEFORE ROOT + LAZY ADMIN + READ MORE v21 + DIRECT SEND ====='

for m in [
    old_header,
    'data class PlainParseDiagV34(',
    'private fun priorityFor(text: String): Pair<Int, String>? {',
    'fun parsePlainTexts(texts: List<String>): RouteResult? {',
    'parserV34=$tdV34ParserDiag',
    'localProofV33=calls=$tdV33LocalCalls',
]:
    if m not in (p+s):
        raise SystemExit('ASCII NORMALIZE FAST v36 wrong base: '+m)

# Keep the original normalize() and priorityFor() untouched for every other parser path.
# Only parsePlainTexts gets an ASCII-equivalent fast normalizer. Any non-ASCII input
# falls back to the original normalize(), preserving semantics for accents/Unicode.
priority_anchor='''    private fun priorityFor(text: String): Pair<Int, String>? {\n        val normalized = normalize(text)\n        if (normalized.isBlank()) return null\n\n        priorities.forEachIndexed { index, rule ->\n            if (rule.requiredTokens.all { normalized.contains(it) }) {\n                return index to rule.name\n            }\n        }\n\n        return null\n    }\n'''
if priority_anchor not in p:
    raise SystemExit('v36 priorityFor anchor not found')
helper_insert=priority_anchor+r'''

    private fun normalizePlainLineV36(value: String): Pair<String, Boolean> {
        var ascii=true
        for(ch in value){
            if(ch.code>127){
                ascii=false
                break
            }
        }
        if(!ascii)return normalize(value) to false

        val out=StringBuilder(value.length)
        var separatorPending=false
        for(rawCh in value){
            val ch=if(rawCh in 'A'..'Z') (rawCh.code+32).toChar() else rawCh
            val alnum=(ch in 'a'..'z') || (ch in '0'..'9')
            if(alnum){
                if(separatorPending && out.isNotEmpty())out.append(' ')
                out.append(ch)
                separatorPending=false
            }else if(out.isNotEmpty()){
                // For ASCII input, both whitespace and punctuation become/collapse to
                // one separator under the original regex pipeline.
                separatorPending=true
            }
        }
        return out.toString() to true
    }

    private fun priorityForNormalizedV36(normalized: String): Pair<Int, String>? {
        if(normalized.isBlank())return null
        priorities.forEachIndexed { index, rule ->
            if(rule.requiredTokens.all { normalized.contains(it) }){
                return index to rule.name
            }
        }
        return null
    }

    data class PlainParseDiagV36(
        val normalizeNs:Long=0L,
        val priorityMatchNs:Long=0L,
        val asciiFastCalls:Int=0,
        val unicodeFallbackCalls:Int=0
    )

    @Volatile var lastPlainParseDiagV36=PlainParseDiagV36()
        private set
'''
p=p.replace(priority_anchor,helper_insert,1)

parse_start=p.find('    fun parsePlainTexts(texts: List<String>): RouteResult? {')
parse_end=p.find('\n    /**\n     * Fallback visual:',parse_start)
if parse_start<0 or parse_end<0:
    raise SystemExit('v36 parsePlainTexts region not found')

parse_new=r'''    fun parsePlainTexts(texts: List<String>): RouteResult? {
        val v34totalStart=System.nanoTime()
        var v34linePrepNs=0L
        var v34priorityNs=0L
        var v34cageNs=0L
        var v34winnerNs=0L
        var v34lines=0
        var v34priorityCalls=0
        var v34cageCalls=0
        var v36normalizeNs=0L
        var v36priorityMatchNs=0L
        var v36asciiFastCalls=0
        var v36unicodeFallbackCalls=0
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
                val v36normalizeStart=System.nanoTime()
                val normalizedResult=normalizePlainLineV36(line)
                v36normalizeNs+=System.nanoTime()-v36normalizeStart
                if(normalizedResult.second)v36asciiFastCalls++ else v36unicodeFallbackCalls++

                val v36priorityStart=System.nanoTime()
                val priority=priorityForNormalizedV36(normalizedResult.first)
                v36priorityMatchNs+=System.nanoTime()-v36priorityStart
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

        v34priorityNs=v36normalizeNs+v36priorityMatchNs
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
        lastPlainParseDiagV36=PlainParseDiagV36(
            normalizeNs=v36normalizeNs,
            priorityMatchNs=v36priorityMatchNs,
            asciiFastCalls=v36asciiFastCalls,
            unicodeFallbackCalls=v36unicodeFallbackCalls
        )
        return result
    }
'''
p=p[:parse_start]+parse_new+p[parse_end:]

state_anchor='    private var tdV34ParserDiag=""\n'
state_insert=state_anchor+'    private var tdV36NormalizeDiag=""\n'
if state_anchor not in s:
    raise SystemExit('v36 service state anchor not found')
s=s.replace(state_anchor,state_insert,1)

snap_anchor='''            tdV34ParserDiag="total=${v34us(v34pd.totalNs)}us | lines=${v34pd.lines} | linePrep=${v34us(v34pd.linePrepNs)}us | priority=${v34us(v34pd.priorityNs)}us | cage=${v34us(v34pd.cageNs)}us | winner=${v34us(v34pd.winnerNs)}us | other=${v34us(v34other)}us | priorityCalls=${v34pd.priorityCalls} | cageCalls=${v34pd.cageCalls} | candidates=${v34pd.candidates}"\n'''
snap_insert=snap_anchor+'''            val v36pd=RouteParser.lastPlainParseDiagV36\n            tdV36NormalizeDiag="normalize=${v34us(v36pd.normalizeNs)}us | match=${v34us(v36pd.priorityMatchNs)}us | asciiFastCalls=${v36pd.asciiFastCalls} | unicodeFallbackCalls=${v36pd.unicodeFallbackCalls} | originalFallback=preserved"\n'''
if snap_anchor not in s:
    raise SystemExit('v36 v34 snapshot anchor not found')
s=s.replace(snap_anchor,snap_insert,1)

report_anchor='''                    appendLine("parserV34=$tdV34ParserDiag")\n'''
report_insert=report_anchor+'''                    appendLine("normalizeV36=$tdV36NormalizeDiag")\n'''
if report_anchor not in s:
    raise SystemExit('v36 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'normalizePlainLineV36(',
    'priorityForNormalizedV36(',
    'PlainParseDiagV36(',
    'normalizeV36=$tdV36NormalizeDiag',
    'originalFallback=preserved',
    'parserV34=$tdV34ParserDiag',
    'localProofV33=calls=$tdV33LocalCalls',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in (p+s):
        raise SystemExit('ASCII NORMALIZE FAST v36 verify failed: '+m)

P.write_text(p,encoding='utf-8')
S.write_text(s,encoding='utf-8')
print('ASCII NORMALIZE FAST v36 applied: ASCII-equivalent one-pass normalize in parsePlainTexts; non-ASCII uses original normalize; priority rules/order unchanged; v34/v33 diagnostics preserved')
