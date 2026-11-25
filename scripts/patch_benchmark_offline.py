from pathlib import Path
p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")
def once(old,new):
    global s
    assert s.count(old)==1, ("BENCH anchor",old,s.count(old))
    s=s.replace(old,new,1)

# Dedicated offline APK: all live entrypoints are disabled. The real OCR
# path runs unchanged on a private file, and its output is intercepted.
once("    override fun onAccessibilityEvent(event: AccessibilityEvent?) {\n",
     "    override fun onAccessibilityEvent(event: AccessibilityEvent?) {\n        if(benchOnlyV1()) return\n")
once("    private fun checkDirectMediaStoreImage() {\n",
     "    private fun checkDirectMediaStoreImage() {\n        if(benchOnlyV1()) return\n")
once("    private fun trySendPendingRouteIfChatOpen(): Boolean {\n",
     "    private fun trySendPendingRouteIfChatOpen(): Boolean {\n        if(benchOnlyV1()) return false\n")
once("    private fun sendRouteInCurrentChat(route: RouteResult) {\n",
     '''    private fun sendRouteInCurrentChat(route: RouteResult) {
        if(benchOnlyV1()) {
            benchFinishV1(route,"ROUTE")
            return
        }
''')
once("    private fun finishFileOnlyFailure(message: String) {\n",
     '''    private fun finishFileOnlyFailure(message: String) {
        if(benchOnlyV1()) {
            benchFinishV1(null,message)
            return
        }
''')
# No production window collection at service startup or after rearming.
once("    private fun primeCurrentScreen() {\n",
     "    private fun primeCurrentScreen() {\n        if(benchOnlyV1()) return\n")
