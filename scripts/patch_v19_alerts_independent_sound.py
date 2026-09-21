from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
activity_path = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")
layout_path = Path("app/src/main/res/layout/activity_main.xml")

s = service_path.read_text(encoding="utf-8")
a = activity_path.read_text(encoding="utf-8")
xml = layout_path.read_text(encoding="utf-8")

# v0.19 - alertas independentes + som real
# 1) Os 20 avisos NAO bloqueiam mais a leitura. O bot continua parado depois de
#    enviar, mas se a pessoa tocar PROCURAR NOVAMENTE antes dos 20 terminarem,
#    a busca recomeça imediatamente e os avisos continuam em paralelo.
# 2) Cria um NOVO canal de notificacao com IMPORTANCE_HIGH, som padrao e vibracao.
#    O ID novo e proposital: Android preserva configuracoes antigas do canal e
#    poderia manter um canal anterior silencioso mesmo alterando o codigo.
# 3) Adiciona botao para abrir/ativar notificacoes caso a permissao esteja negada
#    ou o som do canal tenha sido desligado nas configuracoes do Android.

# -----------------------------------------------------------------------------
# SERVICE - imports de som/notificacao.
# -----------------------------------------------------------------------------
if 'import android.media.AudioAttributes' not in s:
    anchor = 'import android.app.NotificationManager\n'
    if anchor not in s:
        raise SystemExit('patch alerts: NotificationManager import nao encontrado')
    s = s.replace(
        anchor,
        anchor + 'import android.media.AudioAttributes\nimport android.media.RingtoneManager\n',
        1
    )

# Novo channel ID para nao herdar um canal silencioso ja salvo pelo Android.
s = s.replace(
    '        private const val ROUTE_ALERT_CHANNEL_ID = "rota_enviada_20"\n',
    '        private const val ROUTE_ALERT_CHANNEL_ID = "rota_enviada_20_som_v2"\n',
    1
)

# -----------------------------------------------------------------------------
# Nao bloqueia eventos enquanto os 20 avisos ainda estao rodando.
# SearchArmed continua sendo a trava real: apos enviar fica false e so o botao
# PROCURAR NOVAMENTE coloca true.
# -----------------------------------------------------------------------------
s = s.replace(
    '        if (alertSequenceRunning) return\n\n        if (!processing && pendingRoute != null) {\n',
    '        if (!processing && pendingRoute != null) {\n',
    1
)

s = s.replace(
    '        if (alertSequenceRunning || processing) return false\n',
    '        if (processing) return false\n',
    1
)

# -----------------------------------------------------------------------------
# Canal + envio de notificacoes com som e vibracao.
# -----------------------------------------------------------------------------
channel_start = s.find('    private fun createRouteAlertChannel() {')
alerts_start = s.find('    private fun startTwentyAlerts(route: RouteResult, elapsedMs: Long) {', channel_start)
if channel_start < 0 or alerts_start < 0:
    raise SystemExit(
        f'patch alerts: bloco de notificacao nao encontrado '
        f'(channel={channel_start}, alerts={alerts_start})'
    )

new_channel_block = r'''    private fun canPostRouteNotifications(): Boolean {
        return Build.VERSION.SDK_INT < 33 ||
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
    }

    private fun createRouteAlertChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            val manager = getSystemService(NotificationManager::class.java)

            // Remove o canal antigo usado pelas primeiras versoes. O Android nao
            // permite que o app volte a ligar som de um canal antigo que ficou
            // salvo como silencioso; por isso usamos tambem um ID novo.
            try {
                manager.deleteNotificationChannel("rota_enviada_20")
            } catch (_: Throwable) {}

            val soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)
            val audioAttributes = AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build()

            val channel = NotificationChannel(
                ROUTE_ALERT_CHANNEL_ID,
                "Rota enviada - avisos com som",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "20 avisos sonoros depois que uma rota e enviada"
                enableVibration(true)
                vibrationPattern = longArrayOf(0L, 300L, 180L, 300L)
                setSound(soundUri, audioAttributes)
                setShowBadge(true)
            }
            manager.createNotificationChannel(channel)
        }
    }

    private fun postRouteAlert(
        route: RouteResult,
        index: Int,
        notificationId: Int
    ): Boolean {
        if (!canPostRouteNotifications()) {
            return false
        }

        val soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)
        val notification = NotificationCompat.Builder(this, ROUTE_ALERT_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Rota enviada (${index + 1}/$ROUTE_ALERT_COUNT)")
            .setContentText("${route.neighborhood} - Gaiola ${route.cage}")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setSound(soundUri)
            .setVibrate(longArrayOf(0L, 300L, 180L, 300L))
            .setAutoCancel(true)
            .build()

        NotificationManagerCompat.from(this).notify(notificationId, notification)
        return true
    }

'''

