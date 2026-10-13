from pathlib import Path

# Esta alteracao roda no final do workflow ORIGINAL da v66,
# depois de todos os patches v18..v66. Nao altera o parser de textos.
src = Path("app/src/main/java/com/gy/rotarapida")
f = src / "WhatsRouteAccessibilityService.kt"
s = f.read_text(encoding="utf-8")

def replace_once(old, new, label):
    global s
    if s.count(old) != 1:
        raise SystemExit("v68: esperado 1 anchor para " + label + "; encontrados=" + str(s.count(old)))
    s = s.replace(old, new, 1)

replace_once(
    "import android.graphics.BitmapFactory\n",
    "import android.graphics.BitmapFactory\nimport java.io.ByteArrayOutputStream\nimport java.util.ArrayDeque\nimport java.util.concurrent.Executors\n",
    "imports da ponte"
)
replace_once(
    "    private val handler = Handler(Looper.getMainLooper())\n",
    """    private val handler = Handler(Looper.getMainLooper())
    private val pcExecutorV68 = Executors.newSingleThreadExecutor { r ->
        Thread(r, "RyzenUSB-v68").apply { isDaemon = true }
    }
    private val pcCageQueueV68 = ArrayDeque<RouteResult>()
""",
    "executor OCR de fundo"
)
replace_once(
    "    override fun onDestroy() {\n",
    """    override fun onDestroy() {
        pcExecutorV68.shutdownNow()
        pcCageQueueV68.clear()
""",
    "shutdown da ponte"
)

# O MediaStore da v66 ja fornece a URI do arquivo original.
# Mantemos o corpo ORIGINAL de readMediaOriginal no novo metodo readMediaLocalV68;
# ele somente e chamado quando Ryzen estiver desligado, indisponivel ou inconclusivo.
replace_once(
    "    private fun readMediaOriginal(media: MediaImage) {\n",
    """    private fun readMediaOriginal(media: MediaImage) {
        if (!processing) return
        if (!Prefs.pcOcrEnabledV68(this)) {
            readMediaLocalV68(media)
            return
        }
        readMediaViaRyzenV68(media)
    }

    private fun readMediaViaRyzenV68(media: MediaImage) {
        val started = SystemClock.elapsedRealtime()
        try {
            pcExecutorV68.execute {
                val resultado = try {
                    val jpg = contentResolver.openInputStream(media.uri)?.use { input ->
                        val output = ByteArrayOutputStream(250_000)
                        val buf = ByteArray(32768)
                        while (true) {
                            val n = input.read(buf)
                            if (n < 0) break
                            if (n == 0) continue
                            if (output.size() + n > 4_000_000) break
                            output.write(buf, 0, n)
                        }
                        if (output.size() in 1..4_000_000) output.toByteArray() else null
                    }
                    if (jpg == null) null else RyzenOcrBridgeV68.reconhecer(jpg)
                } catch (_: Throwable) {
                    null
                }
                handler.post {
                    if (!processing) return@post
                    if (resultado == null) {
                        Prefs.setStatus(this, "Ryzen offline/sem resultado; usando OCR local v66.")
                        readMediaLocalV68(media)
                        return@post
                    }
                    val rotas = resultado.gaiolas
                        .map { RouteResult(resultado.bairro, it, resultado.priority) }
                        .filterNot { isDuplicate(it) }
                    if (rotas.isEmpty()) {
                        finishFileOnlyFailure("Ryzen: rota repetida ignorada.")
                        return@post
                    }
                    pcCageQueueV68.clear()
                    rotas.drop(1).forEach { pcCageQueueV68.addLast(it) }
                    val ms = SystemClock.elapsedRealtime() - started
                    Prefs.setStatus(
                        this,
                        "RYZEN USB v68: " + resultado.bairro + " -> " +
                            resultado.gaiolas.joinToString(", ") + " | " + ms + "ms; enviando."
                    )
                    sendRouteInCurrentChat(rotas.first())
                }
            }
        } catch (_: Throwable) {
            readMediaLocalV68(media)
        }
    }

    private fun readMediaLocalV68(media: MediaImage) {
""",
    "interceptador MediaStore"
)

