from pathlib import Path
p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")
def once(src,old,new):
    assert src.count(old)==1, ("V82 anchor",old,src.count(old))
    return src.replace(old,new,1)
def section(name):
    a=s.index("    private fun "+name+"(")
    b=s.index("\n    private fun ",a+20)
    return a,b,s[a:b]

# Keep identical BitmapFactory defaults; only change the transport to a
# seekable descriptor. Stream path remains available if FD decoding fails.
for name in ["readMediaLargeColorCrop","readMediaUltraThinV59"]:
    a,b,t=section(name)
    old='''contentResolver.openInputStream(media.uri)?.use { stream ->
                BitmapFactory.decodeStream(stream)
            }'''
    new="decodeMediaV82(media)"
    if name=="readMediaUltraThinV59":
        old='''contentResolver.openInputStream(media.uri)?.use { stream ->
                BitmapFactory.decodeStream(stream)?.let { original ->
                    ModalFilter.filter(original, original, 0, Prefs.includeFake(this))
                }
            }'''
        new='''decodeMediaV82(media)?.let { original ->
                ModalFilter.filter(original, original, 0, Prefs.includeFake(this))
            }'''
    assert t.count(old)==1,(name,t.count(old))
    t=t.replace(old,new,1)
    s=s[:a]+t+s[b:]
a=s.index("    private fun readMediaUltraThinV59(")
s=s[:a]+'''    private fun decodeMediaV82(media: MediaImage): Bitmap? {
        val fdAt=SystemClock.elapsedRealtime()
        val decoded=try {
            contentResolver.openFileDescriptor(media.uri,"r")?.use { descriptor ->
                BitmapFactory.decodeFileDescriptor(descriptor.fileDescriptor)
            }
        } catch (_: Throwable) { null }
        v82FdMs+=SystemClock.elapsedRealtime()-fdAt
        if(decoded!=null) {
            v82DecodeMode="FD"
            return decoded
        }
        v82DecodeMode="STREAM_FALLBACK"
        val streamAt=SystemClock.elapsedRealtime()
        return try {
            contentResolver.openInputStream(media.uri)?.use { BitmapFactory.decodeStream(it) }
        } finally {
            v82StreamMs+=SystemClock.elapsedRealtime()-streamAt
        }
    }

'''+s[a:]

# Only remove completely white edge columns; keep 12 px of white margin.
# No vertical changes, all non-white pixels retained, original full fallback.
a,b,t=section("readDenseBairroFirst")
t=once(t,"        val bairroBitmap = try {\n","        var bairroBitmap = try {\n")
# Avoid mutable nullable smart-casts: keep original immutable crop and use
# an immutable trimmed alias AFTER the original null guard.
t=t.replace("        var bairroBitmap = try {\n","        val v82OriginalBairro = try {\n",1)
t=once(t,"        if (bairroBitmap == null) {","        if (v82OriginalBairro == null) {")
t=once(t,"        val started = SystemClock.elapsedRealtime()\n",'''        val v82TrimAt=SystemClock.elapsedRealtime()
        val bairroBitmap=trimWhiteBairroV82(v82OriginalBairro)
        v82TrimMs=SystemClock.elapsedRealtime()-v82TrimAt
        val started = SystemClock.elapsedRealtime()
''')
s=s[:a]+t+s[b:]
a=s.index("    private fun readDenseBairroFirst(")
s=s[:a]+'''    private fun trimWhiteBairroV82(original: Bitmap): Bitmap {
        val w=original.width
        val h=original.height
        v82BairroOriginal=w
        v82BairroFinal=w
        if(w<200 || h<32 || w.toLong()*h>600000L) return original
        return try {
            val pixels=IntArray(w*h)
            original.getPixels(pixels,0,w,0,0,w,h)
            val range=WhiteMarginV82.range(pixels,w,h)
            if(range.first==0 && range.second==w) return original
            val trimmed=Bitmap.createBitmap(original,range.first,0,range.second-range.first,h)
            if(trimmed!==original) {
                v82BairroFinal=trimmed.width
                original.recycle()
            }
            trimmed
        } catch (_: Throwable) { original }
    }

'''+s[a:]

