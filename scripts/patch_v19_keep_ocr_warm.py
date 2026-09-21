from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# Mantem o ML Kit aquecido enquanto o bot estiver ARMADO procurando rota.
# Nao altera a leitura real da v0.19, o parser, o envio ou as notificacoes.
# Quando o bot para depois de enviar, o aquecimento tambem para de executar OCR.
# Teste A/B: intervalo de 15 segundos.

const_anchor = '        private const val DEDUP_MS = 8_000L\n'
if 'KEEP_OCR_WARM_INTERVAL_MS' not in s:
    if const_anchor not in s:
        raise SystemExit('patch_v19_keep_ocr_warm: constante DEDUP_MS nao encontrada')
    s = s.replace(
        const_anchor,
        const_anchor + '        private const val KEEP_OCR_WARM_INTERVAL_MS = 15_000L\n',
        1
    )

recognizer_anchor = '''    private val recognizer by lazy {
        TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
    }
'''

warm_state = '''    private var keepWarmBusy = false

    private val keepOcrWarmRunnable = object : Runnable {
        override fun run() {
            try {
                if (
                    Prefs.isEnabled(this@WhatsRouteAccessibilityService) &&
                    Prefs.searchArmed(this@WhatsRouteAccessibilityService) &&
                    !processing &&
                    !keepWarmBusy
                ) {
                    keepOcrEngineWarm()
                }
            } catch (_: Throwable) {
                // Aquecimento e opcional; nunca pode interferir na rota real.
            } finally {
                handler.postDelayed(this, KEEP_OCR_WARM_INTERVAL_MS)
            }
        }
    }
'''

if 'keepOcrWarmRunnable' not in s:
    if recognizer_anchor not in s:
        raise SystemExit('patch_v19_keep_ocr_warm: recognizer nao encontrado')
    s = s.replace(recognizer_anchor, recognizer_anchor + '\n' + warm_state, 1)

connect_anchor = '''        warmUpRecognizer()
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
connect_new = '''        warmUpRecognizer()
        handler.removeCallbacks(keepOcrWarmRunnable)
        handler.postDelayed(keepOcrWarmRunnable, KEEP_OCR_WARM_INTERVAL_MS)
        handler.postDelayed({ primeCurrentScreen() }, 350)
'''
if connect_anchor not in s:
    raise SystemExit('patch_v19_keep_ocr_warm: onServiceConnected nao encontrado')
s = s.replace(connect_anchor, connect_new, 1)

warm_func_anchor = '''    private fun warmUpRecognizer() {
'''
keep_func = '''    private fun keepOcrEngineWarm() {
        if (keepWarmBusy || processing || !Prefs.searchArmed(this)) return

        keepWarmBusy = true
        var tiny: Bitmap? = null

        try {
            tiny = Bitmap.createBitmap(48, 48, Bitmap.Config.ARGB_8888)
            val input = InputImage.fromBitmap(tiny, 0)

            recognizer.process(input)
                .addOnCompleteListener {
                    try {
                        tiny?.recycle()
                    } catch (_: Throwable) {}
                    keepWarmBusy = false
                }
        } catch (_: Throwable) {
            try {
                tiny?.recycle()
            } catch (_: Throwable) {}
            keepWarmBusy = false
        }
    }

'''
if 'private fun keepOcrEngineWarm()' not in s:
    if warm_func_anchor not in s:
        raise SystemExit('patch_v19_keep_ocr_warm: warmUpRecognizer nao encontrado')
    s = s.replace(warm_func_anchor, keep_func + warm_func_anchor, 1)

destroy_anchor = '''    override fun onDestroy() {
        recognizer.close()
        super.onDestroy()
    }
'''
destroy_new = '''    override fun onDestroy() {
        handler.removeCallbacks(keepOcrWarmRunnable)
        recognizer.close()
        super.onDestroy()
    }
'''
if destroy_anchor not in s:
    raise SystemExit('patch_v19_keep_ocr_warm: onDestroy nao encontrado')
s = s.replace(destroy_anchor, destroy_new, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 KEEP OCR WARM aplicado: aquecimento a cada 15s somente enquanto procurando rota")
