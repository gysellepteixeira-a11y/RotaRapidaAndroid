from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

def replace_once(old, new, desc):
    global s
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f"V69 {desc}: expected one anchor, found {n}")
    s = s.replace(old, new, 1)

# Only this M52 experiment is changed; do not alter the image OCR or WhatsApp sender.
helper_anchor = "    private var photoSuppressedTextV68=false"
helper = '''    // V69: a route in the text-accessibility fast path is allowed only when
    // one fresh, message-sized text node independently contains both a priority
    // neighborhood and the exact cage. No cross-message geometry association.
    private fun isDeletedTextV69(raw: String): Boolean {
        val n = RouteParser.normalize(raw)
        return "mensagem apagada" in n ||
            "mensagem excluida" in n ||
            "voce apagou esta mensagem" in n ||
            "this message was deleted" in n ||
            "you deleted this message" in n
    }

    private fun isUnambiguousFreshTextRouteV69(
        fresh: List<NodeItem>,
        route: RouteResult
    ): Boolean {
        val screenW = resources.displayMetrics.widthPixels
        val screenH = resources.displayMetrics.heightPixels
        for (item in fresh) {
            val box = item.rect
            if (box.isEmpty || box.width() > screenW * 0.96f ||
                box.height() > screenH * 0.70f) continue
            val cls = item.className
            if (cls.contains("RecyclerView", ignoreCase = true) ||
                cls.contains("ScrollView", ignoreCase = true)) continue

            // The combined NodeItem.text can concatenate a node's text and
            // its contentDescription, possibly from different UI semantics.
            // Check one native field at a time.
            val candidates = arrayOf(
                try { item.node.text?.toString().orEmpty() }
                catch (_: Throwable) { "" },
                try { item.node.contentDescription?.toString().orEmpty() }
                catch (_: Throwable) { "" }
            )
            for (raw in candidates) {
                if (raw.length !in 5..8000 || isDeletedTextV69(raw)) continue
                val p = RouteParser.matchPriority(raw) ?: continue
                if (p.first != route.priorityIndex ||
                    p.second != route.neighborhood) continue
                val cage = RouteParser.extractCage(raw) ?: continue
                if (cage == route.cage) return true
            }
        }
        return false
    }

'''
replace_once(helper_anchor, helper+helper_anchor, "fresh text proof helper")

fast_anchor = "            if (tfRoute != null && !isDuplicate(tfRoute)) {"
fast_new = '''            val deletedNewV69 = tfNewItems.any { isDeletedTextV69(it.text) }
            val validTextV69 = !deletedNewV69 && tfRoute != null &&
                isUnambiguousFreshTextRouteV69(tfNewItems, tfRoute)
            if (validTextV69 && tfRoute != null && !isDuplicate(tfRoute)) {'''
replace_once(fast_anchor, fast_new, "TEXT v37 fast gate")

legacy_anchor = "if (!photoIncomingV68 && textRoute != null && !isDuplicate(textRoute)) {"
legacy_new = '''if (!photoIncomingV68 && textRoute != null &&
            newItems.none { isDeletedTextV69(it.text) } &&
            isUnambiguousFreshTextRouteV69(newItems, textRoute) &&
            !isDuplicate(textRoute)) {'''
replace_once(legacy_anchor, legacy_new, "legacy text gate")

for marker in ["ModalFilter.filter(", "isFeuRosaRowV684", "sendRouteInCurrentChat(",
               "readMediaLargeColorCrop(", "private fun waitForTextDirectSendReadyV5("]:
    if marker not in s:
        raise RuntimeError("V69 marker missing: "+marker)
if "sendSmsOnlyV664(" in s:
    raise RuntimeError("SMS code unexpectedly present")

service_path.write_text(s, encoding="utf-8")
print("V69 M52 strict text proof installed: same-message neighborhood+cage; deleted-event safety.")