once("    override fun onServiceConnected() {\n        super.onServiceConnected()\n",
     '''    override fun onServiceConnected() {
        super.onServiceConnected()
        benchConnectV1()
''')
once("    override fun onDestroy() {\n",
     '''    override fun onDestroy() {
        benchObserverV1?.stopWatching()
        benchObserverV1=null
        java.io.File(filesDir,"bench_ready").delete()
''')
anchor="    private fun idBegin("
idx=s.index(anchor)
helper='''    // This patch is applied ONLY to a separate benchmark package.
    private fun benchOnlyV1():Boolean=true
    private var benchObserverV1:android.os.FileObserver?=null
    private var benchTokenV1:String?=null
    private var benchStartedV1=0L
    private var benchHeightV1=0
    private var benchSerialV1=0L

    private fun benchConnectV1() {
        val directory=filesDir
        java.io.File(directory,"bench_request.json").delete()
        java.io.File(directory,"bench_result.json").delete()
        java.io.File(directory,"bench_ready").delete()
        benchObserverV1?.stopWatching()
        benchObserverV1=object:android.os.FileObserver(directory.absolutePath,
                android.os.FileObserver.MOVED_TO or android.os.FileObserver.CLOSE_WRITE) {
            override fun onEvent(event:Int,path:String?) {
                if(path=="bench_request.json") handler.post { benchReadV1() }
            }
        }
        benchObserverV1?.startWatching()
        Prefs.setEnabled(this,true)
        Prefs.setSearchArmed(this,true)
        java.io.File(directory,"bench_ready").writeText("OFFLINE_BENCHMARK_V1")
    }

    private fun benchReadV1() {
        val request=java.io.File(filesDir,"bench_request.json")
        if(!request.exists() || benchTokenV1!=null || processing) return
        var token:String?=null
        try {
            val obj=org.json.JSONObject(request.readText())
            request.delete()
            token=obj.getString("token")
            require(token.matches(Regex("[a-f0-9]{32}")))
            val name=obj.getString("file")
            require(name.matches(Regex("fixture_[a-f0-9]{64}")))
            val file=java.io.File(filesDir,name)
            require(file.isFile)
            val bounds=BitmapFactory.Options().apply { inJustDecodeBounds=true }
            BitmapFactory.decodeFile(file.absolutePath,bounds)
            require(bounds.outWidth>0 && bounds.outHeight>0)
            benchTokenV1=token
            benchHeightV1=bounds.outHeight
            benchSerialV1++
            val at=SystemClock.elapsedRealtime()
            benchStartedV1=at
            currentStartedAt=at
            processing=true
            idBegin(at,at,0L,benchHeightV1)
            readMediaOriginal(MediaImage(android.net.Uri.fromFile(file),benchSerialV1,
                name,"BENCHMARK_PRIVATE",System.currentTimeMillis(),benchHeightV1))
        } catch(error:Throwable) {
            if(benchTokenV1==null && token!=null) benchTokenV1=token
            benchFinishV1(null,"EXCEPTION:"+error.javaClass.simpleName)
        }
    }

    private fun benchFinishV1(route:RouteResult?,reason:String) {
        val token=benchTokenV1 ?: return
        val end=SystemClock.elapsedRealtime()
        val obj=org.json.JSONObject()
        obj.put("token",token)
        obj.put("mode","OFFLINE_NO_SEND")
        obj.put("height",benchHeightV1)
        obj.put("route_ms",(end-benchStartedV1).coerceAtLeast(0L))
        obj.put("neighborhood",route?.neighborhood ?: "")
        obj.put("cage",route?.cage ?: "")
        obj.put("reason",reason)
        obj.put("path",tracePathV67)
        obj.put("decode_ms",if(v78ThinCalls>0) v78ThinDecodeMs else traceDecodeMsV67)
        obj.put("scan_ms",traceScanMsV67)
        obj.put("ocr_bairro_ms",idBairroOcr)
        obj.put("ocr_cage_ms",idCageOcr)
        obj.put("ocr_thin_ms",v78ThinOcrMs)
        obj.put("thin_mode",v80ThinMode)
        obj.put("fallback",v74FallbackReason)
        obj.put("warm_busy",ocrWarmBusyV66)
        obj.put("warm_ms",lastOcrWarmDurationV66)
        obj.put("warm_age_ms",if(lastOcrWarmCompletedAtV66>0L) end-lastOcrWarmCompletedAtV66 else -1L)
        BENCH_EXTRA
        val battery=registerReceiver(null,android.content.IntentFilter(android.content.Intent.ACTION_BATTERY_CHANGED))
        obj.put("battery_temp_c",(battery?.getIntExtra(android.os.BatteryManager.EXTRA_TEMPERATURE,-999) ?: -999)/10.0)
        val temp=java.io.File(filesDir,"bench_result.tmp")
        temp.writeText(obj.toString())
        val final=java.io.File(filesDir,"bench_result.json")
        final.delete()
        check(temp.renameTo(final))
        benchTokenV1=null
        idOn=false
        processing=false
    }

'''
extra=[]
if "private var v82DecodeMode=" in s:
    extra+=['obj.put("decoder",v82DecodeMode)','obj.put("fd_ms",v82FdMs)','obj.put("stream_ms",v82StreamMs)']
else:
    extra+=['obj.put("decoder","STREAM")']
if "private var v84WarmOverlapAtRoute=" in s:
    extra+=['obj.put("warm_overlap_start",v84WarmOverlapAtRoute)','obj.put("warm_full_count",v84WarmFullCount)','obj.put("warm_count",v84WarmCount)','obj.put("warm_detector_ms",v84WarmScanMs)']
helper=helper.replace("BENCH_EXTRA","\n        ".join(extra))
s=s[:idx]+helper+s[idx:]
p.write_text(s,encoding="utf-8")
# Build identity is intentionally distinct from production versions.
p=Path("app/build.gradle.kts")
g=p.read_text()
import re
g,n=re.subn(r'applicationIdSuffix\s*=\s*"[^"]+"','applicationIdSuffix = ".benchmark"',g,count=1)
assert n==1
p.write_text(g)
p=Path("app/src/main/res/values/strings.xml")
g=p.read_text()
g,n=re.subn(r'(<string name="app_name">)[^<]+(</string>)',r'\g<1>Rota Rapida BENCHMARK OFFLINE\g<2>',g,count=1)
assert n==1
p.write_text(g)
print("OFFLINE benchmark guard: live event, MediaStore watcher, pending send and route send disabled; private fixture entry active.")
