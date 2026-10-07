from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
L=Path("app/src/main/res/layout/activity_main.xml")

s=S.read_text(encoding="utf-8")
layout=L.read_text(encoding="utf-8")

required=[
    'private fun waitForReadMoreDescV20(startedAt:Long,poll:Int,generation:Long){',
    'TEXT v21: rota truncada detectada, mas o botao Ler mais real nao apareceu em',
    '===== DIAGNOSTICO IMAGEM v17 | V37 + MATA DA PRAIA + REPUBLICA =====',
]
for m in required:
    if m not in s:
        raise SystemExit("v50 wrong base: "+m)

anchor='''    private fun waitForReadMoreDescV20(startedAt:Long,poll:Int,generation:Long){
'''
helper=r'''    private fun buildReadMoreTreeDumpV50(): String {
        val root=try{rootInActiveWindow}catch(_:Throwable){null}
            ?: return "===== READ MORE TREE DIAG v50 =====\nrootInActiveWindow=null"

        fun clean(v:String,max:Int=180):String =
            v.replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")
                .replace(Regex("\\s+")," ").trim().take(max)

        val out=StringBuilder()
        out.appendLine("===== READ MORE TREE DIAG v50 | V37 + MATA + REPUBLICA =====")
        out.appendLine("Objetivo: descobrir como o WhatsApp expoe o Ler mais agora.")
        out.appendLine("status: timeout do no real contentDescription=Ler mais")
        out.appendLine()

        val q=java.util.ArrayDeque<Pair<AccessibilityNodeInfo,Int>>()
        q.add(root to 0)
        var visited=0
        var emitted=0
        val maxVisited=320
        val maxEmitted=180

        while(q.isNotEmpty() && visited<maxVisited && emitted<maxEmitted){
            val (n,depth)=q.removeFirst()
            visited++

            val textObj=try{n.text}catch(_:Throwable){null}
            val rawText=try{textObj?.toString().orEmpty()}catch(_:Throwable){""}
            val desc=try{n.contentDescription?.toString().orEmpty()}catch(_:Throwable){""}
            val cls=try{n.className?.toString().orEmpty()}catch(_:Throwable){""}
            val id=try{n.viewIdResourceName.orEmpty()}catch(_:Throwable){""}
            val clickable=try{n.isClickable}catch(_:Throwable){false}
            val enabled=try{n.isEnabled}catch(_:Throwable){false}
            val focusable=try{n.isFocusable}catch(_:Throwable){false}
            val editable=try{n.isEditable}catch(_:Throwable){false}
            val visible=try{n.isVisibleToUser}catch(_:Throwable){false}
            val cc=try{n.childCount}catch(_:Throwable){0}

            val rect=Rect()
            try{n.getBoundsInScreen(rect)}catch(_:Throwable){}

            val actions=try{
                n.actionList.joinToString(","){ a ->
                    val label=try{a.label?.toString().orEmpty()}catch(_:Throwable){""}
                    if(label.isBlank()) a.id.toString() else "${a.id}:${clean(label,60)}"
                }
            }catch(_:Throwable){""}

            val spans=try{
                val sp=textObj as? android.text.Spanned
                if(sp!=null && sp.length>0){
                    sp.getSpans(0,sp.length,Any::class.java)
                        .map{it.javaClass.name.substringAfterLast('.')}
                        .distinct()
                        .joinToString(",")
                }else ""
            }catch(_:Throwable){""}

            val interesting =
                rawText.isNotBlank() ||
                desc.isNotBlank() ||
                clickable ||
                editable ||
                cls.contains("TextView",true) ||
                cls.contains("Button",true) ||
                cls.contains("EditText",true)

            if(interesting){
                emitted++
                out.append("#").append(emitted)
                    .append(" d=").append(depth)
                    .append(" cls=").append(clean(cls,90))
                    .append(" id=").append(clean(id,100))
                    .append(" rect=").append(rect.left).append(",").append(rect.top)
                    .append("-").append(rect.right).append(",").append(rect.bottom)
                    .append(" click=").append(clickable)
                    .append(" enabled=").append(enabled)
                    .append(" focus=").append(focusable)
                    .append(" edit=").append(editable)
                    .append(" visible=").append(visible)
                    .append(" children=").append(cc)
                    .appendLine()
                if(rawText.isNotBlank()) out.append("  text=[").append(clean(rawText)).appendLine("]")
                if(desc.isNotBlank()) out.append("  desc=[").append(clean(desc)).appendLine("]")
                if(actions.isNotBlank()) out.append("  actions=[").append(clean(actions,260)).appendLine("]")
                if(spans.isNotBlank()) out.append("  spans=[").append(clean(spans,220)).appendLine("]")
            }

            for(i in 0 until cc){
                val child=try{n.getChild(i)}catch(_:Throwable){null}
                if(child!=null)q.addLast(child to depth+1)
            }
        }

        out.appendLine()
        out.append("visited=").append(visited)
            .append(" | emitted=").append(emitted)
            .append(" | queueLeft=").append(q.size)

        return out.toString()
    }

'''
if anchor not in s:
    raise SystemExit("v50 waiter anchor missing")
s=s.replace(anchor,helper+anchor,1)

old='''        Prefs.setStatus(this,"TEXT v21: rota truncada detectada, mas o botao Ler mais real nao apareceu em ${rmDescWaitMsV20}ms (${rmDescWaitPollsV20} polls). Nenhuma rota parcial foi enviada.")
'''
new='''        val readMoreDumpV50=try{buildReadMoreTreeDumpV50()}catch(e:Throwable){
            "===== READ MORE TREE DIAG v50 =====\\nERRO: ${e.javaClass.simpleName}: ${e.message ?: "sem detalhes"}"
        }
        Prefs.setSpeedDiagnosticReport(this,readMoreDumpV50)
        Prefs.setStatus(this,"TEXT v21: rota truncada detectada, mas o botao Ler mais real nao apareceu em ${rmDescWaitMsV20}ms (${rmDescWaitPollsV20} polls). Diagnostico v50 salvo abaixo. Nenhuma rota parcial foi enviada.")
'''
if old not in s:
    raise SystemExit("v50 timeout status anchor missing")
s=s.replace(old,new,1)

for m in [
    'private fun buildReadMoreTreeDumpV50()',
    'READ MORE TREE DIAG v50',
    'Prefs.setSpeedDiagnosticReport(this,readMoreDumpV50)',
    '7 to "Mata da Praia"',
    '8 to "Republica"',
]:
    if m not in s:
        raise SystemExit("v50 service verify failed: "+m)

old_priority='''android:text="1. Valparaiso&#10;2. Colina de Laranjeiras&#10;3. Praia da Baleia&#10;4. Morada de Laranjeiras&#10;5. Eurico&#10;6. Manoel Plaza&#10;7. Rosario"'''
new_priority='''android:text="1. Valparaiso&#10;2. Colina de Laranjeiras&#10;3. Praia da Baleia&#10;4. Morada de Laranjeiras&#10;5. Eurico&#10;6. Manoel Plaza&#10;7. Rosario&#10;8. Mata da Praia&#10;9. Republica"'''
if old_priority not in layout:
    raise SystemExit("v50 priority UI anchor missing")
layout=layout.replace(old_priority,new_priority,1)

layout=layout.replace(
    'android:text="Diagnóstico de velocidade da última imagem"',
    'android:text="Diagnóstico técnico / última imagem"',
    1
)

S.write_text(s,encoding="utf-8")
L.write_text(layout,encoding="utf-8")
print("v50 READ MORE TREE DIAG aplicado: comportamento v37 preservado; dump tecnico so apos timeout; 9 bairros na UI")
