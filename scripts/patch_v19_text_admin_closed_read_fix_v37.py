from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

old_header='===== DIAGNOSTICO TEXTO v36 | TEXT v6 + ASCII NORMALIZE FAST + PARSER SPLIT DIAG + LOCAL ANCHOR PROOF + SKIP BAND + TRUNC BEFORE ROOT + LAZY ADMIN + READ MORE v21 + DIRECT SEND ====='
new_header='===== DIAGNOSTICO TEXTO v37 | TEXT v6 + ADMIN CLOSED READ FIX + ASCII NORMALIZE FAST + LOCAL ANCHOR PROOF + READ MORE v21 + DIRECT SEND ====='

required=[
    old_header,
    'private var adminLockedConversationActive = false',
    'private fun isAdminLockedGroup(items: List<NodeItem>): Boolean {',
    'private fun isGroupSettingsSystemText(text: String): Boolean {',
    'private fun subtreeNormalizedText(',
    'val adminLockedGroupNow = if(messageEditorAvailable)',
    'lazyAdminV29=collect->editor=',
    'normalizeV36=$tdV36NormalizeDiag',
    'private const val PENDING_ROUTE_SEND_WATCH_MS = 10L',
]
for m in required:
    if m not in s:
        raise SystemExit('ADMIN CLOSED READ FIX v37 wrong base: '+m)

state_anchor='    private var adminLockedConversationActive = false\n'
state_insert=state_anchor+'    private var rmV37AdminLockSource="NONE"\n    private var tdV37AdminLockSource="NONE"\n'
if state_anchor not in s:
    raise SystemExit('v37 admin state anchor not found')
s=s.replace(state_anchor,state_insert,1)

# Replace EXACTLY isAdminLockedGroup(), using brace matching. Do not delete any
# helper that later patches may have inserted between this function and the next
# historically-known function (e.g. direct MediaStore helpers).
start=s.find('    private fun isAdminLockedGroup(items: List<NodeItem>): Boolean {')
if start<0:
    raise SystemExit('v37 isAdminLockedGroup start not found')
open_brace=s.find('{',start)
if open_brace<0:
    raise SystemExit('v37 isAdminLockedGroup opening brace not found')
depth=0
end=-1
for i in range(open_brace,len(s)):
    ch=s[i]
    if ch=='{':
        depth+=1
    elif ch=='}':
        depth-=1
        if depth==0:
            end=i+1
            break
if end<0:
    raise SystemExit('v37 isAdminLockedGroup closing brace not found')

new_helper=r'''    private fun isAdminLockedGroup(items: List<NodeItem>): Boolean {
        val allVisibleText = items.asSequence()
            .map { RouteParser.normalize(it.text) }
            .filter { it.isNotBlank() }
            .joinToString(" ")

        if (allVisibleText.isNotBlank()) {
            val directRestricted =
                allVisibleText.contains("somente admin") ||
                allVisibleText.contains("somente os admin") ||
                allVisibleText.contains("somente administrador") ||
                allVisibleText.contains("apenas admin") ||
                allVisibleText.contains("apenas os admin") ||
                allVisibleText.contains("so admin") ||
                allVisibleText.contains("so os admin") ||
                allVisibleText.contains("only admin") ||
                allVisibleText.contains("only administrators")

            val directSendMessage =
                allVisibleText.contains("enviar mensagens") ||
                allVisibleText.contains("enviar mensagem") ||
                (allVisibleText.contains("podem enviar") && allVisibleText.contains("mensagem")) ||
                allVisibleText.contains("send messages") ||
                allVisibleText.contains("send message")

            val explicitlyOpen =
                allVisibleText.contains("todos os membros podem enviar") ||
                allVisibleText.contains("todos podem enviar") ||
                allVisibleText.contains("all participants can send") ||
                allVisibleText.contains("everyone can send")

            if (directRestricted && directSendMessage && !explicitlyOpen) {
                rmV37AdminLockSource="DIRECT_BANNER"
                return true
            }
        }

        val latest = items.asSequence()
            .map { item ->
                val own = RouteParser.normalize(item.text)
                val text = if (isGroupSettingsSystemText(own)) {
                    own
                } else {
                    val cls = item.className
                    val genericContainer =
                        cls.contains("View", ignoreCase = true) ||
                        cls.contains("Frame", ignoreCase = true) ||
                        cls.contains("Layout", ignoreCase = true)
                    if (genericContainer) {
                        subtreeNormalizedText(item.node, maxDepth = 5)
                    } else {
                        ""
                    }
                }
                item to text
            }
            .filter { (_, text) -> isGroupSettingsSystemText(text) }
            .maxByOrNull { (item, _) -> item.rect.bottom }

        if (latest == null) {
            rmV37AdminLockSource="NONE"
            return false
        }

        val text = latest.second
        val openedForEveryone =
            text.contains("todos os membros") ||
            text.contains("all participants") ||
            text.contains("everyone")

        if (openedForEveryone) {
            rmV37AdminLockSource="CONFIG_OPEN"
            return false
        }

        val locked =
            text.contains("somente admin") ||
            text.contains("apenas admin") ||
            text.contains("only admin")

        rmV37AdminLockSource=if(locked) "CONFIG_LOCKED" else "NONE"
        return locked
    }'''
