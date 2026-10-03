from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s = S.read_text(encoding='utf-8')

required = [
    '===== DIAGNOSTICO TEXTO v6 | OLD BASE + TEXT TAIL DELTA + DIRECT SEND =====',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
    'val tfNewItems = tfNewItemsReverse.asReversed()',
    'private fun waitForTextDirectSendReadyV5(',
]
for marker in required:
    if marker not in s:
        raise SystemExit('READ MORE PROBE v13 wrong base / missing marker: ' + marker)

helper_anchor = '    private fun waitForTextDirectSendReadyV5(\n'
helper = r'''    private fun rmProbeV13Short(raw: String?, max: Int = 220): String {
        val clean = raw.orEmpty().replace("\n", "\\n").replace("\r", "")
        return if (clean.length <= max) clean else clean.take(max) + "…"
    }

    private fun rmProbeV13Node(prefix: String, node: AccessibilityNodeInfo?): String {
        if (node == null) return "$prefix <null>"
        val r = Rect()
        try { node.getBoundsInScreen(r) } catch (_: Throwable) {}
        val actions = try {
            node.actionList.joinToString(",") { a ->
                val label = a.label?.toString()?.let { ":${rmProbeV13Short(it, 50)}" }.orEmpty()
                "${a.id}$label"
            }
        } catch (_: Throwable) { "ERR" }
        val spans = try {
            val cs = node.text
            if (cs is android.text.Spanned) {
                val arr = cs.getSpans(0, cs.length, android.text.style.ClickableSpan::class.java)
                if (arr.isEmpty()) "0" else arr.joinToString(";") { sp ->
                    val st = cs.getSpanStart(sp).coerceAtLeast(0)
                    val en = cs.getSpanEnd(sp).coerceAtMost(cs.length)
                    val label = if (en > st) cs.subSequence(st, en).toString() else ""
                    "[$st,$en]='${rmProbeV13Short(label, 80)}'"
                }
            } else "0"
        } catch (_: Throwable) { "ERR" }
        val id = try { node.viewIdResourceName.orEmpty() } catch (_: Throwable) { "" }
        val desc = try { node.contentDescription?.toString().orEmpty() } catch (_: Throwable) { "" }
        val cls = try { node.className?.toString().orEmpty() } catch (_: Throwable) { "" }
        val text = try { node.text?.toString().orEmpty() } catch (_: Throwable) { "" }
        return "$prefix text='${rmProbeV13Short(text)}' desc='${rmProbeV13Short(desc,120)}' class=$cls id=$id rect=[${r.left},${r.top},${r.right},${r.bottom}] clickable=${node.isClickable} enabled=${node.isEnabled} focusable=${node.isFocusable} actions=[$actions] spans=$spans"
    }

    private fun captureReadMoreProbeV13(
        root: AccessibilityNodeInfo,
        items: List<NodeItem>,
        newItems: List<NodeItem>
    ): Boolean {
        if (newItems.isEmpty()) return false

        val ellipsis = newItems.filter {
            it.text.contains("...") || it.text.contains("…")
        }.maxByOrNull { it.rect.bottom }

        val labelItems = items.filter {
            val n = RouteParser.normalize(it.text)
            n.contains("ler mais") || n.contains("read more")
        }

        val queryNodes = ArrayList<AccessibilityNodeInfo>()
        for (q in arrayOf("Ler mais", "Read more")) {
            try { queryNodes.addAll(root.findAccessibilityNodeInfosByText(q)) } catch (_: Throwable) {}
        }

        if (ellipsis == null && labelItems.isEmpty() && queryNodes.isEmpty()) return false

        val now = SystemClock.elapsedRealtime()
        val dm = resources.displayMetrics
        val report = buildString {
            appendLine("===== DIAGNOSTICO LER MAIS v13 | PROBE SEM ENVIO =====")
            appendLine("capturadoAt=$now | tela=${dm.widthPixels}x${dm.heightPixels} | density=${dm.density}")
            appendLine("newItems=${newItems.size} | allItems=${items.size} | ellipsis=${ellipsis != null} | labelItems=${labelItems.size} | queryNodes=${queryNodes.size}")
            appendLine()
            appendLine("--- NEW ITEMS (ultimos 12) ---")
            newItems.takeLast(12).forEachIndexed { i, it ->
                appendLine("#${i} raw='${rmProbeV13Short(it.text)}' rect=[${it.rect.left},${it.rect.top},${it.rect.right},${it.rect.bottom}]")
                appendLine(rmProbeV13Node("  node", it.node))
            }
            appendLine()
            appendLine("--- ELLIPSIS TARGET ---")
            if (ellipsis == null) appendLine("nenhum") else {
                appendLine(rmProbeV13Node("target", ellipsis.node))
                var p: AccessibilityNodeInfo? = try { ellipsis.node.parent } catch (_: Throwable) { null }
                var depth = 1
                while (p != null && depth <= 5) {
                    appendLine(rmProbeV13Node("parent$depth", p))
                    p = try { p.parent } catch (_: Throwable) { null }
                    depth++
                }
            }
            appendLine()
            appendLine("--- LABEL ITEMS ---")
            if (labelItems.isEmpty()) appendLine("nenhum") else labelItems.takeLast(8).forEachIndexed { i, it ->
                appendLine(rmProbeV13Node("label#$i", it.node))
            }
            appendLine()
            appendLine("--- findAccessibilityNodeInfosByText ---")
            if (queryNodes.isEmpty()) appendLine("nenhum") else queryNodes.takeLast(8).forEachIndexed { i, n ->
                appendLine(rmProbeV13Node("query#$i", n))
            }
            appendLine()
            appendLine("RESULTADO: rota NAO enviada. Use COPIAR DIAGNOSTICO e envie aqui.")
        }

        Prefs.setStatus(this, "DIAGNOSTICO LER MAIS v13 capturado. Rota nao enviada.")
        getSharedPreferences("rota_rapida", android.content.Context.MODE_PRIVATE)
            .edit().putString("speed_diagnostic", report).apply()
        return true
    }

'''
if helper_anchor not in s:
    raise SystemExit('READ MORE PROBE v13 helper anchor not found')
