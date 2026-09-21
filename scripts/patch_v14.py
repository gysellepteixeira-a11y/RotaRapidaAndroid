from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
manifest_path = Path("app/src/main/AndroidManifest.xml")
activity_path = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")

s = service_path.read_text(encoding="utf-8")

# v0.14 - TESTE MEDIASTORE
#
# Em vez de abrir a miniatura no WhatsApp para tirar screenshot, tenta primeiro
# localizar no MediaStore o arquivo ORIGINAL que acabou de ser baixado pelo
# WhatsApp. Se encontrar, o ML Kit le o arquivo sem sair do grupo e a resposta e
# enviada no campo que ja esta aberto. O fluxo antigo continua inteiro como
# fallback, usando openImageFromSavedRect() da v0.10.

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------
imports_anchor = 'import android.accessibilityservice.AccessibilityService.ScreenshotResult\n'
extra_imports = '''import android.Manifest\nimport android.content.ContentUris\nimport android.content.pm.PackageManager\nimport android.net.Uri\nimport android.os.Build\nimport android.provider.MediaStore\n'''

if 'import android.provider.MediaStore' not in s:
    if imports_anchor not in s:
        raise SystemExit('Patch v0.14: ponto de imports nao encontrado')
    s = s.replace(imports_anchor, imports_anchor + extra_imports, 1)

# -----------------------------------------------------------------------------
# CONSTANTES
# -----------------------------------------------------------------------------
const_anchor = '        private const val DEDUP_MS = 8_000L\n'
const_extra = '''        private const val MEDIASTORE_RETRY_MS = 110L\n        private const val MEDIASTORE_MAX_ATTEMPTS = 14\n        private const val MEDIASTORE_TRIGGER_TOLERANCE_MS = 2_500L\n'''

if 'MEDIASTORE_MAX_ATTEMPTS' not in s:
    if const_anchor not in s:
        raise SystemExit('Patch v0.14: bloco de constantes nao encontrado')
    s = s.replace(const_anchor, const_anchor + const_extra, 1)

# -----------------------------------------------------------------------------
# MODELO DO ARQUIVO DO MEDIASTORE
# -----------------------------------------------------------------------------
node_anchor = '''    private data class NodeItem(\n        val text: String,\n        val rect: Rect,\n        val className: String,\n        val clickable: Boolean,\n        val editable: Boolean,\n        val node: AccessibilityNodeInfo\n    )\n'''

media_data = '''\n    private data class MediaImage(\n        val uri: Uri,\n        val id: Long,\n        val displayName: String,\n        val relativePath: String,\n        val dateAddedMs: Long,\n        val height: Int\n    )\n'''

if 'private data class MediaImage' not in s:
    if node_anchor not in s:
        raise SystemExit('Patch v0.14: NodeItem nao encontrado')
    s = s.replace(node_anchor, node_anchor + media_data, 1)

# -----------------------------------------------------------------------------
# ESTADO
# -----------------------------------------------------------------------------
state_anchor = '    private var currentStartedAt = 0L\n'
state_extra = '''    private var currentImageWallTimeMs = 0L\n    private var lastMediaImageId = -1L\n'''

if 'currentImageWallTimeMs' not in s:
    if state_anchor not in s:
        raise SystemExit('Patch v0.14: estado nao encontrado')
    s = s.replace(state_anchor, state_anchor + state_extra, 1)

# -----------------------------------------------------------------------------
# TROCA SOMENTE O BLOCO candidate DA IMAGEM.
# A v0.10 deixa esse bloco imediatamente antes de openImageFromSavedRect().
# Guardamos Rect + fingerprint porque, se o MediaStore falhar, o fallback antigo
# precisa conseguir abrir exatamente a mesma miniatura.
# -----------------------------------------------------------------------------
image_section = s.find('// ---------------- IMAGEM ----------------')
start = s.find('        if (candidate != null) {', image_section)
end = s.find('\n    }\n\n    private fun openImageFromSavedRect(', start)

if image_section < 0 or start < 0 or end < 0:
    raise SystemExit(
        f'Patch v0.14: bloco candidate pos-v0.10 nao encontrado '
        f'(image_section={image_section}, start={start}, end={end})'
    )

new_candidate = '''        if (candidate != null) {\n            currentStartedAt = SystemClock.elapsedRealtime()\n            currentImageWallTimeMs = System.currentTimeMillis()\n            processing = true\n\n            val savedRect = Rect(candidate.rect)\n            val savedFingerprint = imageFingerprint(candidate)\n\n            Prefs.setStatus(\n                this,\n                "Imagem nova detectada. Procurando o arquivo original do WhatsApp..."\n            )\n\n            readImageFromMediaStoreOrFallback(\n                targetRect = savedRect,\n                fingerprint = savedFingerprint,\n                attempt = 0\n            )\n            return\n        }\n'''

s = s[:start] + new_candidate + s[end:]

