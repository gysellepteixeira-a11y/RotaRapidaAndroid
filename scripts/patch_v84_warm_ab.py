from pathlib import Path
import re
p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")
def once(src,old,new):
    assert src.count(old)==1, ("V84 anchor",old,src.count(old))
    return src.replace(old,new,1)
def section(name):
    a=s.index("    private fun "+name+"(")
    b=s.index("\n    private fun ",a+20)
    return a,b,s[a:b]

# One periodic warm scheduler. Legacy 15s scheduler and duplicate startup
# recognizer call are suppressed, if still present in the reconstructed base.
s=s.replace("        handler.postDelayed(keepOcrWarmRunnable, KEEP_OCR_WARM_INTERVAL_MS)\n","")
s=once(s,"        warmUpRecognizer()\n","        handler.post { runOcrWarmV66() }\n")
s=once(s,"OCR_WARM_INTERVAL_V66_MS = 120_000L","OCR_WARM_INTERVAL_V66_MS = 15_000L")
s=once(s,"OCR_WARM_MIN_GAP_V66_MS = 15_000L","OCR_WARM_MIN_GAP_V66_MS = 12_000L")
s=once(s,"interval=120s","interval=15s")
s=once(s,'''                    Prefs.isEnabled(this@WhatsRouteAccessibilityService) &&
                    Prefs.searchArmed(this@WhatsRouteAccessibilityService) &&
                    !processing &&
                    !ocrWarmBusyV66''','''                    !v84Destroyed && !processing &&
                    !analyzeScheduled && !ocrWarmBusyV66''')

# Snapshot all detector telemetry fields actually assigned by this reconstructed
# detector; keep only its reusable pixel array. Warm scan runs on the same
# handler, so no real scan can interleave with these temporary fields.
a=s.index("    private fun detectLargeTableCrop(source: Bitmap): ColorTableCrop? {")
b=s.index("\n    private fun readMediaOriginal(",a)
det=s[a:b]
assigned=set(re.findall(r'(?m)^\s*(v(?:74|75|76|81)\w+)\s*(?:\+=|=(?!=))',det))
assigned.add("v74DenseWhy")
assigned.discard("v81PixelBuffer")
for f in assigned:
    assert re.search(r'\bprivate var '+f+r'\b',s), f
assert {"v74DenseWhy","v76LeftShiftAccepted","v81PixelCount","v81CopyMs"} <= assigned, assigned
snapshot="\n".join("        val saved_"+f+"="+f for f in sorted(assigned))
restore="\n".join("            "+f+"=saved_"+f for f in sorted(assigned))
s=once(s,"    private var ocrWarmBusyV66 = false\n",'''    private var v84Destroyed=false
    private var v84LastFullAt=0L
    private var v84WarmScanMs=0L
    private var v84WarmScanOk=false
    private var v84WarmFullCount=0
    private var v84WarmCount=0
    private var v84WarmOverlapAtRoute=false
    private var v84WarmKind="NONE"
    private var v84Requested="NOT_USED"
    private val v84NextStream=HashMap<Int,Boolean>()
    private var ocrWarmBusyV66 = false
''')
a,b,t=section("runOcrWarmV66")
new='''    // Allow idle warming while disarmed only on external power. Never arm,
    // send or consume a real image from this routine.
    private fun v84WarmAllowed():Boolean {
        if(v84Destroyed || processing || analyzeScheduled || ocrWarmBusyV66) return false
        if(android.os.Build.VERSION.SDK_INT>=29) {
            val pm=getSystemService(android.content.Context.POWER_SERVICE) as? android.os.PowerManager
            if(pm!=null && pm.currentThermalStatus>=3) return false
        }
        if(Prefs.isEnabled(this) && Prefs.searchArmed(this)) return true
        val battery=registerReceiver(null,android.content.IntentFilter(android.content.Intent.ACTION_BATTERY_CHANGED))
        return (battery?.getIntExtra(android.os.BatteryManager.EXTRA_PLUGGED,0) ?: 0)!=0
    }

    private fun v84WarmDetector() {
''' + snapshot + '''
        val at=SystemClock.elapsedRealtime()
        var fixture:Bitmap?=null
        var crop:Bitmap?=null
        v84WarmScanOk=false
        try {
            val image=Bitmap.createBitmap(1384,523,Bitmap.Config.ARGB_8888)
            fixture=image
            val canvas=android.graphics.Canvas(image)
            canvas.drawColor(android.graphics.Color.WHITE)
            val paint=android.graphics.Paint()
            paint.color=android.graphics.Color.rgb(255,153,0)
            for(i in 0 until 29) {
                val y=12f+i*17f
                canvas.drawRect(750f,y,880f,y+13f,paint)
            }
            val detected=detectLargeTableCrop(image)
            crop=detected?.bitmap
            v84WarmScanOk=detected!=null
        } finally {
            if(crop!=null && crop!==fixture) crop.recycle()
            fixture?.recycle()
''' + restore + '''
            v84WarmScanMs=SystemClock.elapsedRealtime()-at
        }
    }

    private fun runOcrWarmV66() {
        if(!v84WarmAllowed()) return
        val now=SystemClock.elapsedRealtime()
        if(lastOcrWarmCompletedAtV66>0L &&
            now-lastOcrWarmCompletedAtV66<OCR_WARM_MIN_GAP_V66_MS) return
        ocrWarmBusyV66=true
        var bitmap:Bitmap?=null
        val full=v84LastFullAt==0L || now-v84LastFullAt>=60_000L
        try {
            if(full) {
                v84WarmDetector()
                v84LastFullAt=SystemClock.elapsedRealtime()
            }
            val sample=Bitmap.createBitmap(if(full) 387 else 160,if(full) 812 else 64,Bitmap.Config.ARGB_8888)
            bitmap=sample
            val canvas=android.graphics.Canvas(sample)
            canvas.drawColor(android.graphics.Color.WHITE)
            val paint=android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG)
            paint.color=android.graphics.Color.BLACK
            paint.textSize=18f
            val names=arrayOf("Mata da Praia","Morada de Laranjeiras","Rosario","Manoel Plaza","Eurico","Praia da Baleia")
            for(i in 0 until (if(full) 29 else 2)) {
                canvas.drawText(names[i%names.size],8f,22f+i*27f,paint)
            }
            v84WarmKind=if(full) "FULL_SYNTHETIC" else "SMALL_TEXT"
            val started=SystemClock.elapsedRealtime()
            recognizer.process(InputImage.fromBitmap(sample,0))
                .addOnCompleteListener { task ->
                    try {
                        if(task.isSuccessful && !processing && !v84Destroyed) {
                            // Pure normalization only: no route acceptance or sending.
                            for(block in task.result.textBlocks) {
                                for(line in block.lines) RouteParser.normalize(line.text)
                            }
                        }
                    } finally {
                        sample.recycle()
                        lastOcrWarmDurationV66=SystemClock.elapsedRealtime()-started
                        lastOcrWarmCompletedAtV66=SystemClock.elapsedRealtime()
                        if(task.isSuccessful) {
                            v84WarmCount++
                            if(full) v84WarmFullCount++
                        }
                        ocrWarmBusyV66=false
                    }
                }
        } catch(_:Throwable) {
            bitmap?.recycle()
            ocrWarmBusyV66=false
        }
    }

'''
# runOcrWarm is followed by warmUpRecognizer in V66. Preserve unrelated code.
assert "private fun warmUpRecognizer(" in s[b:b+100],s[b:b+100]
s=s[:a]+new+s[b:]
s=once(s,"    override fun onDestroy() {\n","    override fun onDestroy() {\n        v84Destroyed=true\n")

