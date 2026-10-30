from pathlib import Path
import re

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

# v64: reutiliza a posicao da coluna Agency que o detector colorido JA calculou.
# Nenhum OCR extra e nenhum scan extra: apenas reduz a faixa horizontal enviada
# ao OCR de Bairro. Se algo fugir do esperado, usa exatamente o crop legado v61.

# 1) Carrega agencyRatio junto do ColorTableCrop.
old_data='''    private data class ColorTableCrop(
        val bitmap: Bitmap,
        val widthRatio: Float,
        val scanMs: Long,
        val rowCount: Int
    )
'''
new_data='''    private data class ColorTableCrop(
        val bitmap: Bitmap,
        val widthRatio: Float,
        val scanMs: Long,
        val rowCount: Int,
        val agencyRatio: Float
    )
'''
if old_data not in s:
    raise SystemExit("v64 ColorTableCrop anchor missing")
s=s.replace(old_data,new_data,1)

old_ret='''        return ColorTableCrop(
            bitmap = crop,
            widthRatio = widthRatio,
            scanMs = SystemClock.elapsedRealtime() - started,
            rowCount = rowCount
        )
'''
new_ret='''        return ColorTableCrop(
            bitmap = crop,
            widthRatio = widthRatio,
            scanMs = SystemClock.elapsedRealtime() - started,
            rowCount = rowCount,
            agencyRatio = agencyRatio
        )
'''
if old_ret not in s:
    raise SystemExit("v64 detector return anchor missing")
s=s.replace(old_ret,new_ret,1)

# 2) readDenseBairroFirst recebe o anchor ja calculado.
start=s.find('    private fun readDenseBairroFirst(')
end=s.find('\n    private fun readDenseFullFallback(',start)
if start<0 or end<0:
    raise SystemExit("v64 readDenseBairroFirst bounds missing")
block=s[start:end]

sig_old='''        widthRatio: Float,
        decodeMs: Long,
'''
sig_new='''        widthRatio: Float,
        agencyRatio: Float,
        decodeMs: Long,
'''
if sig_old not in block:
    raise SystemExit("v64 signature anchor missing")
block=block.replace(sig_old,sig_new,1)

legacy='''        val safeWidthRatio = widthRatio.coerceIn(0.42f, 0.90f)
        val leftRatio = (0.270f / safeWidthRatio).coerceIn(0.45f, 0.72f)
        val rightRatio = 0.975f
            .coerceAtLeast(leftRatio + 0.16f)

        val x1 = (denseBitmap.width * leftRatio).toInt()
            .coerceIn(0, denseBitmap.width - 2)
        val x2 = (denseBitmap.width * rightRatio).toInt()
            .coerceIn(x1 + 2, denseBitmap.width)
        val bairroWidth = x2 - x1
'''
anchored='''        val safeWidthRatio = widthRatio.coerceIn(0.42f, 0.90f)

        // v64: nas imagens reais a coluna Agency colorida e um anchor muito mais
        // estavel que uma coordenada fixa. O detector acima ja encontrou agencyRatio.
        // Testes geometricos nas rotas reais mostraram:
        // 18% ainda cortou Rosário de Fátima no teste real; ampliar para 28% sem adicionar uma segunda leitura.
        val anchorValid = agencyRatio in 0.42f..0.95f
        val leftRatio: Float
        val rightRatio: Float

        if (anchorValid) {
            val agencyInDense = (agencyRatio / safeWidthRatio)
                .coerceIn(0.20f, 0.995f)
            val bandInDense = (0.28f / safeWidthRatio)
            leftRatio = (agencyInDense - bandInDense)
                .coerceIn(0.02f, 0.94f)
            rightRatio = agencyInDense
                .coerceIn(leftRatio + 0.12f, 0.995f)
        } else {
            // Fallback byte-for-byte equivalente ao criterio v61.
            leftRatio = (0.270f / safeWidthRatio).coerceIn(0.45f, 0.72f)
            rightRatio = 0.975f
                .coerceAtLeast(leftRatio + 0.16f)
        }

        val x1 = (denseBitmap.width * leftRatio).toInt()
            .coerceIn(0, denseBitmap.width - 2)
        val x2 = (denseBitmap.width * rightRatio).toInt()
            .coerceIn(x1 + 2, denseBitmap.width)
        val bairroWidth = x2 - x1
'''
if legacy not in block:
    raise SystemExit("v64 legacy crop block missing")
