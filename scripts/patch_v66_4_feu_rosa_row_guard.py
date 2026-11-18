from pathlib import Path
root = Path("app/src/main/java/com/gy/rotarapida")
parser_file = root / "RouteParser.kt"
service_file = root / "WhatsRouteAccessibilityService.kt"
r = parser_file.read_text(encoding="utf-8")
s = service_file.read_text(encoding="utf-8")
if "isFeuRosaRowV684" in r:
    raise SystemExit("guard already applied")
parser_anchor = "    private fun priorityFor(text: String): Pair<Int, String>? {"
helper = '''    private fun isFeuRosaNormalizedV684(n: String): Boolean {
        if (!n.contains("feu") && !n.contains("fev")) return false
        val words = n.split(' ')
        for (i in 0 until words.size - 1) {
            val first = words[i]
            val second = words[i + 1]
            if ((first == "feu" || first == "fev") &&
                (second.startsWith("rosa") || second.startsWith("roza"))) {
                return true
            }
        }
        return false
    }

    fun isFeuRosaRowV684(text: String): Boolean =
        isFeuRosaNormalizedV684(normalize(text))

'''
if parser_anchor not in r: raise SystemExit("priorityFor missing")
r = r.replace(parser_anchor, helper + parser_anchor, 1)
start = r.index(parser_anchor)
end = r.find("\n    /**", start)
if end < 0: raise SystemExit("priorityFor end missing")
block = r[start:end]
old_loop = "        priorities.forEachIndexed { index, rule ->\n"
if old_loop not in block: raise SystemExit("priorityFor loop missing")
block = block.replace(old_loop, '''        val feuRosaV684 = isFeuRosaNormalizedV684(normalized)
        priorities.forEachIndexed { index, rule ->
            if (feuRosaV684 && "rosar" in rule.requiredTokens) return@forEachIndexed
''', 1)
r = r[:start] + block + r[end:]

start = r.index("    private fun priorityForNormalizedV36(normalized: String): Pair<Int, String>? {")
end = r.find("\n    data class PlainParseDiagV36", start)
if end < 0: raise SystemExit("v36 function end missing")
block = r[start:end]
if old_loop not in block: raise SystemExit("v36 loop missing")
block = block.replace(old_loop, '''        val feuRosaV684 = isFeuRosaNormalizedV684(normalized)
        priorities.forEachIndexed { index, rule ->
            if (feuRosaV684 && "rosar" in rule.requiredTokens) return@forEachIndexed
''', 1)
r = r[:start] + block + r[end:]

needle = '''                for (block in text.textBlocks) {
                    for (line in block.lines) {
                        // Linha inteira primeiro: resolve bairros de varias palavras.
                        consider(line.text, line.boundingBox)
'''
replacement = '''                for (block in text.textBlocks) {
                    for (line in block.lines) {
                        // Prevent a misread fragment from matching Feu Rosa.
                        if (RouteParser.isFeuRosaRowV684(line.text)) continue
                        // Linha inteira primeiro: resolve bairros de varias palavras.
                        consider(line.text, line.boundingBox)
'''
if needle not in s: raise SystemExit("bairro-first loop missing")
s = s.replace(needle,replacement,1)

old = '''                    "BAIRRO PRIMEIRO: ${chosen.neighborhood} | " +
                        "linhaY=${chosen.centerY} | OCR=${bairroOcrMs}ms | agora Gaiola..."
'''
new = '''                    "BAIRRO PRIMEIRO: ${chosen.neighborhood} | " +
                        "ocr=[${chosen.raw.take(38)}] | " +
                        "linhaY=${chosen.centerY} | OCR=${bairroOcrMs}ms | agora Gaiola..."
'''
if old not in s: raise SystemExit("status anchor missing")
s = s.replace(old,new,1)
assert '"rosario de fatima" -> listOf("rosar")' in r
assert 'if (token == "rosar")' in r
assert "sendRouteInCurrentChat(route)" in s
parser_file.write_text(r, encoding="utf-8")
service_file.write_text(s, encoding="utf-8")
print("V66.4 FEU ROSA GUARD: explicit priority-row exclusion, no extra OCR.")