# -----------------------------------------------------------------------------
# HELPERS MEDIASTORE - inseridos antes do fallback v0.10.
# -----------------------------------------------------------------------------
insert_at = s.find('    private fun openImageFromSavedRect(')
if insert_at < 0:
    raise SystemExit('Patch v0.14: openImageFromSavedRect nao encontrado')

helpers = r'''    private fun hasImageReadPermission(): Boolean {
        val permission = if (Build.VERSION.SDK_INT >= 33) {
            Manifest.permission.READ_MEDIA_IMAGES
        } else {
            Manifest.permission.READ_EXTERNAL_STORAGE
        }

        return checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED
    }

    private fun findNewestWhatsAppImage(): MediaImage? {
        if (!hasImageReadPermission()) return null

        val projection = arrayOf(
            MediaStore.Images.Media._ID,
            MediaStore.Images.Media.DISPLAY_NAME,
            MediaStore.Images.Media.RELATIVE_PATH,
            MediaStore.Images.Media.DATE_ADDED,
            MediaStore.Images.Media.HEIGHT
        )

        // DATE_ADDED usa segundos. Abrimos uma janela curta para tolerar a ordem
        // entre o evento de acessibilidade e a gravacao real do arquivo.
        val minimumAddedSeconds =
            ((currentImageWallTimeMs - MEDIASTORE_TRIGGER_TOLERANCE_MS) / 1000L)
                .coerceAtLeast(0L)

        val selection =
            "${MediaStore.Images.Media.RELATIVE_PATH} LIKE ? AND " +
                "${MediaStore.Images.Media.DATE_ADDED} >= ?"

        val selectionArgs = arrayOf(
            "%WhatsApp%Images%",
            minimumAddedSeconds.toString()
        )

        val sortOrder = "${MediaStore.Images.Media.DATE_ADDED} DESC"

        return try {
            contentResolver.query(
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                projection,
                selection,
                selectionArgs,
                sortOrder
            )?.use { cursor ->
                val idCol = cursor.getColumnIndexOrThrow(MediaStore.Images.Media._ID)
                val nameCol = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.DISPLAY_NAME)
                val pathCol = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.RELATIVE_PATH)
                val dateCol = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.DATE_ADDED)
                val heightCol = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.HEIGHT)

                while (cursor.moveToNext()) {
                    val id = cursor.getLong(idCol)
                    if (id == lastMediaImageId) continue

                    val uri = ContentUris.withAppendedId(
                        MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                        id
                    )

                    return@use MediaImage(
                        uri = uri,
                        id = id,
                        displayName = cursor.getString(nameCol).orEmpty(),
                        relativePath = cursor.getString(pathCol).orEmpty(),
                        dateAddedMs = cursor.getLong(dateCol) * 1000L,
                        height = cursor.getInt(heightCol)
                    )
                }

                null
            }
        } catch (error: Throwable) {
            Prefs.setStatus(
                this,
                "Erro ao procurar arquivo do WhatsApp: " +
                    (error.message ?: error.javaClass.simpleName)
            )
            null
        }
    }

    private fun readImageFromMediaStoreOrFallback(
        targetRect: Rect,
        fingerprint: String,
        attempt: Int
    ) {
        if (!processing) return

        if (!hasImageReadPermission()) {
            Prefs.setStatus(
                this,
                "Permissao de Fotos nao concedida. Usando leitura antiga pela tela."
            )
            openImageFromSavedRect(targetRect, fingerprint)
            return
        }

        val media = findNewestWhatsAppImage()

        if (media == null) {
            if (attempt < MEDIASTORE_MAX_ATTEMPTS) {
                if (attempt == 0) {
                    Prefs.setStatus(
                        this,
                        "Imagem detectada; aguardando o WhatsApp terminar o download..."
                    )
                }

                handler.postDelayed(
                    {
                        readImageFromMediaStoreOrFallback(
                            targetRect,
                            fingerprint,
                            attempt + 1
                        )
                    },
                    MEDIASTORE_RETRY_MS
                )
            } else {
                Prefs.setStatus(
                    this,
                    "Arquivo nao apareceu no MediaStore. Usando leitura antiga pela tela."
                )
                openImageFromSavedRect(targetRect, fingerprint)
            }
            return
        }

        lastMediaImageId = media.id
        val ageMs = (System.currentTimeMillis() - media.dateAddedMs).coerceAtLeast(0L)

        Prefs.setStatus(
            this,
            "ARQUIVO encontrado em ${ageMs}ms: ${media.displayName}. OCR original..."
        )

        try {
            val input = InputImage.fromFilePath(this, media.uri)
            val started = SystemClock.elapsedRealtime()

            recognizer.process(input)
                .addOnSuccessListener { visionText ->
                    if (!processing) return@addOnSuccessListener

                    val parseHeight = if (media.height > 0) {
                        media.height
                    } else {
                        resources.displayMetrics.heightPixels
                    }

                    val route = parseVisionText(
                        visionText,
                        parseHeight
                    )

                    val elapsed = SystemClock.elapsedRealtime() - started
                    val totalLinhas = contarLinhasVisionText(visionText)

                    if (route != null) {
                        if (isDuplicate(route)) {
                            processing = false
                            Prefs.setStatus(
                                this,
                                "Arquivo repetido ignorado | OCR=${elapsed}ms"
                            )
                            handler.postDelayed({ primeCurrentScreen() }, 120L)
                        } else {
                            Prefs.setStatus(
                                this,
                                "ARQUIVO: ${route.neighborhood} -> ${route.cage} | " +
                                    "OCR=${elapsed}ms | enviando sem abrir foto"
                            )

                            // O campo de mensagem continua visivel porque nunca saimos
                            // do grupo. Envia imediatamente pelo AccessibilityService.
                            sendRouteInCurrentChat(route)
                        }
                    } else {
                        Prefs.setStatus(
                            this,
                            "Arquivo original leu $totalLinhas linhas, mas nao fechou a rota. " +
                                "Tentando visualizador antigo..."
                        )
                        openImageFromSavedRect(targetRect, fingerprint)
                    }
                }
                .addOnFailureListener { error ->
                    if (!processing) return@addOnFailureListener

                    Prefs.setStatus(
                        this,
                        "OCR do arquivo falhou: ${error.message ?: "sem detalhes"}. " +
                            "Tentando visualizador antigo..."
                    )
                    openImageFromSavedRect(targetRect, fingerprint)
                }
        } catch (error: Throwable) {
            Prefs.setStatus(
                this,
                "Nao consegui abrir o arquivo original: " +
                    (error.message ?: error.javaClass.simpleName) +
                    ". Tentando visualizador antigo..."
            )
            openImageFromSavedRect(targetRect, fingerprint)
        }
    }

'''