s = s[:channel_start] + new_channel_block + s[alerts_start:]

# -----------------------------------------------------------------------------
# Os avisos rodam localmente e nao usam mais alertSequenceRunning como trava.
# Cada sequencia ganha IDs proprios, entao se a pessoa rearmar e mandar outra
# rota antes dos 40 s, os avisos da rota anterior ainda conseguem completar.
# -----------------------------------------------------------------------------
alerts_start = s.find('    private fun startTwentyAlerts(route: RouteResult, elapsedMs: Long) {')
mark_start = s.find('    private fun markSent(route: RouteResult) {', alerts_start)
if alerts_start < 0 or mark_start < 0:
    raise SystemExit('patch alerts: startTwentyAlerts/markSent nao encontrados')

new_alerts = r'''    private fun startTwentyAlerts(route: RouteResult, elapsedMs: Long) {
        // Base unica por sequencia para uma nova rota nao sobrescrever os avisos
        // que ainda restam da rota anterior.
        val sequenceBase = ROUTE_ALERT_BASE_ID +
            ((SystemClock.elapsedRealtime() % 100_000L).toInt() * 100)
        val elapsedText = formatElapsedMs(elapsedMs)
        val signature = "${route.priorityIndex}:${route.cage}"

        fun fire(index: Int) {
            if (index >= ROUTE_ALERT_COUNT) {
                // So atualiza o status se esta ainda for a ultima rota enviada.
                // Uma sequencia antiga nao deve apagar o status de uma rota nova.
                if (lastSentSignature == signature) {
                    Prefs.setStatus(
                        this,
                        "ENVIADO: ${route.neighborhood} -> ${route.cage} | app=$elapsedText | " +
                            "20 avisos concluidos. BOT PARADO ate PROCURAR NOVAMENTE."
                    )
                }
                return
            }

            val posted = postRouteAlert(
                route = route,
                index = index,
                notificationId = sequenceBase + index
            )

            if (lastSentSignature == signature) {
                Prefs.setStatus(
                    this,
                    if (posted) {
                        "ENVIADO: ${route.neighborhood} -> ${route.cage} | app=$elapsedText | " +
                            "aviso Android ${index + 1}/$ROUTE_ALERT_COUNT"
                    } else {
                        "ENVIADO: ${route.neighborhood} -> ${route.cage} | app=$elapsedText | " +
                            "NOTIFICACOES BLOQUEADAS PELO ANDROID. Toque em ATIVAR AVISOS no APK."
                    }
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

# -----------------------------------------------------------------------------
# UI - botao para pedir permissao / abrir configuracoes do canal do app.
# -----------------------------------------------------------------------------
if 'buttonNotificationSettings' not in xml:
    search_button = '''        <Button
            android:id="@+id/buttonSearchAgain"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="12dp"
            android:text="PROCURAR NOVAMENTE" />
'''
    replacement = search_button + '''
        <Button
            android:id="@+id/buttonNotificationSettings"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:text="ATIVAR AVISOS / SOM" />
'''
    if search_button not in xml:
        raise SystemExit('patch alerts: buttonSearchAgain nao encontrado no XML')
    xml = xml.replace(search_button, replacement, 1)
layout_path.write_text(xml, encoding="utf-8")

if 'buttonNotificationSettings' not in a:
    var_anchor = '        val searchAgain = findViewById<Button>(R.id.buttonSearchAgain)\n'
    if var_anchor not in a:
        raise SystemExit('patch alerts: searchAgain var nao encontrada')
    a = a.replace(
        var_anchor,
        var_anchor + '        val notificationSettings = findViewById<Button>(R.id.buttonNotificationSettings)\n',
        1
    )

    listener_anchor = '''        searchAgain.setOnClickListener {
            Prefs.setSearchArmed(this, true)
            Prefs.setNeedsPrime(this, false)
            Prefs.setStatus(
                this,
                "Procurar novamente ativado. Aguardando rota no grupo configurado."
            )
        }
'''
    notification_listener = listener_anchor + '''

        notificationSettings.setOnClickListener {
            if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
            ) {
                requestPermissions(
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    715
                )
            } else {
                try {
                    val intent = Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).apply {
                        putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
                    }
                    startActivity(intent)
                } catch (_: Throwable) {
                    startActivity(Intent(Settings.ACTION_SETTINGS))
                }
            }
        }
'''
    if listener_anchor not in a:
        raise SystemExit('patch alerts: listener searchAgain nao encontrado')
    a = a.replace(listener_anchor, notification_listener, 1)

activity_path.write_text(a, encoding="utf-8")

print("Patch v0.19 ALERTAS INDEPENDENTES + SOM aplicado")
