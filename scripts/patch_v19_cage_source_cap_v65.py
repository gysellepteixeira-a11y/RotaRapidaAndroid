from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

# v65: crop da Gaiola limitado pela largura ORIGINAL da imagem.
# Motivo observado nos testes reais:
# - quando Agency estava ~47-50%, OCR da Gaiola ficou ~31-40ms;
# - quando Agency estava ~58-59%, o recorte legado de 11.5% do denseBitmap
#   ficava fisicamente mais largo e o OCR subia para ~60-79ms.
# O cap de 5.2% da largura original foi validado geometricamente nas imagens
# reais fornecidas: todas as gaiolas permaneceram inteiras, sem precisar ler AT/TO.
# Fallback/extração/parsers/envio permanecem idênticos.

# Estado com widthRatio da imagem densa atual + diagnóstico.
field_old='''    private var idAgencyAnchorV64=false; private var idAgencyRatioV64=0f; private var idBairroBandPxV64=0
    private var lastDenseRecoveryDebug = ""
'''
field_new='''    private var idAgencyAnchorV64=false; private var idAgencyRatioV64=0f; private var idBairroBandPxV64=0
    private var lastDenseWidthRatioV65=0f; private var idCageBandPxV65=0; private var idCageDenseRatioV65=0f
    private var lastDenseRecoveryDebug = ""
'''
if field_old not in s:
    raise SystemExit("v65 diagnostic fields anchor missing")
s=s.replace(field_old,field_new,1)

# Guarda a proporção original->dense assim que o detector fechou a tabela.
anchor='''        val decodeMs = SystemClock.elapsedRealtime() - decodeStarted
        val detected = detectLargeTableCrop(source)

        if (detected == null) {
'''
replacement='''        val decodeMs = SystemClock.elapsedRealtime() - decodeStarted
        val detected = detectLargeTableCrop(source)

        if (detected != null) {
            lastDenseWidthRatioV65 = detected.widthRatio
        }

        if (detected == null) {
'''
if anchor not in s:
    raise SystemExit("v65 detected anchor missing")
s=s.replace(anchor,replacement,1)

# Troca somente a largura do slice da Gaiola.
old_width='''        val sliceWidth = maxOf(52, (denseBitmap.width * 0.115f).toInt())
            .coerceAtMost(denseBitmap.width)
'''
new_width='''        val legacyDenseRatioV65 = 0.115f
        val sourceCapRatioV65 = 0.052f
        val denseWidthRatioV65 = lastDenseWidthRatioV65
            .takeIf { it in 0.42f..0.90f }
            ?: 0f

        val cageDenseRatioV65 = if (denseWidthRatioV65 > 0f) {
            minOf(
                legacyDenseRatioV65,
                (sourceCapRatioV65 / denseWidthRatioV65)
                    .coerceAtLeast(0.055f)
            )
        } else {
            legacyDenseRatioV65
        }

        val sliceWidth = maxOf(52, (denseBitmap.width * cageDenseRatioV65).toInt())
            .coerceAtMost(denseBitmap.width)

        idCageBandPxV65 = sliceWidth
        idCageDenseRatioV65 = cageDenseRatioV65
'''
if old_width not in s:
    raise SystemExit("v65 cage width anchor missing")
s=s.replace(old_width,new_width,1)

# Reset do diagnóstico.
reset_old='''        idAgencyAnchorV64=false; idAgencyRatioV64=0f; idBairroBandPxV64=0
    }
'''
reset_new='''        idAgencyAnchorV64=false; idAgencyRatioV64=0f; idBairroBandPxV64=0
        idCageBandPxV65=0; idCageDenseRatioV65=0f
    }
'''
if reset_old not in s:
    raise SystemExit("v65 reset anchor missing")
s=s.replace(reset_old,reset_new,1)

# Linha de diagnóstico após a Gaiola.
report_old='''            if(idCage>0L) appendLine("[${idA(idCage)}] Gaiola: $idCageText | OCR=${idCageOcr}ms")
'''
report_new='''            if(idCage>0L) appendLine("[${idA(idCage)}] Gaiola: $idCageText | OCR=${idCageOcr}ms")
            if(idCageBandPxV65>0) appendLine("cageCropV65=true | band=${idCageBandPxV65}px | dense=${String.format(java.util.Locale.US, "%.1f", idCageDenseRatioV65*100f)}% | sourceCap=5.2%")
'''
if report_old not in s:
    raise SystemExit("v65 report anchor missing")
s=s.replace(report_old,report_new,1)

old_title='===== DIAGNOSTICO IMAGEM v19 | V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
new_title='===== DIAGNOSTICO IMAGEM v19 | V65 CAGE SOURCE CAP + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
if old_title not in s:
    raise SystemExit("v65 title anchor missing")
s=s.replace(old_title,new_title,1)

for m in [
    'sourceCapRatioV65 = 0.052f',
    'lastDenseWidthRatioV65 = detected.widthRatio',
    'cageCropV65=true',
    'sourceCap=5.2%',
    'legacyDenseRatioV65 = 0.115f',
]:
    if m not in s:
        raise SystemExit("v65 verify failed: "+m)

S.write_text(s,encoding="utf-8")
print("v65 aplicado: Gaiola limitada a no maximo 5.2% da largura original; v64 e fallbacks preservados")
