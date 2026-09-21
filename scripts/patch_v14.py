from pathlib import Path
import re

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
manifest_path = Path("app/src/main/AndroidManifest.xml")
activity_path = Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")

s = service_path.read_text(encoding="utf-8")

# v0.14: quando uma imagem nova aparece no grupo, primeiro tentamos ler o
# ARQUIVO ORIGINAL que o WhatsApp gravou no MediaStore. Assim o grupo continua
# aberto e o ML Kit recebe a imagem em resolucao original, sem abrir/zoom/captura.
# Se o arquivo ainda nao existir, a permissao faltar ou o OCR nao fechar a rota,
# o fluxo antigo do visualizador continua como fallback.

imports_anchor = 'import android.accessibilityservice.AccessibilityService.ScreenshotResult\n'
extra_imports = '''import android.Manifest\nimport android.content.ContentUris\nimport android.content.pm.PackageManager\nimport android.net.Uri\nimport android.os.Build\nimport android.provider.MediaStore\n'''
if 'import android.provider.MediaStore' not in s:
    if imports_anchor not in s:
        raise SystemExit('Patch v0.14: ponto de imports nao encontrado')
    s = s.replace(imports_anchor, imports_anchor + extra_imports, 1)

const_anchor = '        private const val DEDUP_MS = 8_000L\n'
const_extra = '''        private const val MEDIASTORE_RETRY_MS = 110L\n        private const val MEDIASTORE_MAX_ATTEMPTS = 14\n        private const val MEDIASTORE_TRIGGER_TOLERANCE_MS = 2_500L\n'''
if 'MEDIASTORE_MAX_ATTEMPTS' not in s:
    if const_anchor not in s:
        raise SystemExit('Patch v0.14: bloco de constantes nao encontrado')
    s = s.replace(const_anchor, const_anchor + const_extra, 1)

node_anchor = '''    private data class NodeItem(\n        val text: String,\n        val rect: Rect,\n        val className: String,\n        val clickable: Boolean,\n        val editable: Boolean,\n        val node: AccessibilityNodeInfo\n    )\n'''
media_data = '''\n    private data class MediaImage(\n        val uri: Uri,\n        val id: Long,\n        val displayName: String,\n        val relativePath: String,\n        val dateAddedMs: Long,\n        val height: Int\n    )\n'''
if 'private data class MediaImage' not in s:
    if node_anchor not in s:
        raise SystemExit('Patch v0.14: NodeItem nao encontrado')
    s = s.replace(node_anchor, node_anchor + media_data, 1)

state_anchor = '    private var currentStartedAt = 0L\n'
state_extra = '''    private var currentImageWallTimeMs = 0L\n    private var lastMediaImageId = -1L\n'''
if 'currentImageWallTimeMs' not in s:
    if state_anchor not in s:
        raise SystemExit('Patch v0.14: estado nao encontrado')
    s = s.replace(state_anchor, state_anchor + state_extra, 1)

pattern = re.compile(
    r'''        if \(candidate != null\) \{.*?            return\n        \}\n    \}\n\n    private fun inspectImageHint''',
    re.S,
)

