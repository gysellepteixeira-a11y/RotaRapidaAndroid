from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")

r=R.read_text(encoding="utf-8")
s=S.read_text(encoding="utf-8")

old='''    private fun containsTokenApprox(normalized: String, token: String): Boolean {
        if (normalized.contains(token)) return true
        if (token.length < 5) return false

        return normalized
            .split(' ')
            .filter { it.isNotBlank() }
            .any { word ->
                // v57: evita falso positivo por "prefixo curto".
                // Exemplo real: Feu Rosa -> palavra "rosa" nao pode ser tratada
                // como Rosario/"rosar" apenas porque falta 1 caractere no fim.
                if (word.length < token.length && token.startsWith(word)) {
                    false
                } else {
                    editDistanceAtMostOne(word, token)
                }
            }
    }
'''

new='''    private fun containsTokenApprox(normalized: String, token: String): Boolean {
        if (normalized.contains(token)) return true
        if (token.length < 5) return false

        // v66.2: Rosário de Fátima apareceu numa tabela real acima de Mata da Praia,
        // mas o OCR denso escolheu Mata. A causa mais provável é o ML Kit quebrar
        // "Rosário" dentro da própria palavra (ex.: "Rosa rio"), caso em que a
        // proteção v57 corretamente rejeita a palavra curta "rosa".
        //
        // Para o token específico "rosar", tentamos também a linha sem espaços e
        // aceitamos uma janela de 5 letras com no máximo 1 erro. Isso recupera
        // "rosa rio"/"rosano"/"rosár io" sem reabrir o falso positivo Feu Rosa:
        // "feu rosa" -> "feurosa", que não contém/faz fuzzy com "rosar".
        if (token == "rosar") {
            val compact = normalized.replace(" ", "")
            if (compact.contains(token)) return true

            if (compact.length >= token.length) {
                for (i in 0..(compact.length - token.length)) {
                    val w = compact.substring(i, i + token.length)
                    if (editDistanceAtMostOne(w, token)) return true
                }
            }
        }

        return normalized
            .split(' ')
            .filter { it.isNotBlank() }
            .any { word ->
                // v57 preservado: "rosa" isolado nao casa com "rosar".
                if (word.length < token.length && token.startsWith(word)) {
                    false
                } else {
                    editDistanceAtMostOne(word, token)
                }
            }
    }
'''

if old not in r:
    raise SystemExit("v66.2 containsTokenApprox anchor missing")
r=r.replace(old,new,1)

old_title='===== DIAGNOSTICO IMAGEM v19 | V66.1 ROSARIO FATIMA FIX + V66 HYBRID CAGE + OCR WARM + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
new_title='===== DIAGNOSTICO IMAGEM v19 | V66.2 ROSARIO ROBUST + V66 HYBRID CAGE + OCR WARM + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
if old_title not in s:
    raise SystemExit("v66.2 title anchor missing")
s=s.replace(old_title,new_title,1)

for marker in [
    'if (token == "rosar")',
    'val compact = normalized.replace(" ", "")',
    'editDistanceAtMostOne(w, token)',
    'word.length < token.length && token.startsWith(word)',
    '"rosario de fatima" -> listOf("rosar")',
    'V66.2 ROSARIO ROBUST',
]:
    if marker not in r+s:
        raise SystemExit("v66.2 verify failed: "+marker)

R.write_text(r,encoding="utf-8")
S.write_text(s,encoding="utf-8")
print("v66.2 aplicado: Rosario robusto contra quebra interna do OCR; Feu Rosa continua protegido; sem OCR extra")
