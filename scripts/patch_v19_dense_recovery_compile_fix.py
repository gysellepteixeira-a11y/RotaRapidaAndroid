from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

old = '''                            RouteParser.extractCage(line.text)?.let {
                                cage = it
                                break@outer
                            }
                            for (element in line.elements) {
                                RouteParser.extractCage(element.text)?.let {
                                    cage = it
                                    break@outer
                                }
                            }
'''

new = '''                            val lineCage = RouteParser.extractCage(line.text)
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
'''

if old not in s:
    raise SystemExit("dense recovery compile fix: bloco de break em lambda nao encontrado")

s = s.replace(old, new, 1)
service_path.write_text(s, encoding="utf-8")
print("Dense recovery compile fix aplicado: break fora de lambda para Kotlin atual")