# Image send only. Inspect bounded fresh root tree for a named, visible,
# enabled node with the exact WhatsApp send ID and same positional criteria.
# On miss use unchanged V69 lookup. Never alter click/confirm or admin flow.
a,b,t=section("waitForImageDirectSendReadyV8")
t=once(t,"        val root = rootInActiveWindow\n",'''        val v82RootAt=SystemClock.elapsedRealtime()
        val root = rootInActiveWindow
        v82RootMs+=SystemClock.elapsedRealtime()-v82RootAt
''')
t=once(t,"        val sendNode = findAdminUltraSendNodeFast(root, editorRect)\n",'''        val v82LookupAt=SystemClock.elapsedRealtime()
        // Only the first poll attempts the bounded BFS; subsequent polls use
        // the original lookup so a missing ID never causes repeated overhead.
        val quick=if(poll==0) findNamedSendV82(root,editorRect) else null
        v82BfsMs+=SystemClock.elapsedRealtime()-v82LookupAt
        val v82LegacyAt=SystemClock.elapsedRealtime()
        val sendNode=quick ?: findAdminUltraSendNodeFast(root,editorRect)
        v82LegacyMs+=SystemClock.elapsedRealtime()-v82LegacyAt
        if(sendNode!=null) v82SendSource=if(quick!=null) "BFS_ID_NAMED" else "LEGACY_"+adminUltraSendSourceV69
''')
s=s[:a]+t+s[b:]
a=s.index("    private fun waitForImageDirectSendReadyV8(")
s=s[:a]+'''    private fun findNamedSendV82(root: AccessibilityNodeInfo, editorRect: Rect): AccessibilityNodeInfo? {
        val w=resources.displayMetrics.widthPixels
        val h=resources.displayMetrics.heightPixels
        val tolerance=maxOf(70,(h*0.06f).toInt())
        val queue=java.util.ArrayDeque<AccessibilityNodeInfo>()
        queue.add(root)
        var visited=0
        try {
            while(queue.isNotEmpty() && visited<48) {
                val node=queue.removeFirst()
                visited++
                val viewId=node.viewIdResourceName
                if(viewId=="com.whatsapp:id/send" || viewId=="com.whatsapp.w4b:id/send") {
                    val rect=Rect()
                    node.getBoundsInScreen(rect)
                    val named=RouteParser.normalize(
                        node.text?.toString().orEmpty()+" "+node.contentDescription?.toString().orEmpty()
                    )
                    if(node.isVisibleToUser && node.isEnabled && !rect.isEmpty &&
                        (named=="enviar" || named=="send" || named=="send message") &&
                        rect.right >= (w*0.78f).toInt() &&
                        kotlin.math.abs(rect.centerY()-editorRect.centerY())<=tolerance) {
                        v82BfsVisited=visited
                        return node
                    }
                }
                // Bound the number of remote getChild calls too.
                val count=minOf(node.childCount,48-visited-queue.size).coerceAtLeast(0)
                for(i in 0 until count) node.getChild(i)?.let { queue.addLast(it) }
            }
        } catch (_: Throwable) {}
        v82BfsVisited=visited
        return null
    }

'''+s[a:]
s=once(s,'    private var v80ThinMode="NOT_USED"\n','''    private var v82DecodeMode="NOT_USED"
    private var v82FdMs=0L
    private var v82StreamMs=0L
    private var v82BairroOriginal=0
    private var v82BairroFinal=0
    private var v82TrimMs=0L
    private var v82RootMs=0L
    private var v82BfsMs=0L
    private var v82LegacyMs=0L
    private var v82BfsVisited=0
    private var v82SendSource="NOT_USED"
    private var v80ThinMode="NOT_USED"
''')
s=once(s,'        v80ThinMode="NOT_USED"\n','''        v82DecodeMode="NOT_USED"
        v82FdMs=0L
        v82StreamMs=0L
        v82BairroOriginal=0
        v82BairroFinal=0
        v82TrimMs=0L
        v82RootMs=0L
        v82BfsMs=0L
        v82LegacyMs=0L
        v82BfsVisited=0
        v82SendSource="NOT_USED"
        v80ThinMode="NOT_USED"
''')
a,b,t=section("idReport")
t=once(t,'            appendLine("RESUMO")\n','''            appendLine("V82 DECODE | modo="+v82DecodeMode+" | fd="+v82FdMs+"ms | stream="+v82StreamMs+"ms")
            appendLine("V82 BAIRRO | original="+v82BairroOriginal+" | final="+v82BairroFinal+" | trim="+v82TrimMs+"ms")
            appendLine("V82 ENVIO | fonte="+v82SendSource+" | root="+v82RootMs+"ms | bfs="+v82BfsMs+"ms | visitados="+v82BfsVisited+" | legacy="+v82LegacyMs+"ms")
            appendLine("RESUMO")
''')
s=s[:a]+t+s[b:]
for marker in ["UltraThinProofV80.accept(route,screenItems)","starts.addAll(originalStarts)","ModalFilter.filter(","V79 PARSER FAST","V77 TABELA CURTA","V76 COLUNA ESQUERDA","hasExactNativeRouteProofV70(","isFeuRosaRowV684","readMediaOriginalFull(media)","findAdminUltraSendNodeFast(root,editorRect)","verifySendResult(route, 0, 0)"]:
    assert marker in s,marker
assert "sendSmsOnlyV664(" not in s
p.write_text(s,encoding="utf-8")
(p.parent/"WhiteMarginV82.kt").write_text(r'''package com.gy.rotarapida

internal object WhiteMarginV82 {
    // Exact opaque white only. Never trim colored or antialiased pixels.
    fun range(pixels:IntArray,w:Int,h:Int):Pair<Int,Int> {
        if(w<200 || h<32 || pixels.size!=w*h) return 0 to w
        fun white(x:Int):Boolean {
            for(y in 0 until h) if(pixels[y*w+x]!=-1) return false
            return true
        }
        var left=0
        while(left<w && white(left)) left++
        if(left==w) return 0 to w
        var right=w
        while(right>left && white(right-1)) right--
        left=(left-12).coerceAtLeast(0)
        right=(right+12).coerceAtMost(w)
        if(right-left<160 || w-(right-left)<maxOf(24,w/8)) return 0 to w
        return left to right
    }
}
''',encoding="utf-8")
Path("app/src/test/java/com/gy/rotarapida/WhiteMarginV82Test.kt").write_text(r'''package com.gy.rotarapida
import org.junit.Assert.assertEquals
import org.junit.Test
class WhiteMarginV82Test {
    @Test fun onlyExactWhiteWithPadding() {
        val w=320; val h=40
        val p=IntArray(w*h){-1}
        assertEquals(0 to w,WhiteMarginV82.range(p,w,h))
        for(x in 60 until 260) p[20*w+x]=0xff000000.toInt()
        assertEquals(48 to 272,WhiteMarginV82.range(p,w,h))
        p[0]=0xffeeeeee.toInt()
        assertEquals(0 to 272,WhiteMarginV82.range(p,w,h))
        p[w-1]=0xffeeeeee.toInt()
        assertEquals(0 to w,WhiteMarginV82.range(p,w,h))
    }
}
''',encoding="utf-8")
print("V82: descriptor decode with stream fallback; exact white margins only; bounded named send lookup with V69 fallback; timings")
