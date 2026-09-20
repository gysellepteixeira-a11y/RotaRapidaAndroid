# Gerar o APK pelo GitHub

Este projeto já inclui o workflow:

`.github/workflows/build-apk.yml`

Ele prepara automaticamente:
- Java 17
- Android SDK 35
- Gradle 8.10.2
- build `app-debug.apk`

## Depois de enviar os arquivos para um repositório GitHub

1. Abra a aba **Actions**.
2. Clique em **Gerar APK**.
3. Clique em **Run workflow**.
4. Espere o job terminar.
5. Abra a execução concluída.
6. Na parte **Artifacts**, baixe **RotaRapida-APK**.
7. Extraia o ZIP baixado pelo GitHub.
8. O arquivo dentro será `app-debug.apk`.

Também está configurado para compilar automaticamente quando houver `push` para `main` ou `master`.
