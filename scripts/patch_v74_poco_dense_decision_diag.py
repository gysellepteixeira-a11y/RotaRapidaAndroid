from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
P=Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
s=S.read_text(encoding="utf-8")
p=P.read_text(encoding="utf-8")
r=R.read_text(encoding="utf-8")

def once(src, old, new, label):
    if src.count(old)!=1:
        raise RuntimeError("V74 anchor "+label+" missing or repeated: "+str(src.count(old)))
    return src.replace(old,new,1)

# Fresh installs use the user's six priorities; custom saved lists still win.
new_list='''        "Eurico",
        "Rosario",
        "Manoel Plaza",
        "Mata da Praia",
        "Praia da Baleia",
        "Morada de Laranjeiras"'''
start=p.index('    private val DEFAULT_NEIGHBORHOODS_V55 = listOf(')
end=p.index('\n    )',start)+len('\n    )')
p=p[:start]+'''    private val DEFAULT_NEIGHBORHOODS_V55 = listOf(
'''+new_list+'''
    )'''+p[end:]
start=r.index('    @Volatile\n    private var priorities: List<PriorityRule> = listOf(')
end=r.index('\n    ).map(::buildPriorityRuleV55)',start)+len('\n    ).map(::buildPriorityRuleV55)')
r=r[:start]+'''    @Volatile
    private var priorities: List<PriorityRule> = listOf(
'''+new_list+'''
    ).map(::buildPriorityRuleV55)'''+r[end:]

fields='''    private var v74DenseWhy="NAO_TENTADO"
    private var v74DetectedRows=0
    private var v74AgencyRatio=0f
    private var v74FallbackReason=""

'''
s=once(s,'    private var tracePathV67=""',fields+'    private var tracePathV67=""',"fields")
s=once(s,'        tracePathV67=""\n','''        tracePathV67=""
        v74DenseWhy="NAO_TENTADO"
        v74DetectedRows=0
        v74AgencyRatio=0f
        v74FallbackReason=""
''',"reset")

detSig='    private fun detectLargeTableCrop(source: Bitmap): ColorTableCrop? {'
helper='''    private fun v74RejectDense(reason:String):ColorTableCrop? {
        v74DenseWhy=reason
        return null
    }

'''
s=once(s,detSig,helper+detSig,"helper")
b0=s.index(detSig); b1=s.index('\n    private fun readMediaOriginal(',b0)
b=s[b0:b1]
lines=b.splitlines(keepends=True)
n=0
for i,line in enumerate(lines):
    if 'return null' not in line:continue
    n+=1
    v=line.lower()
    if "w <" in v or "h <" in v: reason="DIMENSOES"
    elif "totalhits" in v: reason="COR_INSUFICIENTE"
    elif "bestbin" in v or "besthits" in v:reason="AGENCIA_COLUNA_FRACA"
    elif "agencyratio" in v:reason="AGENCIA_FORA_FAIXA"
    elif "widthratio" in v:reason="RECORTE_HORIZONTAL_INVALIDO"
    elif "bandhits" in v or "maxcolory" in v:reason="BANDA_COR_INSUFICIENTE"
    elif "cropheight" in v:reason="RECORTE_VERTICAL_PEQUENO"
    elif "rowcount" in v:reason="LINHAS_NAO_CONFIRMADAS"
    else:reason="RETORNO_"+str(n)
    lines[i]=line.replace('return null','return v74RejectDense("'+reason+'")',1)
if n<5:raise RuntimeError("V74 detector returns fewer than expected: "+str(n))
b=''.join(lines)
b=once(b,'        return ColorTableCrop(\n',
'''        v74DenseWhy="DETECTOR_APROVADO"
        return ColorTableCrop(
''',"detector success")
s=s[:b0]+b+s[b1:]

b0=s.index('    private fun readMediaLargeColorCrop(media: MediaImage) {')
b1=s.index('\n    private fun readDenseCageOnly(',b0)
b=s[b0:b1]
b=once(b,'        val decodeStarted = SystemClock.elapsedRealtime()\n',
'''        v74DenseWhy="DECODIFICANDO"
        val decodeStarted = SystemClock.elapsedRealtime()
''',"decode start")
b=once(b,'''        if (source == null) {
            readMediaOriginalFull(media)
''','''        if (source == null) {
            v74DenseWhy="DECODIFICACAO_FALHOU"
            readMediaOriginalFull(media)
''',"decode fail")
b=once(b,'        val detected = detectLargeTableCrop(source)\n',
'''        val detected = detectLargeTableCrop(source)
        v74DetectedRows=detected?.rowCount ?: 0
        v74AgencyRatio=detected?.agencyRatio ?: 0f
''',"detector details")
b=once(b,'        if (detected.rowCount < DENSE_MIN_ROWS) {\n',
'''        if (detected.rowCount < DENSE_MIN_ROWS) {
            v74DenseWhy="POUCAS_LINHAS_" + detected.rowCount + "_MIN_" + DENSE_MIN_ROWS
''',"row guard")
b=once(b,'        var crop = detected.bitmap\n',
'''        v74DenseWhy="DENSO_APROVADO_" + detected.rowCount + "_LINHAS"
        var crop = detected.bitmap
''',"dense approved")
s=s[:b0]+b+s[b1:]

fb0=s.index('    private fun readDenseFullFallback(')
fb1=s.index('\n    private fun ',fb0+15)
fb=s[fb0:fb1]
if 'reason: String' not in fb and 'reason:String' not in fb:
    raise RuntimeError("V74 dense fallback reason parameter not found")
index=fb.find('    ) {\n')
if index<0:raise RuntimeError("V74 fallback body missing")
index+=len('    ) {\n')
fb=fb[:index]+'        v74FallbackReason=reason\n'+fb[index:]
s=s[:fb0]+fb+s[fb1:]

r0=s.index('    private fun idReport(route:RouteResult){')
r1=s.index('\n    private fun ',r0+20)
rep=s[r0:r1]
rep=once(rep,'            appendLine("RESUMO")\n',
'''            appendLine("V74 DETECTOR | motivo="+v74DenseWhy+" | linhas="+v74DetectedRows+" | minimo="+DENSE_MIN_ROWS+" | agencia="+(v74AgencyRatio*100f)+"% | fallback="+(if(v74FallbackReason.isBlank()) "nao" else v74FallbackReason))
            appendLine("RESUMO")
''',"report")
s=s[:r0]+rep+s[r1:]
for marker in ['showFloatingToggleV52(', 'V71 SISTEMA APOS ENVIO',
               'V69 GRUPO FECHADO |','ModalFilter.filter(',
               'isFeuRosaRowV684','hasExactNativeRouteProofV70(',
               'sendRouteInCurrentChat(','ocrWarmV66=true']:
    if marker not in s:raise RuntimeError("V74 prior feature missing: "+marker)
if 'sendSmsOnlyV664(' in s:raise RuntimeError("V74 unwanted SMS")
S.write_text(s,encoding="utf-8")
P.write_text(p,encoding="utf-8")
R.write_text(r,encoding="utf-8")
print("V74 diagnostics on "+str(n)+" detector rejection sites; no routing decisions modified.")
print("New default priority order: Eurico, Rosario, Manoel Plaza, Mata da Praia, Praia da Baleia, Morada de Laranjeiras.")
