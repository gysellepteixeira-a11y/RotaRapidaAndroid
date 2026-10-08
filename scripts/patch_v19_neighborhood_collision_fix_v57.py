from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
r=R.read_text(encoding="utf-8")

old='''    private fun containsTokenApprox(normalized: String, token: String): Boolean {
        if (normalized.contains(token)) return true
        if (token.length < 5) return false

        return normalized
            .split(' ')
            .filter { it.isNotBlank() }
            .any { word -> editDistanceAtMostOne(word, token) }
    }
'''

new='''    private fun containsTokenApprox(normalized: String, token: String): Boolean {
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

if old not in r:
    raise SystemExit("v57 containsTokenApprox final-v56 block missing")

r=r.replace(old,new,1)

for m in [
    'word.length < token.length && token.startsWith(word)',
    'editDistanceAtMostOne(word, token)',
    'if (normalized.contains(token)) return true',
]:
    if m not in r:
        raise SystemExit("v57 verify failed: "+m)

R.write_text(r,encoding="utf-8")
print("v57 aplicado: 'rosa' nao casa mais fuzzy com 'rosar'; Rosario real continua por contains direto")
