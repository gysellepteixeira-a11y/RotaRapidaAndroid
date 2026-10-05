from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

required=[
    '===== DIAGNOSTICO IMAGEM v11 | SAME-PASS CAGE RECOVERY v40 + COMBINED OCR v39 + V37 FALLBACK =====',
    'samePassV40=recovered=$idV40Recovery',
    'idV39Reason=if(idV40Recovery) "SUCCESS_V40_RECOVERY" else "SUCCESS"',
]
for m in required:
    if m not in s:
        raise SystemExit('v41 wrong base: '+m)

state_anchor='    private var idV40Recovery=false; private var idV40Candidates=0; private var idV40Joined=""\n'
state_new=state_anchor+'    private var idV41Recovery=false; private var idV41Raw=""; private var idV41Normalized=""\n'
if state_anchor not in s:
    raise SystemExit('v41 state anchor missing')
s=s.replace(state_anchor,state_new,1)

reset_anchor='        idV40Recovery=false; idV40Candidates=0; idV40Joined=""\n'
reset_new=reset_anchor+'        idV41Recovery=false; idV41Raw=""; idV41Normalized=""\n'
if reset_anchor not in s:
    raise SystemExit('v41 reset anchor missing')
s=s.replace(reset_anchor,reset_new,1)

old='''                    idV40Candidates=rowPieces.size
                    if(rowPieces.isNotEmpty()){
                        val rawJoined=rowPieces.joinToString("") { it.text.trim() }
                        val spacedJoined=rowPieces.joinToString(" ") { it.text.trim() }
                        val compact=rawJoined.replace(" ","")
                        idV40Joined=(spacedJoined+" | "+compact).take(120)

                        cage = RouteParser.extractCage(rawJoined)
                            ?: RouteParser.extractCage(spacedJoined)
                            ?: RouteParser.extractCage(compact)

                        // One extra conservative reconstruction: OCR sometimes reads
                        // the letter and digits as separate punctuation-heavy pieces.
                        if(cage==null){
                            val cleaned=compact.uppercase(java.util.Locale.ROOT)
                                .replace(Regex("[^A-Z0-9-]"),"")
                            cage=RouteParser.extractCage(cleaned)
                        }
                        if(cage!=null) idV40Recovery=true
                    }
'''
new='''                    // v41: ML Kit may expose the same visual cell both as a line
                    // and as an element. De-duplicate equal text before reconstruction.
                    val uniqueTexts=rowPieces
                        .map { it.text.trim() }
                        .filter { it.isNotBlank() }
                        .distinct()
                    idV40Candidates=uniqueTexts.size

                    if(uniqueTexts.isNotEmpty()){
                        fun normalizeCageV41(raw:String):String {
                            return raw.uppercase(java.util.Locale.ROOT)
                                .replace(Regex("[\\s\\-‐‑‒–—−_]+"),"")
                                .replace(Regex("[^A-Z0-9]"),"")
                        }

                        // First try each de-duplicated token by itself. This handles
                        // the observed J-16 case without concatenating duplicates.
                        for(raw in uniqueTexts){
                            val normalized=normalizeCageV41(raw)
                            if(normalized.isBlank()) continue
                            val parsed=RouteParser.extractCage(normalized) ?: continue
                            cage=parsed
                            idV41Recovery=true
                            idV41Raw=raw.take(60)
                            idV41Normalized=normalized.take(60)
                            break
                        }

                        // If the OCR genuinely split the cell (for example J + 16),
                        // concatenate only distinct left-to-right fragments.
                        if(cage==null){
                            val spacedJoined=uniqueTexts.joinToString(" ")
                            val compactJoined=uniqueTexts.joinToString("")
                            val normalized=normalizeCageV41(compactJoined)
                            idV40Joined=(spacedJoined+" | "+compactJoined).take(120)
                            if(normalized.isNotBlank()){
                                cage=RouteParser.extractCage(normalized)
                                if(cage!=null){
                                    idV41Recovery=true
                                    idV41Raw=compactJoined.take(60)
                                    idV41Normalized=normalized.take(60)
                                }
                            }
                        } else {
                            idV40Joined=uniqueTexts.joinToString(" ").take(120)
                        }

                        if(cage!=null) idV40Recovery=true
                    }
'''
if old not in s:
    raise SystemExit('v41 v40 recovery block missing')
s=s.replace(old,new,1)

s=s.replace(
    'idV39Reason=if(idV40Recovery) "SUCCESS_V40_RECOVERY" else "SUCCESS"',
    'idV39Reason=if(idV41Recovery) "SUCCESS_V41_NORMALIZED" else if(idV40Recovery) "SUCCESS_V40_RECOVERY" else "SUCCESS"',
    1
)

old_header='===== DIAGNOSTICO IMAGEM v11 | SAME-PASS CAGE RECOVERY v40 + COMBINED OCR v39 + V37 FALLBACK ====='
new_header='===== DIAGNOSTICO IMAGEM v12 | CAGE NORMALIZE v41 + SAME-PASS v40 + COMBINED OCR v39 + V37 FALLBACK ====='
s=s.replace(old_header,new_header,1)

report_anchor='''            appendLine("samePassV40=recovered=$idV40Recovery | rowCandidates=$idV40Candidates | joined=[$idV40Joined]")
'''
report_new=report_anchor+'''            appendLine("cageNormalizeV41=recovered=$idV41Recovery | raw=[$idV41Raw] | normalized=[$idV41Normalized]")
'''
if report_anchor not in s:
    raise SystemExit('v41 report anchor missing')
s=s.replace(report_anchor,report_new,1)

for m in [
    new_header,
    'SUCCESS_V41_NORMALIZED',
    'cageNormalizeV41=recovered=$idV41Recovery',
    'readDenseBairroFirst(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)',
    '===== DIAGNOSTICO TEXTO v37 |',
]:
    if m not in s:
        raise SystemExit('v41 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('IMAGE v41 applied: normalize J-16/J 16/J–16 -> J16, deduplicate OCR line+element, v37 fallback preserved')
