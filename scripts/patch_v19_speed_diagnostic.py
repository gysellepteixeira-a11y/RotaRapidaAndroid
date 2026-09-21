from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
activity_path = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")
layout_path = Path("app/src/main/res/layout/activity_main.xml")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")
a = activity_path.read_text(encoding="utf-8")
xml = layout_path.read_text(encoding="utf-8")

# -----------------------------------------------------------------------------
# v0.19 - DIAGNOSTICO DE VELOCIDADE
#
# Nao muda a estrategia de leitura. Apenas mede e registra as etapas para ser
# possivel comparar alteracoes futuras como no bot do PC.
# -----------------------------------------------------------------------------

# PREFS: historico copiavel da ultima imagem.
if 'import android.os.SystemClock' not in prefs:
    prefs = prefs.replace(
        'import android.content.Context\n',
        'import android.content.Context\nimport android.os.SystemClock\n',
        1
    )

if 'KEY_SPEED_DIAGNOSTIC' not in prefs:
    prefs = prefs.replace(
        '    private fun prefs(context: Context) =\n',
        '    private const val KEY_SPEED_DIAGNOSTIC = "speed_diagnostic"\n'
        '    private const val KEY_SPEED_DIAGNOSTIC_ACTIVE = "speed_diagnostic_active"\n'
        '    private const val KEY_SPEED_DIAGNOSTIC_START = "speed_diagnostic_start"\n\n'
        '    private fun prefs(context: Context) =\n',
        1
    )

old_set_status = '''    fun setStatus(context: Context, value: String) {
        prefs(context).edit().putString(KEY_STATUS, value).apply()
    }
'''
new_set_status = '''    fun setStatus(context: Context, value: String) {
        val p = prefs(context)
        p.edit().putString(KEY_STATUS, value).apply()

        val lower = value.lowercase()
        val startsImageDiagnostic =
            lower.startsWith("imagem nova detectada")

        val now = SystemClock.elapsedRealtime()

        if (startsImageDiagnostic) {
            p.edit()
                .putBoolean(KEY_SPEED_DIAGNOSTIC_ACTIVE, true)
                .putLong(KEY_SPEED_DIAGNOSTIC_START, now)
                .putString(
                    KEY_SPEED_DIAGNOSTIC,
                    "===== DIAGNOSTICO IMAGEM v0.19 =====\\n[+0ms] $value"
                )
                .apply()
            return
        }

        if (!p.getBoolean(KEY_SPEED_DIAGNOSTIC_ACTIVE, false)) return

        // Os 20 avisos repetem o mesmo resultado e nao ajudam a analisar a
        // velocidade. Guardamos somente o primeiro ENVIADO e encerramos o trace.
        val isAlertSpam =
            lower.startsWith("enviado:") &&
            !lower.contains("aviso 1/20")

        if (isAlertSpam) return

        val started = p.getLong(KEY_SPEED_DIAGNOSTIC_START, now)
        val elapsed = (now - started).coerceAtLeast(0L)
        val old = p.getString(KEY_SPEED_DIAGNOSTIC, "").orEmpty()

        // Evita duplicar o mesmo status em eventos consecutivos.
        val lastLine = old.substringAfterLast('\\n')
        val normalizedLast = lastLine.substringAfter("] ", "")
        if (normalizedLast == value) return

        var updated = if (old.isBlank()) {
            "===== DIAGNOSTICO IMAGEM v0.19 =====\\n[+${elapsed}ms] $value"
        } else {
            "$old\\n[+${elapsed}ms] $value"
        }

        // SharedPreferences nao precisa carregar um log infinito.
        if (updated.length > 14000) {
            updated = updated.takeLast(14000)
        }

        val editor = p.edit().putString(KEY_SPEED_DIAGNOSTIC, updated)
        if (lower.startsWith("enviado:") && lower.contains("aviso 1/20")) {
            editor.putBoolean(KEY_SPEED_DIAGNOSTIC_ACTIVE, false)
        }
        editor.apply()
    }
'''
if old_set_status not in prefs:
    raise SystemExit('patch_v19_speed_diagnostic: setStatus nao encontrado')
prefs = prefs.replace(old_set_status, new_set_status, 1)

