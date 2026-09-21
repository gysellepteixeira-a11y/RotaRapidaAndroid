from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
activity_path = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")
layout_path = Path("app/src/main/res/layout/activity_main.xml")

s = service_path.read_text(encoding="utf-8")
a = activity_path.read_text(encoding="utf-8")
xml = layout_path.read_text(encoding="utf-8")

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

a = a.replace(
    '''                when {\n                    checked && Prefs.groupName(this).isBlank() ->\n                        "Automação ligada, mas falta configurar o nome do grupo."\n                    checked ->\n                        "Automação ligada. Abra o grupo no WhatsApp."\n                    else ->\n                        "Automação desligada."\n                }\n''',
    '''                when {\n                    checked ->\n                        "Automação ligada. Abra qualquer grupo no WhatsApp."\n                    else ->\n                        "Automação desligada."\n                }\n''',
    1
)
activity_path.write_text(a, encoding="utf-8")

old_analyze = '''        val group = Prefs.groupName(this)\n        if (group.isBlank()) {\n            Prefs.setStatus(this, "Configure o nome exato do grupo no app.")\n            return\n        }\n\n        val root = rootInActiveWindow ?: return\n        val items = collectNodeItems(root)\n\n        if (!isTargetGroup(items, group)) {\n            previousTexts = textSignatures(items)\n            previousImageFingerprints = findImageCandidates(items)\n                .map(::imageFingerprint)\n                .toSet()\n            primed = true\n            return\n        }\n'''
new_analyze = '''        val root = rootInActiveWindow ?: return\n        val items = collectNodeItems(root)\n\n        if (findMessageEditor(items) == null) {\n            previousTexts = textSignatures(items)\n            previousImageFingerprints = findImageCandidates(items)\n                .map(::imageFingerprint)\n                .toSet()\n            primed = true\n            return\n        }\n'''
if old_analyze not in s:
    raise SystemExit('patch_v19_any_group: bloco inicial de analyzeCurrentWindow nao encontrado')
s = s.replace(old_analyze, new_analyze, 1)

s = s.replace(
    '''        val items = collectNodeItems(root)\n        val group = Prefs.groupName(this)\n\n        if (!isTargetGroup(items, group)) {\n            handler.postDelayed({ sendRouteWhenChatReady(route, attempt + 1) }, 25L)\n            return\n        }\n\n        if (findMessageEditor(items) == null) {\n''',
    '''        val items = collectNodeItems(root)\n\n        if (findMessageEditor(items) == null) {\n''',
    1
)

s = s.replace(
    '''            "Rota pronta: ${route.neighborhood} -> ${route.cage}. " +\n                "$reason Abra o grupo ${Prefs.groupName(this)} e eu envio automaticamente."\n''',
    '''            "Rota pronta: ${route.neighborhood} -> ${route.cage}. " +\n                "$reason Abra uma conversa/grupo do WhatsApp e eu envio automaticamente."\n''',
    1
)

s = s.replace(
    '''        val root = rootInActiveWindow ?: return false\n        val items = collectNodeItems(root)\n        val group = Prefs.groupName(this)\n\n        if (!isTargetGroup(items, group)) return false\n        if (findMessageEditor(items) == null) return false\n''',
    '''        val root = rootInActiveWindow ?: return false\n        val items = collectNodeItems(root)\n\n        if (findMessageEditor(items) == null) return false\n''',
    1
)

s = s.replace(
    '''        val items = collectNodeItems(root)\n        val group = Prefs.groupName(this)\n\n        if (!isTargetGroup(items, group)) {\n            holdRouteUntilChatOpen(route, "O grupo nao esta aberto.")\n            return\n        }\n\n        val editor = findMessageEditor(items)\n''',
    '''        val items = collectNodeItems(root)\n\n        val editor = findMessageEditor(items)\n''',
    1
)

old_guard = '''        if (!isTargetGroup(items, Prefs.groupName(this))) {\n            holdRouteUntilChatOpen(route, "O grupo foi fechado antes de concluir o envio.")\n            return\n        }\n'''
new_guard = '''        if (findMessageEditor(items) == null) {\n            holdRouteUntilChatOpen(route, "A conversa foi fechada antes de concluir o envio.")\n            return\n        }\n'''
if old_guard not in s:
    raise SystemExit('patch_v19_any_group: protecao de grupo durante envio nao encontrada')
s = s.replace(old_guard, new_guard)

remaining = [line for line in s.splitlines() if 'Prefs.groupName(this)' in line]
if remaining:
    print('DEPENDENCIAS RESTANTES:')
    for line in remaining:
        print(line)
    raise SystemExit('patch_v19_any_group: ainda existe Prefs.groupName(this) no service final')

service_path.write_text(s, encoding="utf-8")
print("Patch v0.19 ANY GROUP aplicado: sem nome de grupo, qualquer conversa aberta funciona")
