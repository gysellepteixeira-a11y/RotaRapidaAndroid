from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - ADMIN MESSAGE NOISE FIX
#
# Quando existem varios avisos do WhatsApp do tipo
# "X mudou as configuracoes desse grupo ... somente admins/todos os membros ...",
# alguns containers desses avisos sao expostos como View/FrameLayout sem texto
# proprio. O detector antigo de miniatura tratava esses containers como imagens.
# Como eles mudam de posicao quando novas mensagens chegam, pareciam sempre uma
# "imagem nova", iniciavam o fluxo MediaStore antes da rota real e podiam deixar
# a leitura intermitente.
#
# Correcao isolada:
# 1) containers que pertencem a avisos de mudanca de configuracao do grupo nunca
#    podem ser candidatos de imagem;
# 2) para saber se o grupo esta fechado pelo admin, usa o aviso de configuracao
#    MAIS BAIXO/RECENTE visivel, em vez de misturar todos os avisos antigos.
# Nao altera OCR, parser, prioridades, crop denso ou envio.

# -----------------------------------------------------------------------------
# Helper de texto da subarvore + detector de aviso de configuracao.
# -----------------------------------------------------------------------------
anchor = '    private fun findImageCandidates(items: List<NodeItem>): List<NodeItem> {\n'
if 'private fun subtreeNormalizedText(' not in s:
    if anchor not in s:
        raise SystemExit('patch_v19_admin_message_noise_fix: findImageCandidates nao encontrado')

    helper = r'''    private fun subtreeNormalizedText(
        node: AccessibilityNodeInfo,
        maxDepth: Int = 4,
        depth: Int = 0
    ): String {
        if (depth > maxDepth) return ""

        val parts = ArrayList<String>(8)

        val own = buildString {
            node.text?.toString()?.takeIf { it.isNotBlank() }?.let { append(it) }
            node.contentDescription?.toString()?.takeIf { it.isNotBlank() }?.let {
                if (isNotEmpty()) append(' ')
                append(it)
            }
        }

        val normalizedOwn = RouteParser.normalize(own)
        if (normalizedOwn.isNotBlank()) parts += normalizedOwn

        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            val childText = subtreeNormalizedText(child, maxDepth, depth + 1)
            if (childText.isNotBlank()) parts += childText
        }

        return parts.joinToString(" ")
    }

    private fun isGroupSettingsSystemText(text: String): Boolean {
        if (text.isBlank()) return false

        val changedSettings =
            text.contains("mudou as configuracoes") ||
            text.contains("alterou as configuracoes") ||
            text.contains("changed the group settings")

        val messagePermission =
            text.contains("enviem mensagens") ||
            text.contains("enviar mensagens") ||
            text.contains("send messages")

        val membershipRule =
            text.contains("somente admin") ||
            text.contains("apenas admin") ||
            text.contains("todos os membros") ||
            text.contains("all participants") ||
            text.contains("only admin")

        return changedSettings && messagePermission && membershipRule
    }

    private fun isGroupSettingsSystemCandidate(item: NodeItem): Boolean {
        val own = RouteParser.normalize(item.text)
        if (isGroupSettingsSystemText(own)) return true

        // So desce na subarvore para os candidatos genericos/containers.
        val cls = item.className
        val genericContainer =
            cls.contains("View", ignoreCase = true) ||
            cls.contains("Frame", ignoreCase = true) ||
            cls.contains("Layout", ignoreCase = true)

        if (!genericContainer) return false

        return isGroupSettingsSystemText(
            subtreeNormalizedText(item.node, maxDepth = 5)
        )
    }

'''
    s = s.replace(anchor, helper + anchor, 1)

# -----------------------------------------------------------------------------
# Nunca deixa aviso de configuracao entrar como miniatura/imagem.
# -----------------------------------------------------------------------------
old = '''                val n = RouteParser.normalize(item.text)

                val notToolbar =
'''
new = '''                val n = RouteParser.normalize(item.text)

                // Avisos de sistema de mudanca de configuracao do grupo podem ser
                // containers grandes e sem texto proprio. Eles NAO sao imagens.
                if (isGroupSettingsSystemCandidate(item)) {
                    return@filter false
                }

                val notToolbar =
'''
if old not in s:
    raise SystemExit('patch_v19_admin_message_noise_fix: ponto de filtro de imagem nao encontrado')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Troca o detector de admin agregado por detector do aviso MAIS RECENTE visivel.
# Isso evita que 7 avisos antigos, alternando fechado/aberto, contaminem o estado.
# -----------------------------------------------------------------------------
start = s.find('    private fun isAdminLockedGroup(items: List<NodeItem>): Boolean {')
end = s.find('\n    private fun keepOcrEngineWarm() {', start)
if start < 0 or end < 0:
    raise SystemExit(
        f'patch_v19_admin_message_noise_fix: isAdminLockedGroup nao encontrado (start={start}, end={end})'
    )

new_admin = r'''    private fun isAdminLockedGroup(items: List<NodeItem>): Boolean {
        // Usa o aviso de configuracao mais baixo na conversa, que corresponde ao
        // estado mais recente visivel. Avisos antigos acima nao podem dominar.
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
            ?: return false

        val text = latest.second

        val openedForEveryone =
            text.contains("todos os membros") ||
            text.contains("all participants") ||
            text.contains("everyone")

        if (openedForEveryone) return false

        return text.contains("somente admin") ||
            text.contains("apenas admin") ||
            text.contains("only admin")
    }
'''

s = s[:start] + new_admin + s[end:]

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 ADMIN MESSAGE NOISE FIX aplicado: avisos de configuracao nao viram imagens e usa somente o estado mais recente")
