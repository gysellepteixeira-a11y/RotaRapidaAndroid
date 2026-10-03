from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
activity_path = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")

s = service_path.read_text(encoding="utf-8")
prefs = prefs_path.read_text(encoding="utf-8")
a = activity_path.read_text(encoding="utf-8")

# CLEAN STATE WATCH v1
# Base esperada: MEDIA10 STATUSLEAN + ADMIN ULTRA DIRECT FAST, SEM TEXT DIRECT.
# Objetivo: reduzir degradacao com o tempo sem alterar OCR/parser/prioridade/envio.
# 1) diagnostico de imagem deixa de ficar ativo depois de falha;
# 2) PROCURAR NOVAMENTE limpa somente o buffer/estado do diagnostico;
# 3) watcher MediaStore continua 10ms quando existe hint de imagem, mas fica 60ms ocioso;
# 4) watcher de rota pendente continua 10ms quando ha pendingRoute, mas 250ms ocioso;
# 5) ao criar pendingRoute, acorda o watcher imediatamente.

required = [
    'private const val DIRECT_MEDIASTORE_WATCH_MS = 10L',
    'private const val PENDING_ROUTE_SEND_WATCH_MS = 10L',
    'private fun findAdminUltraSendNodeFast(',
    'MEDIA10 STATUSLEAN ADMIN ULTRA DIRECT FAST',
]
for marker in required:
    if marker not in (s + prefs):
        raise SystemExit(f'CLEAN STATE WATCH: base esperada ausente: {marker}')

# -----------------------------------------------------------------------------
# PREFS: finalizar/limpar diagnostico de forma explicita.
# -----------------------------------------------------------------------------
if 'fun stopSpeedDiagnostic(context: Context)' not in prefs:
    insert_pos = prefs.rfind('\n}')
    if insert_pos < 0:
        raise SystemExit('CLEAN STATE WATCH: fim de Prefs nao encontrado')
    helper = r'''

    fun stopSpeedDiagnostic(context: Context) {
        prefs(context).edit()
            .putBoolean(KEY_SPEED_DIAGNOSTIC_ACTIVE, false)
            .putLong(KEY_SPEED_DIAGNOSTIC_START, 0L)
            .apply()
    }

    fun resetSpeedDiagnosticForNewSearch(context: Context) {
        prefs(context).edit()
            .putBoolean(KEY_SPEED_DIAGNOSTIC_ACTIVE, false)
            .putLong(KEY_SPEED_DIAGNOSTIC_START, 0L)
            .putString(KEY_SPEED_DIAGNOSTIC, "Aguardando novo diagnostico.")
            .apply()
    }
'''
    prefs = prefs[:insert_pos] + helper + prefs[insert_pos:]

# -----------------------------------------------------------------------------
# MAIN ACTIVITY: ao rearmar, zera somente o diagnostico persistido.
# Nao limpa configuracao, permissao, mensagem, prioridade ou estado funcional.
# -----------------------------------------------------------------------------
old_listener = '''        searchAgain.setOnClickListener {
            Prefs.setSearchArmed(this, true)
            Prefs.setNeedsPrime(this, false)
            Prefs.setStatus(
                this,
                "Procurar novamente ativado. Aguardando rota no grupo configurado."
            )
        }
'''
new_listener = '''        searchAgain.setOnClickListener {
            Prefs.resetSpeedDiagnosticForNewSearch(this)
            Prefs.setSearchArmed(this, true)
            Prefs.setNeedsPrime(this, false)
            Prefs.setStatus(
                this,
                "Procurar novamente ativado. Aguardando rota no grupo configurado."
            )
        }
'''
if old_listener not in a:
    raise SystemExit('CLEAN STATE WATCH: listener PROCURAR NOVAMENTE nao encontrado')
a = a.replace(old_listener, new_listener, 1)

# -----------------------------------------------------------------------------
# SERVICE: qualquer encerramento de leitura de arquivo/imagem sem envio encerra
# o diagnostico. Evita carregar um trace antigo para rotas de texto futuras.
# -----------------------------------------------------------------------------
old_finish = '''    private fun finishFileOnlyFailure(message: String) {
        processing = false
        Prefs.setStatus(this, message)
        handler.postDelayed({ primeCurrentScreen() }, 120L)
    }
'''
new_finish = '''    private fun finishFileOnlyFailure(message: String) {
        processing = false
        Prefs.setStatus(this, message)
        Prefs.stopSpeedDiagnostic(this)
        handler.postDelayed({ primeCurrentScreen() }, 120L)
    }
'''
if old_finish not in s:
    raise SystemExit('CLEAN STATE WATCH: finishFileOnlyFailure nao encontrado')
s = s.replace(old_finish, new_finish, 1)

