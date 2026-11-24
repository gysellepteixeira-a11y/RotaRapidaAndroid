from pathlib import Path

# V72 A/B: reuse the decoded bitmap only when the density scan cannot
# identify a valid dense table. Everything else uses the V71 path verbatim.
# No OCR/parser, sending, text, priorities, SMS, or group changes.
p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")

def one(block,old,new,label):
    n=block.count(old)
    if n!=1:
        raise RuntimeError(f"V72 {label}: expected 1 anchor, found {n}")
    return block.replace(old,new,1)

# Diagnostic flag, reporting only; no extra work on the hot path.
s=one(s, "    private var tracePathV67=\"\"\n",
    "    private var v72ReusedBitmap=false\n    private var tracePathV67=\"\"\n",
    "state flag")
s=one(s, "        tracePathV67=\"\"\n",
    "        tracePathV67=\"\"\n        v72ReusedBitmap=false\n",
    "per-image state reset")

# Original full OCR accepts an optional predecoded bitmap; if it is absent,
# keep existing decoding/MLKit/filtering behavior exactly unchanged.
full_begin=s.index("    private fun readMediaOriginalFull(media: MediaImage) {")
dense_begin=s.index("    private fun readMediaLargeColorCrop(media: MediaImage) {",full_begin)
full=s[full_begin:dense_begin]

full=one(full,
    "    private fun readMediaOriginalFull(media: MediaImage) {",
    "    private fun readMediaOriginalFull(media: MediaImage, predecodedV72: Bitmap? = null) {",
    "full OCR method signature")
full=one(full,
    '''        if (!processing) return
''',
    '''        if (!processing) {
            if(predecodedV72 != null) try { predecodedV72.recycle() } catch (_:Throwable) {}
            return
        }
        v72ReusedBitmap = predecodedV72 != null
''',
    "guard, prevent leaked bitmap for canceled route")
full=one(full,
    '''val rawBitmap = contentResolver.openInputStream(media.uri)?.use { stream ->
                BitmapFactory.decodeStream(stream)
            } ?: throw IllegalStateException("Imagem nao decodificada")''',
    '''val rawBitmap = predecodedV72 ?: contentResolver.openInputStream(media.uri)?.use { stream ->
                BitmapFactory.decodeStream(stream)
            } ?: throw IllegalStateException("Imagem nao decodificada")''',
    "reuse predecoded source with original full OCR fallback")
if "ModalFilter.filter(" not in full or "recognizer.process(input)" not in full:
    raise RuntimeError("V72 full OCR and color filter missing")

s=s[:full_begin]+full+s[dense_begin:]

# Two safe fast fallbacks from dense-check to full OCR: pass the bitmap in.
dense_begin=s.index("    private fun readMediaLargeColorCrop(media: MediaImage) {")
dense_end=s.index("    private fun readDenseCageOnly(",dense_begin)
dense=s[dense_begin:dense_end]

dense=one(dense,
    '''        if (detected == null) {
            try { source.recycle() } catch (_: Throwable) {}
            readMediaOriginalFull(media)
            return
        }''',
    '''        if (detected == null) {
            readMediaOriginalFull(media, source)
            return
        }''',
    "no density table fallback")
dense=one(dense,
    '''        if (detected.rowCount < DENSE_MIN_ROWS) {
            try { detected.bitmap.recycle() } catch (_: Throwable) {}
            try { source.recycle() } catch (_: Throwable) {}
            readMediaOriginalFull(media)
            return
        }''',
    '''        if (detected.rowCount < DENSE_MIN_ROWS) {
            try { detected.bitmap.recycle() } catch (_: Throwable) {}
            readMediaOriginalFull(media, source)
            return
        }''',
    "insufficient dense rows fallback")
if "val detected = detectLargeTableCrop(source)" not in dense:
    raise RuntimeError("V72 dense detection missing")
if "ModalFilter.filter(" not in dense:
    raise RuntimeError("V72 dense-mode color filter missing")
s=s[:dense_begin]+dense+s[dense_end:]

# Report after local send to compare V71 to V72 without affecting latency.
report_anchor='''            appendLine("RESUMO")
'''
s=one(s, report_anchor,
    '''            appendLine("V72 REUSO BITMAP | ativado=$v72ReusedBitmap | caminho=DENSE_CHECK>FULL quando sem tabela densa")
'''+report_anchor,
    "image diagnostic report")

for marker in (
    "fun hasExactNativeRouteProofV70(", "V71 SISTEMA APOS ENVIO",
    "V69 GRUPO FECHADO |", "ModalFilter.filter(",
    "readMediaLargeColorCrop(", "readMediaOriginalFull(",
    "sendRouteInCurrentChat(", "isFeuRosaRowV684"
):
    if marker not in s: raise RuntimeError("V72 preserved marker missing: "+marker)
if "sendSmsOnlyV664(" in s: raise RuntimeError("V72 SMS feature unexpectedly found")

p.write_text(s, encoding="utf-8")
print("V72 A/B bitmap reuse applied; dense fallback passes existing decoded bitmap to unmodified full OCR/filter; reporting after sending.")
