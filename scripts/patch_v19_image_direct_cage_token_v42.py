from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

required=[
    '===== DIAGNOSTICO IMAGEM v12 | CAGE NORMALIZE v41 + SAME-PASS v40 + COMBINED OCR v39 + V37 FALLBACK =====',
    'cageNormalizeV41=recovered=$idV41Recovery',
    'fun normalizeCageV41(raw:String):String',
]
for m in required:
    if m not in s:
        raise SystemExit('v42 wrong base: '+m)

state_anchor='    private var idV41Recovery=false; private var idV41Raw=""; private var idV41Normalized=""\n'
state_new=state_anchor+'    private var idV42Recovery=false; private var idV42Raw=""; private var idV42Compact=""\n'
if state_anchor not in s:
    raise SystemExit('v42 state anchor missing')
s=s.replace(state_anchor,state_new,1)

reset_anchor='        idV41Recovery=false; idV41Raw=""; idV41Normalized=""\n'
reset_new=reset_anchor+'        idV42Recovery=false; idV42Raw=""; idV42Compact=""\n'
if reset_anchor not in s:
    raise SystemExit('v42 reset anchor missing')
s=s.replace(reset_anchor,reset_new,1)

func_anchor='''                        fun normalizeCageV41(raw:String):String {
                            return raw.uppercase(java.util.Locale.ROOT)
                                .replace(Regex("""[\\s\\-‐‑‒–—−_]+"""),"")
                                .replace(Regex("[^A-Z0-9]"),"")
                        }
'''
func_new=func_anchor+'''                        // v42: this runs only inside the cage column on the already
                        // selected neighborhood row. Accept an exact compact cage token
                        // directly instead of depending on the generic route parser.
                        fun directCageV42(compact:String):String? {
                            if(compact.length!=3) return null
                            val first=compact[0]
                            if(!(first in 'A'..'Z' || first=='1')) return null
                            if(!compact[1].isDigit() || !compact[2].isDigit()) return null
                            val letter=if(first=='1') 'I' else first
                            return letter.lowercaseChar().toString()+compact.substring(1,3)
                        }
'''
if func_anchor not in s:
    raise SystemExit('v42 normalize function anchor missing')
s=s.replace(func_anchor,func_new,1)

old='''                            val parsed=RouteParser.extractCage(normalized) ?: continue
                            cage=parsed
                            idV41Recovery=true
                            idV41Raw=raw.take(60)
                            idV41Normalized=normalized.take(60)
                            break
'''
new='''                            val direct=directCageV42(normalized)
                            val parsed=direct ?: RouteParser.extractCage(normalized) ?: continue
                            cage=parsed
                            if(direct!=null){
                                idV42Recovery=true
                                idV42Raw=raw.take(60)
                                idV42Compact=normalized.take(60)
                            } else {
                                idV41Recovery=true
                                idV41Raw=raw.take(60)
                                idV41Normalized=normalized.take(60)
                            }
                            break
'''
if old not in s:
    raise SystemExit('v42 token parse block missing')
s=s.replace(old,new,1)

old2='''                                cage=RouteParser.extractCage(normalized)
                                if(cage!=null){
                                    idV41Recovery=true
                                    idV41Raw=compactJoined.take(60)
                                    idV41Normalized=normalized.take(60)
                                }
'''
new2='''                                val direct=directCageV42(normalized)
                                cage=direct ?: RouteParser.extractCage(normalized)
                                if(cage!=null){
                                    if(direct!=null){
                                        idV42Recovery=true
                                        idV42Raw=compactJoined.take(60)
                                        idV42Compact=normalized.take(60)
                                    } else {
                                        idV41Recovery=true
                                        idV41Raw=compactJoined.take(60)
                                        idV41Normalized=normalized.take(60)
                                    }
                                }
'''
if old2 not in s:
    raise SystemExit('v42 joined parse block missing')
s=s.replace(old2,new2,1)

s=s.replace(
    'idV39Reason=if(idV41Recovery) "SUCCESS_V41_NORMALIZED" else if(idV40Recovery) "SUCCESS_V40_RECOVERY" else "SUCCESS"',
    'idV39Reason=if(idV42Recovery) "SUCCESS_V42_DIRECT" else if(idV41Recovery) "SUCCESS_V41_NORMALIZED" else if(idV40Recovery) "SUCCESS_V40_RECOVERY" else "SUCCESS"',
    1
)

old_header='===== DIAGNOSTICO IMAGEM v12 | CAGE NORMALIZE v41 + SAME-PASS v40 + COMBINED OCR v39 + V37 FALLBACK ====='
new_header='===== DIAGNOSTICO IMAGEM v13 | DIRECT CAGE TOKEN v42 + CAGE NORMALIZE v41 + COMBINED OCR v39 + V37 FALLBACK ====='
s=s.replace(old_header,new_header,1)

report_anchor='''            appendLine("cageNormalizeV41=recovered=$idV41Recovery | raw=[$idV41Raw] | normalized=[$idV41Normalized]")
'''
report_new=report_anchor+'''            appendLine("directCageV42=recovered=$idV42Recovery | raw=[$idV42Raw] | compact=[$idV42Compact]")
'''
if report_anchor not in s:
    raise SystemExit('v42 report anchor missing')
s=s.replace(report_anchor,report_new,1)

for m in [
    new_header,
    'SUCCESS_V42_DIRECT',
    'directCageV42=recovered=$idV42Recovery',
    'fun directCageV42(compact:String):String?',
    '===== DIAGNOSTICO TEXTO v37 |',
]:
    if m not in s:
        raise SystemExit('v42 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('IMAGE v42 applied: direct exact cage token parse on selected row; v41/v37 fallbacks preserved')
