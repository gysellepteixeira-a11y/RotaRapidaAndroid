from pathlib import Path
import re

# V75: Identify the actual failed Agency column ratio and the strongest
# competing color band without changing ANY OCR/route choice. A rival peak is
# inspected from xHits already collected by the existing detector, and only
# when the original Agency position fails the existing geometry gate.
# The FULL fallback remains untouched until real images validate the idea.

file=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=file.read_text(encoding="utf-8")

def once(src,old,new,name):
    if src.count(old)!=1:
        raise RuntimeError(f"V75 {name}: expected 1 anchor, got {src.count(old)}")
    return src.replace(old,new,1)

fields='''    // V75: shadow-only color-band investigation, never changes send decisions.
    private var v75OriginalAgencyRatio=-1f
    private var v75OriginalPeakHits=0
    private var v75OtherAgencyRatio=-1f
    private var v75OtherPeakHits=0
    private var v75OtherStatus="NAO_NECESSARIA"

    private data class V75RivalBand(
        val ratio:Float,
        val hits:Int,
        val status:String
    )

    // Inspect only the already-created histogram when the original gate fails.
    // No new bitmap reads, OCR requests, crop changes, or accepted fallbacks.
    private fun v75InspectRivalAgencyBand(
        histogram:IntArray,
        originalBestBin:Int,
        originalBestHits:Int,
        minimumColumnHits:Int,
        xStart:Int,
        sampleStep:Int,
        bitmapWidth:Int
    ):V75RivalBand {
        if(bitmapWidth<=0 || sampleStep<=0 || originalBestBin<0)
            return V75RivalBand(-1f,0,"SEM_DADOS")

        val excludeBins=maxOf(8, (bitmapWidth*0.07f/sampleStep).toInt())
        var candidateBin=-1
        var candidateHits=0

        for(bin in histogram.indices){
            if(kotlin.math.abs(bin-originalBestBin)<excludeBins)continue
            val count=histogram[bin]
            if(count<minimumColumnHits)continue
            if(count>candidateHits){
                candidateHits=count
                candidateBin=bin
            }
        }
        if(candidateBin<0)return V75RivalBand(-1f,0,"SEM_PICO_RIVAL_FORTE")

        // Apply the exact same left-edge expansion as the original detector.
        val threshold=maxOf(4,(candidateHits*0.22f).toInt())
        var leftBin=candidateBin
        var consecutiveGaps=0
        var i=candidateBin-1
        while(i>=0){
            if(histogram[i]>=threshold){
                leftBin=i
                consecutiveGaps=0
            }else{
                consecutiveGaps++
                if(consecutiveGaps>=3)break
            }
            i--
        }

        val leftRatio=(xStart+leftBin*sampleStep).toFloat()/bitmapWidth
        val separated=kotlin.math.abs(candidateBin-originalBestBin)>=excludeBins
        val strong=candidateHits>=maxOf(minimumColumnHits,(originalBestHits*0.65f).toInt())

        // This label is NOT proof that a crop is correct. Additional independent
        // checks and real-image comparison are required before ever using it.
        val status=if(
            separated && strong && leftRatio in 0.42f..0.90f
        )"RIVAL_PLAUSIVEL_SOMENTE_DIAGNOSTICO" else "RIVAL_INCONCLUSIVO"

        return V75RivalBand(leftRatio,candidateHits,status)
    }

'''
s=once(s,'    private var v74DenseWhy="NAO_TENTADO"\n',fields+'    private var v74DenseWhy="NAO_TENTADO"\n',"state insert")

reset='''        v74DenseWhy="NAO_TENTADO"
'''
s=once(s,reset,reset+'''        v75OriginalAgencyRatio=-1f
        v75OriginalPeakHits=0
        v75OtherAgencyRatio=-1f
        v75OtherPeakHits=0
        v75OtherStatus="NAO_NECESSARIA"
''',"reset")

