from pathlib import Path

# Isolated A/B experiment: only 100..179px images change dispatch.
# Keep the original V76 gates, including the 12-row left-Agency guard.
p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")
def once(src, old, new):
    assert src.count(old)==1, ("V77 anchor",old,src.count(old))
    return src.replace(old,new,1)

s=once(s,'if (media.height >= 180) {','if (media.height >= 100) {')
s=once(s,'if (w < 500 || h < 180) return v74RejectDense("DIMENSOES")',
         'if (w < 500 || h < 100) return v74RejectDense("DIMENSOES")')
s=once(s,'        if (detected.rowCount < DENSE_MIN_ROWS) {\n            v74DenseWhy="POUCAS_LINHAS_" + detected.rowCount + "_MIN_" + DENSE_MIN_ROWS',
'''        val v77ShortTable = media.height in 100..179 && source.height in 100..179
        val v77MinRows = if (v77ShortTable) 6 else DENSE_MIN_ROWS
        if (detected.rowCount < v77MinRows) {
            v74DenseWhy="POUCAS_LINHAS_" + detected.rowCount + "_MIN_" + v77MinRows''')
s=once(s,'    private var v76LeftShiftAccepted=false\n','    private var v77ShortCandidate=false\n    private var v77EffectiveMinRows=8\n    private var v76LeftShiftAccepted=false\n')
s=once(s,'        v76LeftShiftAccepted=false\n        v76LeftShiftReason="NAO_AVALIADO"',
         '        v77ShortCandidate=false\n        v77EffectiveMinRows=8\n        v76LeftShiftAccepted=false\n        v76LeftShiftReason="NAO_AVALIADO"')
s=once(s,'        v74DenseWhy="DECODIFICANDO"','        v77ShortCandidate=media.height in 100..179\n        v74DenseWhy="DECODIFICANDO"')
s=once(s,'        if (detected.rowCount < v77MinRows) {','        v77EffectiveMinRows=v77MinRows\n        if (detected.rowCount < v77MinRows) {')
a=s.index('    private fun idReport(route:RouteResult){')
b=s.index('\n    private fun ',a+20)
report=s[a:b]
report=once(report,'            appendLine("RESUMO")\n',
'''            appendLine("V77 TABELA CURTA | candidata="+v77ShortCandidate+" | minimoEfetivo="+v77EffectiveMinRows+" | linhas="+v74DetectedRows+" | caminho="+tracePathV67)
            appendLine("RESUMO")\n''')
s=s[:a]+report+s[b:]
assert 'v76LeftNarrow && rowCount < 12' in s
assert 'readMediaOriginalFull(media)' in s
assert 'ModalFilter.filter(' in s and 'isFeuRosaRowV684' in s
p.write_text(s,encoding="utf-8")
print("V77 short table experiment: 100..179px, minimum 6 rows; V76 fallback and guards retained")
