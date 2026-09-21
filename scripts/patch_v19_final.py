from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
parser_path = Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
activity_path = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")
layout_path = Path("app/src/main/res/layout/activity_main.xml")
manifest_path = Path("app/src/main/AndroidManifest.xml")

s = service_path.read_text(encoding="utf-8")
p = parser_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")
a = activity_path.read_text(encoding="utf-8")
xml = layout_path.read_text(encoding="utf-8")
m = manifest_path.read_text(encoding="utf-8")

# -----------------------------------------------------------------------------
# 1) SOMENTE AS 7 PRIORIDADES PEDIDAS
# -----------------------------------------------------------------------------
for line in [
    '        PriorityRule("Helio Ferraz", listOf("helio", "ferraz")),\n',
    '        PriorityRule("Parque Residencial Laranjeiras", listOf("parque", "residencial", "laranjeiras")),\n',
    '        PriorityRule("Barcelona", listOf("barcelona")),\n',
    '        PriorityRule("Maringa", listOf("maringa"))\n',
]:
    p = p.replace(line, '')

parser_path.write_text(p, encoding="utf-8")

old_priority_text = (
    '1. Valparaiso&#10;2. Colina de Laranjeiras&#10;3. Praia da Baleia&#10;'
    '4. Morada de Laranjeiras&#10;5. Eurico&#10;6. Manoel Plaza&#10;7. Rosario&#10;'
    '8. Helio Ferraz&#10;9. Parque Residencial Laranjeiras&#10;10. Barcelona&#10;11. Maringa'
)
new_priority_text = (
    '1. Valparaiso&#10;2. Colina de Laranjeiras&#10;3. Praia da Baleia&#10;'
    '4. Morada de Laranjeiras&#10;5. Eurico&#10;6. Manoel Plaza&#10;7. Rosario'
)
xml = xml.replace(old_priority_text, new_priority_text)

# -----------------------------------------------------------------------------
# 2) "MENSAGEM ENVIADA" PASSA A SER DINAMICA
# -----------------------------------------------------------------------------
old_message_view = '''        <TextView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="22dp"
            android:text="Mensagem enviada:&#10;Felipe lima de Castilho&#10;1347515&#10;Passeio&#10;Gaiola: g03"
            android:textSize="14sp" />
'''
new_message_view = '''        <TextView
            android:id="@+id/textLastMessage"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="22dp"
            android:text="Mensagem enviada:&#10;Nenhuma rota enviada ainda."
            android:textIsSelectable="true"
            android:textSize="14sp" />
'''
if old_message_view not in xml:
    raise SystemExit('patch_v19_final: TextView estatico de Mensagem enviada nao encontrado')
xml = xml.replace(old_message_view, new_message_view, 1)
layout_path.write_text(xml, encoding="utf-8")

if 'KEY_LAST_MESSAGE' not in prefs:
    prefs = prefs.replace(
        '    private const val KEY_STATUS = "status"\n',
        '    private const val KEY_STATUS = "status"\n'
        '    private const val KEY_LAST_MESSAGE = "last_message"\n',
        1
    )

    prefs = prefs.replace(
        '    fun setStatus(context: Context, value: String) {\n'
        '        prefs(context).edit().putString(KEY_STATUS, value).apply()\n'
        '    }\n',
        '    fun setStatus(context: Context, value: String) {\n'
        '        prefs(context).edit().putString(KEY_STATUS, value).apply()\n'
        '    }\n\n'
        '    fun lastMessage(context: Context): String =\n'
        '        prefs(context).getString(\n'
        '            KEY_LAST_MESSAGE,\n'
        '            "Mensagem enviada:\\nNenhuma rota enviada ainda."\n'
        '        ).orEmpty()\n\n'
        '    fun setLastMessage(context: Context, value: String) {\n'
        '        prefs(context).edit().putString(KEY_LAST_MESSAGE, value).apply()\n'
        '    }\n',
        1
    )
prefs_path.write_text(prefs, encoding="utf-8")

if 'private lateinit var lastMessage: TextView' not in a:
    a = a.replace(
        '    private lateinit var status: TextView\n',
        '    private lateinit var status: TextView\n'
        '    private lateinit var lastMessage: TextView\n',
        1
    )

    a = a.replace(
        '            status.text = Prefs.status(this@MainActivity)\n',
        '            status.text = Prefs.status(this@MainActivity)\n'
        '            lastMessage.text = Prefs.lastMessage(this@MainActivity)\n',
        1
    )

    a = a.replace(
        '        status = findViewById(R.id.textStatus)\n',
        '        status = findViewById(R.id.textStatus)\n'
        '        lastMessage = findViewById(R.id.textLastMessage)\n',
        1
    )

