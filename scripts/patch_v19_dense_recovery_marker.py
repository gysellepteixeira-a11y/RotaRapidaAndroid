from pathlib import Path

prefs_path = Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
gradle_path = Path("app/build.gradle.kts")

prefs = prefs_path.read_text(encoding="utf-8")
gradle = gradle_path.read_text(encoding="utf-8")

prefs = prefs.replace(
    '===== DIAGNOSTICO IMAGEM v0.19 =====',
    '===== DIAGNOSTICO IMAGEM v0.19 DENSA RECOVERY ====='
)

gradle = gradle.replace('versionCode = 1', 'versionCode = 3')
gradle = gradle.replace('versionName = "0.1-test"', 'versionName = "0.19-densa-cage-fix"')

prefs_path.write_text(prefs, encoding="utf-8")
gradle_path.write_text(gradle, encoding="utf-8")

print("Marker DENSA RECOVERY aplicado + versionCode 3")
