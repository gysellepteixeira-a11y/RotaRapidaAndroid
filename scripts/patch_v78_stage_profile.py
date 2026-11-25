from pathlib import Path

# V78 profiling only: no extra OCR calls, changes to crops, parser or send.
p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")
def once(src, old, new):
    assert src.count(old)==1, ("V78 anchor",old,src.count(old))
    return src.replace(old,new,1)
def section(src,name):
    a=src.index("    private fun "+name+"(")
    b=src.find("\n    private fun ",a+20)
    return a,b if b>=0 else len(src)

fields = [
    "v78ThinDecodeMs","v78ThinPlanMs","v78ThinPrepMs",
    "v78ThinOcrMs","v78ThinExtractMs","v78ThinParseMs",
    "v78DenseScanCpuMs","v78BairroPrepMs","v78BairroSelectMs"
]
counts = ["v78ThinTiles","v78ThinCalls","v78ThinErrors","v78BairroHeight","v78BairroWidth"]
anchor="    private var tracePathV67=\"\"\n"
s=once(s,anchor,anchor+''.join("    private var "+f+"=0L\n" for f in fields)+''.join("    private var "+f+"=0\n" for f in counts))
reset='        tracePathV67=""\n'
s=once(s,reset,reset+''.join("        "+f+"=0L\n" for f in fields)+''.join("        "+f+"=0\n" for f in counts))

a,b=section(s,"readMediaUltraThinV59")
t=s[a:b]
t=once(t,"        val source = try {\n",
"""        tracePathV67("ULTRAFINA_TILES")
        val v78DecodeAt=SystemClock.elapsedRealtime()
        val source = try {
""")
t=once(t,"        if (source == null) {\n",
"""        v78ThinDecodeMs+=SystemClock.elapsedRealtime()-v78DecodeAt
        if (source == null) {
""")
t=once(t,"        val tileWidth = minOf(\n",
"""        val v78PlanAt=SystemClock.elapsedRealtime()
        val tileWidth = minOf(
""")
t=once(t,"        val startedAll = SystemClock.elapsedRealtime()\n",
"""        val startedAll = SystemClock.elapsedRealtime()
        v78ThinTiles=starts.size
        v78ThinPlanMs+=startedAll-v78PlanAt
""")
t=once(t,"            val routeFromGeometry = RouteParser.parseImageScreenTexts(screenItems)\n",
"""            val v78ParseAt=SystemClock.elapsedRealtime()
            val routeFromGeometry = RouteParser.parseImageScreenTexts(screenItems)
""")
t=once(t,"            val route = routeFromGeometry ?: oneRowRoute\n",
"""            val route = routeFromGeometry ?: oneRowRoute
            v78ThinParseMs+=SystemClock.elapsedRealtime()-v78ParseAt
""")
t=once(t,"            val x = starts[index]\n",
"""            val v78PrepAt=SystemClock.elapsedRealtime()
            val x = starts[index]
""")
t=once(t,"            if (tile == null) {\n",
"""            if (tile == null) {
                v78ThinPrepMs+=SystemClock.elapsedRealtime()-v78PrepAt
                v78ThinErrors++
""")
t=once(t,"            recognizer.process(InputImage.fromBitmap(work, 0))\n",
"""            v78ThinPrepMs+=SystemClock.elapsedRealtime()-v78PrepAt
            v78ThinCalls++
            val v78OcrAt=SystemClock.elapsedRealtime()
            recognizer.process(InputImage.fromBitmap(work, 0))
""")
t=once(t,"                    for (block in visionText.textBlocks) {\n",
"""                    v78ThinOcrMs+=SystemClock.elapsedRealtime()-v78OcrAt
                    val v78ExtractAt=SystemClock.elapsedRealtime()
                    for (block in visionText.textBlocks) {
""")
t=once(t,"                    try { work.recycle() } catch (_: Throwable) {}\n                    processTile(index + 1)\n",
"""                    try { work.recycle() } catch (_: Throwable) {}
                    v78ThinExtractMs+=SystemClock.elapsedRealtime()-v78ExtractAt
                    processTile(index + 1)
""")
t=once(t,"                .addOnFailureListener {\n",
"""                .addOnFailureListener {
                    if (processing) {
                        v78ThinOcrMs+=SystemClock.elapsedRealtime()-v78OcrAt
                        v78ThinErrors++
                    }
""")
s=s[:a]+t+s[b:]

