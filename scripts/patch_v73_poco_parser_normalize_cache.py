from pathlib import Path

# V73: cache only the three immutable normalization regexes used by
# RouteParser.normalize. No matching rules, priorities, OCR input,
# send paths, group state, or filters are changed.
# The parser's exact NFD -> accent strip -> punctuation -> space collapse
# transformation is preserved byte-for-byte for Unicode/ASCII strings.

p=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
s=p.read_text(encoding="utf-8")

fields_anchor='''    private val cageRegex =
'''
fields=r'''    // V73: avoid compiling these same patterns for each OCR fragment.
    private val v73AccentMarksRegex = Regex("""\p{Mn}+""")
    private val v73PunctuationRegex = Regex("""[^a-z0-9\s]""")
    private val v73SpaceRegex = Regex("""\s+""")

'''
if s.count(fields_anchor)!=1:
    raise RuntimeError("V73: regex field anchor count != 1")
s=s.replace(fields_anchor,fields+fields_anchor,1)

begin=s.index("    fun normalize(value: String): String {")
end=s.find("\n    fun extractCage(value: String): String?",begin)
if end<0:raise RuntimeError("V73: normalize end missing")
block=s[begin:end]

rules=[
    ('            .replace(Regex("""\\p{Mn}+"""), "")',
     '            .replace(v73AccentMarksRegex, "")'),
    ('            .replace(Regex("""[^a-z0-9\\s]"""), " ")',
     '            .replace(v73PunctuationRegex, " ")'),
    ('            .replace(Regex("""\\s+"""), " ")',
     '            .replace(v73SpaceRegex, " ")')
]
for old,new in rules:
    if block.count(old)!=1:
        raise RuntimeError("V73: normalize pattern anchor not unique: "+old)
    block=block.replace(old,new,1)
if "Normalizer.normalize(" not in block or "Normalizer.Form.NFD" not in block:
    raise RuntimeError("V73: Unicode normalization is missing")
s=s[:begin]+block+s[end:]

# No high-frequency diagnostic calls: just a static post-send marker.
sfile=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
t=sfile.read_text(encoding="utf-8")
report_begin=t.index("    private fun idReport(route:RouteResult){")
report_end=t.find("\n    private fun ",report_begin+20)
if report_end<0:raise RuntimeError("V73: image report end missing")
report=t[report_begin:report_end]
anchor='''            appendLine("RESUMO")
'''
assert report.count(anchor)==1
report=report.replace(anchor,'''            appendLine("V73 PARSER CACHE | normalizacao=regex_precompilada | regras=V71")
'''+anchor,1)
t=t[:report_begin]+report+t[report_end:]

for marker in (
    "isFeuRosaRowV684", "private fun containsTokenApprox(",
    "private fun priorityForNormalizedV36(", "fun parseImageScreenTexts(",
    "fun parsePlainTexts(", "fun extractCage("
):
    if marker not in s: raise RuntimeError("V73 preserved parser marker missing: "+marker)
for marker in (
    "V71 SISTEMA APOS ENVIO", "V69 GRUPO FECHADO |",
    "fun hasExactNativeRouteProofV70(", "ModalFilter.filter(",
    "sendRouteInCurrentChat("
):
    if marker not in t: raise RuntimeError("V73 preserved service marker missing: "+marker)
if "sendSmsOnlyV664(" in t:raise RuntimeError("V73: unexpected SMS path")

p.write_text(s, encoding="utf-8")
sfile.write_text(t, encoding="utf-8")
print("V73 parser cache: three Regex instances compiled once; exact matching and safety rules preserved")