# -----------------------------------------------------------------------------
# 3) PERMISSAO DE NOTIFICACAO PARA OS 20 AVISOS
# -----------------------------------------------------------------------------
if 'POST_NOTIFICATIONS' not in m:
    marker = '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
    if marker not in m:
        raise SystemExit('patch_v19_final: marker do manifest nao encontrado')
    m = m.replace(
        marker,
        marker + '\n    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />\n',
        1
    )
manifest_path.write_text(m, encoding="utf-8")

if 'requestNotificationPermissionIfNeeded' not in a:
    # patch_v14 ja adiciona Manifest, PackageManager e Build.
    call_anchor = '        requestImagePermissionIfNeeded()\n'
    if call_anchor not in a:
        raise SystemExit('patch_v19_final: requestImagePermissionIfNeeded nao encontrado')
    a = a.replace(
        call_anchor,
        call_anchor + '        requestNotificationPermissionIfNeeded()\n',
        1
    )

    helper_anchor = '    override fun onResume() {\n'
    helper = '''    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                715
            )
        }
    }

'''
    if helper_anchor not in a:
        raise SystemExit('patch_v19_final: ponto para helper de notificacao nao encontrado')
    a = a.replace(helper_anchor, helper + helper_anchor, 1)
activity_path.write_text(a, encoding="utf-8")

# -----------------------------------------------------------------------------
# 4) SERVICO: 20 AVISOS, PAUSA DURANTE AVISOS E ROTA PENDENTE ATE ABRIR O GRUPO
# -----------------------------------------------------------------------------
if 'import android.app.NotificationChannel' not in s:
    import_anchor = 'import android.Manifest\n'
    extra = (
        'import android.app.NotificationChannel\n'
        'import android.app.NotificationManager\n'
        'import android.Manifest\n'
    )
    if import_anchor not in s:
        raise SystemExit('patch_v19_final: import android.Manifest nao encontrado')
    s = s.replace(import_anchor, extra, 1)

if 'import androidx.core.app.NotificationCompat' not in s:
    anchor = 'import com.google.mlkit.vision.common.InputImage\n'
    if anchor not in s:
        raise SystemExit('patch_v19_final: import InputImage nao encontrado')
    s = s.replace(
        anchor,
        'import androidx.core.app.NotificationCompat\n'
        'import androidx.core.app.NotificationManagerCompat\n'
        + anchor,
        1
    )

if 'ROUTE_ALERT_CHANNEL_ID' not in s:
    const_anchor = '        private const val DEDUP_MS = 8_000L\n'
    if const_anchor not in s:
        raise SystemExit('patch_v19_final: DEDUP_MS nao encontrado')
    s = s.replace(
        const_anchor,
        const_anchor +
        '        private const val ROUTE_ALERT_CHANNEL_ID = "rota_enviada_20"\n'
        '        private const val ROUTE_ALERT_COUNT = 20\n'
        '        private const val ROUTE_ALERT_INTERVAL_MS = 2_000L\n'
        '        private const val ROUTE_ALERT_BASE_ID = 9100\n',
        1
    )

state_anchor = '    private var currentStartedAt = 0L\n'
if 'private var pendingRoute: RouteResult?' not in s:
    if state_anchor not in s:
        raise SystemExit('patch_v19_final: estado currentStartedAt nao encontrado')
    s = s.replace(
        state_anchor,
        state_anchor +
        '    private var pendingRoute: RouteResult? = null\n'
        '    private var alertSequenceRunning = false\n',
        1
    )

# Cria canal ao conectar o servico.
service_connect_anchor = '        Prefs.setStatus(this, "Serviço de acessibilidade conectado.")\n'
if 'createRouteAlertChannel()' not in s:
    if service_connect_anchor not in s:
        raise SystemExit('patch_v19_final: onServiceConnected nao encontrado')
    s = s.replace(
        service_connect_anchor,
        service_connect_anchor + '        createRouteAlertChannel()\n',
        1
    )

