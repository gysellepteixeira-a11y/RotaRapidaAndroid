from pathlib import Path

S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s=S.read_text(encoding='utf-8')

required=[
    '===== DIAGNOSTICO IMAGEM v17 | V37 + MATA DA PRAIA + REPUBLICA =====',
    'inspectImageHint(event)',
    'val currentImageCandidates = findImageCandidates(items)',
    'val candidate: NodeItem? = null',
    '"Imagem nova detectada direto nos arquivos do WhatsApp | "',
    '"BAIRRO PRIMEIRO: ${chosen.neighborhood} | "',
    '"DENSA RECOVERY: ${route.neighborhood} -> ${route.cage} | "',
    '"ENVIO: campo preenchido em ${formatElapsedMs(fillMs)} | "',
]
for m in required:
    if m not in s:
        raise SystemExit('v47 wrong base: '+m)

s=s.replace('        inspectImageHint(event)\n\n','',1)

prime_old='''        previousImageFingerprints = findImageCandidates(items)
            .map(::imageFingerprint)
            .toSet()
'''
if prime_old not in s:
    raise SystemExit('v47 prime legacy fingerprint block missing')
s=s.replace(prime_old,'',1)

invalid_prime='''            previousImageFingerprints = findImageCandidates(items)
                .map(::imageFingerprint)
                .toSet()
'''
if invalid_prime not in s:
    raise SystemExit('v47 invalid-chat legacy fingerprint block missing')
s=s.replace(invalid_prime,'',1)

full_scan_old='''        val currentImageCandidates = findImageCandidates(items)
        val currentImageFingerprints = currentImageCandidates
            .map(::imageFingerprint)
            .toSet()
'''
if full_scan_old not in s:
    raise SystemExit('v47 full legacy image scan block missing')
s=s.replace(full_scan_old,'',1)

s=s.replace('            previousImageFingerprints = emptySet()\n','',1)
s=s.replace('            previousImageFingerprints = currentImageFingerprints\n','',1)

image_block='''        // ---------------- IMAGEM ----------------
        //
        // v0.2:
        // No M52 o WhatsApp não expôs a miniatura com o texto "foto/imagem".
        // Por isso não dependemos mais do imageHintUntil.
        //
        // Agora detectamos também um NOVO bloco visual grande, sem texto,
        // dentro da região da conversa. Isso cobre miniaturas expostas como
        // android.view.View / FrameLayout, algo comum no WhatsApp/Samsung.
        val imageNow = SystemClock.elapsedRealtime()
        val newImageCandidates = currentImageCandidates.filter { candidate ->
            val fp = imageFingerprint(candidate)
            val isNew = fp !in previousImageFingerprints
            val wasJustOpened =
                fp == lastOpenedImageFingerprint &&
                imageNow - lastOpenedImageAt < IMAGE_REOPEN_COOLDOWN_MS

            isNew && !wasJustOpened
        }

        val candidate: NodeItem? = null


        // Atualiza a referência ANTES de qualquer clique.
        previousImageFingerprints = currentImageFingerprints

        if (candidate != null) {
            currentStartedAt = SystemClock.elapsedRealtime()
            currentImageWallTimeMs = System.currentTimeMillis()
            processing = true

            val savedRect = Rect(candidate.rect)
            val savedFingerprint = imageFingerprint(candidate)

            Prefs.setStatus(
                this,
                "Imagem nova detectada. Procurando o arquivo original do WhatsApp..."
            )

            readImageFromMediaStoreOrFallback(
                targetRect = savedRect,
                fingerprint = savedFingerprint,
                attempt = 0
            )
            return
        }

'''
if image_block not in s:
    raise SystemExit('v47 unreachable image candidate block not found')
s=s.replace(image_block,'',1)

def drop(block, label):
    global s
    if block not in s:
        raise SystemExit('v47 status block missing: '+label)
    s=s.replace(block,'',1)

drop('''        Prefs.setStatus(
            this,
            "Imagem nova detectada direto nos arquivos do WhatsApp | " +
                "MediaStore=${mediaStoreMs}ms | h=${media.height}px | OCR v0.19..."
        )

''','media pre-ocr')

drop('''        val ageMs = (System.currentTimeMillis() - media.dateAddedMs).coerceAtLeast(0L)
        Prefs.setStatus(
            this,
            "ARQUIVO h=${media.height}: OCR completo... (${ageMs}ms desde arquivo)"
        )

''','full pre-ocr')

drop('''                            Prefs.setStatus(
                                this,
                                "ARQUIVO: ${route.neighborhood} -> ${route.cage} | " +
                                    "OCR=${elapsed}ms parse=${parserMs}ms | enviando"
                            )
''','full route send')

drop('''                Prefs.setStatus(
                    this,
                    "BAIRRO PRIMEIRO: ${chosen.neighborhood} | " +
                        "linhaY=${chosen.centerY} | OCR=${bairroOcrMs}ms | agora Gaiola..."
                )

''','bairro to cage')

