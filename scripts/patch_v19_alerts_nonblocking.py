from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - 20 avisos totalmente independentes da busca
#
# Problema observado:
# - depois de enviar uma rota, os 20 avisos continuam por ~40 s;
# - mesmo tocando em PROCURAR NOVAMENTE antes do aviso 20, o service ignorava
#   os eventos do WhatsApp por causa de alertSequenceRunning;
# - ao terminar os 20 avisos, a rotina ainda podia alterar processing/status e
#   interferir em uma nova leitura ja iniciada.
#
# Ajuste:
# - notificacoes continuam as 20, de 2 em 2 segundos;
# - tocar PROCURAR NOVAMENTE libera a leitura IMEDIATAMENTE, sem esperar os 20;
# - a sequencia antiga nao muda processing e nao pode interromper OCR/envio novo;
# - cada sequencia usa IDs proprios para nao sobrescrever uma nova sequencia.

# 1) Nao bloquear eventos do WhatsApp durante os 20 avisos.
s = s.replace(
    '        if (alertSequenceRunning) return\n\n'
    '        // Uma rota que JA foi encontrada continua pendente ate conseguir enviar.\n',
    '        // Uma rota que JA foi encontrada continua pendente ate conseguir enviar.\n',
    1
)

# 2) Rota pendente tambem pode ser enviada enquanto os avisos anteriores continuam.
s = s.replace(
    '        if (alertSequenceRunning || processing) return false\n',
    '        if (processing) return false\n',
    1
)

# 3) Cada sequencia de notificacao recebe IDs proprios e nao cancela outra sequencia.
post_start = s.find('    private fun postRouteAlert(route: RouteResult, index: Int) {')
post_end = s.find('    private fun formatElapsedMs(ms: Long): String {', post_start)
if post_start < 0 or post_end < 0:
    raise SystemExit(
        f'patch_v19_alerts_nonblocking: postRouteAlert/formatElapsedMs nao encontrados '
        f'(post={post_start}, format={post_end})'
    )

new_post = r'''    private fun postRouteAlert(
        route: RouteResult,
        index: Int,
        notificationId: Int
    ) {
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        val notification = NotificationCompat.Builder(this, ROUTE_ALERT_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Rota enviada (${index + 1}/$ROUTE_ALERT_COUNT)")
            .setContentText("${route.neighborhood} - Gaiola ${route.cage}")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setAutoCancel(true)
            .build()

        NotificationManagerCompat.from(this).notify(notificationId, notification)
    }

'''
s = s[:post_start] + new_post + s[post_end:]

# 4) Avisos em paralelo: nunca mexem em processing/searchArmed.
alerts_start = s.find('    private fun startTwentyAlerts(route: RouteResult, elapsedMs: Long) {')
mark_start = s.find('    private fun markSent(route: RouteResult) {', alerts_start)
if alerts_start < 0 or mark_start < 0:
    raise SystemExit(
        f'patch_v19_alerts_nonblocking: startTwentyAlerts/markSent nao encontrados '
        f'(alerts={alerts_start}, mark={mark_start})'
    )

new_alerts = r'''    private fun startTwentyAlerts(route: RouteResult, elapsedMs: Long) {
        val elapsedText = formatElapsedMs(elapsedMs)
        val signature = "${route.priorityIndex}:${route.cage}"

        // IDs exclusivos desta sequencia. Assim, se uma nova rota for enviada
        // antes de estes 20 avisos terminarem, uma sequencia nao apaga a outra.
        val sequenceBase = ROUTE_ALERT_BASE_ID +
            ((SystemClock.elapsedRealtime() % 1_000_000L).toInt() * 100)

        fun fire(index: Int) {
            if (index >= ROUTE_ALERT_COUNT) {
                // Se a pessoa ainda nao rearmou, mostramos que o bot segue parado.
                // Se ja tocou PROCURAR NOVAMENTE, nao sobrescrevemos o status da
                // nova busca e, principalmente, nao alteramos processing.
                if (!Prefs.searchArmed(this) && lastSentSignature == signature) {
                    Prefs.setStatus(
                        this,
                        "ENVIADO: ${route.neighborhood} -> ${route.cage} | app=$elapsedText | " +
                            "20 avisos concluidos. BOT PARADO. Toque em PROCURAR NOVAMENTE para buscar outra rota."
                    )
                }
                return
            }

            postRouteAlert(
                route = route,
                index = index,
                notificationId = sequenceBase + index
            )

            // A contagem aparece no APK apenas enquanto o bot continua parado.
            // Ao rearmar, os avisos seguem no Android sem atrapalhar a leitura.
            if (!Prefs.searchArmed(this) && lastSentSignature == signature) {
                Prefs.setStatus(
                    this,
                    "ENVIADO: ${route.neighborhood} -> ${route.cage} | app=$elapsedText | " +
                        "aviso ${index + 1}/$ROUTE_ALERT_COUNT"
                )
            }

            handler.postDelayed(
                { fire(index + 1) },
                ROUTE_ALERT_INTERVAL_MS
            )
        }

        fire(0)
    }

'''
s = s[:alerts_start] + new_alerts + s[mark_start:]

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 aplicado: 20 avisos independentes; PROCURAR NOVAMENTE libera leitura imediatamente")
