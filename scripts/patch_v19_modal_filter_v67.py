from pathlib import Path
import re

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
P=Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
A=Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")
L=Path("app/src/main/res/layout/activity_main.xml")
s=S.read_text(encoding="utf-8"); p=P.read_text(encoding="utf-8")
a=A.read_text(encoding="utf-8"); x=L.read_text(encoding="utf-8")

# Preferencia + UI
ka='    private const val KEY_MESSAGE_MODAL_V56 = "message_modal_v56"\n'
if 'KEY_BLOCK_FAKE_VOLUMOSO_V67' not in p:
    if ka not in p: raise SystemExit("v67 prefs anchor")
    p=p.replace(ka,ka+'    private const val KEY_BLOCK_FAKE_VOLUMOSO_V67 = "block_fake_volumoso_v67"\n',1)
    pos=p.rfind('\n}')
    p=p[:pos]+r'''
    fun blockFakeVolumoso(context: Context): Boolean =
        prefs(context).getBoolean(KEY_BLOCK_FAKE_VOLUMOSO_V67, true)

    fun setBlockFakeVolumoso(context: Context, value: Boolean) {
        prefs(context).edit().putBoolean(KEY_BLOCK_FAKE_VOLUMOSO_V67, value).apply()
    }
'''+p[pos:]

if 'switchBlockFakeVolumoso' not in x:
    m=re.search(r'(\s*<androidx\.appcompat\.widget\.SwitchCompat\s+android:id="@\+id/switchFloatingOverlay"[\s\S]*?/>)',x)
    if not m: raise SystemExit("v67 layout anchor")
    ins=m.group(1)+r'''
        <androidx.appcompat.widget.SwitchCompat
            android:id="@+id/switchBlockFakeVolumoso"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="10dp"
            android:text="Ignorar FAKE VOLUMOSO" />
        <TextView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="2dp"
            android:text="Ativado: só envia quando o Modal da linha vencedora for PASSEIO."
            android:textSize="12sp" />
'''
    x=x[:m.start()]+ins+x[m.end():]

ba='        val floatingOverlay = findViewById<SwitchCompat>(R.id.switchFloatingOverlay)\n'
if ba not in a: raise SystemExit("v67 activity bind anchor")
if 'switchBlockFakeVolumoso' not in a:
    a=a.replace(ba,ba+'        val blockFakeVolumoso = findViewById<SwitchCompat>(R.id.switchBlockFakeVolumoso)\n',1)

ia='        floatingOverlay.isChecked = Prefs.floatingOverlayEnabled(this)\n'
if ia not in a: raise SystemExit("v67 activity init anchor")
if 'blockFakeVolumoso.isChecked' not in a:
    a=a.replace(ia,ia+'        blockFakeVolumoso.isChecked = Prefs.blockFakeVolumoso(this)\n',1)

la='''        floatingOverlay.setOnCheckedChangeListener { _, checked ->
            Prefs.setFloatingOverlayEnabled(this, checked)
            Prefs.setStatus(
                this,
                if (checked)
                    "Botão flutuante ativado."
                else
                    "Botão flutuante ocultado."
            )
        }
'''
if la not in a: raise SystemExit("v67 activity listener anchor")
if 'blockFakeVolumoso.setOnCheckedChangeListener' not in a:
    a=a.replace(la,la+r'''
        blockFakeVolumoso.setOnCheckedChangeListener { _, checked ->
            Prefs.setBlockFakeVolumoso(this, checked)
            Prefs.setStatus(
                this,
                if (checked)
                    "Filtro FAKE VOLUMOSO ativado: só PASSEIO será enviado."
                else
                    "Filtro FAKE VOLUMOSO desativado."
            )
        }
''',1)

# Estado do servico
sa='''    @Volatile private var messageModalV56 = "Passeio"

    private fun refreshMessageProfileV56() {
'''
if sa not in s: raise SystemExit("v67 state anchor")
s=s.replace(sa,'''    @Volatile private var messageModalV56 = "Passeio"
    @Volatile private var blockFakeVolumosoV67 = true
    private var currentModalMediaV67: MediaImage? = null
    private var modalVerifiedV67 = false
    private var modalCenterRatioV67 = -1f
    private var modalHalfRatioV67 = -1f
    private var idModalOcrV67 = 0L
    private var idModalTextV67 = ""

    private fun refreshMessageProfileV56() {
''',1)

ca='        refreshMessageProfileV56()\n'
if ca not in s: raise SystemExit("v67 connect anchor")
s=s.replace(ca,ca+'        blockFakeVolumosoV67 = Prefs.blockFakeVolumoso(this)\n',1)

pla='''                "message_name_v56", "message_id_v56", "message_modal_v56" ->
                    handler.post { refreshMessageProfileV56() }
'''
if pla not in s: raise SystemExit("v67 prefs listener")
s=s.replace(pla,pla+'''                "block_fake_volumoso_v67" ->
                    handler.post { blockFakeVolumosoV67 = Prefs.blockFakeVolumoso(this) }
''',1)