s=s[:start]+new_helper+s[end:]

admin_old='''        val adminLockedGroupNow = if(messageEditorAvailable){
            rmV29AdminSkipped=true
            false
        }else{
            rmV29AdminSkipped=false
            isAdminLockedGroup(items)
        }
'''
admin_new='''        val adminLockedGroupNow = if(messageEditorAvailable){
            rmV29AdminSkipped=true
            rmV37AdminLockSource="EDITOR"
            false
        }else{
            rmV29AdminSkipped=false
            isAdminLockedGroup(items)
        }
'''
if admin_old not in s:
    raise SystemExit('v37 lazy admin block not found')
s=s.replace(admin_old,admin_new,1)

copy_anchor='tdV29TailLoopMs=rmV29TailLoopMs'
if copy_anchor not in s:
    raise SystemExit('v37 v29 snapshot anchor not found')
s=s.replace(copy_anchor,copy_anchor+'; tdV37AdminLockSource=rmV37AdminLockSource',1)

report_anchor='''                    appendLine("lazyAdminV29=collect->editor=${tdD(tdV27CollectDoneAt,tdV29EditorStartAt)} | editor=${tdV29EditorMs}ms | adminCheck=${tdV29AdminMs}ms | adminSkipped=$tdV29AdminSkipped | editorDone->tailStart=${tdD(tdV29EditorDoneAt,tdV29TailLoopStartAt)} | tailLoop=${tdV29TailLoopMs}ms | tailDone->desc=${tdD(tdV29TailLoopDoneAt,tdV27DescStartAt)}")
'''
report_insert=report_anchor+'''                    appendLine("adminLockV37=source=$tdV37AdminLockSource | directBannerRestored=true | pendingWatch=10ms")
'''
if report_anchor not in s:
    raise SystemExit('v37 report anchor not found')
s=s.replace(report_anchor,report_insert,1)

s=s.replace(old_header,new_header,1)

for m in [
    new_header,
    'rmV37AdminLockSource="DIRECT_BANNER"',
    '"CONFIG_LOCKED"',
    'rmV37AdminLockSource="EDITOR"',
    'adminLockV37=source=$tdV37AdminLockSource',
    'pendingWatch=10ms',
    'normalizeV36=$tdV36NormalizeDiag',
    'localProofV33=calls=$tdV33LocalCalls',
    'speedDiagnosticSendMethod = "TEXT_DIRECT_V5"',
    'checkDirectMediaStoreImage(',
    '===== DIAGNOSTICO IMAGEM v9 | BAIRRO FIRST + GAIOLA NARROW + DIRECT SEND + BULK PIXELS =====',
]:
    if m not in s:
        raise SystemExit('ADMIN CLOSED READ FIX v37 verify failed: '+m)

S.write_text(s,encoding='utf-8')
print('ADMIN CLOSED READ FIX v37 applied: direct live admin-lock banner + existing latest-config fallback; exact function replacement; MediaStore helpers preserved; pending watcher preserved')
