from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")

# ADMIN ULTRA SIBLING FAST
# - somente rota pendente apos admin liberar
# - remove Prefs.setStatus do caminho critico ANTES do clique
# - procura Enviar primeiro no pequeno ramo estrutural ao redor do EditText
# - so usa busca global da versao DIRECT FAST como fallback
# - nao altera OCR, parser, MediaStore nem envio normal

# Helper localizado: valida um no nomeado Enviar/Send perto do editor.
anchor = '    private fun findAdminUltraSendNodeFast(\n'
if anchor not in s:
    raise SystemExit('ADMIN ULTRA SIBLING: findAdminUltraSendNodeFast nao encontrado')

helper = r'''    private fun adminUltraNamedSendCandidate(
        node: AccessibilityNodeInfo,
        editorRect: Rect
    ): Boolean {
        val rect = Rect()
        try {
            node.getBoundsInScreen(rect)
        } catch (_: Throwable) {
            return false
        }
        if (rect.isEmpty) return false

        val merged = buildString {
            node.text?.toString()?.let { append(it) }
            node.contentDescription?.toString()?.let {
                if (isNotEmpty()) append(' ')
                append(it)
            }
        }
        val n = RouteParser.normalize(merged)
        val namedSend =
            "enviar" in n ||
            n == "send" ||
            "send message" in n
        if (!namedSend) return false

        val w = resources.displayMetrics.widthPixels
        val h = resources.displayMetrics.heightPixels
        val yTolerance = maxOf(80, (h * 0.075f).toInt())

        return rect.right >= (w * 0.76f).toInt() &&
            kotlin.math.abs(rect.centerY() - editorRect.centerY()) <= yTolerance
    }

    private fun findAdminUltraSendInSmallBranch(
        node: AccessibilityNodeInfo,
        editorRect: Rect,
        depth: Int,
        maxDepth: Int
    ): AccessibilityNodeInfo? {
        if (depth > maxDepth) return null

        if (adminUltraNamedSendCandidate(node, editorRect)) {
            return node
        }

        val childCount = try { node.childCount } catch (_: Throwable) { 0 }
        for (i in 0 until childCount) {
            val child = try { node.getChild(i) } catch (_: Throwable) { null } ?: continue
            val found = findAdminUltraSendInSmallBranch(
                child,
                editorRect,
                depth + 1,
                maxDepth
            )
            if (found != null) return found
        }
        return null
    }

    private fun findAdminUltraSendSiblingFast(
        editorNode: AccessibilityNodeInfo,
        editorRect: Rect
    ): AccessibilityNodeInfo? {
        // O botao Enviar costuma estar no mesmo container (ou 1-3 pais acima)
        // do EditText. Procurar so aqui evita varrer a arvore inteira do WhatsApp.
        var parent = try { editorNode.parent } catch (_: Throwable) { null }
        var up = 0

        while (parent != null && up < 4) {
            val childCount = try { parent.childCount } catch (_: Throwable) { 0 }
            for (i in 0 until childCount) {
                val child = try { parent.getChild(i) } catch (_: Throwable) { null } ?: continue
                val found = findAdminUltraSendInSmallBranch(
                    child,
                    editorRect,
                    0,
                    2
                )
                if (found != null) return found
            }

            parent = try { parent.parent } catch (_: Throwable) { null }
            up++
        }

        return null
    }

'''

s = s.replace(anchor, helper + anchor, 1)

# Substitui somente o wait da rota pendente. Primeiro tenta o ramo pequeno;
# busca global so entra depois de alguns polls locais ou quando necessario.
start = s.find('    private fun waitForAdminUltraSendReady(\n')
end = s.find('    private fun currentEditorText(items: List<NodeItem>): String {', start)
if start < 0 or end < 0:
    raise SystemExit('ADMIN ULTRA SIBLING: waitForAdminUltraSendReady nao encontrado')