# Uma mensagem POR gaiola. Marca apenas ultima concluida e conserva
# o tratamento preexistente de grupo fechado para os proximos envios.
mark_start = s.find("    private fun markSent(route: RouteResult) {")
mark_end = s.find("    private fun isDuplicate(route: RouteResult)", mark_start)
if mark_start < 0 or mark_end < 0:
    raise SystemExit("v68: markSent e isDuplicate nao encontrados")
block = s[mark_start:mark_end]
anchor = "        startTwentyAlerts(route, elapsed)"
if block.count(anchor) != 1:
    raise SystemExit("v68: startTwentyAlerts em markSent ausente ou ambiguo")
block = block.replace(anchor, """        // A primeira gaiola ja foi confirmada pelo fluxo V66.
        // Envia uma gaiola por mensagem; se o campo estiver fechado, o fluxo
        // normal segura a rota pendente ate poder enviar.
        if (pcCageQueueV68.isNotEmpty()) {
            val next = pcCageQueueV68.removeFirst()
            processing = true
            handler.postDelayed({
                if (processing) sendRouteInCurrentChat(next)
            }, 45L)
            return
        }
        startTwentyAlerts(route, elapsed)""", 1)
s = s[:mark_start] + block + s[mark_end:]
if "RYZEN USB v68" not in s or "pcCageQueueV68" not in s:
    raise SystemExit("v68: verificacao falhou")
f.write_text(s, encoding="utf-8")

# Configuracao nao destrutiva, padrao ON apenas para V68 experimental.
f = src / "Prefs.kt"
p = f.read_text(encoding="utf-8")
marker = "object Prefs {\n"
if p.count(marker) != 1:
    raise SystemExit("v68: objeto Prefs nao encontrado")
p = p.replace(marker, """object Prefs {
    fun pcOcrEnabledV68(context: Context): Boolean =
        context.getSharedPreferences("rota_rapida", Context.MODE_PRIVATE)
            .getBoolean("pc_ocr_enabled_v68", true)

    fun setPcOcrEnabledV68(context: Context, value: Boolean) {
        context.getSharedPreferences("rota_rapida", Context.MODE_PRIVATE)
            .edit().putBoolean("pc_ocr_enabled_v68", value).apply()
    }

""", 1)
f.write_text(p, encoding="utf-8")

# Alternancia entre USB/ocr-local VISIVEL no aplicativo.
f = src / "MainActivity.kt"
m = f.read_text(encoding="utf-8")
needle = "        enabled.isChecked = Prefs.isEnabled(this)\n"
if m.count(needle) != 1:
    raise SystemExit("v68: estado do toggle enabled nao encontrado")
m = m.replace(needle, needle + """        val pcSwitchV68 = SwitchCompat(this)
        pcSwitchV68.text = "OCR Ryzen USB (reserva no celular)"
        pcSwitchV68.isChecked = Prefs.pcOcrEnabledV68(this)
        pcSwitchV68.setOnCheckedChangeListener { _, checked ->
            Prefs.setPcOcrEnabledV68(this, checked)
            Prefs.setStatus(
                this,
                if (checked) "OCR Ryzen USB ativado. Execute o servidor no PC."
                else "OCR local v66 ativado."
            )
        }
        (enabled.parent as? android.view.ViewGroup)?.let { parent ->
            val at = parent.indexOfChild(enabled)
            if (at >= 0) parent.addView(pcSwitchV68, at + 1)
        }
""", 1)
f.write_text(m, encoding="utf-8")

manifest = Path("app/src/main/AndroidManifest.xml")
x = manifest.read_text(encoding="utf-8")
if "android.permission.INTERNET" not in x:
    x = x.replace(
        "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\">",
        "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\">\n"
        "    <uses-permission android:name=\"android.permission.INTERNET\" />",
        1
    )
manifest.write_text(x, encoding="utf-8")

print("v68: bridge ligado ao MediaStore V66, fallback local, fila de gaiolas e switch UI")
