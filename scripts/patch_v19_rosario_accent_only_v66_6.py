from pathlib import Path

path = Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
source = path.read_text(encoding="utf-8")

anchor = """    private fun priorityFor(text: String): Pair<Int, String>? {
        val normalized = normalize(text)
"""
replacement = """    private fun priorityFor(text: String): Pair<Int, String>? {
        // Rosário só é reconhecido quando o OCR preserva o acento agudo.
        val hasAccentedRosario = Regex(
            """ + '"""(?i)(?<![\\p{L}])rosário(?![\\p{L}])"""' + """
        ).containsMatchIn(text)

        val normalized = normalize(text)
"""
if anchor not in source:
    if "hasAccentedRosario" in source:
        print("Regra de acento ja aplicada")
        raise SystemExit(0)
    raise SystemExit("Ancora priorityFor v66.5 nao encontrada")

source = source.replace(anchor, replacement, 1)
loop = """        priorities.forEachIndexed { index, rule ->
            if (rule.requiredTokens.all { normalized.contains(it) }) {
"""
guarded = """        priorities.forEachIndexed { index, rule ->
            if (rule.name == "Rosario" && !hasAccentedRosario) {
                return@forEachIndexed
            }
            if (rule.requiredTokens.all { normalized.contains(it) }) {
"""
if loop not in source:
    raise SystemExit("Loop de prioridades v66.5 nao encontrado")
source = source.replace(loop, guarded, 1)
path.write_text(source, encoding="utf-8")
print("Rosario agora exige acento agudo literal; demais bairros permanecem iguais")
