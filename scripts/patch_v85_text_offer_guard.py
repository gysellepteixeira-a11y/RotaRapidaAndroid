from pathlib import Path
import re

root = Path("app/src/main/java/com/gy/rotarapida")
service = root / "WhatsRouteAccessibilityService.kt"
s = service.read_text(encoding="utf-8")
before = s

def once(old, new):
    global s
    assert s.count(old) == 1, (old, s.count(old))
    s = s.replace(old, new, 1)

# A dedicated text-only grammar; never change RouteParser or image OCR.
(root / "TextOfferGuardV85.kt").write_text(r'''package com.gy.rotarapida

internal object TextOfferGuardV85 {
    data class Row(val cage: String, val code: String, val neighborhood: String) {
        val key: String get() = code + ":" + cage
    }

    private val cage = Regex("[A-Z]-?\\d{2}", RegexOption.IGNORE_CASE)
    private val code = Regex("AT\\d{8}[A-Z0-9]{3,24}", RegexOption.IGNORE_CASE)
    private val qty = Regex("\\d{1,6}")
    private val town = Regex("[\\p{L}][\\p{L} .'-]*(?:\\s*;\\s*[\\p{L}][\\p{L} .'-]*)*")
    private val columns = Regex("\\t+| {2,}")
    // If accessibility collapses separators to a single space, identify the
    // municipality boundary using the known Grande Vitoria delivery area.
    private val towns = "(?:Serra|Fund[aã]o|Vit[oó]ria|Vila Velha|Cariacica|Viana|Guarapari|Aracruz|Santa Leopoldina|Santa Teresa|Ibira[cç]u)"
    private val flat = Regex(
        "^([A-Z]-?\\d{2}) +((?:AT)\\d{8}[A-Z0-9]{3,24}) +(\\d{1,6}) +(.+?) +(" +
            towns + "(?: *; *" + towns + ")*) +(.+)$",
        RegexOption.IGNORE_CASE
    )
    private val quoted = Regex(
        "\\b(?:mensagem citada|mensagem respondida|respondeu a|respondendo a|quoted message|replying to|replied to)\\b",
        RegexOption.IGNORE_CASE
    )

    fun rows(raw: String): List<Row> {
        if (raw.isBlank() || quoted.containsMatchIn(raw)) return emptyList()
        val result = ArrayList<Row>()
        for (physical in raw.lineSequence()) {
            val line = physical.trim()
            if (line.length !in 15..1500 || !line.startsWithLetter()) continue
            val fields = if (line.contains('\t')) {
                line.split('\t').map { it.trim() }.filter { it.isNotEmpty() }
            } else {
                val parts = columns.split(line).map { it.trim() }.filter { it.isNotEmpty() }
                if (parts.size == 6) parts else flat.matchEntire(line)?.groupValues?.drop(1) ?: continue
            }
            if (fields.size != 6) continue
            val (c, id, count, status, municipality) = fields
            val bairro = fields[5]
            if (!cage.matches(c) || !code.matches(id) || !qty.matches(count)) continue
            if (status.isBlank() || !town.matches(municipality) || bairro.none { it.isLetter() }) continue
            // Reject reply/metadata appended to a supposedly physical table row.
            if (bairro.contains('|') || bairro.contains("...") || bairro.contains('…')) continue
            result.add(Row(c.replace("-", "").uppercase(java.util.Locale.ROOT),
                id.uppercase(java.util.Locale.ROOT), bairro))
        }
        return result
    }
    private fun String.startsWithLetter() = firstOrNull()?.isLetter() == true
}
''', encoding="utf-8")

# Remember route IDs from the prior visible baseline. Bounded, service-local
# history survives UI rebuilds and rearming, not process death. Never mark
# a fresh candidate before evaluating it.
anchor = "        val tfNewItemsReverse = ArrayList<NodeItem>(8)"
once(anchor, "        v85RememberBaseline(previousFastTexts)\n" + anchor)

