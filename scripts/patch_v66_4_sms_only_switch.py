"""V66.4: SMS ON => apenas SMS; SMS OFF => apenas WhatsApp Android.
Executar depois de patch_v66_4_sms_iphone.py.
"""
from pathlib import Path

S = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
L = Path("app/src/main/res/layout/activity_main.xml")
A = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")
STR = Path("app/src/main/res/values/strings.xml")
G = Path("app/build.gradle.kts")

def exactly_once(s, old, new, label):
    n = s.count(old)
    if n != 1:
        raise RuntimeError("SMS ONLY: marcador inesperado %s (%d)" % (label, n))
    return s.replace(old, new, 1)

s = S.read_text(encoding="utf-8")
l = L.read_text(encoding="utf-8")
a = A.read_text(encoding="utf-8")
strings = STR.read_text(encoding="utf-8")
g = G.read_text(encoding="utf-8")

s = exactly_once(
    s,
    """    private fun markSent(route: RouteResult) {
        SmsRelay.sendIfEnabled(this, buildMessage(route.cage))""",
    """    private fun markSent(route: RouteResult) {""",
    "remover SMS apos WhatsApp",
)

sms_helper = """    private fun sendSmsOnlyV664(route: RouteResult) {
        if (isDuplicate(route)) {
            processing = false
            primeCurrentScreen()
            return
        }

        // Usa a mesma mensagem completa montada para o WhatsApp.
        // Nunca abre o editor nem tenta clicar em Enviar no WhatsApp.
        SmsRelay.sendIfEnabled(this, buildMessage(route.cage))
        lastSentSignature = "${route.priorityIndex}:${route.cage}"
        lastSentAt = SystemClock.elapsedRealtime()
        Prefs.setStatus(
            this,
            "MODO SMS: ${route.neighborhood} -> ${route.cage} | ${Prefs.smsStatus(this)}"
        )
        handler.postDelayed({
            processing = false
            primeCurrentScreen()
        }, 220L)
    }

"""
anchor = "    private fun sendRouteWhenChatReady(route: RouteResult, attempt: Int) {"
s = exactly_once(
    s,
    anchor,
    sms_helper + anchor + """
        if (Prefs.smsEnabled(this)) {
            sendSmsOnlyV664(route)
            return
        }
""",
    "bypass pronto para envio",
)

anchor = "    private fun sendRouteInCurrentChat(route: RouteResult) {"
s = exactly_once(
    s,
    anchor,
    anchor + """
        // Modo mutuamente exclusivo: SMS ativado desvia antes de tocar no WhatsApp.
        if (Prefs.smsEnabled(this)) {
            sendSmsOnlyV664(route)
            return
        }
""",
    "bypass envio direto",
)

l = exactly_once(
    l,
    'android:text="Enviar SMS alem do WhatsApp"',
    'android:text="Enviar SOMENTE SMS ao iPhone (desliga envio WhatsApp Android)"',
    "rotulo botao",
)

a = exactly_once(
    a,
    'Prefs.setSmsStatus(this, "SMS ativado para " + phone)',
    'Prefs.setSmsStatus(this, "MODO SOMENTE SMS ativado para " + phone)',
    "status modo SMS",
)
a = exactly_once(
    a,
    'Prefs.setSmsStatus(this, "Envio por SMS desativado.")',
    'Prefs.setSmsStatus(this, "Modo WhatsApp Android ativado (SMS desligado).")',
    "status modo WhatsApp",
)

strings = strings.replace(
    "Rota Rápida (MODAL + SMS iPhone)",
    "Rota Rápida (SMS OU WhatsApp)",
)
g = exactly_once(
    g,
    'applicationIdSuffix = ".modalredfix"',
    'applicationIdSuffix = ".modalredfix.smsonly"',
    "instalacao paralela e segura",
)

for path, data in [(S, s), (L, l), (A, a), (STR, strings), (G, g)]:
    path.write_text(data, encoding="utf-8")

for marker in ["ModalFilter.filter(", "sendSmsOnlyV664(route)", "R.id.switchIncludeFake"]:
    if marker not in s+a:
        raise RuntimeError("SMS ONLY: recurso original ausente: " + marker)

print("SMS ONLY pronto: SMS ligado => SMS apenas; desligado => WhatsApp apenas.")
