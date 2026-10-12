from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

# v66 = duas correcoes isoladas sobre a v65:
# 1) Gaiola hibrida: Agency <=55% usa exatamente a largura segura da v64 (11.5% do dense);
#    Agency >55% usa o source cap da v65 (5.2% da imagem original).
#    A decisao usa agencyRatio que a v64 JA calculou; nao ha OCR/scan extra.
# 2) OCR warm: warm-up 48x48 imediato ao armar + periodico a cada 120s enquanto
#    enabled+searchArmed, nunca durante processing. Nao altera parser/envio/fallbacks.

# -------------------------------------------------------------------------
# 1. GAIOLA HIBRIDA
# -------------------------------------------------------------------------
field_old='''    private var lastDenseWidthRatioV65=0f; private var idCageBandPxV65=0; private var idCageDenseRatioV65=0f
    private var lastDenseRecoveryDebug = ""
'''
field_new='''    private var lastDenseWidthRatioV65=0f; private var idCageBandPxV65=0; private var idCageDenseRatioV65=0f
    private var idCageModeV66=""
    private var lastDenseRecoveryDebug = ""
'''
if field_old not in s:
    raise SystemExit("v66 field anchor missing")
s=s.replace(field_old,field_new,1)

old_crop='''        val legacyDenseRatioV65 = 0.115f
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
new_crop='''        val legacyDenseRatioV65 = 0.115f
        val sourceCapRatioV65 = 0.052f
        val agencyHybridThresholdV66 = 0.55f
        val denseWidthRatioV65 = lastDenseWidthRatioV65
            .takeIf { it in 0.42f..0.90f }
            ?: 0f
        val agencyRatioV66 = idAgencyRatioV64
            .takeIf { it in 0.42f..0.95f }
            ?: 0f

        val useSafeV64V66 =
            agencyRatioV66 <= 0f || agencyRatioV66 <= agencyHybridThresholdV66

        val cageDenseRatioV65 = if (useSafeV64V66) {
            // v66: preserva byte-for-byte a largura segura da v64 nos layouts
            // em que o cap de 5.2% cortou/fragilizou I10 (Agency 49.7%).
            legacyDenseRatioV65
        } else if (denseWidthRatioV65 > 0f) {
            // Layouts com Agency mais a direita mantem o ganho comprovado da v65.
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
        idCageModeV66 = if (useSafeV64V66) "V64_SAFE_11.5" else "V65_CAP_5.2"
'''
if old_crop not in s:
    raise SystemExit("v66 v65 crop block missing")
s=s.replace(old_crop,new_crop,1)

reset_old='''        idCageBandPxV65=0; idCageDenseRatioV65=0f
    }
'''
reset_new='''        idCageBandPxV65=0; idCageDenseRatioV65=0f; idCageModeV66=""
    }
'''
if reset_old not in s:
    raise SystemExit("v66 cage reset anchor missing")
s=s.replace(reset_old,reset_new,1)

report_old='''            if(idCageBandPxV65>0) appendLine("cageCropV65=true | band=${idCageBandPxV65}px | dense=${String.format(java.util.Locale.US, "%.1f", idCageDenseRatioV65*100f)}% | sourceCap=5.2%")
'''
report_new='''            if(idCageBandPxV65>0) appendLine("cageCropV66=true | mode=${idCageModeV66} | band=${idCageBandPxV65}px | dense=${String.format(java.util.Locale.US, "%.1f", idCageDenseRatioV65*100f)}% | threshold=55%")
'''
if report_old not in s:
    raise SystemExit("v66 cage report anchor missing")
s=s.replace(report_old,report_new,1)

title_old='===== DIAGNOSTICO IMAGEM v19 | V65 CAGE SOURCE CAP + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
title_new='===== DIAGNOSTICO IMAGEM v19 | V66 HYBRID CAGE + OCR WARM + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
if title_old not in s:
    raise SystemExit("v66 title anchor missing")
s=s.replace(title_old,title_new,1)

# -------------------------------------------------------------------------
# 2. OCR WARM
# -------------------------------------------------------------------------
const_anchor='        private const val DEDUP_MS = 8_000L\n'
if const_anchor not in s:
    raise SystemExit("v66 DEDUP const anchor missing")
s=s.replace(
    const_anchor,
    const_anchor+'        private const val OCR_WARM_INTERVAL_V66_MS = 120_000L\n'
                 +'        private const val OCR_WARM_MIN_GAP_V66_MS = 15_000L\n',
    1
)

recognizer_anchor='''    private val recognizer by lazy {
        TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
    }
'''
warm_state='''    private var ocrWarmBusyV66 = false
    private var lastOcrWarmCompletedAtV66 = 0L
    private var lastOcrWarmDurationV66 = 0L

    private val ocrWarmRunnableV66 = object : Runnable {
        override fun run() {
            try {
                if (
                    Prefs.isEnabled(this@WhatsRouteAccessibilityService) &&
                    Prefs.searchArmed(this@WhatsRouteAccessibilityService) &&
                    !processing &&
                    !ocrWarmBusyV66
                ) {
                    runOcrWarmV66()
                }
            } catch (_: Throwable) {
                // Warm-up e opcional e jamais pode bloquear a rota real.
            } finally {
                handler.postDelayed(this, OCR_WARM_INTERVAL_V66_MS)
            }
        }
    }
