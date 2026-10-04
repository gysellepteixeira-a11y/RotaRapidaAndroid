from pathlib import Path

P=Path('app/src/main/java/com/gy/rotarapida/RouteParser.kt')
S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
p=P.read_text(encoding='utf-8')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v34 | TEXT v6 + PARSER SPLIT DIAG + LOCAL ANCHOR PROOF + SKIP BAND + TRUNC BEFORE ROOT + LAZY ADMIN + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v35 | TEXT v6 + PRECOMPILED NORMALIZE REGEX + PARSER SPLIT DIAG + LOCAL ANCHOR PROOF + SKIP BAND + TRUNC BEFORE ROOT + LAZY ADMIN + READ MORE v21 + DIRECT SEND ====='

required=[
    old_header,
    'data class PlainParseDiagV34(',
    'fun normalize(value: String): String {',
    '.replace(Regex("""\\p{Mn}+"""), "")',
    '.replace(Regex("""[^a-z0-9\\s]"""), " ")',
    '.replace(Regex("""\\s+"""), " ")',
    'parserV34=$tdV34ParserDiag',
    'localProofV33=calls=$tdV33LocalCalls',
]
for m in required:
    if m not in (p+s):
        raise SystemExit('PRECOMPILED NORMALIZE REGEX v35 wrong base: '+m)

# Precompile the exact same three patterns once. Put them immediately before
# normalize() so this patch is independent of formatting around cageRegex.
normalize_anchor='    fun normalize(value: String): String {\n'
normalize_insert='''    private val normalizeMarksRegex = Regex("""\\p{Mn}+""")\n    private val normalizeNonAlnumRegex = Regex("""[^a-z0-9\\s]""")\n    private val normalizeWhitespaceRegex = Regex("""\\s+""")\n\n    fun normalize(value: String): String {\n'''
if normalize_anchor not in p:
    raise SystemExit('v35 normalize anchor not found')
p=p.replace(normalize_anchor,normalize_insert,1)

p=p.replace('.replace(Regex("""\\p{Mn}+"""), "")','.replace(normalizeMarksRegex, "")',1)
p=p.replace('.replace(Regex("""[^a-z0-9\\s]"""), " ")','.replace(normalizeNonAlnumRegex, " ")',1)
p=p.replace('.replace(Regex("""\\s+"""), " ")','.replace(normalizeWhitespaceRegex, " ")',1)

s=s.replace(old_header,new_header,1)
report_anchor='''                    appendLine("parserV34=$tdV34ParserDiag")\n'''
report_insert=report_anchor+'''                    appendLine("normalizeV35=regexPrecompiled=true | semantics=same | regexCount=3")\n'''
if report_anchor not in s:
    raise SystemExit('v35 diagnostic report anchor not found')
s=s.replace(report_anchor,report_insert,1)

for m in [
    new_header,
    'private val normalizeMarksRegex = Regex("""\\p{Mn}+""")',
    'private val normalizeNonAlnumRegex = Regex("""[^a-z0-9\\s]""")',
    'private val normalizeWhitespaceRegex = Regex("""\\s+""")',
    '.replace(normalizeMarksRegex, "")',
    '.replace(normalizeNonAlnumRegex, " ")',
    '.replace(normalizeWhitespaceRegex, " ")',
    'normalizeV35=regexPrecompiled=true | semantics=same | regexCount=3',
    'parserV34=$tdV34ParserDiag',
    'localProofV33=calls=$tdV33LocalCalls',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in (p+s):
        raise SystemExit('PRECOMPILED NORMALIZE REGEX v35 verify failed: '+m)

normalize_start=p.find('    fun normalize(value: String): String {')
normalize_end=p.find('\n    fun extractCage', normalize_start)
segment=p[normalize_start:normalize_end]
for old in ['Regex("""\\p{Mn}+""")','Regex("""[^a-z0-9\\s]""")','Regex("""\\s+""")']:
    if old in segment:
        raise SystemExit('v35 old Regex construction still present in normalize: '+old)

P.write_text(p,encoding='utf-8')
S.write_text(s,encoding='utf-8')
print('PRECOMPILED NORMALIZE REGEX v35 applied: same 3 patterns/order, compiled once; v34 parser diagnostics + v33 proof preserved')
