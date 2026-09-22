from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - RECUPERACAO SEGURA DE LINHA EM TABELAS MUITO DENSAS
# Base: OTIMIZACAO 1 (nao usa a Otimizacao 2 de envio).
#
# Caso observado: tabela com 38 linhas, Colina de Laranjeiras visivel em J-16,
# mas o OCR reconhece centenas de fragmentos e o parser estrito nao fecha a linha.
#
# Mantemos o parser estrito como primeira opcao. Somente se ele falhar E a imagem
# for uma tabela densa (20+ linhas detectadas pela coluna Agency), fazemos uma
# recuperacao geometrica controlada:
# - escolhe primeiro o bairro de maior prioridade usando o MESMO RouteParser;
# - calcula o passo medio esperado de uma linha pela altura do crop / qtd. linhas;
# - procura uma gaiola somente a esquerda e a menos de 48% de um passo de linha;
# - assim uma gaiola da linha de cima/baixo nao pode vencer por tolerancia ampla.
#
# Tambem registra diagnostico do bairro/gaiolas proximas quando o parser estrito
# falhar, para podermos ajustar sem adivinhar.

state_anchor = '    private var speedDiagnosticSendMethod = "nenhum"\n'
if 'private var lastDenseRecoveryDebug' not in s:
    if state_anchor not in s:
        raise SystemExit('patch_v19_dense_row_recovery: estado da Otimizacao 1 nao encontrado')
    s = s.replace(
        state_anchor,
        state_anchor + '    private var lastDenseRecoveryDebug = ""\n',
        1
    )

old_signature = '''    private fun parseVisionText(
        visionText: Text,
        screenHeight: Int
    ): RouteResult? {
'''
new_signature = '''    private fun parseVisionText(
        visionText: Text,
        screenHeight: Int,
        expectedDenseRows: Int = 0
    ): RouteResult? {
'''
if old_signature not in s:
    raise SystemExit('patch_v19_dense_row_recovery: assinatura parseVisionText nao encontrada')
s = s.replace(old_signature, new_signature, 1)

old_tail = '''        screenItems.addAll(reconstructedItems)

        return RouteParser.parseImageScreenTexts(screenItems)
    }
'''
new_tail = r'''        screenItems.addAll(reconstructedItems)

        val strictResult = RouteParser.parseImageScreenTexts(screenItems)
        if (strictResult != null) {
            lastDenseRecoveryDebug = "estrito=ok"
            return strictResult
        }

        if (expectedDenseRows < 20) {
            return null
        }

        data class PriorityHit(
            val result: RouteResult,
            val item: ScreenText
        )

        val priorityHits = ArrayList<PriorityHit>()

        for (item in screenItems) {
            val probe = RouteParser.parsePlainTexts(
                listOf("A00 ${item.text}")
            ) ?: continue
            priorityHits += PriorityHit(probe, item)
        }

        if (priorityHits.isEmpty()) {
            lastDenseRecoveryDebug =
                "recovery=${expectedDenseRows} linhas; prioridade OCR=nenhuma"
            return null
        }

        val bestPriority = priorityHits.minOf { it.result.priorityIndex }
        val chosen = priorityHits
            .asSequence()
            .filter { it.result.priorityIndex == bestPriority }
            .minByOrNull { it.item.top }
            ?: return null

        val rowPitch = screenHeight.toFloat() / expectedDenseRows.toFloat()
        val maxSameRowDistance = maxOf(8f, rowPitch * 0.48f)
        val neighborhoodY = chosen.item.centerY

        data class CageHit(
            val cage: String,
            val item: ScreenText,
            val dy: Int
        )

        val cages = ArrayList<CageHit>()

        for (part in parts) {
            val cage = RouteParser.extractCage(part.text) ?: continue
            if (part.rect.left >= chosen.item.left) continue

            val centerY = (part.rect.top + part.rect.bottom) / 2
            val dy = kotlin.math.abs(centerY - neighborhoodY)

            cages += CageHit(
                cage = cage,
                item = ScreenText(
                    text = part.text,
                    left = part.rect.left,
                    top = part.rect.top,
                    right = part.rect.right,
                    bottom = part.rect.bottom
                ),
                dy = dy
            )
        }

        val nearby = cages
            .filter { it.dy.toFloat() <= maxSameRowDistance }
            .sortedWith(compareBy<CageHit>({ it.dy }, { it.item.left }))

        val debugCages = cages
            .sortedBy { it.dy }
            .take(4)
            .joinToString(",") { "${it.cage}@${it.item.centerY}(d${it.dy})" }
            .ifBlank { "nenhuma" }

        val nearest = nearby.firstOrNull()
        if (nearest == null) {
            lastDenseRecoveryDebug =
                "recovery=${expectedDenseRows}; bairro=${chosen.result.neighborhood}@${neighborhoodY}; " +
                    "pitch=${String.format(java.util.Locale.US, "%.1f", rowPitch)}; " +
                    "limite=${String.format(java.util.Locale.US, "%.1f", maxSameRowDistance)}; " +
                    "gaiolas=$debugCages; escolha=nenhuma"
            return null
        }

        lastDenseRecoveryDebug =
            "recovery=${expectedDenseRows}; bairro=${chosen.result.neighborhood}@${neighborhoodY}; " +
                "pitch=${String.format(java.util.Locale.US, "%.1f", rowPitch)}; " +
                "gaiolas=$debugCages; escolha=${nearest.cage}"

        return RouteResult(
            neighborhood = chosen.result.neighborhood,
            cage = nearest.cage,
            priorityIndex = chosen.result.priorityIndex
        )
    }
'''
if old_tail not in s:
    raise SystemExit('patch_v19_dense_row_recovery: final do parser da Otimizacao 1 nao encontrado')
s = s.replace(old_tail, new_tail, 1)

dense_start = s.find('    private fun readMediaLargeColorCrop(media: MediaImage) {')
dense_end = s.find('    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {', dense_start)
if dense_start < 0 or dense_end < 0:
    raise SystemExit('patch_v19_dense_row_recovery: bloco DENSA nao encontrado')

dense_block = s[dense_start:dense_end]
old_call = '                val route = parseVisionText(visionText, crop.height)\n'
new_call = '                val route = parseVisionText(visionText, crop.height, detected.rowCount)\n'
if old_call not in dense_block:
    raise SystemExit('patch_v19_dense_row_recovery: chamada parseVisionText DENSA nao encontrada')
dense_block = dense_block.replace(old_call, new_call, 1)

old_fail = '''                    Prefs.setStatus(
                        this,
                        "OCR denso leu $totalLinhas linhas sem fechar rota. " +
                            "Tentando leitura reforcada do arquivo inteiro..."
                    )
'''
new_fail = '''                    Prefs.setStatus(
                        this,
                        "OCR denso leu $totalLinhas linhas sem fechar rota | " +
                            "$lastDenseRecoveryDebug | " +
                            "Tentando leitura reforcada do arquivo inteiro..."
                    )
'''
if old_fail not in dense_block:
    raise SystemExit('patch_v19_dense_row_recovery: status de falha DENSA nao encontrado')
dense_block = dense_block.replace(old_fail, new_fail, 1)

s = s[:dense_start] + dense_block + s[dense_end:]

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 DENSE ROW RECOVERY aplicado: mesma prioridade + pareamento por passo real da linha")