if 'fun speedDiagnostic(context: Context)' not in prefs:
    insert = '''
    fun speedDiagnostic(context: Context): String =
        prefs(context).getString(
            KEY_SPEED_DIAGNOSTIC,
            "Nenhum diagnostico de imagem ainda."
        ).orEmpty()
'''
    pos = prefs.rfind('\n}')
    if pos < 0:
        raise SystemExit('patch_v19_speed_diagnostic: fim de Prefs nao encontrado')
    prefs = prefs[:pos] + insert + prefs[pos:]

prefs_path.write_text(prefs, encoding="utf-8")

# LAYOUT: area de diagnostico + botao copiar.
if '@+id/textSpeedDiagnostic' not in xml:
    diagnostic_views = '''

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="24dp"
            android:text="Diagnóstico de velocidade da última imagem"
            android:textStyle="bold" />

        <TextView
            android:id="@+id/textSpeedDiagnostic"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="6dp"
            android:text="Nenhum diagnóstico de imagem ainda."
            android:textIsSelectable="true"
            android:textSize="13sp" />

        <Button
            android:id="@+id/buttonCopyDiagnostic"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="10dp"
            android:text="COPIAR DIAGNÓSTICO" />
'''
    close = '\n    </LinearLayout>\n</ScrollView>\n'
    if close not in xml:
        raise SystemExit('patch_v19_speed_diagnostic: fechamento do layout nao encontrado')
    xml = xml.replace(close, diagnostic_views + close, 1)

layout_path.write_text(xml, encoding="utf-8")

# MAIN ACTIVITY: atualiza o trace e copia com um toque.
if 'import android.content.ClipData' not in a:
    a = a.replace(
        'import android.content.Intent\n',
        'import android.content.ClipData\n'
        'import android.content.ClipboardManager\n'
        'import android.content.Context\n'
        'import android.content.Intent\n',
        1
    )
if 'import android.widget.Toast' not in a:
    a = a.replace(
        'import android.widget.TextView\n',
        'import android.widget.TextView\nimport android.widget.Toast\n',
        1
    )

if 'private lateinit var speedDiagnostic: TextView' not in a:
    a = a.replace(
        '    private lateinit var status: TextView\n',
        '    private lateinit var status: TextView\n'
        '    private lateinit var speedDiagnostic: TextView\n',
        1
    )

    refresh_anchor = '            status.text = Prefs.status(this@MainActivity)\n'
    if refresh_anchor not in a:
        raise SystemExit('patch_v19_speed_diagnostic: refresh de status nao encontrado')
    a = a.replace(
        refresh_anchor,
        refresh_anchor +
        '            speedDiagnostic.text = Prefs.speedDiagnostic(this@MainActivity)\n',
        1
    )

    init_anchor = '        status = findViewById(R.id.textStatus)\n'
    if init_anchor not in a:
        raise SystemExit('patch_v19_speed_diagnostic: init de status nao encontrado')
    a = a.replace(
        init_anchor,
        init_anchor +
        '        speedDiagnostic = findViewById(R.id.textSpeedDiagnostic)\n'
        '        val copyDiagnostic = findViewById<Button>(R.id.buttonCopyDiagnostic)\n',
        1
    )

    listener_anchor = '''        accessibility.setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
'''
    listener_new = listener_anchor + '''

        copyDiagnostic.setOnClickListener {
            val text = Prefs.speedDiagnostic(this)
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            clipboard.setPrimaryClip(
                ClipData.newPlainText("Diagnostico Rota Rapida", text)
            )
            Toast.makeText(this, "Diagnóstico copiado", Toast.LENGTH_SHORT).show()
        }
'''
    if listener_anchor not in a:
        raise SystemExit('patch_v19_speed_diagnostic: listener accessibility nao encontrado')
    a = a.replace(listener_anchor, listener_new, 1)

activity_path.write_text(a, encoding="utf-8")

# -----------------------------------------------------------------------------
# SERVICE: tempos extras que ainda nao apareciam nos status da v0.19.
# -----------------------------------------------------------------------------

# Tempo do query do MediaStore + altura do arquivo logo no primeiro status.
old_media = '''        currentImageWallTimeMs = System.currentTimeMillis()
        val media = findNewestWhatsAppImage() ?: return

        // Reserva o arquivo antes de iniciar OCR para nenhum outro evento pegar o
'''
new_media = '''        val mediaStoreStarted = SystemClock.elapsedRealtime()
        currentImageWallTimeMs = System.currentTimeMillis()
        val media = findNewestWhatsAppImage() ?: return
        val mediaStoreMs = SystemClock.elapsedRealtime() - mediaStoreStarted

        // Reserva o arquivo antes de iniciar OCR para nenhum outro evento pegar o
'''
if old_media not in s:
    raise SystemExit('patch_v19_speed_diagnostic: query MediaStore nao encontrado')