det_signature='    private fun detectLargeTableCrop(source: Bitmap): ColorTableCrop? {'
begin=s.index(det_signature)
end=s.index('\n    private fun readMediaOriginal(',begin)
det=s[begin:end]

ratio_anchor='''        val agencyRatio = agencyLeft.toFloat() / w.toFloat()
'''
det=once(det,ratio_anchor,ratio_anchor+'''        // Capture the rejected candidate BEFORE the range guard (V74 showed 0%).
        v75OriginalAgencyRatio=agencyRatio
        v75OriginalPeakHits=bestHits
''',"capture original candidate")

gate_regex=re.compile(
    r'(?m)^([ \t]*)if\s*\(\s*agencyRatio\s*<\s*([0-9.]+)f\s*\|\|\s*agencyRatio\s*>\s*([0-9.]+)f\s*\)\s*return v74RejectDense\("AGENCIA_FORA_FAIXA"\)\s*$'
)
gate=gate_regex.search(det)
if gate is None:
    ix=det.find('AGENCIA_FORA_FAIXA')
    raise RuntimeError("V75 agency range gate not located; excerpt="+det[max(0,ix-170):ix+100])
indent=gate.group(1)
lower=gate.group(2)
upper=gate.group(3)
new_gate='''{indent}if (agencyRatio < {lower}f || agencyRatio > {upper}f) {{
{indent}    val other=v75InspectRivalAgencyBand(
{indent}        xHits,bestBin,bestHits,minColumnHits,xStart,step,w
{indent}    )
{indent}    v75OtherAgencyRatio=other.ratio
{indent}    v75OtherPeakHits=other.hits
{indent}    v75OtherStatus=other.status
{indent}    return v74RejectDense("AGENCIA_FORA_FAIXA")
{indent}}}
'''.format(indent=indent,lower=lower,upper=upper)
det=det[:gate.start()]+new_gate+det[gate.end():]
if 'return v74RejectDense("AGENCIA_FORA_FAIXA")' not in det:
    raise RuntimeError("V75 original rejection is not preserved")
if "return ColorTableCrop(" not in det or 'val detected = detectLargeTableCrop(source)' not in s:
    raise RuntimeError("V75 detector's regular success path missing")
s=s[:begin]+det+s[end:]

r0=s.index('    private fun idReport(route:RouteResult){')
r1=s.index('\n    private fun ',r0+20)
rep=s[r0:r1]
needle='''            appendLine("RESUMO")
'''
replacement='''            appendLine("V75 AGENCIA CANDIDATA | original="+(if(v75OriginalAgencyRatio<0f) "indisponivel" else String.format(java.util.Locale.US,"%.2f",v75OriginalAgencyRatio*100f)+"%")+" | pico="+v75OriginalPeakHits+" | rival="+(if(v75OtherAgencyRatio<0f) "indisponivel" else String.format(java.util.Locale.US,"%.2f",v75OtherAgencyRatio*100f)+"%")+" | picoRival="+v75OtherPeakHits+" | validacao="+v75OtherStatus+" | decisaoOCR=V74_SEM_ALTERACAO")
            appendLine("RESUMO")
'''
rep=once(rep,needle,replacement,"report")
s=s[:r0]+rep+s[r1:]

for marker in (
    'V74 DETECTOR |','V71 SISTEMA APOS ENVIO',
    'V69 GRUPO FECHADO |','showFloatingToggleV52()',
    'isFeuRosaRowV684','hasExactNativeRouteProofV70(',
    'ModalFilter.filter(','readMediaOriginalFull(media)',
    'sendRouteInCurrentChat(','ocrWarmV66=true'
):
    if marker not in s:
        raise RuntimeError("V75 prior feature missing: "+marker)
if 'sendSmsOnlyV664(' in s:
    raise RuntimeError("V75 unexpected SMS path")
file.write_text(s,encoding="utf-8")
print("V75: captured original Agency ratio before rejection; rival color peak from existing histogram only.")
print("V75: thresholds unchanged, original range:",lower,"to",upper,"; no OCR routing or sending changes.")
