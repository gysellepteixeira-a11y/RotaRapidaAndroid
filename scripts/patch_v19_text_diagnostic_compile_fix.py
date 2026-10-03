from pathlib import Path

S = Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
s = S.read_text()

start_marker = '    private fun tdReport(route:RouteResult){'
end_marker = '    private fun formatElapsedMs(ms: Long): String {'
start = s.find(start_marker)
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('tdReport block not found')

fixed = '''    private fun tdReport(route:RouteResult){
        val x=buildString{
            appendLine("===== DIAGNOSTICO TEXTO v1 | OLD BASE =====")
            appendLine("[+0ms] Evento WhatsApp")
            appendLine("[${tdA(tdAnalyze)}] Analise iniciou | evento->analise=${tdD(tdEvent,tdAnalyze)}")
            appendLine("[${tdA(tdCollectDone)}] Arvore inicial coletada | collect=${tdCollect}ms")
            appendLine("[${tdA(tdRoute)}] Rota: ${route.neighborhood} -> ${route.cage} | parser=${tdParse}ms | newItems=$tdNewItems")
            appendLine("[${tdA(tdStatusTextoDone)}] Status Texto | write=${tdStatusTexto}ms")
            appendLine("[${tdA(tdEditor)}] Editor encontrado | collectEnvio=${tdSendCollect}ms")
            if(tdHeld>0) appendLine("[${tdA(tdHeld)}] Rota pendente: sem editor")
            if(tdReleased>0) appendLine("[${tdA(tdReleased)}] Editor/admin liberado | wait=${tdD(tdHeld,tdReleased)}")
            appendLine("[${tdA(tdFilled)}] Campo preenchido | setText=${tdSet}ms")
            appendLine("[${tdA(tdStatusEnvioDone)}] Status ENVIO | write=${tdStatusEnvio}ms")
            appendLine("[${tdA(tdReady)}] SEND READY iniciou")
            appendLine("[${tdA(tdReadyFound)}] Enviar encontrado | collectReady=${tdReadyCollect}ms | polls=$tdReadyPoll")
            appendLine("[${tdA(tdStatusReadyDone)}] Status READY | write=${tdStatusReady}ms")
            appendLine("[${tdA(tdCandidateSend)}] Candidato Enviar | collectClick=${tdClickCollect}ms")
            appendLine("[${tdA(tdClicked)}] Clique aceito | action=${tdAction}ms | metodo=$speedDiagnosticSendMethod")
            appendLine("[${tdA(tdConfirmed)}] Confirmado | collectConfirm=${tdConfirmCollect}ms | polls=$tdConfirmPoll")
            appendLine()
            appendLine("RESUMO")
            appendLine("evento->rota=${tdD(tdEvent,tdRoute)}")
            appendLine("rota->campo=${tdD(tdRoute,tdFilled)}")
            appendLine("campo->click=${tdD(tdFilled,tdClicked)}")
            appendLine("click->confirm=${tdD(tdClicked,tdConfirmed)}")
            appendLine("rota->click=${tdD(tdRoute,tdClicked)}")
            appendLine("rota->confirm=${tdD(tdRoute,tdConfirmed)}")
            appendLine("evento->confirm=${tdD(tdEvent,tdConfirmed)}")
            append("collectTotal=${tdCollect+tdSendCollect+tdReadyCollect+tdClickCollect+tdConfirmCollect}ms | statusWrites=${tdStatusTexto+tdStatusEnvio+tdStatusReady}ms")
        }
        Prefs.setSpeedDiagnosticReport(this,x); tdOn=false; tdCandidate=0
    }

'''

s = s[:start] + fixed + s[end:]
S.write_text(s)
print('TEXT DIAGNOSTIC compile fix aplicado')