old_close = '''    private fun closeImageWithoutSending(message: String) {
        backOnlyIfImageViewerOpen()
        Prefs.setStatus(this, message)

        handler.postDelayed({
'''
new_close = '''    private fun closeImageWithoutSending(message: String) {
        backOnlyIfImageViewerOpen()
        Prefs.setStatus(this, message)
        Prefs.stopSpeedDiagnostic(this)

        handler.postDelayed({
'''
if old_close not in s:
    raise SystemExit('CLEAN STATE WATCH: closeImageWithoutSending nao encontrado')
s = s.replace(old_close, new_close, 1)

old_image_failed = '''    private fun imageFailed(message: String) {
        backOnlyIfImageViewerOpen()
        Prefs.setStatus(this, message)

        handler.postDelayed({
'''
new_image_failed = '''    private fun imageFailed(message: String) {
        backOnlyIfImageViewerOpen()
        Prefs.setStatus(this, message)
        Prefs.stopSpeedDiagnostic(this)

        handler.postDelayed({
'''
if old_image_failed not in s:
    raise SystemExit('CLEAN STATE WATCH: imageFailed nao encontrado')
s = s.replace(old_image_failed, new_image_failed, 1)

# -----------------------------------------------------------------------------
# WATCHERS ADAPTATIVOS.
# -----------------------------------------------------------------------------
const_anchor = '''        private const val PENDING_ROUTE_SEND_WATCH_MS = 10L
        private const val DIRECT_MEDIASTORE_WATCH_MS = 10L
'''
const_new = '''        private const val PENDING_ROUTE_SEND_WATCH_MS = 10L
        private const val PENDING_ROUTE_IDLE_WATCH_MS = 250L
        private const val DIRECT_MEDIASTORE_WATCH_MS = 10L
        private const val DIRECT_MEDIASTORE_IDLE_WATCH_MS = 60L
'''
if const_anchor not in s:
    raise SystemExit('CLEAN STATE WATCH: constantes 10ms nao encontradas')
s = s.replace(const_anchor, const_new, 1)

old_pending_finally = '''            } finally {
                handler.postDelayed(this, PENDING_ROUTE_SEND_WATCH_MS)
            }
        }
    }
'''
new_pending_finally = '''            } finally {
                val fastPending =
                    pendingRoute != null &&
                    !processing &&
                    !alertSequenceRunning
                handler.postDelayed(
                    this,
                    if (fastPending) PENDING_ROUTE_SEND_WATCH_MS else PENDING_ROUTE_IDLE_WATCH_MS
                )
            }
        }
    }
'''
if old_pending_finally not in s:
    raise SystemExit('CLEAN STATE WATCH: finally watcher pending nao encontrado')
s = s.replace(old_pending_finally, new_pending_finally, 1)

# Segundo bloco finally pertence ao watcher MediaStore.
old_media_finally = '''            } finally {
                handler.postDelayed(this, DIRECT_MEDIASTORE_WATCH_MS)
            }
        }
    }
'''
new_media_finally = '''            } finally {
                val fastImageWindow =
                    Prefs.searchArmed(this@WhatsRouteAccessibilityService) &&
                    SystemClock.elapsedRealtime() <= imageHintUntil
                handler.postDelayed(
                    this,
                    if (fastImageWindow) DIRECT_MEDIASTORE_WATCH_MS else DIRECT_MEDIASTORE_IDLE_WATCH_MS
                )
            }
        }
    }
'''
if old_media_finally not in s:
    raise SystemExit('CLEAN STATE WATCH: finally watcher MediaStore nao encontrado')
s = s.replace(old_media_finally, new_media_finally, 1)

# Quando uma rota passa a ficar pendente, nao espera o watcher ocioso de 250ms.
old_hold = '''    private fun holdRouteUntilChatOpen(route: RouteResult, reason: String) {
        pendingRoute = route
        processing = false
        Prefs.setStatus(
'''
new_hold = '''    private fun holdRouteUntilChatOpen(route: RouteResult, reason: String) {
        pendingRoute = route
        processing = false
        handler.removeCallbacks(pendingRouteSendWatchRunnable)
        handler.post(pendingRouteSendWatchRunnable)
        Prefs.setStatus(
'''
if old_hold not in s:
    raise SystemExit('CLEAN STATE WATCH: holdRouteUntilChatOpen nao encontrado')
s = s.replace(old_hold, new_hold, 1)

# Marca a versao sem interferir em fluxo critico.
prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 MEDIA10 STATUSLEAN ADMIN ULTRA DIRECT FAST =====',
    '===== DIAGNOSTICO IMAGEM v0.19 MEDIA10 ADMIN DIRECT CLEAN STATE WATCH V1 =====',
    1
)

service_path.write_text(s, encoding="utf-8")
prefs_path.write_text(prefs, encoding="utf-8")
activity_path.write_text(a, encoding="utf-8")
print('CLEAN STATE WATCH V1 aplicado: diagnostico encerra corretamente + watchers adaptativos')
