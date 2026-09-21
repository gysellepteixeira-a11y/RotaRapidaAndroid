from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
activity_path = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")
layout_path = Path("app/src/main/res/layout/activity_main.xml")

s = service_path.read_text(encoding="utf-8")
a = activity_path.read_text(encoding="utf-8")
xml = layout_path.read_text(encoding="utf-8")

# -----------------------------------------------------------------------------
# UI: nome do grupo deixa de ser necessario. Mantemos os IDs escondidos para
# nao quebrar MainActivity/patches anteriores.
# -----------------------------------------------------------------------------
xml = xml.replace(
    '''        <com.google.android.material.textfield.TextInputLayout\n            android:layout_width="match_parent"\n            android:layout_height="wrap_content"\n            android:layout_marginTop="22dp"\n            android:hint="Nome exato do grupo do WhatsApp">\n''',
    '''        <com.google.android.material.textfield.TextInputLayout\n            android:layout_width="match_parent"\n            android:layout_height="wrap_content"\n            android:layout_marginTop="22dp"\n            android:visibility="gone"\n            android:hint="Nome exato do grupo do WhatsApp">\n''',
    1
)
xml = xml.replace(
    '''        <Button\n            android:id="@+id/buttonSave"\n            android:layout_width="match_parent"\n            android:layout_height="wrap_content"\n            android:layout_marginTop="10dp"\n            android:text="Salvar grupo" />\n''',
    '''        <Button\n            android:id="@+id/buttonSave"\n            android:layout_width="match_parent"\n            android:layout_height="wrap_content"\n            android:layout_marginTop="10dp"\n            android:visibility="gone"\n            android:text="Salvar grupo" />\n''',
    1
)
layout_path.write_text(xml, encoding="utf-8")

# Switch nao deve reclamar que falta nome de grupo.
a = a.replace(
    '''                when {\n                    checked && Prefs.groupName(this).isBlank() ->\n                        "Automação ligada, mas falta configurar o nome do grupo."\n                    checked ->\n                        "Automação ligada. Abra o grupo no WhatsApp."\n                    else ->\n                        "Automação desligada."\n                }\n''',
    '''                when {\n                    checked ->\n                        "Automação ligada. Abra qualquer grupo no WhatsApp."\n                    else ->\n                        "Automação desligada."\n                }\n''',
    1
)
activity_path.write_text(a, encoding="utf-8")

# -----------------------------------------------------------------------------
# LEITURA: qualquer conversa aberta do WhatsApp com campo de mensagem serve.
# -----------------------------------------------------------------------------
old_analyze = '''        val group = Prefs.groupName(this)\n        if (group.isBlank()) {\n            Prefs.setStatus(this, "Configure o nome exato do grupo no app.")\n            return\n        }\n\n        val root = rootInActiveWindow ?: return\n        val items = collectNodeItems(root)\n\n        if (!isTargetGroup(items, group)) {\n            previousTexts = textSignatures(items)\n            previousImageFingerprints = findImageCandidates(items)\n                .map(::imageFingerprint)\n                .toSet()\n            primed = true\n            return\n        }\n'''
new_analyze = '''        val root = rootInActiveWindow ?: return\n        val items = collectNodeItems(root)\n\n        // So trabalha dentro de uma conversa normal. Na lista inicial do\n        // WhatsApp nao existe o editor de mensagem da conversa.\n        if (findMessageEditor(items) == null) {\n            previousTexts = textSignatures(items)\n            previousImageFingerprints = findImageCandidates(items)\n                .map(::imageFingerprint)\n                .toSet()\n            primed = true\n            return\n        }\n'''
if old_analyze not in s:
    raise SystemExit('patch_v19_any_group: bloco inicial de analyzeCurrentWindow nao encontrado')
s = s.replace(old_analyze, new_analyze, 1)

# Ao voltar de uma leitura antiga pelo visualizador, basta o campo da conversa
# reaparecer; nao compara mais o titulo com um nome salvo.
s = s.replace(
    '''        val items = collectNodeItems(root)\n        val group = Prefs.groupName(this)\n\n        if (!isTargetGroup(items, group)) {\n            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)\n            return\n        }\n\n        if (findMessageEditor(items) == null) {\n''',
    '''        val items = collectNodeItems(root)\n\n        if (findMessageEditor(items) == null) {\n''',
    1
)

# Rota pendente nao menciona mais um grupo configurado.
s = s.replace(
    '''            "Rota pronta: ${route.neighborhood} -> ${route.cage}. " +\n                "$reason Abra o grupo ${Prefs.groupName(this)} e eu envio automaticamente."\n''',
    '''            "Rota pronta: ${route.neighborhood} -> ${route.cage}. " +\n                "$reason Abra uma conversa/grupo do WhatsApp e eu envio automaticamente."\n''',
    1
)

# Rota pendente pode ser enviada em qualquer conversa que esteja aberta.
s = s.replace(
    '''        val root = rootInActiveWindow ?: return false\n        val items = collectNodeItems(root)\n        val group = Prefs.groupName(this)\n\n        if (!isTargetGroup(items, group)) return false\n        if (findMessageEditor(items) == null) return false\n''',
    '''        val root = rootInActiveWindow ?: return false\n        val items = collectNodeItems(root)\n\n        if (findMessageEditor(items) == null) return false\n''',
    1
)

