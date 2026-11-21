from pathlib import Path

p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")

def once(block,needle,replacement,tag):
    if block.count(needle)!=1:
        raise RuntimeError(f"TRACE V67 {tag}: expected 1 anchor, found {block.count(needle)}")
    return block.replace(needle,replacement,1)

field_anchor="    private var idOn=false; private var idStart=0L;"
fields='''    // V67: diagnostics only; no OCR calls, gestures or delays added.
    private var tracePathV67=""
    private var traceDecodeMsV67=0L
    private var traceScanMsV67=0L
    private var tracePrepMsV67=0L
    private var traceOcrMsV67=0L
    private var traceParseMsV67=0L

    private fun tracePathV67(stage:String) {
        tracePathV67=if(tracePathV67.isEmpty()) stage else tracePathV67+">"+stage
    }

'''
s=once(s,field_anchor,fields+field_anchor,"fields")

reset='''        idNeighborhood=""; idCageText=""
'''
reset_new=reset+'''        tracePathV67=""
        traceDecodeMsV67=0L
        traceScanMsV67=0L
        tracePrepMsV67=0L
        traceOcrMsV67=0L
        traceParseMsV67=0L
'''
s=once(s,reset,reset_new,"reset image markers")

report='''            appendLine("RESUMO")
'''
extra='''            appendLine("ETAPAS OCR V67 | Poco x M52")
            appendLine("caminho=" + tracePathV67)
            appendLine(
                "decodeTabela=" + traceDecodeMsV67 + "ms | scanTabela=" +
                traceScanMsV67 + "ms | preparoOCR=" + tracePrepMsV67 + "ms"
            )
            appendLine(
                "OCRcompleto=" + traceOcrMsV67 + "ms | parser=" +
                traceParseMsV67 + "ms | OCRbairro=" + idBairroOcr +
                "ms | OCRgaiola=" + idCageOcr + "ms"
            )
            appendLine()
'''
begin=s.index("    private fun idReport(route:RouteResult){")
end=s.find("\n    private fun ",begin+20)
if end<0: end=len(s)
block=once(s[begin:end],report,extra+report,"image report")
s=s[:begin]+block+s[end:]

def method(name,following):
    start=s.index("    private fun "+name+"(")
    end=s.find("\n    private fun "+following+"(",start)
    if end<0: raise RuntimeError("end missing "+following)
    return start,end,s[start:end]

# Dense preliminary image decoding/scanning (called for 646px image).
start,end,b=method("readMediaLargeColorCrop","readDenseCageOnly")
b=once(b,'''        if (!processing) return

        val decodeStarted''','''        if (!processing) return
        tracePathV67("DENSE_CHECK")

        val decodeStarted''',"dense stage")
b=once(b,"        val detected = detectLargeTableCrop(source)\n",'''        val traceScanStartV67=SystemClock.elapsedRealtime()
        val detected = detectLargeTableCrop(source)
        traceDecodeMsV67+=decodeMs
        traceScanMsV67+=SystemClock.elapsedRealtime()-traceScanStartV67
''',"dense scan")
s=s[:start]+b+s[end:]

# Whole image OCR, when table is not classified as dense.
start,end,b=method("readMediaOriginalFull","readMediaLargeColorCrop")
b=once(b,'''    private fun readMediaOriginalFull(media: MediaImage) {
''','''    private fun readMediaOriginalFull(media: MediaImage) {
        tracePathV67("FULL")
        val tracePrepBeginV67=SystemClock.elapsedRealtime()
''',"full stage")
b=once(b,"        recognizer.process(input)\n",'''        tracePrepMsV67+=SystemClock.elapsedRealtime()-tracePrepBeginV67
        val traceOcrStartV67=SystemClock.elapsedRealtime()
        recognizer.process(input)
''',"full OCR begin")
b=once(b,"                    val ocrFinishedAt = SystemClock.elapsedRealtime()\n",'''                    val ocrFinishedAt = SystemClock.elapsedRealtime()
                    traceOcrMsV67+=(ocrFinishedAt-traceOcrStartV67).coerceAtLeast(0L)
''',"full OCR finish")
b=once(b,"                    val parserMs = SystemClock.elapsedRealtime() - parserStarted\n",'''                    val parserMs = SystemClock.elapsedRealtime() - parserStarted
                    traceParseMsV67+=parserMs
''',"full parser")
s=s[:start]+b+s[end:]

# Enhanced OCR fallback, if any.
start=s.index("    private fun readMediaEnhanced(media: MediaImage) {")
end=s.find("\n    private fun ",start+20)
if end<0: end=len(s)
b=s[start:end]
b=once(b,'''    private fun readMediaEnhanced(media: MediaImage) {
''','''    private fun readMediaEnhanced(media: MediaImage) {
        tracePathV67("ENHANCED")
        val tracePrepBeginV67=SystemClock.elapsedRealtime()
''',"enhanced stage")
b=once(b,"        recognizer.process(input)\n",'''        tracePrepMsV67+=SystemClock.elapsedRealtime()-tracePrepBeginV67
        val traceOcrStartV67=SystemClock.elapsedRealtime()
        recognizer.process(input)
''',"enhanced OCR begin")
b=once(b,"                    val ocrFinishedAt = SystemClock.elapsedRealtime()\n",'''                    val ocrFinishedAt = SystemClock.elapsedRealtime()
                    traceOcrMsV67+=(ocrFinishedAt-traceOcrStartV67).coerceAtLeast(0L)
''',"enhanced OCR finish")
b=once(b,"                    val parserMs = SystemClock.elapsedRealtime() - parserStarted\n",'''                    val parserMs = SystemClock.elapsedRealtime() - parserStarted
                    traceParseMsV67+=parserMs
''',"enhanced parser")
s=s[:start]+b+s[end:]

# Annotate two dense paths without changing their behavior.
for method_name,marker in [
    ("readDenseBairroFirst","BAIRRO_FIRST"),
    ("readDenseFullFallback","DENSE_FALLBACK")
]:
    sig="    private fun "+method_name+"("
    begin=s.find(sig)
    if begin<0: raise RuntimeError(method_name+" missing")
    body=s.find("    ) {",begin)
    if body<0: raise RuntimeError(method_name+" body missing")
    at=body+len("    ) {\n")
    s=s[:at]+'        tracePathV67("'+marker+'")\n'+s[at:]

if "sendSmsOnlyV664(" in s: raise RuntimeError("Unexpected SMS code in no-SMS base")
if "idReport(route:RouteResult)" not in s: raise RuntimeError("Image report missing")
if "ModalFilter.filter(" not in s: raise RuntimeError("Modal filter missing")

p.write_text(s,encoding="utf-8")
print("V67 trace: dense decode/scan, full/enhanced OCR and parsing, path. No behavior changes.")
