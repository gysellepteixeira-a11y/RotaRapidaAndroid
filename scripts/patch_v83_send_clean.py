from pathlib import Path
p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")
def once(src,old,new):
    assert src.count(old)==1, ("V83 anchor",old,src.count(old))
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

# V83: restore V81 original crop and V69 direct ID lookup by applying only
# the descriptor decoder from V82. No BFS, no pixel margin inspection.
# Keep fresh root, original click, verification and group-closed flow.
a,b,t=section("waitForImageDirectSendReadyV8")
t=once(t,"        val root = rootInActiveWindow\n",'''        val v83RootAt=SystemClock.elapsedRealtime()
        val root = rootInActiveWindow
        v83RootMs+=SystemClock.elapsedRealtime()-v83RootAt
''')
t=once(t,"        val sendNode = findAdminUltraSendNodeFast(root, editorRect)\n",'''        val v83LookupAt=SystemClock.elapsedRealtime()
        val sendNode = findAdminUltraSendNodeFast(root, editorRect)
        v83LookupMs+=SystemClock.elapsedRealtime()-v83LookupAt
        if(sendNode!=null) v83SendSource="LEGACY_"+adminUltraSendSourceV69
''')
s=s[:a]+t+s[b:]
s=once(s,'    private var v80ThinMode="NOT_USED"\n','''    private var v82DecodeMode="NOT_USED"
    private var v82FdMs=0L
    private var v82StreamMs=0L
    private var v83RootMs=0L
    private var v83LookupMs=0L
    private var v83SendSource="NOT_USED"
    private var v80ThinMode="NOT_USED"
''')
s=once(s,'        v80ThinMode="NOT_USED"\n','''        v82DecodeMode="NOT_USED"
        v82FdMs=0L
        v82StreamMs=0L
        v83RootMs=0L
        v83LookupMs=0L
        v83SendSource="NOT_USED"
        v80ThinMode="NOT_USED"
''')
a,b,t=section("idReport")
t=once(t,'            appendLine("RESUMO")\n','''            appendLine("V82 DECODE | modo="+v82DecodeMode+" | fd="+v82FdMs+"ms | stream="+v82StreamMs+"ms")
            appendLine("V83 ENVIO | fonte="+v83SendSource+" | root="+v83RootMs+"ms | lookup="+v83LookupMs+"ms | BFS=REMOVIDA")
            appendLine("V83 BAIRRO | recorte=V81_ORIGINAL | trim=REMOVIDO")
            appendLine("RESUMO")
''')
s=s[:a]+t+s[b:]
for marker in ["UltraThinProofV80.accept(route,screenItems)","starts.addAll(originalStarts)","ModalFilter.filter(","V79 PARSER FAST","V77 TABELA CURTA","V76 COLUNA ESQUERDA","hasExactNativeRouteProofV70(","isFeuRosaRowV684","readMediaOriginalFull(media)","findAdminUltraSendNodeFast(root, editorRect)","verifySendResult(route, 0, 0)","V69 GRUPO FECHADO"]:
    assert marker in s,marker
for removed in ["findNamedSendV82(","trimWhiteBairroV82(","WhiteMarginV82","v82BfsMs","sendSmsOnlyV664("]:
    assert removed not in s,removed
assert s.count("decodeMediaV82(media)")==2
p.write_text(s,encoding="utf-8")
print("V83: FD decoder preserved, V81 crop and direct ID lookup restored, fresh-root safety and diagnostics preserved")