# Synchronous scan: compare thread CPU vs elapsed (includes preemption, waits).
a,b=section(s,"readMediaLargeColorCrop")
t=s[a:b]
t=once(t,"        val traceScanStartV67=SystemClock.elapsedRealtime()\n",
"""        val v78ScanCpuAt=SystemClock.currentThreadTimeMillis()
        val traceScanStartV67=SystemClock.elapsedRealtime()
""")
t=once(t,"        val detected = detectLargeTableCrop(source)\n",
"""        val detected = detectLargeTableCrop(source)
        v78DenseScanCpuMs+=SystemClock.currentThreadTimeMillis()-v78ScanCpuAt
""")
s=s[:a]+t+s[b:]

# Dense Bairro path: time crop/preparation and candidate selection separately.
a,b=section(s,"readDenseBairroFirst")
t=s[a:b]
t=once(t,'        tracePathV67("BAIRRO_FIRST")\n',
"""        tracePathV67("BAIRRO_FIRST")
        val v78BairroPrepAt=SystemClock.elapsedRealtime()
""")
t=once(t,"        recognizer.process(InputImage.fromBitmap(bairroBitmap, 0))\n",
"""        v78BairroWidth=bairroBitmap.width
        v78BairroHeight=bairroBitmap.height
        v78BairroPrepMs+=SystemClock.elapsedRealtime()-v78BairroPrepAt
        recognizer.process(InputImage.fromBitmap(bairroBitmap, 0))
""")
t=once(t,"                val bairroOcrMs = SystemClock.elapsedRealtime() - started\n",
"""                val bairroOcrMs = SystemClock.elapsedRealtime() - started
                val v78BairroSelectAt=SystemClock.elapsedRealtime()
""")
t=once(t,"                readDenseCageOnly(\n",
"""                v78BairroSelectMs+=SystemClock.elapsedRealtime()-v78BairroSelectAt
                readDenseCageOnly(
""")
s=s[:a]+t+s[b:]

a,b=section(s,"idReport")
t=s[a:b]
t=once(t,'            appendLine("RESUMO")\n',
'''            appendLine("V78 PERFIL | diagnostico=true | scanCPU="+v78DenseScanCpuMs+"ms | scanWall="+traceScanMsV67+"ms | bairroDim="+v78BairroWidth+"x"+v78BairroHeight+" | bairroPrep="+v78BairroPrepMs+"ms | bairroSelecao="+v78BairroSelectMs+"ms")
            if (v78ThinTiles>0 || tracePathV67.contains("ULTRAFINA_TILES")) {
                appendLine("V78 ULTRAFINA | tiles="+v78ThinTiles+" | chamadas="+v78ThinCalls+" | falhas="+v78ThinErrors+" | decode="+v78ThinDecodeMs+"ms | plano="+v78ThinPlanMs+"ms | preparo="+v78ThinPrepMs+"ms | OCR="+v78ThinOcrMs+"ms | extracao="+v78ThinExtractMs+"ms | parser="+v78ThinParseMs+"ms")
            }
            appendLine("RESUMO")
''')
s=s[:a]+t+s[b:]
for marker in ['V77 TABELA CURTA','V76 COLUNA ESQUERDA','hasExactNativeRouteProofV70(', 'ModalFilter.filter(', 'isFeuRosaRowV684','readMediaOriginalFull(media)','ocrWarmV66=true']:
    assert marker in s, marker
assert 'sendSmsOnlyV664(' not in s
p.write_text(s,encoding="utf-8")
print("V78 profile: ultrathin tiles, dense scan CPU/wall, Bairro crop and selection; no recognition or send changes")
