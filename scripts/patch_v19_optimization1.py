from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - OTIMIZACAO 1
#
# Base: versao estavel ADMIN TOGGLE + diagnostico de velocidade.
# Objetivos conservadores:
# 1) tentar o detector de tabela densa a partir de 300 px, nao 500 px;
# 2) aceitar tabela colorida com 8+ linhas para evitar OCR completo inutil em
#    imagens medias (o fallback continua igual se nao detectar/nao fechar rota);
# 3) acelerar o parser sem mudar prioridade: primeiro testa SOMENTE as linhas
#    reconstruidas; se nao fechar rota, cai no mesmo fallback com elementos;
# 4) diagnosticar envio com numero de tentativas e metodo, SEM alterar a logica
#    de confirmacao do WhatsApp nesta etapa.

# -----------------------------------------------------------------------------
# 1) TABELAS MEDIAS TAMBEM PODEM USAR O CAMINHO DENSO
# -----------------------------------------------------------------------------
old_dense_rows = '        private const val DENSE_MIN_ROWS = 14\n'
new_dense_rows = '        private const val DENSE_MIN_ROWS = 8\n'
if old_dense_rows not in s:
    raise SystemExit('patch_v19_optimization1: DENSE_MIN_ROWS=14 nao encontrado')
s = s.replace(old_dense_rows, new_dense_rows, 1)

old_dispatch = '''        if (media.height >= 500) {
            readMediaLargeColorCrop(media)
        } else {
            readMediaOriginalFull(media)
        }
'''
new_dispatch = '''        if (media.height >= 300) {
            readMediaLargeColorCrop(media)
        } else {
            readMediaOriginalFull(media)
        }
'''
if old_dispatch not in s:
    raise SystemExit('patch_v19_optimization1: dispatch de 500px nao encontrado')
s = s.replace(old_dispatch, new_dispatch, 1)

# -----------------------------------------------------------------------------
# 2) PARSER RAPIDO COM FALLBACK IDENTICO
# -----------------------------------------------------------------------------
parse_start = s.find('    private fun parseVisionText(\n')
parse_end = s.find('\n    private fun closeImageWithoutSending(', parse_start)
if parse_start < 0 or parse_end < 0:
    raise SystemExit(
        f'patch_v19_optimization1: parseVisionText nao encontrado '
        f'(start={parse_start}, end={parse_end})'
    )

new_parse = r'''    private fun parseVisionText(
        visionText: Text,
        screenHeight: Int
    ): RouteResult? {
        data class OcrPart(
            val text: String,
            val rect: Rect
        ) {
            val centerY: Int get() = (rect.top + rect.bottom) / 2
            val height: Int get() = (rect.bottom - rect.top).coerceAtLeast(1)
        }

        val parts = ArrayList<OcrPart>(256)

        for (block in visionText.textBlocks) {
            for (line in block.lines) {
                var addedElement = false

                for (element in line.elements) {
                    val box = element.boundingBox ?: continue
                    val text = element.text.trim()
                    if (text.isBlank()) continue
                    parts += OcrPart(text, Rect(box))
                    addedElement = true
                }

                if (!addedElement) {
                    val box = line.boundingBox ?: continue
                    val text = line.text.trim()
                    if (text.isNotBlank()) {
                        parts += OcrPart(text, Rect(box))
                    }
                }
            }
        }

        if (parts.isEmpty()) return null

        val heights = IntArray(parts.size)
        for (i in parts.indices) heights[i] = parts[i].height
        heights.sort()
        val medianHeight = heights[heights.size / 2].coerceAtLeast(5)
        val rowTolerance = maxOf(5, (medianHeight * 0.66f).toInt())

        data class RowBucket(
            val parts: MutableList<OcrPart> = ArrayList(),
            var centerY: Double = 0.0,
            var centerSum: Long = 0L,
            var count: Int = 0
        )

        val rows = ArrayList<RowBucket>(64)
        val orderedByY = parts.sortedBy { it.centerY }

        for (part in orderedByY) {
            var nearest: RowBucket? = null
            var nearestDiff = Double.MAX_VALUE

            // Mantem a MESMA regra da v0.16 (linha visual mais proxima dentro da
            // tolerancia), mas sem criar listas temporarias em filter/minBy.
            for (row in rows) {
                val diff = kotlin.math.abs(row.centerY - part.centerY)
                if (diff <= rowTolerance && diff < nearestDiff) {
                    nearest = row
                    nearestDiff = diff
                }
            }

            if (nearest == null) {
                rows += RowBucket(
                    parts = arrayListOf(part),
                    centerY = part.centerY.toDouble(),
                    centerSum = part.centerY.toLong(),
                    count = 1
                )
            } else {
                nearest.parts += part
                nearest.centerSum += part.centerY.toLong()
                nearest.count += 1
                nearest.centerY = nearest.centerSum.toDouble() / nearest.count.toDouble()
            }
        }

        // FAST PATH: quase todas as tabelas corretas ja possuem gaiola + bairro
        // na linha reconstruida. Testar somente ~8-35 linhas evita normalizar e
        // comparar centenas de palavras individualmente.
        val reconstructedItems = ArrayList<ScreenText>(rows.size)

        for (row in rows) {
            val ordered = row.parts.sortedBy { it.rect.left }
            if (ordered.isEmpty()) continue

            val text = buildString {
                for (i in ordered.indices) {
                    if (i > 0) append(' ')
                    append(ordered[i].text)
                }
            }.replace(Regex("\\s+"), " ").trim()

            if (text.isBlank()) continue

            reconstructedItems += ScreenText(
                text = text,
                left = ordered.minOf { it.rect.left },
                top = ordered.minOf { it.rect.top },
                right = ordered.maxOf { it.rect.right },
                bottom = ordered.maxOf { it.rect.bottom }
            )
        }

        RouteParser.parseImageScreenTexts(reconstructedItems)?.let { return it }

        // FALLBACK: exatamente a ideia da v0.16. Se a linha reconstruida nao
        // conseguiu fechar bairro+gaiola, inclui os elementos originais e tenta
        // a geometria fina. Assim a otimizacao nao sacrifica robustez/prioridade.
        val screenItems = ArrayList<ScreenText>(parts.size + reconstructedItems.size)

        for (part in parts) {
            screenItems += ScreenText(
                text = part.text,
                left = part.rect.left,
                top = part.rect.top,
                right = part.rect.right,
                bottom = part.rect.bottom
            )
        }
        screenItems.addAll(reconstructedItems)

        return RouteParser.parseImageScreenTexts(screenItems)
    }
'''

