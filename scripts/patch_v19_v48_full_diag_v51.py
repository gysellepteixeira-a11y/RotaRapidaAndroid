from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
s=S.read_text(encoding="utf-8")

required=[
    '===== DIAGNOSTICO IMAGEM v19 | V48 EDITOR FAST PATH + V47 CLEAN FAST =====',
    'private fun waitForReadMoreDescV20(startedAt:Long,poll:Int,generation:Long){',
    'TEXT v21: rota truncada detectada, mas o botao Ler mais real nao apareceu em',
    'editorFastV48',
]
for m in required:
    if m not in s:
        raise SystemExit("v51 wrong base: "+m)

anchor='''    private fun waitForReadMoreDescV20(startedAt:Long,poll:Int,generation:Long){
'''
helper=r'''    private fun buildReadMoreTreeDumpV51(): String {
        val root=try{rootInActiveWindow}catch(_:Throwable){null}
            ?: return "===== READ MORE TREE DIAG v51 =====\nrootInActiveWindow=null"

        fun clean(v:String,max:Int=180):String =
            v.replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")
                .replace(Regex("\\s+")," ").trim().take(max)

        val out=StringBuilder()
        out.appendLine("===== READ MORE TREE DIAG v51 | V48 FULL DIAG =====")
        out.appendLine("Base: V48 EDITOR FAST PATH + V47 CLEAN FAST + 9 BAIRROS")
        out.appendLine("Motivo: timeout do no real contentDescription=Ler mais")
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
    raise SystemExit("v51 waiter anchor missing")
s=s.replace(anchor,helper+anchor,1)

old='''        Prefs.setStatus(this,"TEXT v21: rota truncada detectada, mas o botao Ler mais real nao apareceu em ${rmDescWaitMsV20}ms (${rmDescWaitPollsV20} polls). Nenhuma rota parcial foi enviada.")
'''
new='''        val readMoreDumpV51=try{buildReadMoreTreeDumpV51()}catch(e:Throwable){
            "===== READ MORE TREE DIAG v51 =====\\nERRO: ${e.javaClass.simpleName}: ${e.message ?: "sem detalhes"}"
        }
        Prefs.setSpeedDiagnosticReport(this,readMoreDumpV51)
        Prefs.setStatus(this,"TEXT v21: rota truncada detectada, mas o botao Ler mais real nao apareceu em ${rmDescWaitMsV20}ms (${rmDescWaitPollsV20} polls). Diagnostico v51 salvo abaixo. Nenhuma rota parcial foi enviada.")
'''
if old not in s:
    raise SystemExit("v51 timeout status anchor missing")
s=s.replace(old,new,1)

for m in [
    'private fun buildReadMoreTreeDumpV51()',
    'READ MORE TREE DIAG v51 | V48 FULL DIAG',
    'Prefs.setSpeedDiagnosticReport(this,readMoreDumpV51)',
    'editorFastV48',
    '7 to "Mata da Praia"',
    '8 to "Republica"',
]:
    if m not in s:
        raise SystemExit("v51 verify failed: "+m)

S.write_text(s,encoding="utf-8")
print("v51 V48 FULL DIAG aplicado: comportamento v48 preservado; dump tecnico somente apos falha do Ler mais")
