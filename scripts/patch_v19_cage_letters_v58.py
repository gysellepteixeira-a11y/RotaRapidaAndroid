from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
r=R.read_text(encoding="utf-8")

old='''    private val cageRegex =
        Regex("""(?<![A-Z0-9])([A-I])[-.\\s]?(\\d{2})(?![A-Z0-9])""")
'''
new='''    private val cageRegex =
        Regex("""(?<![A-Z0-9])([A-Z])[-.\\s]?(\\d{2})(?![A-Z0-9])""")
'''

if old not in r:
    raise SystemExit("v58 cageRegex [A-I] final-v57 block missing")

r=r.replace(old,new,1)

for required in [
    '([A-Z])[-.\\\\s]?(\\\\d{2})',
    'private val cageIFallbackRegex',
    'fun extractCage(value: String): String?',
]:
    if required not in r:
        raise SystemExit("v58 verify failed: "+required)

if '([A-I])[-.\\\\s]?(\\\\d{2})' in r:
    raise SystemExit("v58 verify failed: old A-I cage range still active")

R.write_text(r,encoding="utf-8")
print("v58 aplicado: gaiola aceita A-Z; formato/bordas/2 digitos preservados")