# Enquanto os 20 avisos rodam, nao le nova rota. Se ha rota pendente, tenta enviar
# assim que o grupo correto estiver aberto.
event_old = '''        inspectImageHint(event)

        if (processing) return
        scheduleAnalyze(12L)
'''
event_new = '''        if (alertSequenceRunning) return

        if (!processing && pendingRoute != null) {
            if (trySendPendingRouteIfChatOpen()) return
        }

        inspectImageHint(event)

        if (processing) return
        scheduleAnalyze(12L)
'''
if event_old not in s:
    raise SystemExit('patch_v19_final: bloco onAccessibilityEvent nao encontrado')
s = s.replace(event_old, event_new, 1)

# Substitui apenas sendRouteInCurrentChat; toda a confirmacao de envio da v0.16/v0.17
# continua sendo usada depois que o grupo correto estiver realmente aberto.
send_start = s.find('    private fun sendRouteInCurrentChat(route: RouteResult) {')
send_end = s.find('    private fun currentEditorText(', send_start)
if send_start < 0 or send_end < 0:
    raise SystemExit(
        f'patch_v19_final: sendRouteInCurrentChat nao encontrado (start={send_start}, end={send_end})'
    )

new_send = r'''    private fun holdRouteUntilChatOpen(route: RouteResult, reason: String) {
        pendingRoute = route
        processing = false
        Prefs.setStatus(
            this,
            "Rota pronta: ${route.neighborhood} -> ${route.cage}. " +
                "$reason Abra o grupo ${Prefs.groupName(this)} e eu envio automaticamente."
        )
    }

    private fun trySendPendingRouteIfChatOpen(): Boolean {
        val route = pendingRoute ?: return false
        if (alertSequenceRunning || processing) return false

        val root = rootInActiveWindow ?: return false
        val items = collectNodeItems(root)
        val group = Prefs.groupName(this)

        if (!isTargetGroup(items, group)) return false
        if (findMessageEditor(items) == null) return false

        processing = true
        currentStartedAt = SystemClock.elapsedRealtime()
        Prefs.setStatus(
            this,
            "Grupo aberto. Enviando rota pendente: ${route.neighborhood} -> ${route.cage}..."
        )
        sendRouteInCurrentChat(route)
        return true
    }

    private fun sendRouteInCurrentChat(route: RouteResult) {
        if (isDuplicate(route)) {
            pendingRoute = null
            processing = false
            primeCurrentScreen()
            return
        }

        val root = rootInActiveWindow
        if (root == null) {
            holdRouteUntilChatOpen(route, "WhatsApp/grupo fechado.")
            return
        }

        val items = collectNodeItems(root)
        val group = Prefs.groupName(this)

        if (!isTargetGroup(items, group)) {
            holdRouteUntilChatOpen(route, "O grupo nao esta aberto.")
            return
        }

        val editor = findMessageEditor(items)
        if (editor == null) {
            holdRouteUntilChatOpen(route, "O campo de mensagem ainda nao apareceu.")
            return
        }

        pendingRoute = route
        val message = buildMessage(route.cage)

        val args = Bundle().apply {
            putCharSequence(
                AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                message
            )
        }

        val setOk = editor.node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        )

        if (!setOk) {
            holdRouteUntilChatOpen(route, "Nao consegui preencher o campo agora.")
            return
        }

        handler.postDelayed(
            { tryClickSend(route, 0) },
            SEND_BUTTON_DELAY_MS
        )
    }

'''
s = s[:send_start] + new_send + s[send_end:]

# Se a pessoa sair do grupo no meio das tentativas, nao perde a rota e nao envia em
# outro chat: guarda e espera o grupo correto abrir de novo.
try_start = s.find('    private fun tryClickSend(route: RouteResult, attempt: Int) {')
if try_start < 0:
    raise SystemExit('patch_v19_final: tryClickSend nao encontrado')
items_pos = s.find('        val items = collectNodeItems(root)\n', try_start)
if items_pos < 0:
    raise SystemExit('patch_v19_final: items de tryClickSend nao encontrado')
insert_pos = items_pos + len('        val items = collectNodeItems(root)\n')
check_group = '''
        if (!isTargetGroup(items, Prefs.groupName(this))) {
            holdRouteUntilChatOpen(route, "O grupo foi fechado antes de concluir o envio.")
            return
        }
'''
s = s[:insert_pos] + check_group + s[insert_pos:]

verify_start = s.find('    private fun verifySendResult(route: RouteResult, attempt: Int) {')
if verify_start < 0:
    raise SystemExit('patch_v19_final: verifySendResult nao encontrado')
