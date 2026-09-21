from pathlib import Path

parser_path = Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
p = parser_path.read_text(encoding="utf-8")

# O patch v0.11 altera internamente priorityFor para adicionar tolerancia OCR.
# A v0.22 precisa apenas expor esse MESMO matcher, sem mudar a ordem/prioridades.
if 'fun matchPriority(text: String)' not in p:
    marker = '''    /**\n     * Primeiro tenta o caso ideal: cada linha contém gaiola + bairro.\n'''
    helper = '''    fun matchPriority(text: String): Pair<Int, String>? {\n        return priorityFor(text)\n    }\n\n'''

    if marker not in p:
        raise SystemExit('Patch v0.22 pre: ponto antes de parsePlainTexts nao encontrado')

    p = p.replace(marker, helper + marker, 1)

parser_path.write_text(p, encoding="utf-8")
print("Patch v0.22 pre aplicado: matcher de prioridade existente exposto para OCR em duas etapas")
