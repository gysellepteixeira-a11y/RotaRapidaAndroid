from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

required=[
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
    'private fun readDenseBairroFirst(',
    'private fun readDenseCageOnly(',
    'private fun matchBairroFirstPriority(',
    'speedDiagnosticSendMethod = "IMAGE_DIRECT_V8"',
    'private var idNeighborhood=""; private var idCageText=""; private var idHeight=0',
]
for m in required:
    if m not in s:
        raise SystemExit('IMAGE COMBINED OCR v39 wrong base: '+m)

# Canvas is used only to pack the existing Gaiola and Bairro columns side-by-side.
if 'import android.graphics.Canvas\n' not in s:
    anchor='import android.graphics.Bitmap\n'
    if anchor not in s:
        raise SystemExit('v39 Bitmap import anchor not found')
    s=s.replace(anchor,anchor+'import android.graphics.Canvas\n',1)

# RAM-only diagnostics. Existing image report persists only after confirmation.
state_anchor='    private var idNeighborhood=""; private var idCageText=""; private var idHeight=0\n'
state_new=state_anchor+'''    private var idV39Used=false; private var idV39Fallback=false; private var idV39Ocr=0L
    private var idV39Pieces=0; private var idV39Scale=1f; private var idV39Reason="NONE"
'''
s=s.replace(state_anchor,state_new,1)

reset_anchor='''        idNeighborhood=""; idCageText=""
'''
reset_new=reset_anchor+'''        idV39Used=false; idV39Fallback=false; idV39Ocr=0; idV39Pieces=0; idV39Scale=1f; idV39Reason="NONE"
'''
if reset_anchor not in s:
    raise SystemExit('v39 image diagnostic reset anchor not found')
s=s.replace(reset_anchor,reset_new,1)

# Insert the combined first-pass immediately before the existing Bairro-first path.
insert_anchor='    private fun readDenseBairroFirst(\n'
idx=s.find(insert_anchor)
if idx<0:
    raise SystemExit('v39 readDenseBairroFirst insertion point not found')

helper=r'''    private data class CombinedV39Piece(
        val text: String,
        val box: Rect
    )

    private fun readDenseCombinedV39(
        media: MediaImage,
        denseBitmap: Bitmap,
        rowCount: Int,
        widthRatio: Float,
        decodeMs: Long,
        scanMs: Long
    ) {
        if (!processing) {
            try { denseBitmap.recycle() } catch (_: Throwable) {}
            return
        }

        // Same geometry already validated by Bairro-first + Gaiola-narrow.
        val safeWidthRatio = widthRatio.coerceIn(0.42f, 0.90f)
        val bairroLeftRatio = (0.270f / safeWidthRatio).coerceIn(0.45f, 0.72f)
        val bairroRightRatio = (0.505f / safeWidthRatio)
            .coerceIn(bairroLeftRatio + 0.16f, 0.985f)

        val bx1 = (denseBitmap.width * bairroLeftRatio).toInt()
            .coerceIn(0, denseBitmap.width - 2)
        val bx2 = (denseBitmap.width * bairroRightRatio).toInt()
            .coerceIn(bx1 + 2, denseBitmap.width)
        val bairroWidth = bx2 - bx1
        val cageWidth = maxOf(52, (denseBitmap.width * 0.115f).toInt())
            .coerceAtMost(denseBitmap.width)

        if (bairroWidth < 70 || cageWidth < 40 || bx1 <= cageWidth) {
            idV39Fallback=true; idV39Reason="GEOMETRY"
            readDenseBairroFirst(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)
            return
        }

        // Put only the two useful columns in one compact bitmap. Vertical Y is
        // preserved, so Bairro and Gaiola from the same row remain matchable.
        val gap=maxOf(20,(denseBitmap.width*0.035f).toInt())
        val packedWidth=cageWidth+gap+bairroWidth
        val packed = try {
            Bitmap.createBitmap(packedWidth,denseBitmap.height,Bitmap.Config.ARGB_8888).also { out ->
                val c=Canvas(out)
                c.drawColor(0xFFFFFFFF.toInt())
                c.drawBitmap(
                    denseBitmap,
                    Rect(0,0,cageWidth,denseBitmap.height),
                    Rect(0,0,cageWidth,denseBitmap.height),
                    null
                )
                c.drawBitmap(
                    denseBitmap,
                    Rect(bx1,0,bx2,denseBitmap.height),
                    Rect(cageWidth+gap,0,packedWidth,denseBitmap.height),
                    null
                )
            }
        } catch (_: Throwable) { null }

        if (packed==null) {
            idV39Fallback=true; idV39Reason="PACK"
            readDenseBairroFirst(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)
            return
        }

        // Mild global enlargement. Much cheaper than rereading the whole table,
        // but gives the narrow Gaiola glyphs more pixels for the single OCR pass.
        val rowPitch=packed.height.toFloat()/rowCount.coerceAtLeast(1).toFloat()
        val wanted=(38f/rowPitch.coerceAtLeast(1f)).coerceIn(1f,1.45f)
        val maxDim=maxOf(packed.width,packed.height).toFloat().coerceAtLeast(1f)
        val maxAllowed=(2200f/maxDim).coerceAtLeast(1f)
        val scale=minOf(wanted,maxAllowed)
        val ocrBitmap = if(scale>1.03f) {
            try {
                Bitmap.createScaledBitmap(
                    packed,
                    (packed.width*scale).toInt().coerceAtLeast(1),
                    (packed.height*scale).toInt().coerceAtLeast(1),
                    true
                )
            } catch (_: Throwable) { packed }
        } else packed
        if(ocrBitmap!==packed) try { packed.recycle() } catch (_: Throwable) {}

        val cageRight=(cageWidth*scale).toInt()
        val bairroLeft=((cageWidth+gap)*scale).toInt()
        idV39Used=true; idV39Scale=scale
        val started=SystemClock.elapsedRealtime()

        recognizer.process(InputImage.fromBitmap(ocrBitmap,0))
            .addOnSuccessListener { result ->
                val ocrMs=SystemClock.elapsedRealtime()-started
                idV39Ocr=ocrMs
                if(!processing){
                    try { ocrBitmap.recycle() } catch (_: Throwable) {}
                    try { denseBitmap.recycle() } catch (_: Throwable) {}
                    return@addOnSuccessListener
                }

                val pieces=ArrayList<CombinedV39Piece>()
                for(block in result.textBlocks){
                    for(line in block.lines){
                        line.boundingBox?.let { pieces += CombinedV39Piece(line.text,Rect(it)) }
                        for(element in line.elements){
                            element.boundingBox?.let { pieces += CombinedV39Piece(element.text,Rect(it)) }
                        }
                    }
                }
                idV39Pieces=pieces.size

                var bestPriority=Int.MAX_VALUE
                var bestNeighborhood=""
                var bestY=-1
                var bestTop=Int.MAX_VALUE
                for(piece in pieces){
                    if(piece.box.centerX()<bairroLeft) continue
                    val hit=matchBairroFirstPriority(piece.text) ?: continue
                    if(hit.first<bestPriority || (hit.first==bestPriority && piece.box.top<bestTop)){
                        bestPriority=hit.first
                        bestNeighborhood=hit.second
                        bestY=piece.box.centerY()
                        bestTop=piece.box.top
                    }
                }

                var cage:String?=null
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

                if(bestPriority!=Int.MAX_VALUE && bestNeighborhood.isNotBlank() && cage!=null){
                    idV39Reason="SUCCESS"
                    lastDensePriorityNeighborhood=bestNeighborhood
                    lastDensePriorityIndex=bestPriority
                    lastDensePriorityCenterY=if(scale>0f)(bestY/scale).toInt() else bestY
                    lastDensePriorityText="combined-v39"
                    val route=RouteResult(bestNeighborhood,cage!!,bestPriority)

                    if(idOn){
                        val now=SystemClock.elapsedRealtime()
                        idDecode=decodeMs; idScan=scanMs
                        idBairroOcr=ocrMs; idBairro=now
                        idCageOcr=0L; idCage=now; idRoute=now
                        idNeighborhood=route.neighborhood; idCageText=route.cage
                    }
                    try { denseBitmap.recycle() } catch (_: Throwable) {}

                    if(isDuplicate(route)){
                        finishFileOnlyFailure("Arquivo repetido ignorado | combinedOCR=${ocrMs}ms")
                    }else{
                        sendRouteInCurrentChat(route)
                    }
                }else{
                    idV39Fallback=true
                    idV39Reason=when{
                        bestPriority==Int.MAX_VALUE -> "NO_BAIRRO"
                        cage==null -> "NO_CAGE"
                        else -> "NO_PAIR"
                    }
                    // Safe fallback: exact v37 two-stage OCR, using the original dense bitmap.
                    readDenseBairroFirst(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)
                }
            }
            .addOnFailureListener {
                try { ocrBitmap.recycle() } catch (_: Throwable) {}
                if(!processing){
                    try { denseBitmap.recycle() } catch (_: Throwable) {}
                    return@addOnFailureListener
                }
                idV39Fallback=true; idV39Reason="OCR_FAIL"
                readDenseBairroFirst(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)
            }
    }

'''
s=s[:idx]+helper+s[idx:]

