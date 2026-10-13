from pathlib import Path
p=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=p.read_text(encoding="utf-8")
old="RyzenOcrBridgeV68.reconhecer(jpg)"
new="RyzenOcrBridgeV68.reconhecer(jpg, Prefs.neighborhoods(this))"
if s.count(old)!=1:
    raise SystemExit("v69: integracao MediaStore V68.1 nao encontrada/ambigua")
s=s.replace(old,new,1)
assert "Prefs.neighborhoods(this)" in s
p.write_text(s,encoding="utf-8")
print("v69: prioridades dinamicas enviadas ao Ryzen a cada imagem")
