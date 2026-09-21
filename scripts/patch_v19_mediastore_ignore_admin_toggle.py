from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# v0.19 - MEDIASTORE INDEPENDENTE DO ABRE/FECHA DO ADMIN
#
# Sintoma real observado:
# - rotas de TEXTO continuam funcionando;
# - imagens voltaram a funcionar com o watcher direto do MediaStore;
# - porem, depois de o admin alternar varias vezes entre "somente admins" e
#   "todos os membros", uma nova imagem podia deixar de ser lida.
#
# Causa: o watcher direto ainda usava o estado visual/editor + detector de
# "grupo fechado pelo admin" como pre-condicao para consultar o MediaStore.
# Depois de varias trocas, a arvore de acessibilidade do WhatsApp pode ficar
# momentaneamente inconsistente e esse gate bloqueava a imagem antes do OCR.
#
# Correcao: para IMAGEM, enquanto PROCURAR ROTA estiver armado, basta o WhatsApp
# estar em primeiro plano. A leitura do arquivo nao depende mais do campo de
# mensagem nem das frases de configuracao do grupo.
#
# Se o grupo estiver fechado pelo admin quando a rota for encontrada, o fluxo
# normal de envio continua seguro: sendRouteInCurrentChat() nao acha editor,
# guarda pendingRoute e o watcher de pending envia assim que o campo reaparecer.
# TEXTO, OCR, parser, prioridades e envio nao sao alterados.

old_gate = r'''        val root = rootInActiveWindow ?: return
        val items = collectNodeItems(root)

        // Conversa comum: editor presente.
        // Grupo fechado pelo admin: editor ausente, mas o detector/sticky de admin
        // identifica que ainda estamos dentro da conversa recebendo mensagens.
        val editorAvailable = findMessageEditor(items) != null
        val adminLockedNow = isAdminLockedGroup(items)

        if (editorAvailable) {
            adminLockedConversationActive = false
        } else if (adminLockedNow) {
            adminLockedConversationActive = true
        }

        if (!editorAvailable && !adminLockedConversationActive) return

        // A janela de findNewestWhatsAppImage e curta de proposito. Atualizando o
'''

new_gate = r'''        val root = rootInActiveWindow ?: return
        val packageName = root.packageName?.toString().orEmpty()

        // Para IMAGEM nao usamos mais editor nem mensagens de "somente admins".
        // Essas informacoes oscilam muito quando o admin abre/fecha o grupo varias
        // vezes. Se o WhatsApp esta em primeiro plano e a busca esta armada, um
        // arquivo novo do WhatsApp deve ser analisado normalmente.
        val whatsAppForeground =
            packageName == "com.whatsapp" ||
            packageName == "com.whatsapp.w4b"

        if (!whatsAppForeground) return

        // A janela de findNewestWhatsAppImage e curta de proposito. Atualizando o
'''

if old_gate not in s:
    raise SystemExit("patch_v19_mediastore_ignore_admin_toggle: gate antigo do MediaStore nao encontrado")

s = s.replace(old_gate, new_gate, 1)

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 MEDIASTORE ADMIN TOGGLE aplicado: imagem independe do abre/fecha do admin")
