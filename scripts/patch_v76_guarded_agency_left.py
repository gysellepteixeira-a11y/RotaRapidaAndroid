from pathlib import Path
import re

# V76: guarded experiment for left-shifted Agency columns.
# V75 measured a strong real orange band at 37.99% on Rosario E08.
# Original guard rejects <42% even when color and repeated rows are good.
# Only a narrow 36.5..42% candidate with double-strength column evidence
# and 12+ detected rows may use the existing BAIRRO_FIRST branch.
# Otherwise, preserve the original FULL OCR fallback. The Bairro crop anchor
# must be extended along with the detector's horizontal width gate.

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

def once(src,old,new,label):
    n=src.count(old)
    if n!=1:
        raise RuntimeError("V76 "+label+" expected unique anchor, got "+str(n))
    return src.replace(old,new,1)

fields='''    private var v76LeftShiftAccepted=false
    private var v76LeftShiftReason="NAO_AVALIADO"
    private var v76LeftShiftRows=0
    private var v76BairroAnchorExtended=false

'''
s=once(s,'    private var v75OriginalAgencyRatio=-1f\n',
       fields+'    private var v75OriginalAgencyRatio=-1f\n',"add state")

s=once(s,'        v75OriginalAgencyRatio=-1f\n',
'''        v76LeftShiftAccepted=false
        v76LeftShiftReason="NAO_AVALIADO"
        v76LeftShiftRows=0
        v76BairroAnchorExtended=false
        v75OriginalAgencyRatio=-1f
''',"reset state")

det_sig='    private fun detectLargeTableCrop(source: Bitmap): ColorTableCrop? {'
start=s.index(det_sig); end=s.index('\n    private fun readMediaOriginal(',start)
d=s[start:end]

# V75's original guard must still route through v74RejectDense when the
# narrow-left pattern does not satisfy conservative criteria.
gate=re.compile(
    r'(?s)        if \(agencyRatio < 0\.42f \|\| agencyRatio > 0\.95f\) \{\n'
    r'.*?'
    r'            return v74RejectDense\("AGENCIA_FORA_FAIXA"\)\n'
    r'        \}'
)
m=gate.search(d)
if m is None:
    raise RuntimeError("V76 old V75 Agency range gate missing")
old_gate=m.group(0)
new_gate='''        // V76: DO NOT simply relax 42%; independently check the strength of
        // the existing orange-column peak. Use no extra bitmap reads or OCR.
        val v76LeftNarrow =
            agencyRatio >= 0.365f && agencyRatio < 0.42f &&
            bestHits >= maxOf(36, minColumnHits * 2) &&
            totalHits >= 200 &&
            leftBin <= bestBin
        v76LeftShiftAccepted=v76LeftNarrow
        if(v76LeftNarrow) {
            v76LeftShiftReason="COLUNA_ESQUERDA_ELEGIVEL"
        } else if(agencyRatio < 0.42f) {
            v76LeftShiftReason="ESQUERDA_SEM_PROVAS"
        } else {
            v76LeftShiftReason="LAYOUT_ORIGINAL"
        }

        if ((agencyRatio < 0.42f && !v76LeftNarrow) || agencyRatio > 0.95f) {
            val other=v75InspectRivalAgencyBand(
                xHits,bestBin,bestHits,minColumnHits,xStart,step,w
            )
            v75OtherAgencyRatio=other.ratio
            v75OtherPeakHits=other.hits
            v75OtherStatus=other.status
            return v74RejectDense("AGENCIA_FORA_FAIXA")
        }'''
d=d.replace(old_gate,new_gate,1)

# Horizontal crop width check needs the SAME narrow-left exception; otherwise
# the 39% crop will be rejected even after accepting the candidate.
width_anchor='''if (widthRatio > 0.90f || widthRatio < 0.42f) return v74RejectDense("RECORTE_HORIZONTAL_INVALIDO")'''
if width_anchor not in d:
    raise RuntimeError("V76 horizontal crop guard unexpectedly different")
width_new='''if (widthRatio > 0.90f ||
            (widthRatio < 0.42f && !v76LeftNarrow) ||
            (v76LeftNarrow && widthRatio < 0.375f)
        ) return v74RejectDense("RECORTE_HORIZONTAL_INVALIDO")'''
d=once(d,width_anchor,width_new,"horizontal crop gate")

# Require a robust density of orange-row tokens before a narrow column may
# advance to Bairro OCR. Reuses previously computed rowCount.
success_anchor='''        v74DenseWhy="DETECTOR_APROVADO"
        return ColorTableCrop('''
success_new='''        v76LeftShiftRows=rowCount
        if(v76LeftNarrow && rowCount < 12) {
            v76LeftShiftAccepted=false
            v76LeftShiftReason="COLUNA_ESQUERDA_MENOS_12_LINHAS"
            return v74RejectDense("V76_ESQUERDA_POUCAS_LINHAS")
        }
        v74DenseWhy=if(v76LeftNarrow) "V76_AGENCIA_ESQUERDA_VALIDADA" else "DETECTOR_APROVADO"
        return ColorTableCrop('''
d=once(d,success_anchor,success_new,"row count guard and report")
s=s[:start]+d+s[end:]

# V64 anchors Bairro crop to detected Agency. It previously disqualified
# ratios <42%; for the specifically validated V76 range, this would cut off
# words such as "Rosario" in "Rosario de Fatima". Keep all old geometry on
# standard layouts.
anchor='''        val anchorValid = agencyRatio in 0.42f..0.95f'''
updated='''        val anchorValid = agencyRatio in 0.42f..0.95f ||
            (v76LeftShiftAccepted && agencyRatio in 0.365f..0.42f)
        v76BairroAnchorExtended=v76LeftShiftAccepted && anchorValid'''
s=once(s,anchor,updated,"Bairro crop valid anchor")

# Retain exact V75 and V74 report and add V76 metadata after the send.
a=s.index('    private fun idReport(route:RouteResult){')
b=s.index('\n    private fun ',a+20)
report=s[a:b]
report=once(report,
    '            appendLine("RESUMO")\n',
    '''            appendLine("V76 COLUNA ESQUERDA | elegivel="+v76LeftShiftAccepted+" | motivo="+v76LeftShiftReason+" | linhasValidacao="+v76LeftShiftRows+" | bairroAnchor="+v76BairroAnchorExtended+" | caminho="+tracePathV67)
            appendLine("RESUMO")
''',"V76 report")
s=s[:a]+report+s[b:]

for marker in (
    "V75 AGENCIA CANDIDATA |", "V74 DETECTOR |",
    'V71 SISTEMA APOS ENVIO','V69 GRUPO FECHADO |',
    'showFloatingToggleV52()', 'hasExactNativeRouteProofV70(',
    'isFeuRosaRowV684','ModalFilter.filter(',
    'readMediaOriginalFull(media)','readDenseBairroFirst(',
    'sendRouteInCurrentChat(','ocrWarmV66=true'
):
    if marker not in s:raise RuntimeError("V76 safety marker missing: "+marker)
if 'sendSmsOnlyV664(' in s:raise RuntimeError("V76 unwanted SMS")
if "AGENCIA_FORA_FAIXA" not in s:raise RuntimeError("V76 original fallback gone")
S.write_text(s,encoding="utf-8")
print("V76 guarded left Agency: 36.5-42% with >=36 strong hits and >=12 colored rows.")
print("V76 adjusts Bairro geometric anchor only for verified left shifted columns; old FULL fallback preserved.")