# Switch only the dense-image entry point. The old method remains intact as fallback.
call_old='''        readDenseBairroFirst(
            media = media,
            denseBitmap = crop,
            rowCount = detected.rowCount,
            widthRatio = detected.widthRatio,
            decodeMs = decodeMs,
            scanMs = detected.scanMs
        )
'''
call_new='''        readDenseCombinedV39(
            media = media,
            denseBitmap = crop,
            rowCount = detected.rowCount,
            widthRatio = detected.widthRatio,
            decodeMs = decodeMs,
            scanMs = detected.scanMs
        )
'''
if call_old not in s:
    raise SystemExit('v39 dense entry call not found')
s=s.replace(call_old,call_new,1)

# Expose the experiment in the existing post-confirm image diagnostic.
old_header='===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS ====='
new_header='===== DIAGNOSTICO IMAGEM v10 | COMBINED OCR v39 + V37 FALLBACK + DIRECT SEND + BULK PIXELS ====='
s=s.replace(old_header,new_header,1)

route_line='''            appendLine("[${idA(idRoute)}] Rota pronta: ${route.neighborhood} -> ${route.cage}")
'''
route_new=route_line+'''            appendLine("combinedV39=used=$idV39Used | fallback=$idV39Fallback | OCR=${idV39Ocr}ms | pieces=$idV39Pieces | scale=${String.format(java.util.Locale.US,"%.2f",idV39Scale)} | reason=$idV39Reason")
'''
if route_line not in s:
    raise SystemExit('v39 image report route line not found')
s=s.replace(route_line,route_new,1)

for m in [
    new_header,
    'private fun readDenseCombinedV39(',
    'combinedV39=used=$idV39Used',
    'readDenseBairroFirst(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)',
    'speedDiagnosticSendMethod = "IMAGE_DIRECT_V8"',
    '===== DIAGNOSTICO TEXTO v37 |',
]:
    if m not in s:
        raise SystemExit('IMAGE COMBINED OCR v39 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('IMAGE COMBINED OCR v39 applied: one packed Bairro+Gaiola OCR first; exact v37 two-stage fallback preserved')
