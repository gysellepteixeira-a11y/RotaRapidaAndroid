from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s = S.read_text(encoding='utf-8')

required = [
    '===== DIAGNOSTICO TEXTO v10 | TEXT v6 + READ MORE FAST + DIRECT SEND =====',
    'private fun findNewestReadMoreV10(',
    'private fun waitForReadMoreExpansionV10(',
    'val readMoreNode = findNewestReadMoreV10(root, tfNewItems)',
    'private fun waitForTextDirectSendReadyV5(',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for marker in required:
    if marker not in s:
        raise SystemExit('READ MORE SPAN v11 wrong base / missing marker: ' + marker)

# Replace the complete v10 Read-more helper region at once. This is deliberately
# independent of the exact formatting inside the old polling helper.
start = s.find('    private fun findNewestReadMoreV10(')
end = s.find('    private fun waitForTextDirectSendReadyV5(', start)
if start < 0 or end < 0:
    raise SystemExit('READ MORE SPAN v11 helper region not found')

helpers = r'''    private fun isReadMoreLabelV11(raw: String): Boolean {
        val n = RouteParser.normalize(raw)
        return n == "ler mais" || n == "read more" ||
            " ler mais" in n || " read more" in n ||
            n.startsWith("ler mais ") || n.startsWith("read more ")
    }

    private fun clickNewestReadMoreSpanV11(newItems: List<NodeItem>): Pair<AccessibilityNodeInfo, String>? {
        val ordered = newItems.sortedByDescending { it.rect.bottom }
        for (item in ordered) {
            val rawCs = item.node.text ?: continue
            val spanned = rawCs as? android.text.Spanned ?: continue
            val rawText = rawCs.toString()
            val spans = spanned.getSpans(0, spanned.length, android.text.style.ClickableSpan::class.java)
            for (span in spans.reversed()) {
                val a = spanned.getSpanStart(span).coerceAtLeast(0)
                val b = spanned.getSpanEnd(span).coerceAtMost(spanned.length)
                val label = if (b > a) spanned.subSequence(a, b).toString() else ""
                val atTailOfTruncated =
                    (rawText.contains("...") || rawText.contains("…")) && b >= spanned.length - 2
                if (!isReadMoreLabelV11(label) && !atTailOfTruncated) continue
                try {
                    // AccessibilityClickableSpan ignores the View argument and dispatches
                    // the hidden clickable-span accessibility action to the source node.
                    span.onClick(null)
                    return item.node to rawText
                } catch (_: Throwable) {
                    // Continue to the node/gesture fallbacks below.
                }
            }
        }
        return null
    }

    private fun findNewestReadMoreItemV11(
        items: List<NodeItem>,
        newItems: List<NodeItem>
    ): NodeItem? {
        if (newItems.isEmpty()) return null
        val validRects = newItems.map { it.rect }.filter { !it.isEmpty }
        if (validRects.isEmpty()) return null
        val newTop = validRects.minOf { it.top }
        val newBottom = validRects.maxOf { it.bottom }
        val h = resources.displayMetrics.heightPixels
        val extraBelow = maxOf(220, (h * 0.10f).toInt())

        return items
            .asSequence()
            .filter { !it.rect.isEmpty }
            .filter { it.rect.bottom >= newTop && it.rect.top <= newBottom + extraBelow }
            .filter { isReadMoreLabelV11(it.text) }
            .maxByOrNull { it.rect.bottom }
    }

    private fun findNewestEllipsisV11(newItems: List<NodeItem>): NodeItem? {
        return newItems
            .asSequence()
            .filter { !it.rect.isEmpty }
            .filter { it.text.contains("...") || it.text.contains("…") }
            .maxByOrNull { it.rect.bottom }
    }

    private fun tapReadMoreFallbackV11(item: NodeItem): Boolean {
        val r = item.rect
        if (r.isEmpty) return false
        val dm = resources.displayMetrics
        // WhatsApp renders the inline Read-more on the last line of the TextView.
        // Keep the tap inside the bubble near its lower-right area; this is only used
        // if neither AccessibilityClickableSpan nor a named node can be clicked.
        val insetX = 56f * dm.density
        val insetY = 18f * dm.density
        val x = (r.right.toFloat() - insetX).coerceIn(r.left + 8f, dm.widthPixels - 8f)
        val y = (r.bottom.toFloat() - insetY).coerceIn(r.top + 8f, dm.heightPixels - 8f)
        val path = Path().apply { moveTo(x, y) }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0L, 1L))
            .build()
        return dispatchGesture(gesture, null, null)
    }

    private fun waitForReadMoreExpansionV11(
        probeNode: AccessibilityNodeInfo,
        beforeText: String,
        startedAt: Long,
        poll: Int
    ) {
        val pollDelayMs = 4L
        val maxPolls = 45
        var changed = false
        var alive = false

        try {
            alive = probeNode.refresh()
            if (alive) {
                val now = probeNode.text?.toString().orEmpty()
                changed = now != beforeText ||
                    (!now.contains("...") && !now.contains("…") && !isReadMoreLabelV11(now))
            } else {
                // WhatsApp often replaces the TextView after expanding it.
                changed = true
            }
        } catch (_: Throwable) {
            changed = true
        }

        if (changed) {
            rmExpanded = SystemClock.elapsedRealtime()
            rmPolls = poll
            rmPending = false
            rmCarry = true
            handler.post { analyzeCurrentWindow() }
            return
        }

        if (poll < maxPolls) {
            handler.postDelayed(
                { waitForReadMoreExpansionV11(probeNode, beforeText, startedAt, poll + 1) },
                pollDelayMs
            )
            return
        }

        // Never choose a priority from a message we know is still truncated.
        rmPending = false
        rmCarry = false
        handler.postDelayed({ analyzeCurrentWindow() }, 20L)
    }

'''
s = s[:start] + helpers + s[end:]

old_hot = '''            val readMoreNode = findNewestReadMoreV10(root, tfNewItems)
            if (readMoreNode != null) {
                val started = SystemClock.elapsedRealtime()
                val ok = clickNodeOrParent(readMoreNode)
                val afterClick = SystemClock.elapsedRealtime()
                if (ok) {
                    rmUsed = true
                    rmPending = true
                    rmCarry = true
                    rmStarted = started
                    rmClicked = afterClick
                    rmClickMs = afterClick - started
                    rmExpanded = 0L
                    rmPolls = 0
                    waitForReadMoreExpansionV10(readMoreNode, started, 0)
                    return
                }
                // Safety over speed: if WhatsApp exposes Ler mais but refuses the click,
                // do not send from a potentially truncated priority list. Retry shortly.
                handler.postDelayed({ analyzeCurrentWindow() }, 20L)
                return
            }
'''
new_hot = '''            // v11: first use Android's clickable-span bridge. WhatsApp can render
            // "Ler mais" inside one TextView, invisible to findAccessibilityNodeInfosByText.
            val spanClick = clickNewestReadMoreSpanV11(tfNewItems)
            if (spanClick != null) {
                val afterClick = SystemClock.elapsedRealtime()
                val started = afterClick
                rmUsed = true
                rmPending = true
                rmCarry = true
                rmStarted = started
                rmClicked = afterClick
                rmClickMs = 0L
                rmExpanded = 0L
                rmPolls = 0
                waitForReadMoreExpansionV11(spanClick.first, spanClick.second, started, 0)
                return
            }

            // Second choice: a normal/embedded accessibility node containing the label.
            val readMoreItem = findNewestReadMoreItemV11(items, tfNewItems)
            if (readMoreItem != null) {
                val before = readMoreItem.node.text?.toString().orEmpty()
                val started = SystemClock.elapsedRealtime()
                val ok = clickNodeOrParent(readMoreItem.node)
                val afterClick = SystemClock.elapsedRealtime()
                if (ok) {
                    rmUsed = true
                    rmPending = true
                    rmCarry = true
                    rmStarted = started
                    rmClicked = afterClick
                    rmClickMs = afterClick - started
                    rmExpanded = 0L
                    rmPolls = 0
                    waitForReadMoreExpansionV11(readMoreItem.node, before, started, 0)
                    return
                }
            }

            // Last fallback: visible ellipsis on the newest truncated message.
            val ellipsisItem = findNewestEllipsisV11(tfNewItems)
            if (ellipsisItem != null) {
                val before = ellipsisItem.node.text?.toString().orEmpty()
                val started = SystemClock.elapsedRealtime()
                val ok = tapReadMoreFallbackV11(ellipsisItem)
                val afterClick = SystemClock.elapsedRealtime()
                if (ok) {
                    rmUsed = true
                    rmPending = true
                    rmCarry = true
                    rmStarted = started
                    rmClicked = afterClick
                    rmClickMs = afterClick - started
                    rmExpanded = 0L
                    rmPolls = 0
                    waitForReadMoreExpansionV11(ellipsisItem.node, before, started, 0)
                    return
                }
                // Known truncated newest message: don't let the parser choose Rosario yet.
                handler.postDelayed({ analyzeCurrentWindow() }, 12L)
                return
            }
'''
if old_hot not in s:
    raise SystemExit('READ MORE SPAN v11 hot block not found')
s = s.replace(old_hot, new_hot, 1)

old_header = '===== DIAGNOSTICO TEXTO v10 | TEXT v6 + READ MORE FAST + DIRECT SEND ====='
new_header = '===== DIAGNOSTICO TEXTO v11 | TEXT v6 + READ MORE SPAN + DIRECT SEND ====='
s = s.replace(old_header, new_header, 1)

for marker in [
    new_header,
    'private fun clickNewestReadMoreSpanV11(',
    'private fun findNewestReadMoreItemV11(',
    'private fun findNewestEllipsisV11(',
    'private fun waitForReadMoreExpansionV11(',
    'val spanClick = clickNewestReadMoreSpanV11(tfNewItems)',
    'val ellipsisItem = findNewestEllipsisV11(tfNewItems)',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if marker not in s:
        raise SystemExit('READ MORE SPAN v11 verification failed: ' + marker)

S.write_text(s, encoding='utf-8')
print('READ MORE SPAN v11 applied: ClickableSpan first, node second, gesture fallback; TEXT v6 + IMAGE v9 preserved')