# Captura o arquivo atual e zera estado modal no inicio da imagem.
ma='''        idBegin(mediaStoreStarted, SystemClock.elapsedRealtime(), mediaStoreMs, media.height)

        // Reserva o arquivo antes de iniciar OCR'''
if ma not in s: raise SystemExit("v67 media start anchor")
s=s.replace(ma,'''        idBegin(mediaStoreStarted, SystemClock.elapsedRealtime(), mediaStoreMs, media.height)
        currentModalMediaV67 = media
        modalVerifiedV67 = false
        modalCenterRatioV67 = -1f
        modalHalfRatioV67 = -1f
        idModalOcrV67 = 0L
        idModalTextV67 = ""

        // Reserva o arquivo antes de iniciar OCR''',1)

# Dense: guarda Y normalizado da linha vencedora sem OCR/scan extra.
da='''                lastDensePriorityNeighborhood = chosen.neighborhood
                lastDensePriorityIndex = chosen.priorityIndex
                lastDensePriorityCenterY = chosen.centerY
'''
if da not in s: raise SystemExit("v67 dense Y anchor")
s=s.replace(da,'''                modalCenterRatioV67 =
                    chosen.centerY.toFloat() / denseBitmap.height.toFloat().coerceAtLeast(1f)
                val rowPitchV67 =
                    denseBitmap.height.toFloat() / rowCount.coerceAtLeast(1).toFloat()
                modalHalfRatioV67 =
                    (rowPitchV67 * 0.52f) / denseBitmap.height.toFloat().coerceAtLeast(1f)
                lastDensePriorityNeighborhood = chosen.neighborhood
                lastDensePriorityIndex = chosen.priorityIndex
                lastDensePriorityCenterY = chosen.centerY
''',1)

# Ultrathin: deriva Y do mesmo OCR que ja existe.
ua='''            val route = routeFromGeometry ?: oneRowRoute
            val elapsed = SystemClock.elapsedRealtime() - startedAll
'''
if ua not in s: raise SystemExit("v67 ultra anchor")
s=s.replace(ua,'''            val route = routeFromGeometry ?: oneRowRoute
            if (route != null) {
                val p = screenItems
                    .filter { RouteParser.matchPriority(it.text)?.first == route.priorityIndex }
                    .minByOrNull { it.top }
                val c = screenItems
                    .filter { RouteParser.extractCage(it.text) == route.cage }
                    .minByOrNull { it.top }
                val anchorV67 = p ?: c
                if (anchorV67 != null) {
                    modalCenterRatioV67 =
                        ((anchorV67.top + anchorV67.bottom) * 0.5f) /
                            source.height.toFloat().coerceAtLeast(1f)
                    modalHalfRatioV67 =
                        maxOf(3f, (anchorV67.bottom - anchorV67.top).toFloat() * 1.4f) /
                            source.height.toFloat().coerceAtLeast(1f)
                } else if (source.height <= 60) {
                    modalCenterRatioV67 = 0.5f
                    modalHalfRatioV67 = 0.45f
                }
            }
            val elapsed = SystemClock.elapsedRealtime() - startedAll
''',1)