s = s[:insert_at] + helpers + s[insert_at:]
service_path.write_text(s, encoding="utf-8")

# -----------------------------------------------------------------------------
# MANIFEST - permissao de leitura de imagens.
# -----------------------------------------------------------------------------
m = manifest_path.read_text(encoding="utf-8")
if 'READ_MEDIA_IMAGES' not in m:
    marker = '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
    perms = '''\n    <uses-permission\n        android:name="android.permission.READ_EXTERNAL_STORAGE"\n        android:maxSdkVersion="32" />\n    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />\n'''

    if marker not in m:
        raise SystemExit('Patch v0.14: manifest marker nao encontrado')
    m = m.replace(marker, marker + perms, 1)
manifest_path.write_text(m, encoding="utf-8")

# -----------------------------------------------------------------------------
# MAIN ACTIVITY - pede acesso as fotos uma vez. No Android 13+ o teste precisa
# usar acesso a todas as fotos para o app enxergar automaticamente as imagens
# novas do WhatsApp no MediaStore.
# -----------------------------------------------------------------------------
a = activity_path.read_text(encoding="utf-8")
if 'READ_MEDIA_IMAGES' not in a:
    import_anchor = 'import android.content.Intent\n'
    import_block = (
        'import android.Manifest\n'
        'import android.content.Intent\n'
        'import android.content.pm.PackageManager\n'
        'import android.os.Build\n'
    )

    if import_anchor not in a:
        raise SystemExit('Patch v0.14: import MainActivity nao encontrado')
    a = a.replace(import_anchor, import_block, 1)

    call_anchor = '        setContentView(R.layout.activity_main)\n'
    if call_anchor not in a:
        raise SystemExit('Patch v0.14: onCreate nao encontrado')
    a = a.replace(
        call_anchor,
        call_anchor + '\n        requestImagePermissionIfNeeded()\n',
        1
    )

    helper_anchor = '    override fun onResume() {\n'
    helper_activity = '''    private fun requestImagePermissionIfNeeded() {\n        val permission = if (Build.VERSION.SDK_INT >= 33) {\n            Manifest.permission.READ_MEDIA_IMAGES\n        } else {\n            Manifest.permission.READ_EXTERNAL_STORAGE\n        }\n\n        if (checkSelfPermission(permission) != PackageManager.PERMISSION_GRANTED) {\n            requestPermissions(arrayOf(permission), 714)\n            Prefs.setStatus(\n                this,\n                "Permita acesso a TODAS as fotos para ler a imagem original do WhatsApp."\n            )\n        }\n    }\n\n'''

    if helper_anchor not in a:
        raise SystemExit('Patch v0.14: ponto helper MainActivity nao encontrado')
    a = a.replace(helper_anchor, helper_activity + helper_anchor, 1)

activity_path.write_text(a, encoding="utf-8")

print("Patch v0.14 aplicado: OCR tenta arquivo original do WhatsApp via MediaStore sem abrir a foto")
