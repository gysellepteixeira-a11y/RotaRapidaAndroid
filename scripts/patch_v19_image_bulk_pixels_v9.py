from pathlib import Path

p = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = p.read_text(encoding="utf-8")

# v9: isolated A/B on the image detector only.
# Keep crop geometry, row counting, OCR, priority and DIRECT SEND unchanged.
# The only hot-path change is replacing thousands of Bitmap.getPixel JNI calls
# with one Bitmap.getPixels bulk copy followed by IntArray reads.

marker_old = "===== DIAGNOSTICO IMAGEM v8 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND ====="
marker_new = "===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS ====="
if marker_old not in s:
    raise SystemExit("IMAGE BULK PIXELS v9: v8 diagnostic marker not found")
s = s.replace(marker_old, marker_new, 1)

anchor = '''        val yStart = (h * 0.015f).toInt().coerceIn(0, h - 1)
        val yEnd = (h * 0.985f).toInt().coerceIn(yStart + 1, h)

        val bins = ((w - xStart) / step + 2).coerceAtLeast(2)
'''
replacement = '''        val yStart = (h * 0.015f).toInt().coerceIn(0, h - 1)
        val yEnd = (h * 0.985f).toInt().coerceIn(yStart + 1, h)

        // v9: one native bulk read instead of thousands of Bitmap.getPixel calls.
        // Geometry and sampling steps below remain byte-for-byte equivalent.
        val bulkPixels = try {
            IntArray(w * h).also { pixels ->
                source.getPixels(pixels, 0, w, 0, 0, w, h)
            }
        } catch (_: Throwable) {
            return null
        }

        val bins = ((w - xStart) / step + 2).coerceAtLeast(2)
'''
if anchor not in s:
    raise SystemExit("IMAGE BULK PIXELS v9: detector insertion anchor not found")
s = s.replace(anchor, replacement, 1)

old1 = '                val pixel = source.getPixel(x, y)\n'
new1 = '                val pixel = bulkPixels[y * w + x]\n'
if s.count(old1) != 1:
    raise SystemExit(f"IMAGE BULK PIXELS v9: expected 1 primary getPixel, got {s.count(old1)}")
s = s.replace(old1, new1, 1)

old2 = '                if (isAgencyColor(source.getPixel(x, y))) {\n'
new2 = '                if (isAgencyColor(bulkPixels[y * w + x])) {\n'
if s.count(old2) != 1:
    raise SystemExit(f"IMAGE BULK PIXELS v9: expected 1 band getPixel, got {s.count(old2)}")
s = s.replace(old2, new2, 1)

old3 = '                if (isAgencyColor(source.getPixel(xx, yy))) {\n'
new3 = '                if (isAgencyColor(bulkPixels[yy * w + xx])) {\n'
if s.count(old3) != 1:
    raise SystemExit(f"IMAGE BULK PIXELS v9: expected 1 row getPixel, got {s.count(old3)}")
s = s.replace(old3, new3, 1)

# Strong verification: no getPixel remains in this detector build and text/direct
# send markers must still be present.
if 'source.getPixel(' in s:
    raise SystemExit("IMAGE BULK PIXELS v9: an unexpected source.getPixel remains")
for required in [
    'TEXT_DIRECT_V5',
    'IMAGE_DIRECT_V8',
    marker_new,
    'bulkPixels[y * w + x]',
    'bulkPixels[yy * w + xx]',
]:
    if required not in s:
        raise SystemExit(f"IMAGE BULK PIXELS v9: required marker missing: {required}")

p.write_text(s, encoding="utf-8")
print("IMAGE BULK PIXELS v9 applied: getPixels bulk scan only; OCR/crop/send unchanged")
