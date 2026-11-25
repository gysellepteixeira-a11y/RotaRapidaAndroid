from pathlib import Path

P=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
p=P.read_text(encoding="utf-8")
s=S.read_text(encoding="utf-8")
def once(src, old, new):
    assert src.count(old)==1, ("V79 anchor",old,src.count(old))
    return src.replace(old,new,1)

# Exact ASCII equivalent of the original lowercase/NFD/regex normalization;
# Unicode retains the original operations with precompiled regexes.
# Initialize before dynamic priority rules, which themselves call normalize().
p=once(p,"object RouteParser {\n",r'''object RouteParser {
    private val v79Marks=Regex("""\p{Mn}+""")
    private val v79NonAlnum=Regex("""[^a-z0-9\s]""")
    private val v79Spaces=Regex("""\s+""")
''')
old=r'''    fun normalize(value: String): String {
        val decomposed = Normalizer.normalize(
            value.lowercase(Locale.ROOT).trim(),
            Normalizer.Form.NFD
        )

        return decomposed
            .replace(Regex("""\p{Mn}+"""), "")
            .replace(Regex("""[^a-z0-9\s]"""), " ")
            .replace(Regex("""\s+"""), " ")
            .trim()
    }
'''
new=r'''    fun normalize(value: String): String {
        // V79: no changes to Unicode normalization or matching rules.
        if (value.all { it.code <= 127 }) {
            val out=StringBuilder(value.length)
            var pending=false
            for (raw in value) {
                val ch=if(raw in 'A'..'Z') (raw.code+32).toChar() else raw
                if (ch in 'a'..'z' || ch in '0'..'9') {
                    if (pending && out.isNotEmpty()) out.append(' ')
                    out.append(ch)
                    pending=false
                } else if (out.isNotEmpty()) {
                    pending=true
                }
            }
            return out.toString()
        }
        val decomposed = Normalizer.normalize(
            value.lowercase(Locale.ROOT).trim(),
            Normalizer.Form.NFD
        )
        return decomposed
            .replace(v79Marks, "")
            .replace(v79NonAlnum, " ")
            .replace(v79Spaces, " ")
            .trim()
    }
'''
p=once(p,old,new)

# Cache only within a single Bairro callback, never across images or rearming.
# Geometry, tie-break, guard and all calls to consider are preserved.
a=s.index("    private fun readDenseBairroFirst(")
b=s.index("\n    private fun readDenseFullFallback(",a)
t=s[a:b]
t=once(t,"                var best: BairroFirstHit? = null\n",'''                var best: BairroFirstHit? = null
                val v79Matches=HashMap<String, Pair<Int,String>?>()
                val v79FeuRows=HashMap<String, Boolean>()
''')
t=once(t,"                    val priority = matchBairroFirstPriority(rawText) ?: return\n",'''                    v79MatchRequests++
                    val priority = if (v79Matches.containsKey(rawText)) {
                        v79CacheHits++
                        v79Matches[rawText]
                    } else {
                        matchBairroFirstPriority(rawText).also { v79Matches[rawText]=it }
                    } ?: return
''')
t=once(t,"                        if (RouteParser.isFeuRosaRowV684(line.text)) continue\n",'''                        if (v79FeuRows.getOrPut(line.text) { RouteParser.isFeuRosaRowV684(line.text) }) continue
''')
# Only construct debug text when fallback actually needs it.
raw=r'''                val rawSample = text.text
                    .replace("\n", " | ")
                    .replace(Regex("\\s+"), " ")
                    .trim()
                    .take(140)

'''
t=once(t,raw,"")
t=once(t,"                if (chosen == null) {\n",
         "                if (chosen == null) {\n"+''.join("    "+line+"\n" for line in raw.rstrip().splitlines())+"\n")
s=s[:a]+t+s[b:]
s=once(s,"    private var v78ThinDecodeMs=0L\n","    private var v79MatchRequests=0\n    private var v79CacheHits=0\n    private var v78ThinDecodeMs=0L\n")
s=once(s,"        v78ThinDecodeMs=0L\n","        v79MatchRequests=0\n        v79CacheHits=0\n        v78ThinDecodeMs=0L\n")
a=s.index("    private fun idReport(route:RouteResult){")
b=s.index("\n    private fun ",a+20)
t=s[a:b]
t=once(t,'            appendLine("RESUMO")\n','''            appendLine("V79 PARSER FAST | normalizacao=ASCII_EQUIVALENTE_UNICODE_REGEX_CACHE | consultas="+v79MatchRequests+" | cacheHits="+v79CacheHits+" | selecao="+v78BairroSelectMs+"ms | ultrafina=V78_3_TILES")
            appendLine("RESUMO")
''')
s=s[:a]+t+s[b:]
for marker in ["V78 PERFIL","V77 TABELA CURTA","V76 COLUNA ESQUERDA","readMediaUltraThinV59(","readMediaOriginalFull(media)","hasExactNativeRouteProofV70(","isFeuRosaRowV684","ModalFilter.filter("]:
    assert marker in s, marker
assert "sendSmsOnlyV664(" not in s
P.write_text(p,encoding="utf-8")
S.write_text(s,encoding="utf-8")
# Unit test the normalization against the exact previous implementation,
# including ASCII control characters, accents and randomized mixed inputs.
test=Path("app/src/test/java/com/gy/rotarapida/RouteParserV79NormalizationTest.kt")
test.parent.mkdir(parents=True,exist_ok=True)
test.write_text(r'''package com.gy.rotarapida

import java.text.Normalizer
import java.util.Locale
import kotlin.random.Random
import org.junit.Assert.assertEquals
import org.junit.Test

class RouteParserV79NormalizationTest {
    private fun legacy(value:String):String =
        Normalizer.normalize(value.lowercase(Locale.ROOT).trim(),Normalizer.Form.NFD)
            .replace(Regex("""\p{Mn}+"""),"")
            .replace(Regex("""[^a-z0-9\s]""")," ")
            .replace(Regex("""\s+""")," ")
            .trim()

    @Test fun exactNormalization() {
        val samples=listOf("", "Rosário de Fátima", "Feu Rosa", "Rosa rio",
            "MORADA DE LARANJEIRAS", "Manoel Plaza", "A-26\tMata da Praia",
            "ÁÉÍÓÚ Ç ß İ １２", "\u0000\t\r\n", "I\u0301", "😀 bairro")
        for (sample in samples) assertEquals(sample,legacy(sample),RouteParser.normalize(sample))
        for (i in 0..127) {
            val sample="A"+i.toChar()+"b"
            assertEquals(sample,legacy(sample),RouteParser.normalize(sample))
        }
        val rng=Random(79)
        val alphabet=(0..127).map{it.toChar()}+"áéíóúãõçİß\u0301\u00a0".toList()
        repeat(3000) {
            val sample=buildString { repeat(rng.nextInt(0,70)) { append(alphabet[rng.nextInt(alphabet.size)]) } }
            assertEquals(sample,legacy(sample),RouteParser.normalize(sample))
        }
    }
}
''',encoding="utf-8")
print("V79 parser fast: exact normalization, callback-local memo, debug sample only on fallback; original OCR dispatch and selection preserved")
