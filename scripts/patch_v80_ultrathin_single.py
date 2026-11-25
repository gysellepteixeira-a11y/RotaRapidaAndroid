from pathlib import Path
root=Path("app/src/main/java/com/gy/rotarapida")
S=root/"WhatsRouteAccessibilityService.kt"
s=S.read_text(encoding="utf-8")
def once(src,old,new):
    assert src.count(old)==1, ("V80 anchor",old,src.count(old))
    return src.replace(old,new,1)

a=s.index("    private fun readMediaUltraThinV59(media: MediaImage) {")
b=s.index("\n    private fun readMediaOriginalFull(",a)
t=s[a:b]
t=once(t,"        val starts = ArrayList<Int>()\n","        val starts = ArrayList<Int>()\n")
t=once(t,"        val screenItems = ArrayList<ScreenText>()\n",'''        val originalStarts=starts.toList()
        var v80Single=source.height in 56..99 && source.width in 420..2200 && starts.size>1
        v80ThinMode=if(v80Single) "SINGLE_TRY" else "ORIGINAL_TILES"
        if(v80Single) {
            starts.clear()
            starts.add(0)
        }
        val screenItems = ArrayList<ScreenText>()
''')
t=once(t,"        fun finishUltraThin() {\n","        fun finishUltraThin(): Boolean {\n")
t=once(t,"                return\n            }\n\n            val v78ParseAt","                return true\n            }\n\n            val v78ParseAt")
t=once(t,"            v78ThinParseMs+=SystemClock.elapsedRealtime()-v78ParseAt\n",'''            if(v80Single) {
                val accepted=route!=null && UltraThinProofV80.accept(route,screenItems)
                v78ThinParseMs+=SystemClock.elapsedRealtime()-v78ParseAt
                v80SingleOcrMs=v78ThinOcrMs
                if(!accepted) {
                    v80ThinMode=if(route==null) "FALLBACK_NO_ROUTE" else "FALLBACK_NO_PROOF"
                    return false
                }
                v80ThinMode="SINGLE_ACCEPTED"
            } else {
                v78ThinParseMs+=SystemClock.elapsedRealtime()-v78ParseAt
            }
''')
t=once(t,"                readMediaEnhanced(media)\n            }\n        }\n\n        fun processTile", "                readMediaEnhanced(media)\n            }\n            return true\n        }\n\n        fun processTile")
t=once(t,"                finishUltraThin()\n                return\n",'''                if(!finishUltraThin()) {
                    v80Single=false
                    starts.clear()
                    starts.addAll(originalStarts)
                    v78ThinTiles+=starts.size
                    screenItems.clear()
                    rawTexts.clear()
                    processTile(0)
                }
                return
''')
t=once(t,"            val width = minOf(tileWidth, source.width - x).coerceAtLeast(1)\n","            val width = if(v80Single) source.width else minOf(tileWidth, source.width - x).coerceAtLeast(1)\n")
# Bitmap.createBitmap/createScaledBitmap may return input itself.
# Never recycle source until all OCR and any fallback have finished.
t=t.replace("if (work !== tile) {","if (work !== tile && tile !== source) {")
t=t.replace("try { work.recycle() } catch (_: Throwable) {}","if(work !== source) { try { work.recycle() } catch (_: Throwable) {} }")
s=s[:a]+t+s[b:]
s=once(s,"    private var v79MatchRequests=0\n",'''    private var v80ThinMode="NOT_USED"
    private var v80SingleOcrMs=0L
    private var v79MatchRequests=0
''')
s=once(s,"        v79MatchRequests=0\n",'''        v80ThinMode="NOT_USED"
        v80SingleOcrMs=0L
        v79MatchRequests=0
''')
s=once(s,' | ultrafina=V78_3_TILES")',' | ultrafina="+v80ThinMode)')
s=once(s,'            appendLine("RESUMO")\n','''            appendLine("V80 ULTRAFINA | modo="+v80ThinMode+" | OCRsingle="+v80SingleOcrMs+"ms | chamadasTotal="+v78ThinCalls+" | tilesPlanejados="+v78ThinTiles)
            appendLine("RESUMO")
''')
for marker in ["ModalFilter.filter(", "V79 PARSER FAST", "V78 PERFIL","V77 TABELA CURTA","V76 COLUNA ESQUERDA","hasExactNativeRouteProofV70(","isFeuRosaRowV684","readMediaEnhanced(media)"]:
    assert marker in s,marker
assert "sendSmsOnlyV664(" not in s
S.write_text(s,encoding="utf-8")
(root/"UltraThinProofV80.kt").write_text(r'''package com.gy.rotarapida

import java.util.Locale
import kotlin.math.abs

// Conservative acceptance of a single full-width OCR. An unreadable higher
// priority can still be missed by OCR, so real mixed-priority samples matter.
internal object UltraThinProofV80 {
    private val cageToken=Regex("""^[A-Z1][-.\s]?\d{2}$""")
    private fun sameRow(a:ScreenText,b:ScreenText):Boolean {
        val h=minOf(a.bottom-a.top,b.bottom-b.top).coerceAtLeast(1)
        return abs(a.centerY-b.centerY)<=maxOf(2,h/2)
    }
    fun accept(route:RouteResult,items:List<ScreenText>):Boolean {
        val hits=items.mapNotNull { item ->
            if(RouteParser.isFeuRosaRowV684(item.text)) null
            else RouteParser.matchPriority(item.text)?.let { it.first to item }
        }
        if(hits.minOfOrNull { it.first }!=route.priorityIndex) return false
        val cages=items.mapNotNull { item ->
            val raw=item.text.trim().uppercase(Locale.ROOT)
            if(!cageToken.matches(raw)) null
            else RouteParser.extractCage(raw)?.let { it to item }
        }
        return hits.any { (priority,bairro) ->
            if(priority!=route.priorityIndex) false
            else if(items.any { RouteParser.isFeuRosaRowV684(it.text) && sameRow(it,bairro) }) false
            else {
                val onRow=cages.filter { (_,cage) ->
                    cage.right<=bairro.right && sameRow(cage,bairro)
                }.map { it.first }.toSet()
                onRow==setOf(route.cage)
            }
        }
    }
}
''',encoding="utf-8")
test=Path("app/src/test/java/com/gy/rotarapida/UltraThinProofV80Test.kt")
test.write_text(r'''package com.gy.rotarapida

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class UltraThinProofV80Test {
    private fun item(t:String,x:Int,y:Int,w:Int=30)=ScreenText(t,x,y,x+w,y+10)
    @Test fun requiresCageInSameRowAndHighestRecognizedPriority() {
        RouteParser.configurePriorities(listOf("Rosario","Morada de Laranjeiras"))
        val route=RouteResult("Morada de Laranjeiras","E06",1)
        val bairro=item("Morada de Laranjeiras",200,20,160)
        val cage=item("E06",10,20)
        assertTrue(UltraThinProofV80.accept(route,listOf(bairro,cage)))
        assertFalse(UltraThinProofV80.accept(route,listOf(bairro,item("E06",10,40))))
        assertFalse(UltraThinProofV80.accept(route,listOf(bairro,cage,item("A01",50,20))))
        assertFalse(UltraThinProofV80.accept(route,listOf(bairro,cage,item("Rosario",200,40))))
        assertFalse(UltraThinProofV80.accept(route,listOf(bairro)))
    }
}
''',encoding="utf-8")
print("V80 single full width at native resolution for 56..99px, original tiles fallback with source reuse, priority/cage proof")