s = s.replace(helper_anchor, helper + helper_anchor, 1)

hot_anchor = '''        val tfNewItems = tfNewItemsReverse.asReversed()

        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.
'''
hot_insert = '''        val tfNewItems = tfNewItemsReverse.asReversed()

        // READ MORE PROBE v13: se a mensagem nova parece truncada, nao tenta clicar
        // nem envia uma prioridade incompleta. Captura a estrutura real do WhatsApp.
        if (primed && Prefs.searchArmed(this) && tfNewItems.isNotEmpty()) {
            if (captureReadMoreProbeV13(root, items, tfNewItems)) return
        }

        // Tenta a rota textual antes de qualquer varredura global/preparo de imagem.
'''
if hot_anchor not in s:
    raise SystemExit('READ MORE PROBE v13 hot anchor not found')
s = s.replace(hot_anchor, hot_insert, 1)

s = s.replace(
    '===== DIAGNOSTICO TEXTO v6 | OLD BASE + TEXT TAIL DELTA + DIRECT SEND =====',
    '===== DIAGNOSTICO TEXTO v13 | TEXT v6 + READ MORE PROBE + DIRECT SEND =====',
    1,
)

for marker in [
    '===== DIAGNOSTICO TEXTO v13 | TEXT v6 + READ MORE PROBE + DIRECT SEND =====',
    'private fun captureReadMoreProbeV13(',
    'DIAGNOSTICO LER MAIS v13 | PROBE SEM ENVIO',
    'RESULTADO: rota NAO enviada.',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
]:
    if marker not in s:
        raise SystemExit('READ MORE PROBE v13 verification failed: ' + marker)

S.write_text(s, encoding='utf-8')
print('READ MORE PROBE v13 applied: TEXT v6 + IMAGE v9 preserved; truncated message is diagnosed and not sent')