s = s.replace(old_media, new_media, 1)

old_detect_status = '''        Prefs.setStatus(
            this,
            "Imagem nova detectada direto nos arquivos do WhatsApp. OCR v0.19..."
        )
'''
new_detect_status = '''        Prefs.setStatus(
            this,
            "Imagem nova detectada direto nos arquivos do WhatsApp | " +
                "MediaStore=${mediaStoreMs}ms | h=${media.height}px | OCR v0.19..."
        )
'''
if old_detect_status not in s:
    raise SystemExit('patch_v19_speed_diagnostic: status inicial da imagem nao encontrado')
s = s.replace(old_detect_status, new_detect_status, 1)

# Estado para medir somente a etapa preencher/clicar/confirmar envio.
state_anchor = '    private var currentStartedAt = 0L\n'
if 'private var speedDiagnosticSendStartedAt' not in s:
    if state_anchor not in s:
        raise SystemExit('patch_v19_speed_diagnostic: currentStartedAt nao encontrado')
    s = s.replace(
        state_anchor,
        state_anchor + '    private var speedDiagnosticSendStartedAt = 0L\n',
        1
    )

# Helpers para editar apenas o corpo de uma funcao.
def function_block(text: str, signature: str, next_signature: str):
    start = text.find(signature)
    end = text.find(next_signature, start)
    if start < 0 or end < 0:
        raise SystemExit(
            f'patch_v19_speed_diagnostic: bloco nao encontrado {signature} -> {next_signature}'
        )
    return start, end, text[start:end]

# OCR completo: separa tempo ML Kit de parser.
start, end, block = function_block(
    s,
    '    private fun readMediaOriginalFull(media: MediaImage) {',
    '    private fun readMediaLargeColorCrop(media: MediaImage) {'
)
old_parse = '''                    val route = parseVisionText(visionText, parseHeight)
                    val elapsed = SystemClock.elapsedRealtime() - started
'''
new_parse = '''                    val ocrFinishedAt = SystemClock.elapsedRealtime()
                    val parserStarted = SystemClock.elapsedRealtime()
                    val route = parseVisionText(visionText, parseHeight)
                    val parserMs = SystemClock.elapsedRealtime() - parserStarted
                    val elapsed = ocrFinishedAt - started
'''
if old_parse not in block:
    raise SystemExit('patch_v19_speed_diagnostic: parse do OCR completo nao encontrado')
block = block.replace(old_parse, new_parse, 1)
block = block.replace(
    '"OCR=${elapsed}ms | enviando"',
    '"OCR=${elapsed}ms parse=${parserMs}ms | enviando"',
    1
)
s = s[:start] + block + s[end:]

# OCR denso: decode/scan/linhas/crop/escala ja existem; adiciona parser separado.
start, end, block = function_block(
    s,
    '    private fun readMediaLargeColorCrop(media: MediaImage) {',
    '    private fun prepareEnhancedFileBitmap(source: Bitmap): Bitmap {'
)
old_dense_parse = '''                val route = parseVisionText(visionText, crop.height)
                val elapsed = SystemClock.elapsedRealtime() - started
'''
new_dense_parse = '''                val ocrFinishedAt = SystemClock.elapsedRealtime()
                val parserStarted = SystemClock.elapsedRealtime()
                val route = parseVisionText(visionText, crop.height)
                val parserMs = SystemClock.elapsedRealtime() - parserStarted
                val elapsed = ocrFinishedAt - started
'''
if old_dense_parse not in block:
    raise SystemExit('patch_v19_speed_diagnostic: parse do OCR denso nao encontrado')
block = block.replace(old_dense_parse, new_dense_parse, 1)
block = block.replace(
    '"OCR=${elapsed}ms | enviando"',
    '"OCR=${elapsed}ms parse=${parserMs}ms | enviando"',
    1
)
s = s[:start] + block + s[end:]

