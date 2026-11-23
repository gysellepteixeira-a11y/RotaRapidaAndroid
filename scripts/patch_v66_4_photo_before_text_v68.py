from pathlib import Path

p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")
if "photoIncomingV68" in s:
    raise SystemExit("V68 already applied")

def one(old,new,label):
    global s
    count=s.count(old)
    if count != 1:
        raise RuntimeError("V68 %s: expected exactly 1 anchor, got %s" % (label,count))
    s=s.replace(old,new,1)

one("    private var idOn=false; private var idStart=0L;",
'''    private var photoSuppressedTextV68=false
    private var photoEvidenceV68=""

    private var idOn=false; private var idStart=0L;''',
"V68 state")

one("        val tfNewItems = tfNewItemsReverse.asReversed()",
'''        val tfNewItems = tfNewItemsReverse.asReversed()

        // New image MUST reach the image OCR. The accessibility tree may
        // contain flattened captions that mix Rosário with another cage.
        val photoIncomingV68 = if (primed && tfNewItems.isNotEmpty()) {
            val hintV68 = SystemClock.elapsedRealtime() < imageHintUntil
            val newNodesV68 = tfNewItems.map { it.node }.toSet()
            val newVisualV68 = findImageCandidates(items).any {
                image.node in newNodesV68 && imageFingerprint(image) !in previousImageFingerprints
            }
            if (hintV68 || newVisualV68) {
                val last = tfNewItems.last()
                val nativeLength = try {
                    last.node.text?.length ?: 0
                } catch (_: Throwable) { 0 }
                val descLength = try {
                    last.node.contentDescription?.length ?: 0
                } catch (_: Throwable) { 0 }
                photoEvidenceV68 =
                    "hint=$hintV68 visual=$newVisualV68 " +
                    "nodes=DOLLAR{tfNewItems.size} raw=$nativeLength desc=$descLength"
                true
            } else {
                photoEvidenceV68="text-only"
                false
            }
        } else {
            false
        }
        photoSuppressedTextV68 = photoIncomingV68
'''.replace('DOLLAR{', chr(36) + '{'),"text image evidence")

one("if (primed && Prefs.searchArmed(this) && tfNewItems.isNotEmpty()) {",
    "if (primed && Prefs.searchArmed(this) && tfNewItems.isNotEmpty() && !photoIncomingV68) {",
    "fast text gate")

one("if (textRoute != null && !isDuplicate(textRoute)) {",
    "if (!photoIncomingV68 && textRoute != null && !isDuplicate(textRoute)) {",
    "legacy text gate")

start=s.index("    private fun idReport(route:RouteResult){")
end=s.find("\n    private fun ",start+20)
if end<0: end=len(s)
section=s[start:end]
old='''            appendLine("RESUMO")
'''
new='''            appendLine("V68 FOTO PRIORITARIA | textoIgnorado=$photoSuppressedTextV68 | $photoEvidenceV68")
            appendLine()
            appendLine("RESUMO")
'''
if section.count(old)!=1: raise RuntimeError("V68 image report anchor not found")
s=s[:start]+section.replace(old,new,1)+s[end:]

assert "readMediaLargeColorCrop(media)" in s
assert "readMediaOriginalFull(media)" in s
assert "sendRouteInCurrentChat(tfRoute)" in s
assert "sendSmsOnlyV664(" not in s
assert "ModalFilter.filter(" in s
assert "isFeuRosaRowV684" in s
p.write_text(s,encoding="utf-8")
print("V68 applied: photos take precedence over text candidates; image OCR unchanged.")
