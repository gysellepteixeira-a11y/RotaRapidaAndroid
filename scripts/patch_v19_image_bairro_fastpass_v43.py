from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

required=[
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
    'private fun readDenseBairroFirst(',
    'private fun readDenseCageOnly(',
    'private fun matchBairroFirstPriority(',
    'speedDiagnosticSendMethod = "IMAGE_DIRECT_V8"',
    '===== DIAGNOSTICO TEXTO v37 |',
]
for m in required:
    if m not in s:
        raise SystemExit('v43 wrong base: '+m)

# Diagnostics only; reset is done at the start of each image attempt.
state_anchor='    private var idNeighborhood=""; private var idCageText=""; private var idHeight=0\n'
state_new=state_anchor+'''    private var idV43Used=false; private var idV43Success=false; private var idV43Fallback=false
    private var idV43Ocr=0L; private var idV43Scale=0.82f; private var idV43Width=0
'''
if state_anchor not in s:
    raise SystemExit('v43 state anchor missing')
s=s.replace(state_anchor,state_new,1)

reset_anchor='''        idNeighborhood=""; idCageText=""
'''
reset_new=reset_anchor+'''        idV43Used=false; idV43Success=false; idV43Fallback=false; idV43Ocr=0L; idV43Scale=0.82f; idV43Width=0
'''
if reset_anchor not in s:
    raise SystemExit('v43 reset anchor missing')
s=s.replace(reset_anchor,reset_new,1)

# Preserve the exact v37 implementation as fallback.
old_sig='    private fun readDenseBairroFirst(\n'
if s.count(old_sig) != 1:
    raise SystemExit('v43 expected exactly one readDenseBairroFirst')
s=s.replace(old_sig,'    private fun readDenseBairroFirstV37(\n',1)

insert_anchor='    private fun readDenseBairroFirstV37(\n'
idx=s.find(insert_anchor)
if idx<0:
    raise SystemExit('v43 insertion anchor missing')