s = s[:parse_start] + new_parse + s[parse_end:]

# -----------------------------------------------------------------------------
# 3) DIAGNOSTICO DO ENVIO: tentativas/metodo, sem acelerar confirmacao ainda
# -----------------------------------------------------------------------------
state_anchor = '    private var speedDiagnosticSendStartedAt = 0L\n'
state_extra = '''    private var speedDiagnosticSendAttempts = 0
    private var speedDiagnosticSendMethod = "nenhum"
'''
if 'private var speedDiagnosticSendAttempts' not in s:
    if state_anchor not in s:
        raise SystemExit('patch_v19_optimization1: estado do diagnostico de envio nao encontrado')
    s = s.replace(state_anchor, state_anchor + state_extra, 1)

send_start_anchor = '        speedDiagnosticSendStartedAt = SystemClock.elapsedRealtime()\n'
if send_start_anchor not in s:
    raise SystemExit('patch_v19_optimization1: inicio do diagnostico de envio nao encontrado')
s = s.replace(
    send_start_anchor,
    send_start_anchor +
    '        speedDiagnosticSendAttempts = 0\n'
    '        speedDiagnosticSendMethod = "nenhum"\n',
    1
)

try_anchor = '''    private fun tryClickSend(route: RouteResult, attempt: Int) {
        if (!processing) return
'''
try_new = '''    private fun tryClickSend(route: RouteResult, attempt: Int) {
        if (!processing) return
        speedDiagnosticSendAttempts = maxOf(speedDiagnosticSendAttempts, attempt + 1)
'''
if try_anchor not in s:
    raise SystemExit('patch_v19_optimization1: tryClickSend nao encontrado')
s = s.replace(try_anchor, try_new, 1)

click_anchor = '''        if (candidate != null && clickNodeOrParent(candidate.node)) {
            handler.postDelayed(
'''
click_new = '''        if (candidate != null && clickNodeOrParent(candidate.node)) {
            speedDiagnosticSendMethod = "ACTION_CLICK"
            handler.postDelayed(
'''
if click_anchor not in s:
    raise SystemExit('patch_v19_optimization1: ACTION_CLICK do envio nao encontrado')
s = s.replace(click_anchor, click_new, 1)

gesture_anchor = '        tapSendAndVerify(route, attempt, x, y)\n'
if gesture_anchor not in s:
    raise SystemExit('patch_v19_optimization1: chamada tapSendAndVerify nao encontrada')
s = s.replace(
    gesture_anchor,
    '        speedDiagnosticSendMethod = "GESTURE"\n' + gesture_anchor,
    1
)

old_confirm = '''        Prefs.setStatus(
            this,
            "CONFIRMADO: ${route.neighborhood} -> ${route.cage} | " +
                "envio=${formatElapsedMs(sendStageMs)} | app=${formatElapsedMs(elapsed)}"
        )
'''
new_confirm = '''        Prefs.setStatus(
            this,
            "CONFIRMADO: ${route.neighborhood} -> ${route.cage} | " +
                "envio=${formatElapsedMs(sendStageMs)} | tentativas=${speedDiagnosticSendAttempts} | " +
                "metodo=${speedDiagnosticSendMethod} | app=${formatElapsedMs(elapsed)}"
        )
'''
if old_confirm not in s:
    raise SystemExit('patch_v19_optimization1: status CONFIRMADO nao encontrado')
s = s.replace(old_confirm, new_confirm, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 OTIMIZACAO 1 aplicado: tabelas medias + parser rapido + diagnostico de envio")
