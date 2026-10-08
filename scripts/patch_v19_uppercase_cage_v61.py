from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
r=R.read_text(encoding="utf-8")

old='''        return letter.lowercase(Locale.ROOT) + match.groupValues[2]
'''
new='''        return letter + match.groupValues[2]
'''

if old not in r:
    raise SystemExit("v61 lowercase cage return not found")

r=r.replace(old,new,1)

if 'return letter.lowercase(Locale.ROOT) + match.groupValues[2]' in r:
    raise SystemExit("v61 lowercase return still present")

if 'return letter + match.groupValues[2]' not in r:
    raise SystemExit("v61 uppercase return missing")

R.write_text(r,encoding="utf-8")
print("v61 aplicado: gaiola normalizada em MAIUSCULA na origem do parser")