block=block.replace(legacy,anchored,1)
s=s[:start]+block+s[end:]

# 3) Passa agencyRatio no unico call-site do caminho denso.
call_old='''            widthRatio = detected.widthRatio,
            decodeMs = decodeMs,
            scanMs = detected.scanMs
'''
call_new='''            widthRatio = detected.widthRatio,
            agencyRatio = detected.agencyRatio,
            decodeMs = decodeMs,
            scanMs = detected.scanMs
'''
if call_old not in s:
    raise SystemExit("v64 readDenseBairroFirst call anchor missing")
s=s.replace(call_old,call_new,1)

# 4) Diagnostico pequeno para confirmar o crop usado.
field_old='''    private var idEditorVisitedV48=0; private var idEditorLookupMsV48=0L
    private var lastDenseRecoveryDebug = ""
'''
field_new='''    private var idEditorVisitedV48=0; private var idEditorLookupMsV48=0L
    private var idAgencyAnchorV64=false; private var idAgencyRatioV64=0f; private var idBairroBandPxV64=0
    private var lastDenseRecoveryDebug = ""
'''
if field_old not in s:
    raise SystemExit("v64 diagnostic fields anchor missing")
s=s.replace(field_old,field_new,1)

# Seta diagnostico assim que o crop foi definido.
set_anchor='''        val bairroWidth = x2 - x1

        if (bairroWidth < 80) {
'''
set_new='''        val bairroWidth = x2 - x1

        idAgencyAnchorV64 = anchorValid
        idAgencyRatioV64 = agencyRatio
        idBairroBandPxV64 = bairroWidth

        if (bairroWidth < 80) {
'''
if set_anchor not in s:
    raise SystemExit("v64 diagnostic set anchor missing")
s=s.replace(set_anchor,set_new,1)

reset_old='''        idEditorFastV48=false; idEditorFallbackV48=false; idEditorVisitedV48=0; idEditorLookupMsV48=0L
    }
'''
reset_new='''        idEditorFastV48=false; idEditorFallbackV48=false; idEditorVisitedV48=0; idEditorLookupMsV48=0L
        idAgencyAnchorV64=false; idAgencyRatioV64=0f; idBairroBandPxV64=0
    }
'''
if reset_old not in s:
    raise SystemExit("v64 reset anchor missing")
s=s.replace(reset_old,reset_new,1)

report_old='''            if(idBairro>0L) appendLine("[${idA(idBairro)}] Bairro: $idNeighborhood | OCR=${idBairroOcr}ms | decode=${idDecode}ms | scan=${idScan}ms")
            if(idCage>0L) appendLine("[${idA(idCage)}] Gaiola: $idCageText | OCR=${idCageOcr}ms")
'''
report_new='''            if(idBairro>0L) appendLine("[${idA(idBairro)}] Bairro: $idNeighborhood | OCR=${idBairroOcr}ms | decode=${idDecode}ms | scan=${idScan}ms")
            if(idAgencyAnchorV64) appendLine("agencyAnchorV64=true | agency=${String.format(java.util.Locale.US, "%.1f", idAgencyRatioV64*100f)}% | bairroBand=${idBairroBandPxV64}px | sourceBand=28%")
            if(idCage>0L) appendLine("[${idA(idCage)}] Gaiola: $idCageText | OCR=${idCageOcr}ms")
'''
if report_old not in s:
    raise SystemExit("v64 report anchor missing")
s=s.replace(report_old,report_new,1)

old_title='===== DIAGNOSTICO IMAGEM v19 | V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
new_title='===== DIAGNOSTICO IMAGEM v19 | V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
if old_title not in s:
    raise SystemExit("v64 diagnostic title missing")
s=s.replace(old_title,new_title,1)

for m in [
    'val agencyRatio: Float',
    'agencyRatio = agencyRatio',
    'agencyRatio: Float,',
    'val bandInDense = (0.18f / safeWidthRatio)',
    'agencyAnchorV64=true',
    'sourceBand=18%',
]:
    if m not in s:
        raise SystemExit("v64 verify failed: "+m)

S.write_text(s,encoding="utf-8")
print("v64 aplicado: crop Bairro ancorado na Agency ja detectada; 28% da largura original; fallback v61 preservado")
