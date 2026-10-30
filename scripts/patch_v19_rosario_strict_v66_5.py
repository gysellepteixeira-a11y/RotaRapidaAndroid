from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
r=R.read_text(encoding="utf-8")
s=S.read_text(encoding="utf-8")

start=r.find("    private fun containsTokenApprox(")
if start < 0:
    raise SystemExit("containsTokenApprox missing")
end=r.find("\n    }", start)
if end < 0:
    raise SystemExit("containsTokenApprox end missing")
end += len("\n    }")

old=r[start:end]
if 'if (token == "rosar")' not in old:
    raise SystemExit("Expected v66.2 matcher not found")

new='''    private fun containsTokenApprox(normalized: String, token: String): Boolean {
        // v66.5: Rosario precisa ser reconhecido pelo nome completo.
        // Aceita "rosario" junto ou separado pelo OCR ("rosa rio"),
        // com no maximo um erro em uma janela de 7 letras.
        // "Feu Rosa" -> "feurosa" nao pode virar Rosario.
        if (token == "rosar") {
            val compact = normalized.replace(" ", "")
            if (compact.contains("rosario")) return true

            val target = "rosario"
            if (compact.length >= target.length) {
                for (i in 0..(compact.length - target.length)) {
                    val window = compact.substring(i, i + target.length)
                    if (editDistanceAtMostOne(window, target)) return true
                }
            }
            return false
        }

        if (normalized.contains(token)) return true
        if (token.length < 5) return false

        return normalized
            .split(' ')
            .filter { it.isNotBlank() }
            .any { word ->
                if (word.length < token.length && token.startsWith(word)) {
                    false
                } else {
                    editDistanceAtMostOne(word, token)
                }
            }
    }'''
r=r[:start]+new+r[end:]

old_title='V66.4 ROSARIO ONLY'
new_title='V66.5 ROSARIO STRICT FULL NAME'
if old_title not in s:
    raise SystemExit("v66.4 title missing")
s=s.replace(old_title,new_title,1)

if 'V66.5 ROSARIO STRICT FULL NAME' not in s:
    raise SystemExit("v66.5 title verification failed")

R.write_text(r,encoding="utf-8")
S.write_text(s,encoding="utf-8")
print("v66.5: Rosario exige nome completo rosario; Feu Rosa rejeitado; demais bairros preservados")
