from pathlib import Path
S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text()

a='''    private val recognizer by lazy {\n        TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)\n    }\n'''
b=a+'''    private val recognizerTopV63 by lazy { TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS) }\n    private val recognizerBottomV63 by lazy { TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS) }\n'''
assert a in s
s=s.replace(a,b,1)

# warm both at service start
old='''        warmUpRecognizer()\n        handler.removeCallbacks(keepOcrWarmRunnable)\n'''
new='''        warmUpRecognizer()\n        warmUpParallelV63()\n        handler.removeCallbacks(keepOcrWarmRunnable)\n'''
assert old in s
s=s.replace(old,new,1)

mark='''    override fun onAccessibilityEvent(event: AccessibilityEvent?) {\n'''
helper='''    private fun warmUpParallelV63() {\n        try {\n            val a=Bitmap.createBitmap(32,32,Bitmap.Config.ARGB_8888)\n            recognizerTopV63.process(InputImage.fromBitmap(a,0)).addOnCompleteListener { try{a.recycle()}catch(_:Throwable){} }\n        } catch(_:Throwable){}\n        try {\n            val b=Bitmap.createBitmap(32,32,Bitmap.Config.ARGB_8888)\n            recognizerBottomV63.process(InputImage.fromBitmap(b,0)).addOnCompleteListener { try{b.recycle()}catch(_:Throwable){} }\n        } catch(_:Throwable){}\n    }\n\n'''
assert mark in s
s=s.replace(mark,helper+mark,1)

old='''        recognizer.close()\n        super.onDestroy()\n'''
new='''        recognizer.close()\n        try{recognizerTopV63.close()}catch(_:Throwable){}\n        try{recognizerBottomV63.close()}catch(_:Throwable){}\n        super.onDestroy()\n'''
assert old in s
s=s.replace(old,new,1)

old='''    private var idEditorVisitedV48=0; private var idEditorLookupMsV48=0L\n    private var lastDenseRecoveryDebug = ""\n'''
new='''    private var idEditorVisitedV48=0; private var idEditorLookupMsV48=0L\n    private var idV63Top=0L; private var idV63Bottom=0L; private var idV63Wall=0L; private var idV63Overlap=0; private var idV63Used=false\n    private var lastDenseRecoveryDebug = ""\n'''
assert old in s
s=s.replace(old,new,1)