# Envio direto: qualquer conversa aberta serve.
s = s.replace(
    '''        val items = collectNodeItems(root)\n        val group = Prefs.groupName(this)\n\n        if (!isTargetGroup(items, group)) {\n            holdRouteUntilChatOpen(route, "O grupo nao esta aberto.")\n            return\n        }\n\n        val editor = findMessageEditor(items)\n''',
    '''        val items = collectNodeItems(root)\n\n        val editor = findMessageEditor(items)\n''',
    1
)

# Durante clique/confirmacao, apenas exige que a conversa continue aberta.
old_guard = '''        if (!isTargetGroup(items, Prefs.groupName(this))) {\n            holdRouteUntilChatOpen(route, "O grupo foi fechado antes de concluir o envio.")\n            return\n        }\n'''
new_guard = '''        if (findMessageEditor(items) == null) {\n            holdRouteUntilChatOpen(route, "A conversa foi fechada antes de concluir o envio.")\n            return\n        }\n'''
if old_guard not in s:
    raise SystemExit('patch_v19_any_group: protecao de grupo durante envio nao encontrada')
s = s.replace(old_guard, new_guard)

# -----------------------------------------------------------------------------
# Tres dependencias antigas do nome de grupo permaneciam em helpers herdados das
# versoes que abriam o visualizador. Elas nao controlam o OCR MediaStore atual,
# mas precisam ficar genericas para o APK nao depender de grupo salvo em nada.
# -----------------------------------------------------------------------------
old_before_viewer = '''        val items = collectNodeItems(root)\n        val group = Prefs.groupName(this)\n\n        if (group.isNotBlank() && !isTargetGroup(items, group)) {\n            processing = false\n            Prefs.setStatus(this, "Saiu do grupo antes de abrir a imagem.")\n            return\n        }\n'''
new_before_viewer = '''        val items = collectNodeItems(root)\n\n        if (findMessageEditor(items) == null) {\n            processing = false\n            Prefs.setStatus(this, "Saiu da conversa antes de concluir a leitura da imagem.")\n            return\n        }\n'''
if old_before_viewer not in s:
    raise SystemExit('patch_v19_any_group: verificacao antiga antes do visualizador nao encontrada')
s = s.replace(old_before_viewer, new_before_viewer, 1)

old_verify_viewer = '''        val items = collectNodeItems(root)\n        val group = Prefs.groupName(this)\n\n        // v0.7: o visualizador de midia do WhatsApp no M52 pode expor\n        // um EditText proprio. Por isso EditText nao serve para decidir\n        // se a imagem abriu. Confirmamos pela ausencia do grupo-alvo.\n        val stillInTargetGroup =\n            group.isNotBlank() && isTargetGroup(items, group)\n'''
new_verify_viewer = '''        val items = collectNodeItems(root)\n\n        // Compatibilidade com o fluxo antigo. O caminho normal da v0.19 le o\n        // arquivo pelo MediaStore e nao precisa abrir a foto. Sem nome salvo,\n        // usamos a presenca do editor como referencia de que ainda estamos no chat.\n        val stillInTargetGroup = findMessageEditor(items) != null\n'''
if old_verify_viewer not in s:
    raise SystemExit('patch_v19_any_group: verificacao antiga do visualizador nao encontrada')
s = s.replace(old_verify_viewer, new_verify_viewer, 1)

old_back_viewer = '''    private fun backOnlyIfImageViewerOpen() {\n        val root = rootInActiveWindow ?: return\n        val items = collectNodeItems(root)\n        val group = Prefs.groupName(this)\n\n        // Se o cabecalho do grupo-alvo esta visivel, ja estamos no chat.\n        // Nao usa EditText como teste porque o visualizador do WhatsApp\n        // no M52 tambem pode expor um campo editavel.\n        if (group.isNotBlank() && isTargetGroup(items, group)) {\n            return\n        }\n\n        performGlobalAction(GLOBAL_ACTION_BACK)\n    }\n'''
new_back_viewer = '''    private fun backOnlyIfImageViewerOpen() {\n        val root = rootInActiveWindow ?: return\n        val items = collectNodeItems(root)\n\n        // Compatibilidade do fluxo antigo: se o editor normal da conversa esta\n        // presente, nao volta. O fluxo MediaStore atual nao abre a imagem.\n        if (findMessageEditor(items) != null) {\n            return\n        }\n\n        performGlobalAction(GLOBAL_ACTION_BACK)\n    }\n'''
if old_back_viewer not in s:
    raise SystemExit('patch_v19_any_group: backOnlyIfImageViewerOpen antigo nao encontrado')
s = s.replace(old_back_viewer, new_back_viewer, 1)

# Garantia: o service final nao pode depender de nome configurado.
remaining = [line for line in s.splitlines() if 'Prefs.groupName(this)' in line]
if remaining:
    print('DEPENDENCIAS RESTANTES:')
    for line in remaining:
        print(line)
    raise SystemExit('patch_v19_any_group: ainda existe Prefs.groupName(this) no service final')

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 ANY GROUP aplicado: sem nome de grupo; qualquer conversa aberta funciona")
