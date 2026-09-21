from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - ADMIN LOCK STABLE
#
# O aviso de "somente admins podem enviar" nem sempre aparece como UM unico no
# de acessibilidade. Em alguns eventos ele vem dividido em varios textos e, em
# outros, some temporariamente da arvore. A versao anterior dependia de achar a
# frase inteira num unico item e por isso a leitura ficava intermitente.
#
# Esta correcao NAO altera OCR, parser ou leitura densa da v0.19. Ela apenas:
# 1) reconhece o aviso juntando TODOS os textos visiveis da tela;
# 2) depois que reconhece que o grupo esta bloqueado pelo admin, memoriza esse
#    estado enquanto o campo de mensagem continuar ausente;
# 3) quando o campo reaparece, limpa o estado e a pendingRoute e enviada pelo
#    watcher ja existente.

# Estado persistente em memoria enquanto a conversa continua bloqueada.
state_anchor = '    private var processing = false\n'
if 'private var adminLockedConversationActive' not in s:
    if state_anchor not in s:
        raise SystemExit('patch_v19_admin_lock_stable: estado processing nao encontrado')
    s = s.replace(
        state_anchor,
        state_anchor + '    private var adminLockedConversationActive = false\n',
        1
    )

# Troca o detector item-a-item por detector da arvore inteira.
start = s.find('    private fun isAdminLockedGroup(items: List<NodeItem>): Boolean {')
end = s.find('\n    private fun keepOcrEngineWarm() {', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'patch_v19_admin_lock_stable: isAdminLockedGroup nao encontrado (start={start}, end={end})'
    )

new_helper = r'''    private fun isAdminLockedGroup(items: List<NodeItem>): Boolean {
        // O WhatsApp pode quebrar "Somente admins podem enviar mensagens" em
        // varios AccessibilityNodeInfo. Por isso analisamos o texto agregado.
        val allText = items.asSequence()
            .map { RouteParser.normalize(it.text) }
            .filter { it.isNotBlank() }
            .joinToString(" ")

        if (allText.isBlank()) return false

        val admin =
            allText.contains("admin") ||
            allText.contains("administrador")

        val restrictive =
            allText.contains("somente") ||
            allText.contains("apenas") ||
            allText.contains("so admin") ||
            allText.contains("so os admin") ||
            allText.contains("only admin") ||
            allText.contains("admins podem") ||
            allText.contains("administradores podem")

        val sendMessage =
            allText.contains("enviar") ||
            allText.contains("mensagem") ||
            allText.contains("send") ||
            allText.contains("message")

        return admin && restrictive && sendMessage
    }
'''

s = s[:start] + new_helper + s[end:]

# Mantem o estado de grupo bloqueado mesmo se o aviso desaparecer da arvore por
# alguns eventos. So limpa quando o campo de mensagem realmente reaparece.
old_analyze = '''        val messageEditorAvailable = findMessageEditor(items) != null
        val adminLockedGroup = isAdminLockedGroup(items)

        if (!messageEditorAvailable && !adminLockedGroup) {
            previousTexts = textSignatures(items)
            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
            primed = true
            return
        }
'''
new_analyze = '''        val messageEditorAvailable = findMessageEditor(items) != null
        val adminLockedGroupNow = isAdminLockedGroup(items)

        if (messageEditorAvailable) {
            // O admin liberou o grupo (ou estamos em uma conversa normal).
            adminLockedConversationActive = false
        } else if (adminLockedGroupNow) {
            // Memoriza o bloqueio porque o aviso pode sumir da arvore em eventos
            // seguintes mesmo continuando na mesma conversa.
            adminLockedConversationActive = true
        }

        if (!messageEditorAvailable && !adminLockedConversationActive) {
            previousTexts = textSignatures(items)
            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
            primed = true
            return
        }
'''
if old_analyze not in s:
    raise SystemExit('patch_v19_admin_lock_stable: bloco de validacao admin nao encontrado')
s = s.replace(old_analyze, new_analyze, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 ADMIN LOCK STABLE aplicado: bloqueio por admin deixa de depender de um unico no de acessibilidade")
