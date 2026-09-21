from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# Corrige a causa do bot so funcionar novamente depois de Forcar parada.
#
# A sequencia de patches anterior deixou `processing = true` apos um envio
# confirmado. O patch dos 20 avisos nao bloqueantes substituiu startTwentyAlerts()
# e removeu, sem querer, a linha que zerava `processing`. Com isso:
# - a primeira rota funciona;
# - depois do envio, onAccessibilityEvent() passa a retornar em `if (processing)`;
# - tocar em PROCURAR NOVAMENTE altera a preferencia, mas o service continua
#   preso em processing=true;
# - Forcar parada funciona porque recria o service e processing volta a false.
#
# A correcao e zerar o estado de processamento imediatamente quando o envio e
# confirmado. Os 20 avisos continuam em paralelo e o bot continua DESARMADO ate
# a pessoa tocar em PROCURAR NOVAMENTE.

mark_anchor = '''    private fun markSent(route: RouteResult) {
        pendingRoute = null
        Prefs.setSearchArmed(this, false)
'''
mark_replacement = '''    private fun markSent(route: RouteResult) {
        pendingRoute = null

        // O envio terminou de verdade. Libera o motor interno imediatamente.
        // A trava para procurar outra rota passa a ser SOMENTE searchArmed=false.
        processing = false
        analyzeScheduled = false

        Prefs.setSearchArmed(this, false)
'''

if mark_anchor not in s:
    raise SystemExit('patch_v19_processing_reset: inicio de markSent nao encontrado')

s = s.replace(mark_anchor, mark_replacement, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 PROCESSING RESET aplicado: envio nao deixa mais o service preso em processing=true")
