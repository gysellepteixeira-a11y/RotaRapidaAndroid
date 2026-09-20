from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.13: tabelas com muitas rotas ficam pequenas demais quando a imagem inteira
# cabe na largura do celular. Ampliar apenas o BITMAP depois da captura nao cria
# detalhe novo. Agora, quando o OCR inicial falha ou detecta texto muito pequeno,
# fazemos um PINCH-ZOOM real no visualizador do WhatsApp, focado na metade esquerda
# (onde ficam Gaiola + Bairro), e so entao tiramos a segunda captura para OCR.

# 1) Depois de calcular totalLinhas/amostra, calcula se o texto esta pequeno demais.
old_metrics = '''                                    val totalLinhas =
                                        contarLinhasVisionText(visionText)
                                    val amostra =
                                        resumirVisionText(visionText)

                                    try {
'''
new_metrics = '''                                    val totalLinhas =
                                        contarLinhasVisionText(visionText)
                                    val amostra =
                                        resumirVisionText(visionText)
                                    val tabelaDensa =
                                        attempt == 0 && isDenseVisionText(visionText)

                                    try {
'''
if old_metrics not in s:
    raise SystemExit("Patch v0.13: bloco de metricas OCR nao encontrado")
s = s.replace(old_metrics, new_metrics, 1)

# 2) Antes de confiar numa rota de texto muito pequeno, da zoom fisico e rele.
old_route_if = '''                                    if (route != null) {
                                        if (isDuplicate(route)) {
'''
new_route_if = '''                                    if (tabelaDensa) {
                                        Prefs.setStatus(
                                            this@WhatsRouteAccessibilityService,
                                            "Tabela com muitas rotas. Ampliando para ler Gaiola + Bairro..."
                                        )
                                        zoomDenseTableAndRetry()
                                    } else if (route != null) {
                                        if (isDuplicate(route)) {
'''
if old_route_if not in s:
    raise SystemExit("Patch v0.13: if route nao encontrado")
s = s.replace(old_route_if, new_route_if, 1)

# 3) Se a primeira leitura nao encontrou rota, em vez de apenas ampliar bitmap,
# faz zoom real no WhatsApp e depois captura novamente.
old_retry = '''                                    } else if (attempt == 0) {
                                        Prefs.setStatus(
                                            this@WhatsRouteAccessibilityService,
                                            "OCR 1 leu $totalLinhas linhas. Tentando leitura reforçada..."
                                        )

                                        handler.postDelayed(
                                            {
                                                captureAndReadImage(
                                                    attempt = 1
                                                )
                                            },
                                            IMAGE_RETRY_DELAY_MS
                                        )
'''
new_retry = '''                                    } else if (attempt == 0) {
                                        Prefs.setStatus(
                                            this@WhatsRouteAccessibilityService,
                                            "OCR inicial nao fechou a rota. Dando zoom real na tabela..."
                                        )
                                        zoomDenseTableAndRetry()
'''
if old_retry not in s:
    raise SystemExit("Patch v0.13: retry OCR sucesso nao encontrado")
s = s.replace(old_retry, new_retry, 1)

# 4) Se o ML Kit falhar na primeira tentativa, tambem usa zoom real.
old_failure_retry = '''                                    if (attempt == 0) {
                                        handler.postDelayed(
                                            {
                                                captureAndReadImage(
                                                    attempt = 1
                                                )
                                            },
                                            IMAGE_RETRY_DELAY_MS
                                        )
                                    } else {
'''
new_failure_retry = '''                                    if (attempt == 0) {
                                        Prefs.setStatus(
                                            this@WhatsRouteAccessibilityService,
                                            "OCR inicial falhou. Ampliando a tabela para nova leitura..."
                                        )
                                        zoomDenseTableAndRetry()
                                    } else {
'''
if old_failure_retry not in s:
    raise SystemExit("Patch v0.13: retry OCR failure nao encontrado")
s = s.replace(old_failure_retry, new_failure_retry, 1)

# 5) Helpers: detectar texto pequeno e executar pinch zoom real.
insert_at = s.find('    private fun prepararBitmapImagemParaOcr(')
if insert_at < 0:
    raise SystemExit("Patch v0.13: ponto de insercao dos helpers nao encontrado")

helpers = r'''    private fun isDenseVisionText(visionText: Text): Boolean {
        val heights = mutableListOf<Int>()

        for (block in visionText.textBlocks) {
            for (line in block.lines) {
                if (line.elements.isNotEmpty()) {
                    for (element in line.elements) {
                        val box = element.boundingBox ?: continue
                        val h = box.height()
                        if (h > 0) heights += h
                    }
                } else {
                    val box = line.boundingBox ?: continue
                    val h = box.height()
                    if (h > 0) heights += h
                }
            }
        }

        if (heights.isEmpty()) return true

        heights.sort()
        val median = heights[heights.size / 2]

        // Em tabelas curtas o texto costuma ficar bem maior. Nas tabelas com
        // 20~30 rotas, a mediana cai para perto de 10-18 px no M52.
        return median <= 20
    }

    private fun zoomDenseTableAndRetry() {
        if (!processing) return

        val w = resources.displayMetrics.widthPixels
        val h = resources.displayMetrics.heightPixels

        // Centro do zoom deslocado para a esquerda: depois de ampliar ficam
        // visiveis ao mesmo tempo as colunas Gaiola e Bairro.
        val cx = (w * 0.27f)
        val cy = (h * 0.50f)

        val startDx = (w * 0.075f)
        val startDy = (h * 0.020f)
        val endDx = (w * 0.155f)
        val endDy = (h * 0.045f)

        val p1 = Path().apply {
            moveTo(cx - startDx, cy - startDy)
            lineTo(cx - endDx, cy - endDy)
        }

        val p2 = Path().apply {
            moveTo(cx + startDx, cy + startDy)
            lineTo(cx + endDx, cy + endDy)
        }

        val gesture = GestureDescription.Builder()
            .addStroke(
                GestureDescription.StrokeDescription(
                    p1,
                    0L,
                    220L
                )
            )
            .addStroke(
                GestureDescription.StrokeDescription(
                    p2,
                    0L,
                    220L
                )
            )
            .build()

        val accepted = dispatchGesture(
            gesture,
            object : GestureResultCallback() {
                override fun onCompleted(gestureDescription: GestureDescription?) {
                    Prefs.setStatus(
                        this@WhatsRouteAccessibilityService,
                        "Tabela ampliada. Lendo novamente..."
                    )
                    handler.postDelayed(
                        { captureAndReadImage(attempt = 1) },
                        180L
                    )
                }

                override fun onCancelled(gestureDescription: GestureDescription?) {
                    Prefs.setStatus(
                        this@WhatsRouteAccessibilityService,
                        "Zoom foi cancelado; tentando OCR reforcado sem zoom."
                    )
                    handler.postDelayed(
                        { captureAndReadImage(attempt = 1) },
                        80L
                    )
                }
            },
            null
        )

        if (!accepted) {
            Prefs.setStatus(
                this,
                "Android nao aceitou o zoom; tentando OCR reforcado."
            )
            handler.postDelayed(
                { captureAndReadImage(attempt = 1) },
                80L
            )
        }
    }

'''

s = s[:insert_at] + helpers + s[insert_at:]
service_path.write_text(s, encoding="utf-8")
print("Patch v0.13 aplicado: tabelas densas usam pinch-zoom real antes do segundo OCR")