start=s.index('    private fun readDenseBairroFirst(')
end=s.index('\n    private fun readDenseFullFallback(',start)
fun=r'''    private fun readDenseBairroFirst(
        media: MediaImage, denseBitmap: Bitmap, rowCount: Int,
        widthRatio: Float, decodeMs: Long, scanMs: Long
    ) {
        if(!processing){ try{denseBitmap.recycle()}catch(_:Throwable){}; return }
        val wr=widthRatio.coerceIn(0.42f,0.90f)
        val lr=(0.270f/wr).coerceIn(0.45f,0.72f)
        val rr=0.975f.coerceAtLeast(lr+0.16f)
        val x1=(denseBitmap.width*lr).toInt().coerceIn(0,denseBitmap.width-2)
        val x2=(denseBitmap.width*rr).toInt().coerceIn(x1+2,denseBitmap.width)
        if(x2-x1<80 || denseBitmap.height<80){
            readDenseFullFallback(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs,"v63 small"); return
        }
        val whole=try{Bitmap.createBitmap(denseBitmap,x1,0,x2-x1,denseBitmap.height)}catch(_:Throwable){null}
        if(whole==null){ readDenseFullFallback(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs,"v63 crop"); return }
        val h=whole.height
        val ov=maxOf(18,(h*0.12f).toInt()).coerceAtMost(maxOf(18,h/3))
        val mid=h/2
        val topEnd=(mid+ov/2).coerceIn(1,h)
        val bottomStart=(mid-ov/2).coerceIn(0,h-1)
        val top=try{Bitmap.createBitmap(whole,0,0,whole.width,topEnd)}catch(_:Throwable){null}
        val bottom=try{Bitmap.createBitmap(whole,0,bottomStart,whole.width,h-bottomStart)}catch(_:Throwable){null}
        try{whole.recycle()}catch(_:Throwable){}
        if(top==null || bottom==null){
            try{top?.recycle()}catch(_:Throwable){}; try{bottom?.recycle()}catch(_:Throwable){}
            readDenseFullFallback(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs,"v63 split"); return
        }
        val wallStart=SystemClock.elapsedRealtime()
        var topDone=false; var bottomDone=false; var failed=false; var finished=false
        var topMs=0L; var bottomMs=0L
        var topHits:List<BairroFirstHit> = emptyList(); var bottomHits:List<BairroFirstHit> = emptyList()

        fun hits(t:Text,off:Int):List<BairroFirstHit>{
            val out=ArrayList<BairroFirstHit>()
            fun add(raw:String,box:Rect?){
                if(box==null || raw.isBlank()) return
                val p=matchBairroFirstPriority(raw)?:return
                out+=BairroFirstHit(p.first,p.second,off+(box.top+box.bottom)/2,off+box.top,raw)
            }
            for(bl in t.textBlocks) for(li in bl.lines){ add(li.text,li.boundingBox); for(e in li.elements) add(e.text,e.boundingBox) }
            return out
        }
        fun finish(){
            if(finished || !topDone || !bottomDone) return
            finished=true
            val wall=SystemClock.elapsedRealtime()-wallStart
            idV63Used=true; idV63Top=topMs; idV63Bottom=bottomMs; idV63Wall=wall; idV63Overlap=ov
            if(!processing){ try{denseBitmap.recycle()}catch(_:Throwable){}; return }
            if(failed){ readDenseFullFallback(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs,"v63 half failed"); return }
            val chosen=(topHits+bottomHits).minWithOrNull(compareBy<BairroFirstHit>({it.priorityIndex},{it.top}))
            if(chosen==null){ readDenseFullFallback(media,denseBitmap,rowCount,widthRatio,decodeMs,scanMs,"v63 no bairro"); return }
            if(idOn){ idDecode=decodeMs; idScan=scanMs; idBairroOcr=wall; idBairro=SystemClock.elapsedRealtime(); idNeighborhood=chosen.neighborhood }
            lastDensePriorityNeighborhood=chosen.neighborhood
            lastDensePriorityIndex=chosen.priorityIndex
            lastDensePriorityCenterY=chosen.centerY
            lastDensePriorityText=chosen.raw
            lastDenseRecoveryDebug="parallel-v63; top=${topMs}ms; bottom=${bottomMs}ms; wall=${wall}ms"
            readDenseCageOnly(media,denseBitmap,rowCount,decodeMs,scanMs,wall,0L)
        }
        val ts=SystemClock.elapsedRealtime()
        recognizerTopV63.process(InputImage.fromBitmap(top,0))
            .addOnSuccessListener{ t-> topMs=SystemClock.elapsedRealtime()-ts; topHits=hits(t,0); topDone=true; try{top.recycle()}catch(_:Throwable){}; finish() }
            .addOnFailureListener{ topMs=SystemClock.elapsedRealtime()-ts; topDone=true; failed=true; try{top.recycle()}catch(_:Throwable){}; finish() }
        val bs=SystemClock.elapsedRealtime()
        recognizerBottomV63.process(InputImage.fromBitmap(bottom,0))
            .addOnSuccessListener{ t-> bottomMs=SystemClock.elapsedRealtime()-bs; bottomHits=hits(t,bottomStart); bottomDone=true; try{bottom.recycle()}catch(_:Throwable){}; finish() }
            .addOnFailureListener{ bottomMs=SystemClock.elapsedRealtime()-bs; bottomDone=true; failed=true; try{bottom.recycle()}catch(_:Throwable){}; finish() }
    }
'''
s=s[:start]+fun+s[end:]

old='''        idEditorFastV48=false; idEditorFallbackV48=false; idEditorVisitedV48=0; idEditorLookupMsV48=0L\n    }\n'''
new='''        idEditorFastV48=false; idEditorFallbackV48=false; idEditorVisitedV48=0; idEditorLookupMsV48=0L\n        idV63Top=0L; idV63Bottom=0L; idV63Wall=0L; idV63Overlap=0; idV63Used=false\n    }\n'''
assert old in s
s=s.replace(old,new,1)

old='''            if(idBairro>0L) appendLine("[${idA(idBairro)}] Bairro: $idNeighborhood | OCR=${idBairroOcr}ms | decode=${idDecode}ms | scan=${idScan}ms")\n            if(idCage>0L) appendLine("[${idA(idCage)}] Gaiola: $idCageText | OCR=${idCageOcr}ms")\n'''
new='''            if(idBairro>0L) appendLine("[${idA(idBairro)}] Bairro: $idNeighborhood | OCR=${idBairroOcr}ms | decode=${idDecode}ms | scan=${idScan}ms")\n            if(idV63Used) appendLine("parallelOCRV63=true | topOCR=${idV63Top}ms | bottomOCR=${idV63Bottom}ms | wallOCR=${idV63Wall}ms | overlap=${idV63Overlap}px")\n            if(idCage>0L) appendLine("[${idA(idCage)}] Gaiola: $idCageText | OCR=${idCageOcr}ms")\n'''
assert old in s
s=s.replace(old,new,1)
s=s.replace('===== DIAGNOSTICO IMAGEM v19 | V48 EDITOR FAST PATH + V47 CLEAN FAST =====','===== DIAGNOSTICO IMAGEM v19 | V63 PARALLEL OCR + V48 EDITOR FAST PATH + V47 CLEAN FAST =====',1)

for m in ['recognizerTopV63.process','recognizerBottomV63.process','parallelOCRV63=true','idBairroOcr=wall','readDenseCageOnly(media,denseBitmap']:
    assert m in s,m
S.write_text(s)
print('v63 parallel OCR aplicado')
