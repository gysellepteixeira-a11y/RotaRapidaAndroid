from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
r=R.read_text(encoding="utf-8")
s=S.read_text(encoding="utf-8")

# v66.4: reconhecer Rosário de Fátima SOMENTE pelo núcleo "rosar".
# "de Fátima" sozinho nunca conta.
# Remove o rescue denso da v66.3, porque ele atrasava imagens onde havia
# Mata/República mas nenhum Rosário visível.

helper='''    fun rosarioConfiguredPriorityV663(): Int? {
        priorities.forEachIndexed { index, rule ->
            val n = normalize(rule.name)
            if (n == "rosario" || n == "rosario de fatima") {
                return index
            }
        }
        return null
    }
'''
if helper in r:
    r=r.replace(helper,'',1)

rescue='''                val rosarioPriorityV663 = RouteParser.rosarioConfiguredPriorityV663()
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

'''
if rescue not in s:
    raise SystemExit("v66.4 rescue block missing")
s=s.replace(rescue,'',1)

old_title='===== DIAGNOSTICO IMAGEM v19 | V66.3 ROSARIO PRIORITY RESCUE + V66 HYBRID CAGE + OCR WARM + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
new_title='===== DIAGNOSTICO IMAGEM v19 | V66.4 ROSARIO ONLY + V66 HYBRID CAGE + OCR WARM + V64 AGENCY ANCHOR + V48 EDITOR FAST PATH + V47 CLEAN FAST ====='
if old_title not in s:
    raise SystemExit("v66.4 title anchor missing")
s=s.replace(old_title,new_title,1)

# Garante que as correções úteis anteriores continuam:
for marker in [
    '"rosario de fatima" -> listOf("rosar")',
    'if (token == "rosar")',
    'word.length < token.length && token.startsWith(word)',
    'V66.4 ROSARIO ONLY'
]:
    if marker not in r+s:
        raise SystemExit("v66.4 verify failed: "+marker)

if 'rescue Rosario acima de' in s or 'rosarioConfiguredPriorityV663' in r:
    raise SystemExit("v66.4 rescue removal failed")

R.write_text(r,encoding="utf-8")
S.write_text(s,encoding="utf-8")
print("v66.4 aplicado: Rosario de Fatima reconhece somente por rosar; de Fatima nao conta; rescue lento removido")