verify_items = s.find('        val items = collectNodeItems(root)\n', verify_start)
if verify_items < 0:
    raise SystemExit('patch_v19_final: items de verifySendResult nao encontrado')
verify_insert = verify_items + len('        val items = collectNodeItems(root)\n')
s = s[:verify_insert] + check_group + s[verify_insert:]

# Nas desistencias do envio, em vez de apagar a rota, deixa pendente.
s = s.replace(
    '                processing = false\n'
    '                Prefs.setStatus(this, "Mensagem preenchida, mas perdi a janela do WhatsApp.")\n',
    '                holdRouteUntilChatOpen(route, "Perdi a janela do WhatsApp antes de enviar.")\n',
    1
)
s = s.replace(
    '                processing = false\n'
    '                Prefs.setStatus(this, "Mensagem preenchida, mas nao achei mais o campo de mensagem.")\n',
    '                holdRouteUntilChatOpen(route, "O campo de mensagem sumiu antes de enviar.")\n',
    1
)
old_final_retry = '''        } else {
            processing = false
            Prefs.setStatus(
                this,
                "Mensagem ficou no campo: nao consegui confirmar o clique em Enviar."
            )
            handler.postDelayed({ primeCurrentScreen() }, 150L)
        }
'''
new_final_retry = '''        } else {
            holdRouteUntilChatOpen(
                route,
                "Nao consegui confirmar o envio agora."
            )
        }
'''
if old_final_retry not in s:
    raise SystemExit('patch_v19_final: final de scheduleNextSendAttempt nao encontrado')
s = s.replace(old_final_retry, new_final_retry, 1)

# markSent: atualiza a mensagem real exibida no APK, pausa leitura e dispara 20 avisos.
mark_start = s.find('    private fun markSent(route: RouteResult) {')
mark_end = s.find('    private fun isDuplicate(route: RouteResult): Boolean {', mark_start)
if mark_start < 0 or mark_end < 0:
    raise SystemExit(
        f'patch_v19_final: markSent nao encontrado (start={mark_start}, end={mark_end})'
    )

new_mark = r'''    private fun createRouteAlertChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            val manager = getSystemService(NotificationManager::class.java)
            val channel = NotificationChannel(
                ROUTE_ALERT_CHANNEL_ID,
                "Rota enviada",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "20 avisos depois que uma rota e enviada"
                enableVibration(true)
                vibrationPattern = longArrayOf(0L, 280L, 180L, 280L)
            }
            manager.createNotificationChannel(channel)
        }
    }

    private fun postRouteAlert(route: RouteResult, index: Int) {
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        val manager = NotificationManagerCompat.from(this)
        if (index > 0) {
            manager.cancel(ROUTE_ALERT_BASE_ID + index - 1)
        }

        val notification = NotificationCompat.Builder(this, ROUTE_ALERT_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Rota enviada (${index + 1}/$ROUTE_ALERT_COUNT)")
            .setContentText("${route.neighborhood} - Gaiola ${route.cage}")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setAutoCancel(true)
            .build()

        manager.notify(ROUTE_ALERT_BASE_ID + index, notification)
    }

    private fun startTwentyAlerts(route: RouteResult) {
        alertSequenceRunning = true
        processing = false

        fun fire(index: Int) {
            if (!alertSequenceRunning) return

            if (index >= ROUTE_ALERT_COUNT) {
                alertSequenceRunning = false
                Prefs.setStatus(
                    this,
                    "ENVIADO: ${route.neighborhood} -> ${route.cage} | 20 avisos concluidos."
                )
                handler.postDelayed({ primeCurrentScreen() }, 120L)
                return
            }

            postRouteAlert(route, index)
            Prefs.setStatus(
                this,
                "ENVIADO: ${route.neighborhood} -> ${route.cage} | aviso ${index + 1}/$ROUTE_ALERT_COUNT"
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
        lastSentSignature = "${route.priorityIndex}:${route.cage}"
        lastSentAt = SystemClock.elapsedRealtime()

        val message = buildMessage(route.cage)
        Prefs.setLastMessage(
            this,
            "Mensagem enviada:\n$message"
        )

        startTwentyAlerts(route)
    }

'''
s = s[:mark_start] + new_mark + s[mark_end:]

service_path.write_text(s, encoding="utf-8")

print("patch_v19_final aplicado: 7 prioridades + mensagem dinamica + 20 avisos + espera grupo abrir")
