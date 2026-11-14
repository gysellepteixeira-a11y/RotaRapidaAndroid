"""SMS imediato: nao aguardar grupo ser liberado pelo admin.
Roda APOS patch_v66_4_sms_only_switch.py.
"""
from pathlib import Path

S = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
G = Path("app/build.gradle.kts")
s = S.read_text(encoding="utf-8")

def exactly_once(old, new, desc):
    global s
    occurrences = s.count(old)
    if occurrences != 1:
        raise RuntimeError("SMS IMEDIATO: marcador %s encontrado %d vez(es)" % (desc, occurrences))
    s = s.replace(old, new, 1)

# Ao identificar a rota mesmo que o grupo esteja fechado, o bot
# chama holdRouteUntilChatOpen para aguardar o editor. Pular esse gate no SMS.
exactly_once(
    "    private fun holdRouteUntilChatOpen(route: RouteResult, reason: String) {\n",
    """    private fun holdRouteUntilChatOpen(route: RouteResult, reason: String) {
        if (Prefs.smsEnabled(this)) {
            sendSmsOnlyV664(route)
            return
        }
""",
    "rota reconhecida sem campo de mensagem",
)

# Tambem envia qualquer rota que ja estava pendente.
exactly_once(
    """    private fun trySendPendingRouteIfChatOpen(): Boolean {
        val route = pendingRoute ?: return false
""",
    """    private fun trySendPendingRouteIfChatOpen(): Boolean {
        val route = pendingRoute ?: return false
        if (Prefs.smsEnabled(this)) {
            if (processing || alertSequenceRunning) return false
            sendSmsOnlyV664(route)
            return true
        }
""",
    "resgate rota pendente sem admin",
)

# Pausa a busca apos o SMS igual ao bot normal.
old = """        SmsRelay.sendIfEnabled(this, buildMessage(route.cage))
        lastSentSignature = "@{route.priorityIndex}:@{route.cage}"
        lastSentAt = SystemClock.elapsedRealtime()
        Prefs.setStatus(
            this,
            "MODO SMS: @{route.neighborhood} -> @{route.cage} | @{Prefs.smsStatus(this)}"
        )
        handler.postDelayed({
            processing = false
            primeCurrentScreen()
        }, 220L)
"""
new = """        pendingRoute = null
        SmsRelay.sendIfEnabled(this, buildMessage(route.cage))
        lastSentSignature = "@{route.priorityIndex}:@{route.cage}"
        lastSentAt = SystemClock.elapsedRealtime()

        Prefs.setSearchArmed(this, false)
        Prefs.setNeedsPrime(this, false)
        Prefs.setLastMessage(this, "SMS solicitado:\\n" + buildMessage(route.cage))
        Prefs.setStatus(
            this,
            "MODO SMS (sem esperar admin): @{route.neighborhood} -> @{route.cage} | @{Prefs.smsStatus(this)}"
        )
        processing = false
"""
exactly_once(old.replace("@{", chr(36) + "{"), new.replace("@{", chr(36) + "{"), "parada SMS apos OCR")

for marker in [
    "private fun holdRouteUntilChatOpen(route: RouteResult, reason: String)",
    "private fun trySendPendingRouteIfChatOpen(): Boolean",
    "private fun sendSmsOnlyV664(route: RouteResult)",
    "Prefs.smsEnabled(this)",
    "ModalFilter.filter(",
]:
    if marker not in s:
        raise RuntimeError("SMS IMEDIATO: verificacao falhou: " + marker)

# Debug APK de teste separado: evita conflito de assinatura com build anterior.
g = G.read_text(encoding="utf-8")
needle = 'applicationIdSuffix = ".modalredfix.smsonly"'
if g.count(needle) != 1:
    raise RuntimeError("SMS IMEDIATO: ID de teste inesperado")
g = g.replace(needle, 'applicationIdSuffix = ".modalredfix.smsonly.immediate"')
G.write_text(g, encoding="utf-8")

S.write_text(s, encoding="utf-8")
print("SMS imediato apos reconhecimento de rota, independente do estado do grupo")
