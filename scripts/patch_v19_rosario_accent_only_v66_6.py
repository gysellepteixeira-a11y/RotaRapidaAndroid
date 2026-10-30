from pathlib import Path

path = Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
source = path.read_text(encoding="utf-8")

start = source.find("    private fun priorityFor(text: String)")
if start < 0:
    raise SystemExit("priorityFor nao encontrado")
end = source.find("\n    }", start)
if end < 0:
    raise SystemExit("fim de priorityFor nao encontrado")
end += len("\n    }")
fn = source[start:end]

if "hasAccentedRosario" in fn:
    print("Regra de acento ja aplicada")
    raise SystemExit(0)

anchor = "        val normalized = normalize(text)"
if anchor not in fn:
    raise SystemExit("normalizacao de priorityFor nao encontrada")
fn = fn.replace(anchor, """        // Rosário só é aceito quando o OCR preserva o acento agudo.
        val hasAccentedRosario = Regex(
            """ + '"""(?i)(?<![\\p{L}])rosário(?![\\p{L}])"""' + """
        ).containsMatchIn(text)
        val normalized = normalize(text)""", 1)

loop = "        priorities.forEachIndexed { index, rule ->"
if loop not in fn:
    raise SystemExit("loop de prioridades nao encontrado")
fn = fn.replace(loop, loop + """
            if (
                normalize(rule.name) == "rosario" &&
                !hasAccentedRosario
            ) return@forEachIndexed""", 1)

source = source[:start] + fn + source[end:]
path.write_text(source, encoding="utf-8")
print("Rosario agora exige acento agudo literal; restante da v66.5 preservado")
