from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 STOP - corrige duas coisas sem mexer no OCR/parsers:
# 1) a primeira rota podia ser engolida quando o service ainda estava primed=false.
#    Isso acontece muito quando o prime de 350 ms roda enquanto a pessoa ainda esta
#    na tela do APK, e o primeiro evento real do WhatsApp ja e justamente a rota.
#    Agora a primeira tela do grupo NAO e descartada: usamos baseline vazio e
#    analisamos o proprio evento.
# 2) volta a mostrar o tempo total app=... desde a deteccao ate o envio confirmado,
#    inclusive durante os 20 avisos e no estado final BOT PARADO.

old_first_prime = '''        if (!primed) {
            previousTexts = currentSignatures
            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
            primed = true
            Prefs.setStatus(this, "Grupo confirmado. Aguardando uma nova rota.")
            return
        }
'''
new_first_prime = '''        if (!primed) {
            // Nao engole a primeira rota. Se o service ainda nao conseguiu criar
            // uma referencia antes de chegar ao WhatsApp, considera a tela atual
            // como potencialmente nova e continua a analise neste mesmo evento.
            previousTexts = emptySet()
            previousImageFingerprints = emptySet()
            primed = true
        }
'''
if old_first_prime not in s:
    raise SystemExit('patch_v19_first_route_timing_fix: bloco !primed nao encontrado')
s = s.replace(old_first_prime, new_first_prime, 1)

start = s.find('    private fun startTwentyAlerts(route: RouteResult) {')
end = s.find('    private fun isDuplicate(route: RouteResult): Boolean {', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'patch_v19_first_route_timing_fix: bloco alertas/markSent nao encontrado '
        f'(start={start}, end={end})'
    )

new_block = r'''    private fun formatElapsedMs(ms: Long): String {
        if (ms < 0L) return "--"
        return if (ms >= 1000L) {
            String.format(java.util.Locale.US, "%.2fs", ms / 1000.0)
        } else {
            "${ms}ms"
        }
    }

    private fun startTwentyAlerts(route: RouteResult, elapsedMs: Long) {
        alertSequenceRunning = true
        processing = false
        val elapsedText = formatElapsedMs(elapsedMs)

        fun fire(index: Int) {
            if (!alertSequenceRunning) return

            if (index >= ROUTE_ALERT_COUNT) {
                alertSequenceRunning = false
                processing = false
                Prefs.setStatus(
                    this,
                    "ENVIADO: ${route.neighborhood} -> ${route.cage} | app=$elapsedText | " +
                        "20 avisos concluidos. BOT PARADO. Toque em PROCURAR NOVAMENTE para buscar outra rota."
                )
                return
            }

            postRouteAlert(route, index)
            Prefs.setStatus(
                this,
                "ENVIADO: ${route.neighborhood} -> ${route.cage} | app=$elapsedText | " +
                    "aviso ${index + 1}/$ROUTE_ALERT_COUNT"
            )

            handler.postDelayed(
                { fire(index + 1) },
                ROUTE_ALERT_INTERVAL_MS
            )
        }

        fire(0)
    }

    private fun markSent(route: RouteResult) {
        pendingRoute = null
        Prefs.setSearchArmed(this, false)
        Prefs.setNeedsPrime(this, false)
        lastSentSignature = "${route.priorityIndex}:${route.cage}"
        lastSentAt = SystemClock.elapsedRealtime()

        val elapsed = if (currentStartedAt > 0L) {
            SystemClock.elapsedRealtime() - currentStartedAt
        } else {
            -1L
        }

        val message = buildMessage(route.cage)
        Prefs.setLastMessage(
            this,
            "Mensagem enviada:\n$message"
        )

        startTwentyAlerts(route, elapsed)
    }

'''

s = s[:start] + new_block + s[end:]
service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 FIRST ROUTE + TIMING aplicado: primeira rota nao e engolida e status mostra app=tempo")
