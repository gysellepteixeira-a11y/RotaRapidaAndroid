from pathlib import Path

base = Path("app/src/main")
service_file = base / "java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt"
prefs_file = base / "java/com/gy/rotarapida/Prefs.kt"
main_file = base / "java/com/gy/rotarapida/MainActivity.kt"
parser_file = base / "java/com/gy/rotarapida/RouteParser.kt"
layout_file = base / "res/layout/activity_main.xml"

service = service_file.read_text(encoding="utf-8")
prefs = prefs_file.read_text(encoding="utf-8")
main = main_file.read_text(encoding="utf-8")
parser = parser_file.read_text(encoding="utf-8")
layout = layout_file.read_text(encoding="utf-8")

def replace_one(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Filtro Modal: marcador ausente: {label}")
    return text.replace(old, new, 1)

# Persistent setting. Default = somente passeio/desconhecidos.
if "fun includeFake(context: Context)" not in prefs:
    idx = prefs.rfind("\n}")
    if idx < 0:
        raise RuntimeError("Prefs nao encerra object")
    prefs = prefs[:idx] + """
    fun includeFake(context: Context): Boolean =
        prefs(context).getBoolean("include_fake_volumoso", false)

    fun setIncludeFake(context: Context, enabled: Boolean) {
        prefs(context).edit().putBoolean("include_fake_volumoso", enabled).apply()
    }
""" + prefs[idx:]

# Switch in existing home screen.
if 'switchIncludeFake' not in layout:
    layout = replace_one(
        layout,
        '    </LinearLayout>',
        '''        <androidx.appcompat.widget.SwitchCompat
            android:id="@+id/switchIncludeFake"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="14dp"
            android:text="Incluir FAKE VOLUMOSO (MOTO sempre ignorada)" />

    </LinearLayout>''',
        "layout"
    )

if 'R.id.switchIncludeFake' not in main:
    main = replace_one(
        main,
        '        setContentView(R.layout.activity_main)',
        '''        setContentView(R.layout.activity_main)
        val includeFake = findViewById<androidx.appcompat.widget.SwitchCompat>(
            R.id.switchIncludeFake
        )
        includeFake.isChecked = Prefs.includeFake(this)
        includeFake.setOnCheckedChangeListener { _, checked ->
            Prefs.setIncludeFake(this, checked)
        }
''',
        "MainActivity.setContentView"
    )

# Tie-breaking: priority remains first, last row among equal priority.
parser = replace_one(
    parser,
    'val winner = candidates.minByOrNull { it.first } ?: return null',
    'val bestPriority = candidates.minOf { it.first }\n        val winner = candidates.lastOrNull { it.first == bestPriority } ?: return null',
    "RouteParser plain-text tie"
)
occ = parser.count('.minByOrNull { it.third.top }')
if occ < 2:
    raise RuntimeError(f"Parser: expected >=2 vertical ties, got {occ}")
parser = parser.replace('.minByOrNull { it.third.top }', '.maxByOrNull { it.third.top }')

# Detector crop vertical offset: needed to align modal cells with cropped OCR bitmap.
service = replace_one(
    service,
    '        val rowCount: Int\n    )\n',
    '        val rowCount: Int,\n        val topOffset: Int\n    )\n',
    "ColorTableCrop definition"
)
service = replace_one(
    service,
    '            rowCount = rowCount\n        )',
    '            rowCount = rowCount,\n            topOffset = cropTop\n        )',
    "ColorTableCrop constructor"
)

# Main OCR: filter the ORIGINAL image before ML Kit. No second OCR.
begin = service.index('    private fun readMediaOriginalFull(media: MediaImage) {')
end = service.index('    private fun readMediaLargeColorCrop(media: MediaImage) {', begin)
block = service[begin:end]
block = replace_one(
    block,
    'val input = InputImage.fromFilePath(this, media.uri)',
    '''val rawBitmap = contentResolver.openInputStream(media.uri)?.use { stream ->
                BitmapFactory.decodeStream(stream)
            } ?: throw IllegalStateException("Imagem nao decodificada")
            val filteredBitmap = ModalFilter.filter(
                rawBitmap, rawBitmap, 0, Prefs.includeFake(this)
            )
            val input = InputImage.fromBitmap(filteredBitmap, 0)''',
    "full image input"
)
block = replace_one(
    block,
    'recognizer.process(input)\n',
    '''recognizer.process(input)
                .addOnCompleteListener {
                    try { filteredBitmap.recycle() } catch (_: Throwable) {}
                }
''',
    "full OCR release"
)
service = service[:begin] + block + service[end:]

# Dense cropped OCR: the original bitmap still contains the modal column.
begin = service.index('    private fun readMediaLargeColorCrop(media: MediaImage) {')
end = service.index('    private fun readDenseCageOnly(', begin)
block = service[begin:end]
block = replace_one(
    block,
    '        var crop = detected.bitmap\n',
    '''        var crop = ModalFilter.filter(
            source,
            detected.bitmap,
            detected.topOffset,
            Prefs.includeFake(this)
        )
''',
    "dense crop filter"
)
service = service[:begin] + block + service[end:]

# Enhanced OCR fallback must also respect modal selection.
enhancedStart = service.find('    private fun readMediaEnhanced(media: MediaImage) {')
if enhancedStart < 0:
    raise RuntimeError("readMediaEnhanced missing")
enhancedEnd = service.find('\n    private fun ', enhancedStart + 20)
if enhancedEnd < 0:
    enhancedEnd = len(service)
block = service[enhancedStart:enhancedEnd]
block = replace_one(
    block,
    'val enhanced = prepareEnhancedFileBitmap(decoded)',
    '''val filtered = ModalFilter.filter(
                decoded, decoded, 0, Prefs.includeFake(this)
            )
            val enhanced = prepareEnhancedFileBitmap(filtered)''',
    "enhanced image filter"
)
service = service[:enhancedStart] + block + service[enhancedEnd:]

# Fast neighborhood-only OCR should choose the final matching occurrence.
service = service.replace(
    'hit.priorityIndex == current.priorityIndex && hit.top < current.top',
    'hit.priorityIndex == current.priorityIndex && hit.top > current.top'
)
service = service.replace(
    '.filter { it.rawPart }\n            .minByOrNull { it.top }',
    '.filter { it.rawPart }\n            .maxByOrNull { it.top }'
)
service = service.replace(
    'samePriority.minByOrNull { it.top }',
    'samePriority.maxByOrNull { it.top }'
)

# Guardrail: no modifications to WhatsApp interaction/send code.
for marker in ["sendRouteInCurrentChat(", "readDenseBairroFirst(", "findNewestWhatsAppImage()"]:
    if marker not in service:
        raise RuntimeError("Preserved marker missing: " + marker)

service_file.write_text(service, encoding="utf-8")
prefs_file.write_text(prefs, encoding="utf-8")
main_file.write_text(main, encoding="utf-8")
parser_file.write_text(parser, encoding="utf-8")
layout_file.write_text(layout, encoding="utf-8")

# Distinct debug application ID and label: do NOT overwrite the production V66.4.
gradle_file = Path("app/build.gradle.kts")
gradle = gradle_file.read_text(encoding="utf-8")
gradle = replace_one(
    gradle,
    "    buildTypes {",
    '''    buildTypes {
        getByName("debug") {
            applicationIdSuffix = ".modaltest"
        }''',
    "test appId"
)
gradle_file.write_text(gradle, encoding="utf-8")

strings_file = base / "res/values/strings.xml"
strings = strings_file.read_text(encoding="utf-8")
strings = replace_one(
    strings,
    '<string name="app_name">Rota Rápida</string>',
    '<string name="app_name">Rota Rápida (TESTE MODAL)</string>',
    "test app name"
)
strings = strings.replace(
    '<string name="service_name">Rota Rápida — WhatsApp</string>',
    '<string name="service_name">Rota Rápida TESTE MODAL — WhatsApp</string>'
)
strings_file.write_text(strings, encoding="utf-8")

print("MODAL FILTER EXPERIMENTAL applied: PASSEIO+UNKNOWN, optional FAKE, never MOTO, last equal-priority cage")
