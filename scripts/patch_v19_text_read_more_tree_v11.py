from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s = S.read_text(encoding='utf-8')

required = [
    '===== DIAGNOSTICO TEXTO v10 | TEXT v6 + READ MORE FAST + DIRECT SEND =====',
    'private fun findNewestReadMoreV10(',
    'private fun waitForReadMoreExpansionV10(',
    'val readMoreNode = findNewestReadMoreV10(root, tfNewItems)',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for marker in required:
    if marker not in s:
        raise SystemExit('READ MORE TREE v11 wrong base / missing marker: ' + marker)

# Replace v10 lookup helper with a tree-scan helper. collectNodeItems already contains
# node.text + contentDescription, even when WhatsApp text search does not index the span.
start = s.find('    private fun findNewestReadMoreV10(')
end = s.find('    private fun waitForReadMoreExpansionV10(', start)
if start < 0 or end < 0:
    raise SystemExit('READ MORE TREE v11 lookup block not found')

helper = r'''    private fun findNewestReadMoreV11(
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

        var best: NodeItem? = null
        var bestBottom = Int.MIN_VALUE
        for (item in items) {
            val r = item.rect
            if (r.isEmpty) continue
            if (r.bottom < newTop) continue
            if (r.top > newBottom + extraBelow) continue

            val n = RouteParser.normalize(item.text)
            val hasReadMore =
                n == "ler mais" || n == "read more" ||
                " ler mais" in n || " read more" in n ||
                n.startsWith("ler mais ") || n.startsWith("read more ")
            if (!hasReadMore) continue

            if (r.bottom > bestBottom) {
                bestBottom = r.bottom
                best = item
            }
        }
        return best
    }

    private fun findNewestEllipsisV11(newItems: List<NodeItem>): NodeItem? {
        return newItems
            .asSequence()
            .filter { !it.rect.isEmpty }
            .filter { it.text.contains("...") || it.text.contains("…") }
            .maxByOrNull { it.rect.bottom }
    }

    private fun tapReadMoreAfterEllipsisV11(item: NodeItem): Boolean {
        val r = item.rect
        if (r.isEmpty) return false
        val dm = resources.displayMetrics
        val offset = 38f * dm.density
        val x = (r.right.toFloat() + offset).coerceIn(8f, dm.widthPixels - 8f)
        val y = r.centerY().toFloat().coerceIn(8f, dm.heightPixels - 8f)
        val path = Path().apply { moveTo(x, y) }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0L, 1L))
            .build()
        return dispatchGesture(gesture, null, null)
    }

'''
s = s[:start] + helper + s[end:]

# Expansion polling now also understands an ellipsis probe node used by the coordinate fallback.
s = s.replace(
    'private fun waitForReadMoreExpansionV10(',
    'private fun waitForReadMoreExpansionV11(',
    1
)
s = s.replace(
    '{ waitForReadMoreExpansionV10(clickedNode, startedAt, poll + 1) }',
    '{ waitForReadMoreExpansionV11(clickedNode, startedAt, poll + 1) }',
    1
)
old_still = '''                val n = RouteParser.normalize(merged)
                stillReadMore = n == "ler mais" || n == "read more" || n.endsWith(" ler mais") || n.endsWith(" read more")
'''
new_still = '''                val n = RouteParser.normalize(merged)
                stillReadMore =
                    n == "ler mais" || n == "read more" ||
                    n.endsWith(" ler mais") || n.endsWith(" read more") ||
                    merged.contains("...") || merged.contains("…")
'''
if old_still not in s:
    raise SystemExit('READ MORE TREE v11 expansion condition not found')
s = s.replace(old_still, new_still, 1)

# Replace only the detection/click portion in the v10 hot path.
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
new_hot = '''            val readMoreItem = findNewestReadMoreV11(items, tfNewItems)
            if (readMoreItem != null) {
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
                    waitForReadMoreExpansionV11(readMoreItem.node, started, 0)
                    return
                }
                handler.postDelayed({ analyzeCurrentWindow() }, 12L)
                return
            }

            // Some WhatsApp builds render "Ler mais" as an inline span that does not
            // appear as an individually searchable accessibility node. In that case,
            // the visible truncation (...) is our anchor: tap immediately to its right.
            val ellipsisItem = findNewestEllipsisV11(tfNewItems)
            if (ellipsisItem != null) {
                val started = SystemClock.elapsedRealtime()
                val ok = tapReadMoreAfterEllipsisV11(ellipsisItem)
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
                    waitForReadMoreExpansionV11(ellipsisItem.node, started, 0)
                    return
                }
                // Do not parse/send a known truncated newest message.
                handler.postDelayed({ analyzeCurrentWindow() }, 12L)
                return
            }
'''
if old_hot not in s:
    raise SystemExit('READ MORE TREE v11 hot block not found')
s = s.replace(old_hot, new_hot, 1)

old_header = '===== DIAGNOSTICO TEXTO v10 | TEXT v6 + READ MORE FAST + DIRECT SEND ====='
new_header = '===== DIAGNOSTICO TEXTO v11 | TEXT v6 + READ MORE TREE/ELLIPSIS + DIRECT SEND ====='
s = s.replace(old_header, new_header, 1)

for marker in [
    new_header,
    'private fun findNewestReadMoreV11(',
    'private fun findNewestEllipsisV11(',
    'private fun tapReadMoreAfterEllipsisV11(',
    'private fun waitForReadMoreExpansionV11(',
    'val readMoreItem = findNewestReadMoreV11(items, tfNewItems)',
    'val ellipsisItem = findNewestEllipsisV11(tfNewItems)',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if marker not in s:
        raise SystemExit('READ MORE TREE v11 verification failed: ' + marker)

S.write_text(s, encoding='utf-8')
print('READ MORE TREE/ELLIPSIS v11 applied: tree scan first, ellipsis coordinate fallback; TEXT v6 + IMAGE v9 preserved')