replacement = '''        if (candidate != null) {\n            currentStartedAt = SystemClock.elapsedRealtime()\n            currentImageWallTimeMs = System.currentTimeMillis()\n            processing = true\n\n            Prefs.setStatus(\n                this,\n                "Imagem nova detectada. Procurando o arquivo original do WhatsApp..."\n            )\n\n            readImageFromMediaStoreOrFallback(\n                candidate = candidate,\n                attempt = 0\n            )\n            return\n        }\n    }\n\n    private fun hasImageReadPermission(): Boolean {\n        val permission = if (Build.VERSION.SDK_INT >= 33) {\n            Manifest.permission.READ_MEDIA_IMAGES\n        } else {\n            Manifest.permission.READ_EXTERNAL_STORAGE\n        }\n\n        return checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED\n    }\n\n    private fun findNewestWhatsAppImage(): MediaImage? {\n        if (!hasImageReadPermission()) return null\n\n        val projection = arrayOf(\n            MediaStore.Images.Media._ID,\n            MediaStore.Images.Media.DISPLAY_NAME,\n            MediaStore.Images.Media.RELATIVE_PATH,\n            MediaStore.Images.Media.DATE_ADDED,\n            MediaStore.Images.Media.HEIGHT\n        )\n\n        // So aceitamos arquivos adicionados praticamente junto com o evento\n        // que apareceu no grupo. Isso evita pegar uma foto antiga por engano.\n        val minimumAddedSeconds =\n            ((currentImageWallTimeMs - MEDIASTORE_TRIGGER_TOLERANCE_MS) / 1000L)\n                .coerceAtLeast(0L)\n\n        val selection =\n            "${MediaStore.Images.Media.RELATIVE_PATH} LIKE ? AND " +\n                "${MediaStore.Images.Media.DATE_ADDED} >= ?"\n\n        val selectionArgs = arrayOf(\n            "%WhatsApp%Images%",\n            minimumAddedSeconds.toString()\n        )\n\n        val sortOrder = "${MediaStore.Images.Media.DATE_ADDED} DESC"\n\n        return try {\n            contentResolver.query(\n                MediaStore.Images.Media.EXTERNAL_CONTENT_URI,\n                projection,\n                selection,\n                selectionArgs,\n                sortOrder\n            )?.use { cursor ->\n                val idCol = cursor.getColumnIndexOrThrow(MediaStore.Images.Media._ID)\n                val nameCol = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.DISPLAY_NAME)\n                val pathCol = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.RELATIVE_PATH)\n                val dateCol = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.DATE_ADDED)\n                val heightCol = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.HEIGHT)\n\n                while (cursor.moveToNext()) {\n                    val id = cursor.getLong(idCol)\n                    if (id == lastMediaImageId) continue\n\n                    val uri = ContentUris.withAppendedId(\n                        MediaStore.Images.Media.EXTERNAL_CONTENT_URI,\n                        id\n                    )\n\n                    return@use MediaImage(\n                        uri = uri,\n                        id = id,\n                        displayName = cursor.getString(nameCol).orEmpty(),\n                        relativePath = cursor.getString(pathCol).orEmpty(),\n                        dateAddedMs = cursor.getLong(dateCol) * 1000L,\n                        height = cursor.getInt(heightCol)\n                    )\n                }\n                null\n            }\n        } catch (error: Throwable) {\n            Prefs.setStatus(\n                this,\n                "Erro ao procurar arquivo do WhatsApp: ${error.message ?: error.javaClass.simpleName}"\n            )\n            null\n        }\n    }\n\n    private fun readImageFromMediaStoreOrFallback(\n        candidate: NodeItem,\n        attempt: Int\n    ) {\n        if (!processing) return\n\n        if (!hasImageReadPermission()) {\n            Prefs.setStatus(\n                this,\n                "Permissao de Fotos nao concedida. Usando leitura antiga pela tela."\n            )\n            openImageViewerFallback(candidate)\n            return\n        }\n\n        val media = findNewestWhatsAppImage()\n\n        if (media == null) {\n            if (attempt < MEDIASTORE_MAX_ATTEMPTS) {\n                if (attempt == 0) {\n                    Prefs.setStatus(\n                        this,\n                        "Imagem detectada; aguardando o WhatsApp terminar o download..."\n                    )\n                }\n                handler.postDelayed(\n                    { readImageFromMediaStoreOrFallback(candidate, attempt + 1) },\n                    MEDIASTORE_RETRY_MS\n                )\n            } else {\n                Prefs.setStatus(\n                    this,\n                    "Arquivo nao apareceu no MediaStore. Usando leitura antiga pela tela."\n                )\n                openImageViewerFallback(candidate)\n            }\n            return\n        }\n\n        lastMediaImageId = media.id\n        val ageMs = (System.currentTimeMillis() - media.dateAddedMs).coerceAtLeast(0L)\n        Prefs.setStatus(\n            this,\n            "ARQUIVO encontrado em ${ageMs}ms: ${media.displayName}. OCR original..."\n        )\n\n        try {\n            val input = InputImage.fromFilePath(this, media.uri)\n            val started = SystemClock.elapsedRealtime()\n\n            recognizer.process(input)\n                .addOnSuccessListener { visionText ->\n                    if (!processing) return@addOnSuccessListener\n\n                    val route = parseVisionText(\n                        visionText,\n                        if (media.height > 0) media.height else input.height\n                    )\n                    val elapsed = SystemClock.elapsedRealtime() - started\n                    val totalLinhas = contarLinhasVisionText(visionText)\n\n                    if (route != null) {\n                        if (isDuplicate(route)) {\n                            processing = false\n                            Prefs.setStatus(\n                                this,\n                                "Arquivo repetido ignorado | OCR=${elapsed}ms"\n                            )\n                            handler.postDelayed({ primeCurrentScreen() }, 120L)\n                        } else {\n                            Prefs.setStatus(\n                                this,\n                                "ARQUIVO: ${route.neighborhood} -> ${route.cage} | " +\n                                    "OCR=${elapsed}ms | enviando sem abrir foto"\n                            )\n                            sendRouteInCurrentChat(route)\n                        }\n                    } else {\n                        Prefs.setStatus(\n                            this,\n                            "Arquivo original leu $totalLinhas linhas, mas nao fechou a rota. " +\n                                "Tentando visualizador antigo..."\n                        )\n                        openImageViewerFallback(candidate)\n                    }\n                }\n                .addOnFailureListener { error ->\n                    if (!processing) return@addOnFailureListener\n                    Prefs.setStatus(\n                        this,\n                        "OCR do arquivo falhou: ${error.message ?: "sem detalhes"}. " +\n                            "Tentando visualizador antigo..."\n                    )\n                    openImageViewerFallback(candidate)\n                }\n        } catch (error: Throwable) {\n            Prefs.setStatus(\n                this,\n                "Nao consegui abrir o arquivo original: " +\n                    (error.message ?: error.javaClass.simpleName) +\n                    ". Tentando visualizador antigo..."\n            )\n            openImageViewerFallback(candidate)\n        }\n    }\n\n    private fun openImageViewerFallback(candidate: NodeItem) {\n        if (!processing) return\n\n        Prefs.setStatus(\n            this,\n            "Fallback: abrindo a imagem no WhatsApp para OCR pela tela..."\n        )\n\n        if (clickImageCandidateSafely(candidate)) {\n            handler.postDelayed(\n                { verifyImageViewerAndRead(attempt = 0) },\n                IMAGE_OPEN_DELAY_MS\n            )\n        } else {\n            processing = false\n            Prefs.setStatus(\n                this,\n                "Imagem detectada, mas nao achei um alvo de clique seguro."\n            )\n            handler.postDelayed({ primeCurrentScreen() }, 100L)\n        }\n    }\n\n    private fun inspectImageHint'''

