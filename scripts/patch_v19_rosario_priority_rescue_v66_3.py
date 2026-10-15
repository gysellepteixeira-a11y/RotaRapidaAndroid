from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
r=R.read_text(encoding="utf-8")
s=S.read_text(encoding="utf-8")

route_anchor='''    fun matchPriority(text: String): Pair<Int, String>? =
        priorityFor(text)
'''
if route_anchor not in r:
    raise SystemExit("v66.3 RouteParser matchPriority anchor missing")

route_new=route_anchor+'''
    fun rosarioConfiguredPriorityV663(): Int? {
        priorities.forEachIndexed { index, rule ->
            val n = normalize(rule.name)
            if (n == "rosario" || n == "rosario de fatima") {
                return index
            }
        }
        return null
    }
'''
r=r.replace(route_anchor,route_new,1)

chosen_anchor='''                val chosen = best
                if (chosen == null) {
                    Prefs.setStatus(
                        this,
                        "BAIRRO PRIMEIRO sem prioridade em ${bairroOcrMs}ms | " +
                            "amostra=[$rawSample] | fallback OCR denso completo..."
                    )
                    readDenseFullFallback(
                        media = media,
                        crop = denseBitmap,
                        rowCount = rowCount,
                        widthRatio = widthRatio,
                        decodeMs = decodeMs,
                        scanMs = scanMs,
                        reason = "bairro nao confirmado"
                    )
                    return@addOnSuccessListener
                }

                // Y do OCR da coluna Bairro e diretamente compativel com
'''
if chosen_anchor not in s:
    raise SystemExit("v66.3 chosen anchor missing")

chosen_new='''                val chosen = best
                if (chosen == null) {
                    Prefs.setStatus(
                        this,
                        "BAIRRO PRIMEIRO sem prioridade em ${bairroOcrMs}ms | " +
                            "amostra=[$rawSample] | fallback OCR denso completo..."
                    )
                    readDenseFullFallback(
                        media = media,
                        crop = denseBitmap,
                        rowCount = rowCount,
                        widthRatio = widthRatio,
                        decodeMs = decodeMs,
                        scanMs = scanMs,
                        reason = "bairro nao confirmado"
                    )
                    return@addOnSuccessListener
                }

                val rosarioPriorityV663 = RouteParser.rosarioConfiguredPriorityV663()
                val chosenNormV663 = RouteParser.normalize(chosen.neighborhood)
                val lowerSensitiveV663 =
                    "mata da praia" in chosenNormV663 ||
                    "republica" in chosenNormV663

                if (
                    rosarioPriorityV663 != null &&
                    rosarioPriorityV663 < chosen.priorityIndex &&
                    lowerSensitiveV663
                ) {
                    Prefs.setStatus(
                        this,
                        "VALIDANDO PRIORIDADE: Rosario acima de ${chosen.neighborhood} | " +
                            "fallback denso seguro..."
                    )
                    readDenseFullFallback(
                        media = media,
                        crop = denseBitmap,
                        rowCount = rowCount,
                        widthRatio = widthRatio,
                        decodeMs = decodeMs,
                        scanMs = scanMs,
                        reason = "rescue Rosario acima de ${chosen.neighborhood}"
                    )
                    return@addOnSuccessListener
                }

                // Y do OCR da coluna Bairro e diretamente compativel com
'''
s=s.replace(chosen_anchor,chosen_new,1)

old_title='===== DIAGNOSTICO IMAGEM v19 | V66.2 ROSARIO ROBUST + V66 HYBRID CAGE + OCR WARM + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
new_title='===== DIAGNOSTICO IMAGEM v19 | V66.3 ROSARIO PRIORITY RESCUE + V66 HYBRID CAGE + OCR WARM + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
if old_title not in s:
    raise SystemExit("v66.3 title anchor missing")
s=s.replace(old_title,new_title,1)

for marker in [
    'fun rosarioConfiguredPriorityV663()',
    'rosarioPriorityV663 < chosen.priorityIndex',
    'rescue Rosario acima de',
    'V66.3 ROSARIO PRIORITY RESCUE'
]:
    if marker not in r+s:
        raise SystemExit("v66.3 verify failed: "+marker)

R.write_text(r,encoding="utf-8")
S.write_text(s,encoding="utf-8")
print("v66.3 aplicado: rescue denso somente quando Rosario configurado acima de Mata/Republica")