drop('''        Prefs.setStatus(
            this,
            "DENSA FALLBACK: $rowCount linhas | $reason | OCR completo do crop..."
        )

''','dense fallback pre-ocr')

drop('''                        Prefs.setStatus(
                            this,
                            "DENSA FALLBACK $rowCount: ${route.neighborhood} -> ${route.cage} | " +
                                "decode=${decodeMs}ms scan=${scanMs}ms " +
                                "OCR=${elapsed}ms parse=${parserMs}ms | enviando"
                        )
''','dense fallback send')

drop('''                        Prefs.setStatus(
                            this,
                            "DENSA RECOVERY: ${route.neighborhood} -> ${route.cage} | " +
                                "denseOCR=${denseOcrMs}ms parse=${denseParseMs}ms " +
                                "gaiolaOCR=${cageOcrMs}ms | lido=[$raw] | enviando"
                        )
''','cage success send')

drop('''                            Prefs.setStatus(
                                this,
                                "ARQUIVO REFORCADO: ${route.neighborhood} -> ${route.cage} | " +
                                    "OCR=${elapsed}ms parse=${parserMs}ms | enviando sem abrir foto"
                            )
''','enhanced success send')

drop('''                val tdSt = SystemClock.elapsedRealtime()
                Prefs.setStatus(
                    this,
                    "Texto: ${tfRoute.neighborhood} -> ${tfRoute.cage}. Enviando..."
                )
                if (tdOn) {
                    tdStatusTexto += SystemClock.elapsedRealtime() - tdSt
                    tdStatusTextoDone = SystemClock.elapsedRealtime()
                }
''','text tail status')

drop('''            val tdSt = SystemClock.elapsedRealtime()
            Prefs.setStatus(
                this,
                "Texto: ${textRoute.neighborhood} -> ${textRoute.cage}. Enviando..."
            )
            if(tdOn){ tdStatusTexto += SystemClock.elapsedRealtime()-tdSt; tdStatusTextoDone=SystemClock.elapsedRealtime() }
''','text fallback status')

drop('''        val fillMs = SystemClock.elapsedRealtime() - releasedAt
        val tdAe = if(tdOn) SystemClock.elapsedRealtime() else 0L
        Prefs.setStatus(
            this,
            "ADMIN ULTRA DIRECT: liberado + preenchido em ${fillMs}ms | watch=10ms | ready=4ms"
        )
        if(tdOn && tdAe>0L){ tdStatusEnvio += SystemClock.elapsedRealtime()-tdAe; tdStatusEnvioDone=SystemClock.elapsedRealtime() }

''','admin release status')

drop('''        val fillMs = if (speedDiagnosticSendStartedAt > 0L) {
            SystemClock.elapsedRealtime() - speedDiagnosticSendStartedAt
        } else {
            -1L
        }
        val tdSe = if(tdOn) SystemClock.elapsedRealtime() else 0L
        Prefs.setStatus(
            this,
            "ENVIO: campo preenchido em ${formatElapsedMs(fillMs)} | " +
                "aguardando clique/confirmacao do WhatsApp..."
        )
        if(tdOn && tdSe>0L){ tdStatusEnvio += SystemClock.elapsedRealtime()-tdSe; tdStatusEnvioDone=SystemClock.elapsedRealtime() }

''','post fill status')

s=s.replace(
    '===== DIAGNOSTICO IMAGEM v17 | V37 + MATA DA PRAIA + REPUBLICA =====',
    '===== DIAGNOSTICO IMAGEM v18 | V47 CLEAN FAST + V46 9 BAIRROS =====',
    1
)

checks=[
    '===== DIAGNOSTICO IMAGEM v18 | V47 CLEAN FAST + V46 9 BAIRROS =====',
    'readMediaOriginal(media)',
    'readDenseCageOnly(',
    'waitForImageDirectSendReadyV8(',
    'waitForTextDirectSendReadyV5(',
    'readDenseFullFallback(',
    'readMediaEnhanced(media)',
    '7 to "Mata da Praia"',
    '8 to "Republica"',
    '===== DIAGNOSTICO TEXTO v37 |',
]
for m in checks:
    if m not in s:
        raise SystemExit('v47 verify failed: '+m)

if '        inspectImageHint(event)\n' in s:
    raise SystemExit('v47 inspectImageHint call still active')
if '        val currentImageCandidates = findImageCandidates(items)\n' in s:
    raise SystemExit('v47 currentImageCandidates still active')
if '        val candidate: NodeItem? = null\n' in s:
    raise SystemExit('v47 forced-null candidate block still present')

S.write_text(s,encoding='utf-8')
print('v47 CLEAN FAST applied: active legacy image scans removed + success-path SharedPreferences writes removed; OCR/send/fallback logic preserved')
