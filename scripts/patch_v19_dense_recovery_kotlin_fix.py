from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

old_line = '''                            RouteParser.extractCage(line.text)?.let {
                                cage = it
                                break@outer
                            }
'''
new_line = '''                            val lineCage = RouteParser.extractCage(line.text)
                            if (lineCage != null) {
                                cage = lineCage
                                break@outer
                            }
'''

old_element = '''                                RouteParser.extractCage(element.text)?.let {
                                    cage = it
                                    break@outer
                                }
'''
new_element = '''                                val elementCage = RouteParser.extractCage(element.text)
                                if (elementCage != null) {
                                    cage = elementCage
                                    break@outer
                                }
'''

if old_line not in s or old_element not in s:
    raise SystemExit("dense recovery Kotlin fix: blocos esperados nao encontrados")

s = s.replace(old_line, new_line, 1)
s = s.replace(old_element, new_element, 1)
service_path.write_text(s, encoding="utf-8")
print("Dense recovery Kotlin fix aplicado: break fora de lambdas inline")
