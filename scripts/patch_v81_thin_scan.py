from pathlib import Path
p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")
def once(src,old,new):
    assert src.count(old)==1, ("V81 anchor",old,src.count(old))
    return src.replace(old,new,1)

# Extend the single OCR experiment only if a full-width proportional enlargement
# to 56 px fits the existing ML Kit width limit. Existing 56..99 path unchanged.
a=s.index("    private fun readMediaUltraThinV59(media: MediaImage) {")
b=s.index("\n    private fun readMediaOriginalFull(",a)
t=s[a:b]
t=once(t,"        var v80Single=source.height in 56..99 && source.width in 420..2200 && starts.size>1\n",'''        val v81ExpandedEligible=source.height in 32..55 &&
            source.width in 420..2200 &&
            source.width.toLong()*56L <= 3000L*source.height
        var v80Single=(source.height in 56..99 || v81ExpandedEligible) &&
            source.width in 420..2200 && starts.size>1
        v81ThinInput=source.width.toString()+"x"+source.height
        v81ThinExpanded=v80Single && v81ExpandedEligible
''')
t=once(t,"            val scaleX = work.width.toFloat() / width.toFloat().coerceAtLeast(1f)\n",'''            if(v80Single) v81SingleDim=work.width.toString()+"x"+work.height
            val scaleX = work.width.toFloat() / width.toFloat().coerceAtLeast(1f)
''')
s=s[:a]+t+s[b:]

# Detector retains identical pixel sampling and all thresholds. Reuse one
# exact-size IntArray, capped at 6 MB, never retain the bitmap. Full overwrite
# by getPixels before use. Synchronize the synchronous detector itself.
a=s.index("    private fun detectLargeTableCrop(source: Bitmap): ColorTableCrop? {")
b=s.index("\n    private fun readMediaOriginal(",a)
t=s[a:b]
t=once(t,"    private fun detectLargeTableCrop(source: Bitmap): ColorTableCrop? {",
       "    @Synchronized\n    private fun detectLargeTableCrop(source: Bitmap): ColorTableCrop? {")
old='''            IntArray(w * h).also { pixels ->
                source.getPixels(pixels, 0, w, 0, 0, w, h)
            }'''
new='''            val v81AllocAt=SystemClock.elapsedRealtime()
            val v81AllocCpuAt=SystemClock.currentThreadTimeMillis()
            val count=w*h
            val previous=v81PixelBuffer
            val pixels=if(previous!=null && previous.size==count) {
                v81BufferReused=true
                previous
            } else {
                IntArray(count).also {
                    if(count<=1500000) v81PixelBuffer=it
                }
            }
            v81PixelCount=count
            v81AllocMs=SystemClock.elapsedRealtime()-v81AllocAt
            v81AllocCpuMs=SystemClock.currentThreadTimeMillis()-v81AllocCpuAt
            val v81CopyAt=SystemClock.elapsedRealtime()
            val v81CopyCpuAt=SystemClock.currentThreadTimeMillis()
            source.getPixels(pixels, 0, w, 0, 0, w, h)
            v81CopyMs=SystemClock.elapsedRealtime()-v81CopyAt
            v81CopyCpuMs=SystemClock.currentThreadTimeMillis()-v81CopyCpuAt
            pixels'''
t=once(t,old,new)
s=s[:a]+t+s[b:]
s=once(s,"    private var v80ThinMode=\"NOT_USED\"\n",'''    private var v81PixelBuffer:IntArray?=null
    private var v81PixelCount=0
    private var v81BufferReused=false
    private var v81AllocMs=0L
    private var v81AllocCpuMs=0L
    private var v81CopyMs=0L
    private var v81CopyCpuMs=0L
    private var v81ThinInput="0x0"
    private var v81SingleDim="0x0"
    private var v81ThinExpanded=false
    private var v80ThinMode="NOT_USED"
''')
s=once(s,'        v80ThinMode="NOT_USED"\n','''        v81PixelCount=0
        v81BufferReused=false
        v81AllocMs=0L
        v81AllocCpuMs=0L
        v81CopyMs=0L
        v81CopyCpuMs=0L
        v81ThinInput="0x0"
        v81SingleDim="0x0"
        v81ThinExpanded=false
        v80ThinMode="NOT_USED"
''')
a=s.index("    private fun idReport(route:RouteResult){")
b=s.index("\n    private fun ",a+20)
t=s[a:b]
t=once(t,'            appendLine("RESUMO")\n','''            appendLine("V81 SCAN | pixels="+v81PixelCount+" | bufferReuso="+v81BufferReused+" | alloc="+v81AllocMs+"ms | allocCPU="+v81AllocCpuMs+"ms | copia="+v81CopyMs+"ms | copiaCPU="+v81CopyCpuMs+"ms | restante="+(traceScanMsV67-v81AllocMs-v81CopyMs).coerceAtLeast(0L)+"ms | restanteCPU="+(v78DenseScanCpuMs-v81AllocCpuMs-v81CopyCpuMs).coerceAtLeast(0L)+"ms")
            appendLine("V81 ULTRAFINA | original="+v81ThinInput+" | entradaSingle="+v81SingleDim+" | ampliada="+v81ThinExpanded+" | modo="+v80ThinMode)
            appendLine("RESUMO")
''')
s=s[:a]+t+s[b:]
for marker in ["UltraThinProofV80.accept(route,screenItems)","starts.addAll(originalStarts)","ModalFilter.filter(","V79 PARSER FAST","V77 TABELA CURTA","V76 COLUNA ESQUERDA","hasExactNativeRouteProofV70(","isFeuRosaRowV684","readMediaOriginalFull(media)","bulkPixels[y * w + x]","bulkPixels[yy * w + xx]"]:
    assert marker in s,marker
assert "sendSmsOnlyV664(" not in s
p.write_text(s,encoding="utf-8")
print("V81: expanded single OCR for 32..55 px within width guard; exact same original fallback; bounded reusable detector buffer, alloc/copy CPU+wall profile.")
