from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
r=R.read_text(encoding="utf-8")
s=S.read_text(encoding="utf-8")

route_anchor='''    fun matchPriority(text: String): Pair<Int, String>? =
        priorityFor(text)
'''
if 'fun rosarioConfiguredPriorityV666()' not in r:
    if route_anchor not in r:
        raise SystemExit("v66.6 RouteParser anchor missing")
    r=r.replace(route_anchor,route_anchor+'''
    fun rosarioConfiguredPriorityV666(): Int? {
        priorities.forEachIndexed { index, rule ->
            val n = normalize(rule.name)
            if (n == "rosario" || n == "rosario de fatima") return index
        }
        return null
    }
''',1)

anchor='''                val chosen = best
                if (chosen == null) {
'''
i=s.find(anchor)
if i<0: raise SystemExit("v66.6 chosen anchor missing")
end=s.find('                // Y do OCR da coluna Bairro',i)
if end<0: raise SystemExit("v66.6 insert point missing")
block=s[i:end]
if 'rosarioPriorityV666' not in block:
    rescue='''                val rosarioPriorityV666 = RouteParser.rosarioConfiguredPriorityV666()
                val chosenNormV666 = RouteParser.normalize(chosen.neighborhood)
                val lowerPriorityV666 =
                    "mata da praia" in chosenNormV666 ||
                    "republica" in chosenNormV666

                // Só faz leitura ampla quando o OCR rápido escolhe Mata/República
                // apesar de Rosário estar acima na lista configurada.
                // O fallback relê a tabela completa e o parser escolhe a maior
                // prioridade entre todos os bairros efetivamente reconhecidos.
                if (
                    rosarioPriorityV666 != null &&
                    rosarioPriorityV666 < chosen.priorityIndex &&
                    lowerPriorityV666
                ) {
                    Prefs.setStatus(
                        this,
                        "VALIDANDO PRIORIDADE: Rosario acima de \${chosen.neighborhood} | " +
                            "leitura ampla..."
                    )
                    readDenseFullFallback(
                        media = media,
                        crop = denseBitmap,
                        rowCount = rowCount,
                        widthRatio = widthRatio,
                        decodeMs = decodeMs,
                        scanMs = scanMs,
                        reason = "v66.6 prioridade Rosario acima de \${chosen.neighborhood}"
                    )
                    return@addOnSuccessListener
                }

'''
    block=block+rescue
    s=s[:i]+block+s[end:]

old='V66.5 ROSARIO STRICT FULL NAME'
if old not in s: raise SystemExit("v66.5 diagnostic title missing")
s=s.replace(old,'V66.6 ROSARIO PRIORITY VERIFY',1)

if 'rosarioConfiguredPriorityV666' not in r or 'v66.6 prioridade Rosario acima de' not in s:
    raise SystemExit("v66.6 verification failed")
R.write_text(r,encoding="utf-8")
S.write_text(s,encoding="utf-8")
print("v66.6: mantém Rosário estrito contra Feu Rosa e relê tabela completa apenas quando OCR rápido escolhe Mata/República abaixo de Rosário")