# Helper: OCR somente da celula Modal da linha vencedora.
ha='    private fun runOcrWarmV66() {\n'
if ha not in s: raise SystemExit("v67 helper anchor")
helper=r'''    private fun modalDecisionV67(text: String): Int {
        val n = RouteParser.normalize(text)
        if (n.isBlank()) return 0
        if (("fake" in n && "volum" in n) || "fakevolum" in n) return -1
        return if ("passeio" in n || "paseio" in n) 1 else 0
    }

    private fun verifyModalAndContinueV67(route: RouteResult) {
        if (!processing) return
        val media = currentModalMediaV67
        val center = modalCenterRatioV67
        val half = modalHalfRatioV67

        if (media == null || center !in 0f..1f || half <= 0f) {
            finishFileOnlyFailure(
                "MODAL: linha vencedora nao confirmada; rota nao enviada."
            )
            return
        }

        val src = try {
            contentResolver.openInputStream(media.uri)?.use { BitmapFactory.decodeStream(it) }
        } catch (_: Throwable) { null }

        if (src == null) {
            finishFileOnlyFailure("MODAL: nao consegui abrir a imagem; rota nao enviada.")
            return
        }

        val x1 = (src.width * 0.885f).toInt().coerceIn(0, src.width - 2)
        val cy = (center * src.height).toInt().coerceIn(0, src.height - 1)
        val hy = maxOf(3, (half * src.height).toInt())
        val y1 = (cy - hy).coerceIn(0, src.height - 1)
        val y2 = (cy + hy + 1).coerceIn(y1 + 1, src.height)

        val crop = try {
            Bitmap.createBitmap(src, x1, y1, src.width - x1, y2 - y1)
        } catch (_: Throwable) { null }
        try { src.recycle() } catch (_: Throwable) {}

        if (crop == null) {
            finishFileOnlyFailure("MODAL: crop falhou; rota nao enviada.")
            return
        }

        val wanted = maxOf(1f, 64f / crop.height.toFloat().coerceAtLeast(1f))
        val maxW = 900f / crop.width.toFloat().coerceAtLeast(1f)
        val scale = minOf(4f, wanted, maxW.coerceAtLeast(1f))
        val work = if (scale > 1.05f) {
            try {
                Bitmap.createScaledBitmap(
                    crop,
                    (crop.width * scale).toInt().coerceAtLeast(1),
                    (crop.height * scale).toInt().coerceAtLeast(1),
                    true
                )
            } catch (_: Throwable) { crop }
        } else crop
        if (work !== crop) try { crop.recycle() } catch (_: Throwable) {}

        val started = SystemClock.elapsedRealtime()
        recognizer.process(InputImage.fromBitmap(work,0))
            .addOnSuccessListener { t ->
                idModalOcrV67 = SystemClock.elapsedRealtime() - started
                idModalTextV67 = t.text.replace("\n"," ")
                    .replace(Regex("\\s+")," ").trim().take(80)
                try { work.recycle() } catch (_: Throwable) {}
                if (!processing) return@addOnSuccessListener

                when (modalDecisionV67(t.text)) {
                    1 -> {
                        modalVerifiedV67 = true
                        sendRouteInCurrentChat(route)
                    }
                    -1 -> finishFileOnlyFailure(
                        "FAKE VOLUMOSO ignorado: ${route.neighborhood} -> ${route.cage} | " +
                            "modalOCR=${idModalOcrV67}ms"
                    )
                    else -> finishFileOnlyFailure(
                        "Modal PASSEIO nao confirmado; rota nao enviada | " +
                            "modalOCR=${idModalOcrV67}ms | lido=[$idModalTextV67]"
                    )
                }
            }
            .addOnFailureListener {
                try { work.recycle() } catch (_: Throwable) {}
                if (processing) finishFileOnlyFailure(
                    "OCR do Modal falhou; rota nao enviada."
                )
            }
    }

'''
s=s.replace(ha,helper+ha,1)

# Intercepta somente rotas de IMAGEM. Filtro OFF = v66 byte-for-byte a partir daqui.
sea='''    private fun sendRouteInCurrentChat(route: RouteResult) {
        if(tdOn && tdSend==0L) tdSend=SystemClock.elapsedRealtime()
        if (idOn) {
'''
if sea not in s: raise SystemExit("v67 send entry anchor")
s=s.replace(sea,'''    private fun sendRouteInCurrentChat(route: RouteResult) {
        if (idOn && blockFakeVolumosoV67 && !modalVerifiedV67) {
            verifyModalAndContinueV67(route)
            return
        }
        if(tdOn && tdSend==0L) tdSend=SystemClock.elapsedRealtime()
        if (idOn) {
''',1)

# Diagnostico de rotas enviadas.
dia='''            if(idCageBandPxV65>0) appendLine("cageCropV66=true | mode=${idCageModeV66} | band=${idCageBandPxV65}px | dense=${String.format(java.util.Locale.US, "%.1f", idCageDenseRatioV65*100f)}% | threshold=55%")
'''
if dia not in s: raise SystemExit("v67 diag anchor")
s=s.replace(dia,dia+'''            appendLine("modalFilterV67=${if(blockFakeVolumosoV67) "ON" else "OFF"} | OCR=${idModalOcrV67}ms | lido=[$idModalTextV67]")
''',1)

old='===== DIAGNOSTICO IMAGEM v19 | V66 HYBRID CAGE + OCR WARM + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
new='===== DIAGNOSTICO IMAGEM v19 | V67 MODAL FILTER + V66 HYBRID CAGE + OCR WARM + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
if old not in s: raise SystemExit("v67 title anchor")
s=s.replace(old,new,1)

for m in [
    'switchBlockFakeVolumoso','KEY_BLOCK_FAKE_VOLUMOSO_V67',
    'verifyModalAndContinueV67','modalCenterRatioV67',
    'FAKE VOLUMOSO ignorado','modalFilterV67=','V67 MODAL FILTER'
]:
    if m not in s+p+a+x: raise SystemExit("v67 verify "+m)

S.write_text(s,encoding="utf-8"); P.write_text(p,encoding="utf-8")
A.write_text(a,encoding="utf-8"); L.write_text(x,encoding="utf-8")
print("v67 aplicado: filtro opcional FAKE VOLUMOSO; PASSEIO confirmado por OCR pequeno da mesma linha")