helper=r'''    private fun readDenseBairroFirst(
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

        // v43 FAST PASS: narrower Bairro-only crop + 0.82x OCR bitmap.
        // The original v37 method remains untouched below and is called immediately
        // if this first pass cannot confirm one of the configured priority bairros.
        val safeWidthRatio=widthRatio.coerceIn(0.42f,0.90f)
        val leftRatio=(0.282f/safeWidthRatio).coerceIn(0.47f,0.74f)
        val rightRatio=(0.493f/safeWidthRatio).coerceIn(leftRatio+0.14f,0.975f)
        val x1=(denseBitmap.width*leftRatio).toInt().coerceIn(0,denseBitmap.width-2)
        val x2=(denseBitmap.width*rightRatio).toInt().coerceIn(x1+2,denseBitmap.width)
        val w=x2-x1
        val fastScale=0.82f
        idV43Used=true; idV43Scale=fastScale; idV43Width=w

        if(w<70){
            idV43Fallback=true
            readDenseBairroFirstV37(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)
            return
        }

        val crop=try { Bitmap.createBitmap(denseBitmap,x1,0,w,denseBitmap.height) } catch(_:Throwable){ null }
        if(crop==null){
            idV43Fallback=true
            readDenseBairroFirstV37(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)
            return
        }

        val fastBitmap=try {
            Bitmap.createScaledBitmap(
                crop,
                (crop.width*fastScale).toInt().coerceAtLeast(1),
                (crop.height*fastScale).toInt().coerceAtLeast(1),
                true
            )
        } catch(_:Throwable){ crop }
        if(fastBitmap!==crop) try { crop.recycle() } catch(_:Throwable){}
        val actualScale=fastBitmap.height.toFloat()/denseBitmap.height.toFloat().coerceAtLeast(1f)
        idV43Scale=actualScale
        val started=SystemClock.elapsedRealtime()

        recognizer.process(InputImage.fromBitmap(fastBitmap,0))
            .addOnSuccessListener { text ->
                val ocrMs=SystemClock.elapsedRealtime()-started
                idV43Ocr=ocrMs
                if(!processing){
                    try { fastBitmap.recycle() } catch(_:Throwable){}
                    try { denseBitmap.recycle() } catch(_:Throwable){}
                    return@addOnSuccessListener
                }

                var bestPriority=Int.MAX_VALUE
                var bestNeighborhood=""
                var bestY=-1
                var bestTop=Int.MAX_VALUE
                var bestRaw=""

                fun consider(raw:String, box:Rect?){
                    if(box==null || raw.isBlank()) return
                    val hit=matchBairroFirstPriority(raw) ?: return
                    if(hit.first<bestPriority || (hit.first==bestPriority && box.top<bestTop)){
                        bestPriority=hit.first
                        bestNeighborhood=hit.second
                        bestY=box.centerY()
                        bestTop=box.top
                        bestRaw=raw
                    }
                }

                for(block in text.textBlocks){
                    for(line in block.lines){
                        consider(line.text,line.boundingBox)
                        for(element in line.elements) consider(element.text,element.boundingBox)
                    }
                }
                try { fastBitmap.recycle() } catch(_:Throwable){}

                if(bestPriority==Int.MAX_VALUE || bestNeighborhood.isBlank() || bestY<0){
                    idV43Fallback=true
                    readDenseBairroFirstV37(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)
                    return@addOnSuccessListener
                }

                idV43Success=true
                val mappedY=(bestY/actualScale.coerceAtLeast(0.01f)).toInt()
                    .coerceIn(0,denseBitmap.height-1)
                lastDensePriorityNeighborhood=bestNeighborhood
                lastDensePriorityIndex=bestPriority
                lastDensePriorityCenterY=mappedY
                lastDensePriorityText=bestRaw
                lastDenseRecoveryDebug="bairro-fast-v43=$rowCount; bairro=$bestNeighborhood; y=$mappedY; OCR=${ocrMs}ms; scale=$actualScale"

                if(idOn){
                    idDecode=decodeMs; idScan=scanMs
                    idBairroOcr=ocrMs
                    idBairro=SystemClock.elapsedRealtime()
                }

                readDenseCageOnly(
                    media=media,
                    denseBitmap=denseBitmap,
                    rowCount=rowCount,
                    decodeMs=decodeMs,
                    scanMs=scanMs,
                    denseOcrMs=ocrMs,
                    denseParseMs=0L
                )
            }
            .addOnFailureListener {
                try { fastBitmap.recycle() } catch(_:Throwable){}
                if(!processing){
                    try { denseBitmap.recycle() } catch(_:Throwable){}
                    return@addOnFailureListener
                }
                idV43Fallback=true
                readDenseBairroFirstV37(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)
            }
    }

'''
s=s[:idx]+helper+s[idx:]

# Image diagnostic marker.
old_header='===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS ====='
new_header='===== DIAGNOSTICO IMAGEM v14 | BAIRRO FAST PASS v43 + V37 FALLBACK + GAIOLA NARROW ====='
s=s.replace(old_header,new_header,1)

route_line='''            appendLine("[${idA(idRoute)}] Rota pronta: ${route.neighborhood} -> ${route.cage}")
'''
route_new=route_line+'''            appendLine("bairroFastV43=used=$idV43Used | success=$idV43Success | fallback=$idV43Fallback | OCR=${idV43Ocr}ms | scale=${String.format(java.util.Locale.US,"%.2f",idV43Scale)} | width=${idV43Width}px")
'''
if route_line not in s:
    raise SystemExit('v43 report route anchor missing')
s=s.replace(route_line,route_new,1)

for m in [
    new_header,
    'private fun readDenseBairroFirstV37(',
    'bairroFastV43=used=$idV43Used',
    'readDenseBairroFirstV37(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs)',
    'speedDiagnosticSendMethod = "IMAGE_DIRECT_V8"',
    '===== DIAGNOSTICO TEXTO v37 |',
]:
    if m not in s:
        raise SystemExit('v43 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('IMAGE v43 applied: 0.82x narrower Bairro fast pass; exact v37 Bairro-first fallback preserved')