start = s.index("    private fun hasExactNativeRouteProofV70(")
end = s.index("\n    private ", start + 20)
old = s[start:end]
assert "singleFieldRoute" in old and "nativeFields" in old
new = r'''    private val v85SeenRows = LinkedHashSet<String>()
    private var v85GuardDecision = "NOT_EVALUATED"

    private fun v85RememberRow(key:String) {
        v85SeenRows.add(key)
        if(v85SeenRows.size > 4096) {
            val iterator=v85SeenRows.iterator()
            if(iterator.hasNext()) { iterator.next(); iterator.remove() }
        }
    }

    private fun v85RememberBaseline(texts:Collection<String>) {
        for(raw in texts) {
            if(raw.indexOf("AT", ignoreCase=true)<0) continue
            for(row in TextOfferGuardV85.rows(raw)) v85RememberRow(row.key)
        }
    }

    private fun v85Matches(row:TextOfferGuardV85.Row, route:RouteResult):Boolean {
        val matched=RouteParser.matchPriority(row.neighborhood) ?: return false
        return matched.first==route.priorityIndex && matched.second==route.neighborhood &&
            row.cage.equals(route.cage.replace("-",""),ignoreCase=true)
    }

    private fun v85Log(reason:String,source:String) {
        v85GuardDecision=reason+" | source="+source
        android.util.Log.i("RotaRapidaV85",v85GuardDecision)
    }

    private fun v85AcceptRows(rows:List<TextOfferGuardV85.Row>, route:RouteResult, source:String):Boolean {
        val matching=rows.filter { v85Matches(it,route) }
        val fresh=matching.firstOrNull { it.key !in v85SeenRows }
        if(fresh==null) {
            v85Log(if(matching.isEmpty()) "BLOCK_NO_VALID_ROW" else "BLOCK_SEEN_ROW",source)
            return false
        }
        for(row in rows) v85RememberRow(row.key)
        v85Log("ACCEPT_VALID_ROW",source)
        return true
    }

    // The strict expanded-message proof is kept; never join different rows.
    private fun v85StrictProofRoute(raw:String):RouteResult? {
        return TextOfferGuardV85.rows(raw).asSequence()
            .filter { it.key !in v85SeenRows }
            .mapNotNull { row ->
                val match=RouteParser.matchPriority(row.neighborhood) ?: return@mapNotNull null
                RouteResult(match.second,row.cage,match.first)
            }.minByOrNull { it.priorityIndex }
    }

    private fun hasExactNativeRouteProofV70(fresh: List<NodeItem>, route: RouteResult): Boolean {
        val sw=resources.displayMetrics.widthPixels
        val sh=resources.displayMetrics.heightPixels
        val rows=ArrayList<TextOfferGuardV85.Row>()
        for(item in fresh) {
            val rect=item.rect
            if(item.editable || rect.isEmpty || rect.width()>sw*0.96f || rect.height()>sh*0.70f) continue
            val cls=item.className
            if(cls.contains("RecyclerView",ignoreCase=true) || cls.contains("ScrollView",ignoreCase=true)) continue
            val nativeFields=arrayOf(
                try { item.node.text?.toString().orEmpty() } catch(_:Throwable) { "" },
                try { item.node.contentDescription?.toString().orEmpty() } catch(_:Throwable) { "" }
            )
            for(raw in nativeFields) {
                if(raw.length !in 5..8000 || isDeletedEventTextV70(raw)) continue
                rows.addAll(TextOfferGuardV85.rows(raw))
            }
        }
        return v85AcceptRows(rows,route,"NATIVE_TEXT")
    }
'''
s = s[:start] + new + s[end:]
# The normal and legacy gates already call the V70 function above. Read More
# direct proof is a separate route to send, and must pass the same guard.
once("RouteParser.parsePlainTexts(listOf(proof.text))", "v85StrictProofRoute(proof.text)")
once("if(v26Route!=null && !isDuplicate(v26Route)){",
     'if(v26Route!=null && !isDuplicate(v26Route) && v85AcceptRows(TextOfferGuardV85.rows(proof.text),v26Route,"READ_MORE")){')

# Keep all existing report timing and show the acceptance reason in the text report.
matches=list(re.finditer(r'appendLine\("===== DIAGNOSTICO TEXTO v37[^"\n]*"\)',s))
assert len(matches)==1, ("text report anchor",len(matches))
m=matches[0]
s=s[:m.end()]+'\n            appendLine("V85 TEXT GUARD | $v85GuardDecision")'+s[m.end():]
assert s.count("hasExactNativeRouteProofV70(")==3
for marker in ["V84 WARM |","V84 AB |","V69 GRUPO FECHADO","ModalFilter.filter(","readMediaOriginalFull(media)","sendRouteInCurrentChat(tfRoute)","sendRouteInCurrentChat(v26Route)"]:
    assert s.count(marker)==before.count(marker),marker
assert "sendSmsOnlyV664(" not in s
# Fail if the image-report section differs at all.
def image_report(src):
    a=src.index("    private fun idReport(")
    b=src.index("\n    private ",a+20)
    return src[a:b]
assert image_report(s)==image_report(before)
service.write_text(s,encoding="utf-8")

test = Path("app/src/test/java/com/gy/rotarapida/TextOfferGuardV85Test.kt")
test.parent.mkdir(parents=True,exist_ok=True)
test.write_text(r'''package com.gy.rotarapida

import org.junit.Assert.*
import org.junit.Test

class TextOfferGuardV85Test {
    @Test fun legitimateTable() {
        val raw = "A-14\tAT20261127DLR4G\t120\t\tAusente\tFundão; Serra\tTimbuí\n" +
            "B-32\tAT20261127DLPMZ\t101\t\tDisponível\tSerra\tColina de Laranjeiras"
        val rows=TextOfferGuardV85.rows(raw)
        assertEquals(2,rows.size)
        assertEquals("B32",rows[1].cage)
        assertEquals("Colina de Laranjeiras",rows[1].neighborhood)
    }
    @Test fun requestsAndGhosts() {
        for(raw in listOf("Entregador\n1234567\nPasseio\nGaiola: A-09",
            "Rosario A09","A-09 Rosario", "A-09\tAT20261127DLR4G\t120\nRosario",
            "A-09\tAT20261127DLR4G\tX\tAusente\tSerra\tRosario",
            "mensagem citada\nA-09\tAT20261127DLR4G\t120\tAusente\tSerra\tRosario"))
            assertTrue(raw,TextOfferGuardV85.rows(raw).isEmpty())
    }
    @Test fun sameLineOnly() {
        val rows=TextOfferGuardV85.rows("A-09\tAT20261127DLR4G\t120\tAusente\tSerra\tBarcelona\nRosario")
        assertEquals(1,rows.size)
        assertEquals("Barcelona",rows.single().neighborhood)
        assertEquals("A09",rows.single().cage)
    }
    @Test fun spaceVariantsAndVariableField() {
        assertEquals("B32",TextOfferGuardV85.rows("B-32 AT20261127DLPMZ 101 Outro nome Serra Colina de Laranjeiras").single().cage)
        assertEquals("C08",TextOfferGuardV85.rows("C-08  AT20261127DLHBI  133  Outro nome  Serra  Nova Carapina II").single().cage)
    }
}
''',encoding="utf-8")
print("V85 text guard applied; image report unchanged; strict rows and Read More guarded.")