# OCR reforcado: tambem separa parser quando o primeiro caminho nao fecha rota.
start, end, block = function_block(
    s,
    '    private fun readMediaEnhanced(media: MediaImage) {',
    '    private fun openImageFromSavedRect('
)
old_enhanced_parse = '''                    val route = parseVisionText(visionText, enhanced.height)
                    val elapsed = SystemClock.elapsedRealtime() - started
'''
new_enhanced_parse = '''                    val ocrFinishedAt = SystemClock.elapsedRealtime()
                    val parserStarted = SystemClock.elapsedRealtime()
                    val route = parseVisionText(visionText, enhanced.height)
                    val parserMs = SystemClock.elapsedRealtime() - parserStarted
                    val elapsed = ocrFinishedAt - started
'''
if old_enhanced_parse not in block:
    raise SystemExit('patch_v19_speed_diagnostic: parse do OCR reforcado nao encontrado')
block = block.replace(old_enhanced_parse, new_enhanced_parse, 1)
block = block.replace(
    '"OCR=${elapsed}ms | enviando sem abrir foto"',
    '"OCR=${elapsed}ms parse=${parserMs}ms | enviando sem abrir foto"',
    1
)
s = s[:start] + block + s[end:]

# Mede preenchimento + espera de confirmacao do WhatsApp.
send_start = s.find('    private fun sendRouteInCurrentChat(route: RouteResult) {')
send_end = s.find('    private fun currentEditorText(', send_start)
if send_start < 0 or send_end < 0:
    raise SystemExit('patch_v19_speed_diagnostic: sendRouteInCurrentChat nao encontrado')
send_block = s[send_start:send_end]

pending_anchor = '        pendingRoute = route\n        val message = buildMessage(route.cage)\n'
if pending_anchor not in send_block:
    raise SystemExit('patch_v19_speed_diagnostic: ponto inicial do envio nao encontrado')
send_block = send_block.replace(
    pending_anchor,
    '        speedDiagnosticSendStartedAt = SystemClock.elapsedRealtime()\n' + pending_anchor,
    1
)

handler_anchor = '''        handler.postDelayed(
            { tryClickSend(route, 0) },
            SEND_BUTTON_DELAY_MS
        )
'''
handler_new = '''        val fillMs = if (speedDiagnosticSendStartedAt > 0L) {
            SystemClock.elapsedRealtime() - speedDiagnosticSendStartedAt
        } else {
            -1L
        }
        Prefs.setStatus(
            this,
            "ENVIO: campo preenchido em ${formatElapsedMs(fillMs)} | " +
                "aguardando clique/confirmacao do WhatsApp..."
        )

        handler.postDelayed(
            { tryClickSend(route, 0) },
            SEND_BUTTON_DELAY_MS
        )
'''
if handler_anchor not in send_block:
    raise SystemExit('patch_v19_speed_diagnostic: postDelayed de envio nao encontrado')
send_block = send_block.replace(handler_anchor, handler_new, 1)
s = s[:send_start] + send_block + s[send_end:]

# Antes dos 20 avisos, registra o tempo da etapa de envio confirmada.
mark_start = s.find('    private fun markSent(route: RouteResult) {')
mark_end = s.find('    private fun isDuplicate(route: RouteResult): Boolean {', mark_start)
if mark_start < 0 or mark_end < 0:
    raise SystemExit('patch_v19_speed_diagnostic: markSent nao encontrado')
mark_block = s[mark_start:mark_end]

start_alert_anchor = '        startTwentyAlerts(route, elapsed)\n'
if start_alert_anchor not in mark_block:
    raise SystemExit('patch_v19_speed_diagnostic: startTwentyAlerts nao encontrado')
mark_block = mark_block.replace(
    start_alert_anchor,
    '''        val sendStageMs = if (speedDiagnosticSendStartedAt > 0L) {
            SystemClock.elapsedRealtime() - speedDiagnosticSendStartedAt
        } else {
            -1L
        }
        Prefs.setStatus(
            this,
            "CONFIRMADO: ${route.neighborhood} -> ${route.cage} | " +
                "envio=${formatElapsedMs(sendStageMs)} | app=${formatElapsedMs(elapsed)}"
        )
        speedDiagnosticSendStartedAt = 0L

        startTwentyAlerts(route, elapsed)
''',
    1
)
s = s[:mark_start] + mark_block + s[mark_end:]

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 SPEED DIAGNOSTIC aplicado: trace copiavel + MediaStore/OCR/parser/envio")
