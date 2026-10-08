from pathlib import Path

R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
r=R.read_text(encoding="utf-8")

old_normal='''            return match.groupValues[1].lowercase(Locale.ROOT) + match.groupValues[2]
'''
new_normal='''            return match.groupValues[1] + match.groupValues[2]
'''

old_i='''        return "i" + iFallback.groupValues[1]
'''
new_i='''        return "I" + iFallback.groupValues[1]
'''

if old_normal not in r:
    raise SystemExit("v61 final normal lowercase cage return not found")
if old_i not in r:
    raise SystemExit("v61 final I fallback lowercase return not found")

r=r.replace(old_normal,new_normal,1)
r=r.replace(old_i,new_i,1)

for bad in [
    'match.groupValues[1].lowercase(Locale.ROOT) + match.groupValues[2]',
    'return "i" + iFallback.groupValues[1]',
]:
    if bad in r:
        raise SystemExit("v61 lowercase cage output still present: "+bad)

for good in [
    'return match.groupValues[1] + match.groupValues[2]',
    'return "I" + iFallback.groupValues[1]',
]:
    if good not in r:
        raise SystemExit("v61 uppercase output missing: "+good)

R.write_text(r,encoding="utf-8")
print("v61 aplicado: gaiola em MAIUSCULA no parser normal e no fallback I")
