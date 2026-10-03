from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v18 | TEXT v6 + READ MORE STRICT PROOF + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v19 | TEXT v6 + CHAT LIST COLLECT + READ MORE STRICT PROOF + DIRECT SEND ====='
required=[
    old_header,
    'private fun analyzeCurrentWindow() {',
    'val tdCollectStart = SystemClock.elapsedRealtime()',
    'val items = collectNodeItems(root)',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]
for m in required:
    if m not in s:
        raise SystemExit('TEXT CHAT LIST COLLECT v19 wrong base: '+m)

# A/B isolated optimization:
# analyzeCurrentWindow() only needs the conversation rows to discover a new text
# route / Read More / image bubble. The old collector walked the whole WhatsApp
# window, including toolbar, composer and unrelated controls. On the M52 this
# showed up as 50ms in "Arvore inicial coletada".
#
# We locate android:id/list (the exact ListView exposed by the probe) and run the
# SAME collectNodeItems() on that subtree. Parser, TAIL v6, Read More v18, IMAGE
# v9 and send paths are untouched. If WhatsApp ever stops exposing the list id,
# the function falls back to the original full-root collection.
analyze_anchor='    private fun analyzeCurrentWindow() {'
helper=r'''    private fun collectConversationItemsV19(root:AccessibilityNodeInfo):List<NodeItem> {
        try {
            val candidates=root.findAccessibilityNodeInfosByViewId("android:id/list")
            if(!candidates.isNullOrEmpty()){
                val sw=resources.displayMetrics.widthPixels
                val sh=resources.displayMetrics.heightPixels
                var best:AccessibilityNodeInfo?=null
                var bestArea=0L
                for(n in candidates){
                    val r=Rect()
                    try{n.getBoundsInScreen(r)}catch(_:Throwable){}
                    if(r.isEmpty)continue
                    val conversationLike = r.width()>=(sw*0.72f).toInt() && r.height()>=(sh*0.35f).toInt()
                    if(!conversationLike)continue
                    val area=r.width().toLong()*r.height().toLong()
                    if(area>bestArea){best=n;bestArea=area}
                }
                if(best!=null){
                    return collectNodeItems(best!!)
                }
            }
        }catch(_:Throwable){}
        return collectNodeItems(root)
    }

'''
if analyze_anchor not in s:
    raise SystemExit('v19 analyze anchor not found')
s=s.replace(analyze_anchor,helper+analyze_anchor,1)

# Replace ONLY the timed initial collection inside analyzeCurrentWindow(). Other
# collectors (prime, editor/send, confirmation, image internals) remain original.
old_block='''        val tdCollectStart = SystemClock.elapsedRealtime()
        val items = collectNodeItems(root)
        val tdCollectDoneLocal = SystemClock.elapsedRealtime()
        val tdCollectLocal = tdCollectDoneLocal - tdCollectStart
'''
new_block='''        val tdCollectStart = SystemClock.elapsedRealtime()
        val items = collectConversationItemsV19(root)
        val tdCollectDoneLocal = SystemClock.elapsedRealtime()
        val tdCollectLocal = tdCollectDoneLocal - tdCollectStart
'''
if old_block not in s:
    raise SystemExit('v19 timed initial collection block not found')
s=s.replace(old_block,new_block,1)

s=s.replace(old_header,new_header,1)

# Safety: exactly one hot-path call should have changed, and critical v18/v9
# markers must remain intact.
for m in [
    new_header,
    'private fun collectConversationItemsV19(',
    'val items = collectConversationItemsV19(root)',
    'findAccessibilityNodeInfosByViewId("android:id/list")',
    'private data class ReadMoreProofV18(',
    'TEXT v18: Ler mais NAO expandiu/nao foi comprovado',
    'readMoreProof=$tdReadMoreProofV18',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('TEXT CHAT LIST COLLECT v19 verify failed: '+m)

if s.count('val items = collectConversationItemsV19(root)') != 1:
    raise SystemExit('v19 expected exactly one analyzer collection replacement')

S.write_text(s,encoding='utf-8')
print('TEXT v19 CHAT LIST COLLECT applied: initial analyzer collection limited to android:id/list; v18 Read More, TEXT v6, IMAGE v9 and send untouched')
