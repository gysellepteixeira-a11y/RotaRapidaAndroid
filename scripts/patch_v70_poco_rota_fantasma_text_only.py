from pathlib import Path

# Strict text-only safeguard. Applied AFTER every existing V68/V69 patch.
# It does not edit image OCR, MediaStore, pending send, modal filters or priorities.
p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")

def exactly(old, new, name):
    global s
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f"V70 anti-ghost: {name}, found {n} anchors (expected 1)")
    s=s.replace(old,new,1)

helper=r'''    // POCO V70: require each textual route to be independently proven by ONE
    // freshly changed message-sized native accessibility field.
    // The older parser may pair a neighborhood from one node with a cage from
    // another during WhatsApp deletions, re-layouts and screen rebuilds.
    // Keep that parser, but do not permit sending without a same-source proof.
    private fun isDeletedEventTextV70(raw: String): Boolean {
        val n=RouteParser.normalize(raw)
        return "mensagem apagada" in n ||
            "mensagem excluida" in n ||
            "voce apagou esta mensagem" in n ||
            "essa mensagem foi apagada" in n ||
            "this message was deleted" in n ||
            "you deleted this message" in n
    }

    private fun hasExactNativeRouteProofV70(
        fresh: List<NodeItem>, route: RouteResult
    ): Boolean {
        val sw=resources.displayMetrics.widthPixels
        val sh=resources.displayMetrics.heightPixels
        for (item in fresh) {
            val rect=item.rect
            if (rect.isEmpty || rect.width() > sw*0.96f ||
                rect.height() > sh*0.70f) continue
            val cls=item.className
            if (cls.contains("RecyclerView",ignoreCase=true) ||
                cls.contains("ScrollView",ignoreCase=true)) continue

            // Never join text and contentDescription from different sources
            // or combine cage/neighborhood from different accessibility nodes.
            val nativeFields=arrayOf(
                try { item.node.text?.toString().orEmpty() } catch (_:Throwable) { "" },
                try { item.node.contentDescription?.toString().orEmpty() }
                catch (_:Throwable) { "" }
            )
            for (raw in nativeFields) {
                if (raw.length !in 5..8000 || isDeletedEventTextV70(raw)) continue

                // Strongest proof: route parser agrees on a single native field
                // and resolves the priority/cage in a physical text line.
                val singleFieldRoute=RouteParser.parsePlainTexts(listOf(raw))
                if (singleFieldRoute != null &&
                    singleFieldRoute.priorityIndex == route.priorityIndex &&
                    singleFieldRoute.neighborhood == route.neighborhood &&
                    singleFieldRoute.cage == route.cage) return true

                // Some valid WhatsApp bubbles put a single cage on another
                // line of the SAME native text field. Allow only one cage in
                // that case; multi-row tables must pass the line proof above.
                val cageCount=Regex("""(?<![A-Za-z0-9])[A-Za-z1][\-.\s]?\d{2}(?!\d)""")
                    .findAll(raw).take(2).count()
                if (cageCount != 1) continue
                val matched=RouteParser.matchPriority(raw) ?: continue
                if (matched.first != route.priorityIndex ||
                    matched.second != route.neighborhood) continue
                if (RouteParser.extractCage(raw) == route.cage) return true
            }
        }
        return false
    }

'''
exactly('    private var photoSuppressedTextV68=false',
        helper+'    private var photoSuppressedTextV68=false',
        "helper insertion")

exactly('            if (tfRoute != null && !isDuplicate(tfRoute)) {',
'''            val deletedNewTextV70=tfNewItems.any { isDeletedEventTextV70(it.text) }
            val nativeProvenV70= !deletedNewTextV70 &&
                tfRoute != null && hasExactNativeRouteProofV70(tfNewItems, tfRoute)
            if (nativeProvenV70 && tfRoute != null && !isDuplicate(tfRoute)) {''',
        "fast TEXT_DIRECT_V5 gate")

exactly('if (!photoIncomingV68 && textRoute != null && !isDuplicate(textRoute)) {',
'''if (!photoIncomingV68 && textRoute != null &&
            newItems.none { isDeletedEventTextV70(it.text) } &&
            hasExactNativeRouteProofV70(newItems, textRoute) &&
            !isDuplicate(textRoute)) {''',
        "legacy text fallback gate")

# Read-more direct proof already validates *growth of the same expanded
# native node* in V18/V33. Retain that path unmodified for compatibility.
# Other fast and legacy paths now reject unproven text routes.

for marker in (
    "fun isDeletedEventTextV70(", "fun hasExactNativeRouteProofV70(",
    "if (nativeProvenV70 && tfRoute != null",
    "hasExactNativeRouteProofV70(newItems, textRoute)",
    "ModalFilter.filter(", "isFeuRosaRowV684", "readMediaLargeColorCrop(media)",
    "readMediaOriginalFull(media)", "sendRouteInCurrentChat(tfRoute)",
    "private fun trySendPendingRouteIfChatOpen()",
    'V69 GRUPO FECHADO |',
):
    if marker not in s:
        raise RuntimeError("V70 invariant missing: "+marker)
if "sendSmsOnlyV664(" in s:
    raise RuntimeError("V70: SMS unexpectedly present")

p.write_text(s,encoding="utf-8")
print("V70 anti-ghost applied: strictly one native text source, deletion-safe on TEXT_DIRECT_V5 + legacy. Image and admin-flow untouched.")