new_wait = r'''    private fun waitForAdminUltraSendReady(
        route: RouteResult,
        startedAt: Long,
        poll: Int,
        editorNode: AccessibilityNodeInfo,
        editorRect: Rect
    ) {
        if (!processing) return

        val localPollDelayMs = 2L
        val maxLocalPollsBeforeGlobal = 6
        val maxPolls = 90

        // PRIMEIRO: ramo pequeno ao redor do proprio EditText. Nao pede root,
        // nao cria NodeItem e nao grava SharedPreferences antes do clique.
        val localSend = try {
            findAdminUltraSendSiblingFast(editorNode, editorRect)
        } catch (_: Throwable) {
            null
        }

        if (localSend != null && clickNodeOrParent(localSend)) {
            val clickedAt = SystemClock.elapsedRealtime()
            speedDiagnosticSendAttempts = 1
            speedDiagnosticSendMethod = "ACTION_CLICK"
            val releaseToClick = if (currentStartedAt > 0L) {
                clickedAt - currentStartedAt
            } else {
                -1L
            }

            // Diagnostico SOMENTE depois que o ACTION_CLICK ja foi aceito.
            Prefs.setStatus(
                this,
                "ADMIN ULTRA SIBLING: clique aceito em ${releaseToClick}ms desde liberacao | " +
                    "ready=${clickedAt - startedAt}ms | polls=$poll"
            )
            handler.postDelayed(
                { verifyAdminUltraFast(route, editorNode, clickedAt, 0) },
                8L
            )
            return
        }

        // Nos primeiros polls nao faz busca global: deixa a arvore local atualizar.
        if (poll < maxLocalPollsBeforeGlobal) {
            handler.postDelayed(
                { waitForAdminUltraSendReady(route, startedAt, poll + 1, editorNode, editorRect) },
                localPollDelayMs
            )
            return
        }

        // FALLBACK: a busca global da DIRECT FAST, mas sem status antes do clique.
        val root = rootInActiveWindow
        if (root != null) {
            val sendNode = findAdminUltraSendNodeFast(root, editorRect)
            if (sendNode != null && clickNodeOrParent(sendNode)) {
                val clickedAt = SystemClock.elapsedRealtime()
                speedDiagnosticSendAttempts = 1
                speedDiagnosticSendMethod = "ACTION_CLICK"
                val releaseToClick = if (currentStartedAt > 0L) {
                    clickedAt - currentStartedAt
                } else {
                    -1L
                }
                Prefs.setStatus(
                    this,
                    "ADMIN ULTRA SIBLING->GLOBAL: clique aceito em ${releaseToClick}ms desde liberacao | " +
                        "ready=${clickedAt - startedAt}ms | polls=$poll"
                )
                handler.postDelayed(
                    { verifyAdminUltraFast(route, editorNode, clickedAt, 0) },
                    8L
                )
                return
            }
        }

        if (poll < maxPolls) {
            handler.postDelayed(
                { waitForAdminUltraSendReady(route, startedAt, poll + 1, editorNode, editorRect) },
                localPollDelayMs
            )
            return
        }

        // Ultimo fallback seguro: SEND READY completo, ainda com apenas 1 clique.
        waitForSendButtonReady(route, startedAt, 0)
    }

'''

s = s[:start] + new_wait + s[end:]

# Remove o status de preenchimento que estava ANTES da busca/clique.
old_status = '''        val fillMs = SystemClock.elapsedRealtime() - releasedAt
        Prefs.setStatus(
            this,
            "ADMIN ULTRA DIRECT: liberado + preenchido em ${fillMs}ms | watch=10ms | ready=4ms"
        )

        waitForAdminUltraSendReady(
'''
new_status = '''        val fillMs = SystemClock.elapsedRealtime() - releasedAt
        // Nao grava status aqui: SharedPreferences/UI ficam fora do caminho critico.
        // O tempo real ate o clique sera registrado DEPOIS que o clique for aceito.

        waitForAdminUltraSendReady(
'''
if old_status not in s:
    raise SystemExit('ADMIN ULTRA SIBLING: status pre-clique DIRECT nao encontrado')
s = s.replace(old_status, new_status, 1)

prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND READY ADMIN ULTRA DIRECT FAST =====',
    '===== DIAGNOSTICO IMAGEM v0.19 BAIRRO FIRST GAIOLA NARROW SEND READY ADMIN ULTRA SIBLING FAST ====='
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")
print('ADMIN ULTRA SIBLING FAST aplicado: busca local no editor + nenhum status antes do clique')
