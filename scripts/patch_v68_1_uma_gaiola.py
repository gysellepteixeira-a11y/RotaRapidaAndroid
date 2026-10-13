from pathlib import Path
p = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = p.read_text(encoding="utf-8")

def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"v68.1 {label}: esperado 1, encontrado {n}")
    s = s.replace(old, new, 1)

# Apenas a primeira gaiola do bairro prioritario por imagem.
# Se ela for duplicada, nao pula para a segunda.
once(
    "val rotas = resultado.gaiolas\n                        .map",
    "val rotas = resultado.gaiolas.take(1)\n                        .map",
    "limite de uma gaiola"
)
# Fila de outras gaiolas fica vazia; markSent da v68 usa envio normal.
once(
    "                    rotas.drop(1).forEach { pcCageQueueV68.addLast(it) }\n",
    "",
    "desativar fila"
)
once(
    'resultado.gaiolas.joinToString(", ") + " | " + ms + "ms; enviando."',
    'rotas.first().cage + " | " + ms + "ms; enviando 1 gaiola."',
    "log mostrar apenas a gaiola enviada"
)
assert "rotas.drop(1)" not in s
assert "resultado.gaiolas.take(1)" in s
p.write_text(s, encoding="utf-8")
print("v68.1 aplicado: uma gaiola por imagem, sem fila de envios")
