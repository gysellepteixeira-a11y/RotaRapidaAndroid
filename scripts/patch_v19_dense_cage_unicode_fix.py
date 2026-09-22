from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - DENSE CAGE OCR FIX
#
# Caso real observado no diagnostico:
#   lido=[J-16 AT2026]
# mas RouteParser.extractCage(...) retornou null.
#
# Isso indica que o caractere visual entre J e 16 pode nao ser o hifen ASCII
# (OCR pode devolver U+2010/U+2011/U+2012/U+2013/U+2014/U+2212 etc.).
# O log parece "J-16", mas internamente o caractere pode ser diferente.
#
# Corrigimos SOMENTE o OCR pequeno de recovery da coluna Gaiola, sem mudar o
# parser normal da Otimizacao 1. Assim reduzimos risco de falso positivo.

old = '''                var cage: String? = RouteParser.extractCage(cageText.text)

                // Se o texto geral veio estranho, tenta cada linha/elemento.
                if (cage == null) {
                    outer@ for (block in cageText.textBlocks) {
                        for (line in block.lines) {
                            val lineCage = RouteParser.extractCage(line.text)
                            if (lineCage != null) {
                                cage = lineCage
                                break@outer
                            }
                            for (element in line.elements) {
                                val elementCage = RouteParser.extractCage(element.text)
                                if (elementCage != null) {
                                    cage = elementCage
                                    break@outer
                                }
                            }
                        }
                    }
                }
'''

new = r'''                fun extractRecoveryCage(rawValue: String): String? {
                    // Primeiro preserva o comportamento existente.
                    RouteParser.extractCage(rawValue)?.let { return it }

                    // OCR frequentemente usa tracos Unicode visualmente iguais a '-'.
                    val normalized = rawValue
                        .uppercase(java.util.Locale.ROOT)
                        .replace('\u2010', '-')
                        .replace('\u2011', '-')
                        .replace('\u2012', '-')
                        .replace('\u2013', '-')
                        .replace('\u2014', '-')
                        .replace('\u2212', '-')
                        .replace('\u2043', '-')
                        .replace('_', '-')

                    val match = Regex(
                        "(?<![A-Z0-9])([A-Z1])[-.\\s]?(\\d{2})(?!\\d)"
                    ).find(normalized) ?: return null

                    var letter = match.groupValues[1]
                    if (letter == "1") letter = "I"
                    return letter.lowercase(java.util.Locale.ROOT) + match.groupValues[2]
                }

                var cage: String? = extractRecoveryCage(cageText.text)

                // Se o texto geral veio estranho, tenta cada linha/elemento.
                if (cage == null) {
                    outer@ for (block in cageText.textBlocks) {
                        for (line in block.lines) {
                            val lineCage = extractRecoveryCage(line.text)
                            if (lineCage != null) {
                                cage = lineCage
                                break@outer
                            }
                            for (element in line.elements) {
                                val elementCage = extractRecoveryCage(element.text)
                                if (elementCage != null) {
                                    cage = elementCage
                                    break@outer
                                }
                            }
                        }
                    }
                }
'''

if old not in s:
    raise SystemExit("dense cage unicode fix: bloco de extracao nao encontrado")

s = s.replace(old, new, 1)
service_path.write_text(s, encoding="utf-8")
print("Dense cage Unicode fix aplicado: J-16/J–16/J—16/J 16/J16 no recovery")
