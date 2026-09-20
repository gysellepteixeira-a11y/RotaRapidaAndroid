# Rota Rápida Android — versão 0.1 de teste

Esta primeira versão leva a lógica do bot para o próprio Android.

## O que ela tenta fazer

### Rota em texto
1. Detecta mudança no WhatsApp pelo Serviço de Acessibilidade.
2. Lê o texto diretamente da interface do WhatsApp, sem OCR.
3. Procura todos os bairros prioritários.
4. Escolhe a prioridade mais alta.
5. Lê a gaiola da mesma linha.
6. Normaliza `G-03` para `g03`.
7. Preenche e envia automaticamente:

Felipe lima de Castilho
1347515
Passeio
Gaiola: g03

### Rota em imagem
1. Detecta uma nova foto/imagem no grupo.
2. Abre a imagem.
3. Faz uma captura da tela usando o Serviço de Acessibilidade.
4. Usa Google ML Kit OCR local.
5. Escolhe o bairro prioritário.
6. Procura a gaiola na mesma altura.
7. Volta ao grupo e envia a mensagem.

## Prioridades

1. Valparaiso
2. Colina de Laranjeiras
3. Praia da Baleia
4. Morada de Laranjeiras
5. Eurico
6. Manoel Plaza
7. Rosario
8. Helio Ferraz
9. Parque Residencial Laranjeiras
10. Barcelona
11. Maringa

## Segurança da prioridade

Se o app encontrar o bairro de maior prioridade, mas não conseguir ler a gaiola daquela linha, ele NÃO troca por um bairro de prioridade menor.

## Antes de testar

No app:
1. Digite o nome EXATO do grupo.
2. Salve.
3. Ligue "Automação ativa".
4. Toque em "Abrir Acessibilidade do Android".
5. Ative o serviço "Rota Rápida — WhatsApp".
6. Abra o grupo no WhatsApp e deixe a conversa aberta.

## Como compilar

Este ZIP é um projeto Android Studio. Abra a pasta `RotaRapidaAndroid` no Android Studio.
O Android Studio precisa ter o Android SDK 35 instalado e acesso à internet na primeira sincronização para baixar as dependências Gradle e o ML Kit.

Depois:
Build > Build APK(s)

## Observação importante

Esta é uma versão de teste. A estrutura interna/acessibilidade do WhatsApp varia por versão e por aparelho.
O primeiro teste no Poco F4 serve para descobrir especialmente:
- se o texto da rota aparece diretamente no AccessibilityService;
- como o WhatsApp identifica a miniatura de imagem;
- como ele identifica o botão "Enviar";
- tempo real texto -> envio;
- tempo real imagem -> OCR -> envio.

O app grava o último estado na tela inicial, incluindo algo como:

ENVIADO: Valparaiso -> g03 | app=123ms

Isso permite comparar com o bot do PC.
