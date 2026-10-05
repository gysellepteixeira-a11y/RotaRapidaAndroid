from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

required=[
    '===== DIAGNOSTICO IMAGEM v10 | COMBINED OCR v39 + V37 FALLBACK + DIRECT SEND + BULK PIXELS =====',
    'private fun readDenseCombinedV39(',
    'private data class CombinedV39Piece(',
    'idV39Reason="SUCCESS"',
    'combinedV39=used=$idV39Used',
]
for m in required:
    if m not in s:
        raise SystemExit('v40 wrong base: '+m)

# Diagnostics for the recovery itself.
state_anchor='    private var idV39Pieces=0; private var idV39Scale=1f; private var idV39Reason="NONE"\n'
state_new=state_anchor+'    private var idV40Recovery=false; private var idV40Candidates=0; private var idV40Joined=""\n'
s=s.replace(state_anchor,state_new,1)

reset_anchor='        idV39Used=false; idV39Fallback=false; idV39Ocr=0; idV39Pieces=0; idV39Scale=1f; idV39Reason="NONE"\n'
reset_new=reset_anchor+'        idV40Recovery=false; idV40Candidates=0; idV40Joined=""\n'
if reset_anchor not in s:
    raise SystemExit('v40 reset anchor missing')
s=s.replace(reset_anchor,reset_new,1)

old='''                var cage:String?=null
                var bestDistance=Int.MAX_VALUE
                if(bestY>=0){
                    val tolerance=maxOf(18,((ocrBitmap.height.toFloat()/rowCount.coerceAtLeast(1))*0.58f).toInt())
                    for(piece in pieces){
                        if(piece.box.centerX()>cageRight) continue
                        val parsed=RouteParser.extractCage(piece.text) ?: continue
                        val distance=kotlin.math.abs(piece.box.centerY()-bestY)
                        if(distance<=tolerance && distance<bestDistance){
                            cage=parsed
                            bestDistance=distance
                        }
                    }
                }

                try { ocrBitmap.recycle() } catch (_: Throwable) {}
'''
new='''                var cage:String?=null
                var bestDistance=Int.MAX_VALUE
                var cageTolerance=0
                if(bestY>=0){
                    cageTolerance=maxOf(18,((ocrBitmap.height.toFloat()/rowCount.coerceAtLeast(1))*0.58f).toInt())
                    for(piece in pieces){
                        if(piece.box.centerX()>cageRight) continue
                        val parsed=RouteParser.extractCage(piece.text) ?: continue
                        val distance=kotlin.math.abs(piece.box.centerY()-bestY)
                        if(distance<=cageTolerance && distance<bestDistance){
                            cage=parsed
                            bestDistance=distance
                        }
                    }
                }

                // v40: if no individual OCR token forms a cage, reuse the SAME
                // combined OCR result. Join only tokens from the Gaiola column and
                // only the winning Bairro row, left-to-right. This recovers cases
                // such as "J" + "16" / "J-" + "16" without a second ML Kit call.
                if(cage==null && bestY>=0){
                    val rowPieces=pieces
                        .filter { p ->
                            p.box.centerX()<=cageRight &&
                            kotlin.math.abs(p.box.centerY()-bestY)<=cageTolerance
                        }
                        .sortedBy { it.box.left }

                    idV40Candidates=rowPieces.size
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
                }

                try { ocrBitmap.recycle() } catch (_: Throwable) {}
'''
if old not in s:
    raise SystemExit('v40 cage block anchor missing')
s=s.replace(old,new,1)

# Distinguish a same-pass recovered success from native v39 success.
s=s.replace('''                    idV39Reason="SUCCESS"
''','''                    idV39Reason=if(idV40Recovery) "SUCCESS_V40_RECOVERY" else "SUCCESS"
''',1)

old_header='===== DIAGNOSTICO IMAGEM v10 | COMBINED OCR v39 + V37 FALLBACK + DIRECT SEND + BULK PIXELS ====='
new_header='===== DIAGNOSTICO IMAGEM v11 | SAME-PASS CAGE RECOVERY v40 + COMBINED OCR v39 + V37 FALLBACK ====='
s=s.replace(old_header,new_header,1)

report_anchor='''            appendLine("combinedV39=used=$idV39Used | fallback=$idV39Fallback | OCR=${idV39Ocr}ms | pieces=$idV39Pieces | scale=${String.format(java.util.Locale.US,"%.2f",idV39Scale)} | reason=$idV39Reason")
'''
report_new=report_anchor+'''            appendLine("samePassV40=recovered=$idV40Recovery | rowCandidates=$idV40Candidates | joined=[$idV40Joined]")
'''
if report_anchor not in s:
    raise SystemExit('v40 report anchor missing')
s=s.replace(report_anchor,report_new,1)

for m in [
    new_header,
    'samePassV40=recovered=$idV40Recovery',
    'SUCCESS_V40_RECOVERY',
    'readDenseBairroFirst(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)',
    '===== DIAGNOSTICO TEXTO v37 |',
]:
    if m not in s:
        raise SystemExit('v40 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('IMAGE v40 applied: same-pass cage token joining before v37 fallback; no extra OCR call')