s, count = pattern.subn(replacement, s, count=1)
if count != 1:
    raise SystemExit(f'Patch v0.14: bloco de imagem nao encontrado (count={count})')

service_path.write_text(s, encoding="utf-8")

# Permissoes de leitura das imagens do MediaStore.
m = manifest_path.read_text(encoding="utf-8")
if 'READ_MEDIA_IMAGES' not in m:
    marker = '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
    perms = '''\n    <uses-permission\n        android:name="android.permission.READ_EXTERNAL_STORAGE"\n        android:maxSdkVersion="32" />\n    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />\n'''
    if marker not in m:
        raise SystemExit('Patch v0.14: manifest marker nao encontrado')
    m = m.replace(marker, marker + perms, 1)
manifest_path.write_text(m, encoding="utf-8")

# Pede a permissao ao abrir o app. No Android recente, escolher TODAS AS FOTOS.
a = activity_path.read_text(encoding="utf-8")
if 'READ_MEDIA_IMAGES' not in a:
    a = a.replace(
        'import android.content.Intent\n',
        'import android.Manifest\nimport android.content.Intent\nimport android.content.pm.PackageManager\nimport android.os.Build\n',
        1,
    )

    call_anchor = '        setContentView(R.layout.activity_main)\n'
    if call_anchor not in a:
        raise SystemExit('Patch v0.14: onCreate nao encontrado')
    a = a.replace(
        call_anchor,
        call_anchor + '\n        requestImagePermissionIfNeeded()\n',
        1,
    )

    helper_anchor = '    override fun onResume() {\n'
    helper = '''    private fun requestImagePermissionIfNeeded() {\n        val permission = if (Build.VERSION.SDK_INT >= 33) {\n            Manifest.permission.READ_MEDIA_IMAGES\n        } else {\n            Manifest.permission.READ_EXTERNAL_STORAGE\n        }\n\n        if (checkSelfPermission(permission) != PackageManager.PERMISSION_GRANTED) {\n            requestPermissions(arrayOf(permission), 714)\n            Prefs.setStatus(\n                this,\n                "Permita acesso a TODAS as fotos para ler a imagem original do WhatsApp."\n            )\n        }\n    }\n\n'''
    if helper_anchor not in a:
        raise SystemExit('Patch v0.14: ponto helper MainActivity nao encontrado')
    a = a.replace(helper_anchor, helper + helper_anchor, 1)

activity_path.write_text(a, encoding="utf-8")

print("Patch v0.14 aplicado: OCR tenta arquivo original do WhatsApp via MediaStore sem abrir a foto")
