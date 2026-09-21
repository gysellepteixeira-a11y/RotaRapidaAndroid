from pathlib import Path

service_path = Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s = service_path.read_text(encoding="utf-8")

# O patch de avisos substitui o bloco onde o helper de tempo estava localizado.
# Recoloca o helper para manter o status app=... como nas versoes anteriores.
if 'private fun formatElapsedMs(ms: Long): String' not in s:
    anchor = '    private fun startTwentyAlerts(route: RouteResult, elapsedMs: Long) {\n'
    helper = '''    private fun formatElapsedMs(ms: Long): String {
        if (ms < 0L) return "--"
        return if (ms >= 1000L) {
            String.format(java.util.Locale.US, "%.2fs", ms / 1000.0)
        } else {
            "${ms}ms"
        }
    }

'''
    if anchor not in s:
        raise SystemExit('patch alerts compile fix: startTwentyAlerts nao encontrado')
    s = s.replace(anchor, helper + anchor, 1)

service_path.write_text(s, encoding="utf-8")
print("Compile fix aplicado: formatElapsedMs restaurado")