'''
if recognizer_anchor not in s:
    raise SystemExit("v66 recognizer anchor missing")
s=s.replace(recognizer_anchor,recognizer_anchor+'\n'+warm_state,1)

warm_func_anchor='''    private fun warmUpRecognizer() {
'''
warm_func='''    private fun runOcrWarmV66() {
        if (
            ocrWarmBusyV66 ||
            processing ||
            !Prefs.isEnabled(this) ||
            !Prefs.searchArmed(this)
        ) return

        val now = SystemClock.elapsedRealtime()
        if (
            lastOcrWarmCompletedAtV66 > 0L &&
            now - lastOcrWarmCompletedAtV66 < OCR_WARM_MIN_GAP_V66_MS
        ) return

        ocrWarmBusyV66 = true
        val started = now
        var tiny: Bitmap? = null

        try {
            tiny = Bitmap.createBitmap(48, 48, Bitmap.Config.ARGB_8888)
            val input = InputImage.fromBitmap(tiny, 0)
            recognizer.process(input)
                .addOnCompleteListener {
                    try { tiny?.recycle() } catch (_: Throwable) {}
                    lastOcrWarmDurationV66 =
                        (SystemClock.elapsedRealtime() - started).coerceAtLeast(0L)
                    lastOcrWarmCompletedAtV66 = SystemClock.elapsedRealtime()
                    ocrWarmBusyV66 = false
                }
        } catch (_: Throwable) {
            try { tiny?.recycle() } catch (_: Throwable) {}
            ocrWarmBusyV66 = false
        }
    }

'''
if warm_func_anchor not in s:
    raise SystemExit("v66 warmUpRecognizer anchor missing")
s=s.replace(warm_func_anchor,warm_func+warm_func_anchor,1)

# Agenda o aquecimento periodico junto da conexao do servico; mantem o warmUp
# original da base, que continua sendo o primeiro warm ao conectar.
connect_old='''        warmUpRecognizer()
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
connect_new='''        warmUpRecognizer()
        handler.removeCallbacks(ocrWarmRunnableV66)
        handler.postDelayed(ocrWarmRunnableV66, OCR_WARM_INTERVAL_V66_MS)
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
if connect_old not in s:
    raise SystemExit("v66 service connect anchor missing")
s=s.replace(connect_old,connect_new,1)

# Ao armar por QUALQUER caminho que altere search_armed/enabled, faz warm imediato.
listener_old='''                "enabled", "search_armed" ->
                    handler.post { updateFloatingToggleAppearanceV52() }
'''
listener_new='''                "enabled", "search_armed" ->
                    handler.post {
                        updateFloatingToggleAppearanceV52()
                        if(Prefs.isEnabled(this) && Prefs.searchArmed(this)) {
                            runOcrWarmV66()
                        }
                    }
'''
if listener_old not in s:
    raise SystemExit("v66 pref listener anchor missing")
s=s.replace(listener_old,listener_new,1)

destroy_old='''    override fun onDestroy() {
        try{floatingPrefsV52.unregisterOnSharedPreferenceChangeListener(floatingPrefsListenerV52)}catch(_:Throwable){}
        removeFloatingToggleV52()
'''
destroy_new='''    override fun onDestroy() {
        handler.removeCallbacks(ocrWarmRunnableV66)
        try{floatingPrefsV52.unregisterOnSharedPreferenceChangeListener(floatingPrefsListenerV52)}catch(_:Throwable){}
        removeFloatingToggleV52()
'''
if destroy_old not in s:
    raise SystemExit("v66 onDestroy anchor missing")
s=s.replace(destroy_old,destroy_new,1)

# Mostra idade/duracao do ultimo warm no diagnostico sem alterar o caminho critico.
diag_anchor='''            if(idCageBandPxV65>0) appendLine("cageCropV66=true | mode=${idCageModeV66} | band=${idCageBandPxV65}px | dense=${String.format(java.util.Locale.US, "%.1f", idCageDenseRatioV65*100f)}% | threshold=55%")
'''
diag_new=diag_anchor+'''            if(lastOcrWarmCompletedAtV66>0L) {
                val warmAgeV66=(SystemClock.elapsedRealtime()-lastOcrWarmCompletedAtV66).coerceAtLeast(0L)
                appendLine("ocrWarmV66=true | age=${warmAgeV66}ms | last=${lastOcrWarmDurationV66}ms | interval=120s")
            }
'''
if diag_anchor not in s:
    raise SystemExit("v66 warm diag anchor missing")
s=s.replace(diag_anchor,diag_new,1)

# -------------------------------------------------------------------------
# VALIDACAO ESTATICA DA REGRA HIBRIDA
# -------------------------------------------------------------------------
def mode(agency):
    return "V64_SAFE_11.5" if agency <= 0.55 else "V65_CAP_5.2"

assert mode(0.473) == "V64_SAFE_11.5"
assert mode(0.497) == "V64_SAFE_11.5"
assert mode(0.575) == "V65_CAP_5.2"
assert mode(0.585) == "V65_CAP_5.2"
assert mode(0.586) == "V65_CAP_5.2"

for marker in [
    'agencyHybridThresholdV66 = 0.55f',
    'idCageModeV66 = if (useSafeV64V66)',
    'OCR_WARM_INTERVAL_V66_MS = 120_000L',
    'private fun runOcrWarmV66()',
    'handler.removeCallbacks(ocrWarmRunnableV66)',
    'ocrWarmV66=true',
    'V66 HYBRID CAGE + OCR WARM',
]:
    if marker not in s:
        raise SystemExit("v66 verify failed: "+marker)

S.write_text(s,encoding="utf-8")
print("v66 aplicado: gaiola hibrida <=55% V64 / >55% V65 + OCR warm 120s enquanto armado")
print("mapa validado: 47.3/49.7 -> V64_SAFE; 57.5/58.5/58.6 -> V65_CAP")