# A/B: one decoder per image, alternating per height. Only attempt the
# other decoder on failure; original full OCR fallback remains unchanged.
a,b,t=section("decodeMediaV82")
s=s[:a]+'''    private fun decodeMediaV82(media: MediaImage): Bitmap? {
        if(v84NextStream.size>=64 && !v84NextStream.containsKey(media.height)) v84NextStream.clear()
        val streamFirst=v84NextStream[media.height] ?: true
        v84NextStream[media.height]=!streamFirst
        v84Requested=if(streamFirst) "STREAM" else "FD"
        fun fd():Bitmap? {
            val at=SystemClock.elapsedRealtime()
            return try {
                contentResolver.openFileDescriptor(media.uri,"r")?.use {
                    BitmapFactory.decodeFileDescriptor(it.fileDescriptor)
                }
            } catch(_:Throwable) { null }
            finally { v82FdMs+=SystemClock.elapsedRealtime()-at }
        }
        fun stream():Bitmap? {
            val at=SystemClock.elapsedRealtime()
            return try {
                contentResolver.openInputStream(media.uri)?.use { BitmapFactory.decodeStream(it) }
            } catch(_:Throwable) { null }
            finally { v82StreamMs+=SystemClock.elapsedRealtime()-at }
        }
        if(streamFirst) {
            v82DecodeMode="STREAM"
            stream()?.let { return it }
            v82DecodeMode="FD_FALLBACK"
            return fd()
        }
        v82DecodeMode="FD"
        fd()?.let { return it }
        v82DecodeMode="STREAM_FALLBACK"
        return stream()
    }
''' + s[b:]
s=once(s,'        v82DecodeMode="NOT_USED"\n','''        v84Requested="NOT_USED"
        v84WarmOverlapAtRoute=ocrWarmBusyV66
        v82DecodeMode="NOT_USED"
''')
a,b,t=section("idReport")
t=once(t,'            appendLine("RESUMO")\n','''            appendLine("V84 WARM | tipo="+v84WarmKind+" | completos="+v84WarmFullCount+" | total="+v84WarmCount+" | detector="+v84WarmScanMs+"ms | detectorAceito="+v84WarmScanOk+" | OCRconcorrenteInicio="+v84WarmOverlapAtRoute+" | intervalo=15s | completo=60s | standbyCarregando=true")
            appendLine("V84 AB | solicitado="+v84Requested+" | usado="+v82DecodeMode+" | fd="+v82FdMs+"ms | stream="+v82StreamMs+"ms")
            appendLine("RESUMO")
''')
s=s[:a]+t+s[b:]
for marker in ["UltraThinProofV80.accept(route,screenItems)","starts.addAll(originalStarts)","ModalFilter.filter(","V79 PARSER FAST","V77 TABELA CURTA","V76 COLUNA ESQUERDA","hasExactNativeRouteProofV70(","isFeuRosaRowV684","readMediaOriginalFull(media)","findAdminUltraSendNodeFast(root, editorRect)","verifySendResult(route, 0, 0)","V69 GRUPO FECHADO"]:
    assert marker in s,marker
assert "sendSmsOnlyV664(" not in s
assert s.count("decodeMediaV82(media)")==2
p.write_text(s,encoding="utf-8")
print("V84: one warm schedule, synthetic detector and OCR, plugged standby, isolated detector telemetry, alternating decoder, original send/crops preserved.")
print("Saved detector fields:",sorted(assigned))
