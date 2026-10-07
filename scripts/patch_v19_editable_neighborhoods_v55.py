from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
P=Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
R=Path("app/src/main/java/com/gy/rotarapida/RouteParser.kt")
A=Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")
L=Path("app/src/main/res/layout/activity_main.xml")

s=S.read_text(encoding="utf-8")
p=P.read_text(encoding="utf-8")
r=R.read_text(encoding="utf-8")
a=A.read_text(encoding="utf-8")
x=L.read_text(encoding="utf-8")

# ------------------------------------------------------------------
# PREFS: persistent ordered neighborhood list.
# ------------------------------------------------------------------
if 'KEY_NEIGHBORHOODS_V55' not in p:
    anchor='    private const val KEY_STATUS = "status"\n'
    if anchor not in p:
        raise SystemExit("v55 prefs status key anchor missing")
    p=p.replace(
        anchor,
        anchor+'    private const val KEY_NEIGHBORHOODS_V55 = "neighborhoods_v55"\n',
        1
    )

    pos=p.rfind('\n}')
    if pos<0:
        raise SystemExit("v55 prefs end missing")

    helper=r'''

    private val DEFAULT_NEIGHBORHOODS_V55 = listOf(
        "Valparaiso",
        "Colina de Laranjeiras",
        "Praia da Baleia",
        "Morada de Laranjeiras",
        "Eurico",
        "Manoel Plaza",
        "Rosario",
        "Mata da Praia",
        "Republica"
    )

    fun defaultNeighborhoods(): List<String> =
        DEFAULT_NEIGHBORHOODS_V55.toList()

    fun neighborhoods(context: Context): List<String> {
        val raw = prefs(context).getString(KEY_NEIGHBORHOODS_V55, null)
        if (raw.isNullOrBlank()) return defaultNeighborhoods()

        return raw
            .split('\u001F')
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .ifEmpty { defaultNeighborhoods() }
    }

    fun setNeighborhoods(context: Context, values: List<String>) {
        val clean = values
            .map {
                it.replace("\u001F", " ")
                    .replace("\n", " ")
                    .replace("\r", " ")
                    .trim()
            }
            .filter { it.isNotBlank() }

        val finalValues = if (clean.isEmpty()) defaultNeighborhoods() else clean
        prefs(context).edit()
            .putString(KEY_NEIGHBORHOODS_V55, finalValues.joinToString("\u001F"))
            .apply()
    }

    fun resetNeighborhoods(context: Context) {
        setNeighborhoods(context, defaultNeighborhoods())
    }
'''
    p=p[:pos]+helper+p[pos:]

# ------------------------------------------------------------------
# ROUTE PARSER: priorities become hot-swappable in memory.
# ------------------------------------------------------------------
start=r.find('    private val priorities = listOf(')
end=r.find('\n\n    private val cageRegex',start)
if start<0 or end<0:
    raise SystemExit("v55 parser priorities block missing")

dynamic=r'''    private val stopTokensV55 = setOf("de", "da", "do", "das", "dos", "e")

    private fun buildPriorityRuleV55(name: String): PriorityRule {
        val normalized = normalize(name)

        // Preserve the tolerant matching already validated in v51/v54 for the
        // default neighborhoods. Custom names use token-prefix matching below.
        val required = when (normalized) {
            "valparaiso" -> listOf("valpar")
            "colina de laranjeiras" -> listOf("colina")
            "praia da baleia" -> listOf("bale")
            "morada de laranjeiras" -> listOf("morada")
            "eurico" -> listOf("euric")
            "manoel plaza" -> listOf("plaza")
            "rosario" -> listOf("rosar")
            "mata da praia" -> listOf("mata", "praia")
            "republica" -> listOf("republic")
            else -> {
                val tokens = normalized
                    .split(" ")
                    .filter { it.isNotBlank() && it !in stopTokensV55 }
                    .map { token ->
                        if (token.length >= 6) token.take(5) else token
                    }
                if (tokens.isEmpty()) listOf(normalized) else tokens
            }
        }

        return PriorityRule(name.trim(), required)
    }

    @Volatile
    private var priorities: List<PriorityRule> = listOf(
        "Valparaiso",
        "Colina de Laranjeiras",
        "Praia da Baleia",
        "Morada de Laranjeiras",
        "Eurico",
        "Manoel Plaza",
        "Rosario",
        "Mata da Praia",
        "Republica"
    ).map(::buildPriorityRuleV55)

    fun configurePriorities(names: List<String>) {
        val clean = names
            .map { it.trim() }
            .filter { it.isNotBlank() }

        if (clean.isNotEmpty()) {
            priorities = clean.map(::buildPriorityRuleV55)
        }
    }

    fun matchPriority(text: String): Pair<Int, String>? =
        priorityFor(text)'''

r=r[:start]+dynamic+r[end:]

# ------------------------------------------------------------------
# IMAGE bairro-first path: use the same dynamic parser priority list.
# ------------------------------------------------------------------
mstart=s.find('    private fun matchBairroFirstPriority(text: String): Pair<Int, String>? {')
mend=s.find('\n    private fun readDenseBairroFirst(',mstart)
if mstart<0 or mend<0:
    raise SystemExit("v55 image priority matcher missing")
replacement='''    private fun matchBairroFirstPriority(text: String): Pair<Int, String>? =
        RouteParser.matchPriority(text)

'''
s=s[:mstart]+replacement+s[mend:]

# ------------------------------------------------------------------
# SERVICE: load once and refresh only when the saved list changes.
# ------------------------------------------------------------------
connect_anchor='''    override fun onServiceConnected() {
        super.onServiceConnected()
'''
if connect_anchor not in s:
    raise SystemExit("v55 service connected anchor missing")
s=s.replace(
    connect_anchor,
    connect_anchor+'        RouteParser.configurePriorities(Prefs.neighborhoods(this))\n',
    1
)

listener_old='''                "floating_overlay_enabled" ->
                    handler.post {
                        if(Prefs.floatingOverlayEnabled(this))
                            showFloatingToggleV52()
                        else
                            removeFloatingToggleV52()
                    }
'''
listener_new='''                "floating_overlay_enabled" ->
                    handler.post {
                        if(Prefs.floatingOverlayEnabled(this))
                            showFloatingToggleV52()
                        else
                            removeFloatingToggleV52()
                    }
                "neighborhoods_v55" ->
                    handler.post {
                        RouteParser.configurePriorities(Prefs.neighborhoods(this))
                    }
'''
if listener_old not in s:
    raise SystemExit("v55 service prefs listener anchor missing")
s=s.replace(listener_old,listener_new,1)

# ------------------------------------------------------------------
# LAYOUT: replace the stale hard-coded priority list with an editor.
# ------------------------------------------------------------------
old_priority='''        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="24dp"
            android:text="Prioridade"
            android:textStyle="bold" />

        <TextView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="6dp"
            android:text="1. Valparaiso&#10;2. Colina de Laranjeiras&#10;3. Praia da Baleia&#10;4. Morada de Laranjeiras&#10;5. Eurico&#10;6. Manoel Plaza&#10;7. Rosario"
            android:textSize="14sp" />
'''
new_priority='''        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="24dp"
            android:text="Bairros / Prioridade"
            android:textStyle="bold" />

        <TextView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="4dp"
            android:text="A ordem define a prioridade. Edite o nome ou use as setas para mover."
            android:textSize="13sp" />

        <LinearLayout
            android:id="@+id/neighborhoodList"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:orientation="vertical" />

        <Button
            android:id="@+id/buttonAddNeighborhood"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:text="+ Adicionar bairro" />

        <Button
            android:id="@+id/buttonSaveNeighborhoods"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="6dp"
            android:text="Salvar bairros" />

        <Button
            android:id="@+id/buttonRestoreNeighborhoods"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="6dp"
            android:text="Restaurar bairros padrão" />
'''
if old_priority not in x:
    raise SystemExit("v55 static priority UI block missing")
x=x.replace(old_priority,new_priority,1)

# ------------------------------------------------------------------
# MAIN ACTIVITY: simple dynamic rows, edit/add/delete/reorder/save.
# ------------------------------------------------------------------
if 'import android.widget.EditText' not in a:
    a=a.replace('import android.widget.Button\n','import android.widget.Button\nimport android.widget.EditText\nimport android.widget.LinearLayout\n',1)
if 'import android.view.ViewGroup' not in a:
    a=a.replace('import android.provider.Settings\n','import android.provider.Settings\nimport android.view.ViewGroup\nimport android.view.Gravity\n',1)

class_anchor='''    private val handler = Handler(Looper.getMainLooper())
    private lateinit var status: TextView
'''
class_insert='''    private val handler = Handler(Looper.getMainLooper())
    private lateinit var status: TextView
    private lateinit var neighborhoodList: LinearLayout
    private val neighborhoodNames = mutableListOf<String>()

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density + 0.5f).toInt()

    private fun captureNeighborhoodRows() {
        neighborhoodNames.clear()
        for (i in 0 until neighborhoodList.childCount) {
            val row = neighborhoodList.getChildAt(i) as? LinearLayout ?: continue
            val edit = row.findViewWithTag<EditText>("name") ?: continue
            neighborhoodNames += edit.text?.toString().orEmpty()
        }
    }

    private fun renderNeighborhoodRows() {
        neighborhoodList.removeAllViews()

        neighborhoodNames.forEachIndexed { index, value ->
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                ).apply { topMargin = dp(4) }
            }

            val number = TextView(this).apply {
                text = "\${index + 1}."
                gravity = Gravity.CENTER
                layoutParams = LinearLayout.LayoutParams(dp(30), dp(48))
            }

            val edit = EditText(this).apply {
                tag = "name"
                setText(value)
                isSingleLine = true
                textSize = 14f
                layoutParams = LinearLayout.LayoutParams(
                    0,
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    1f
                )
            }

            fun smallButton(label: String) = Button(this).apply {
                text = label
                textSize = 14f
                minWidth = 0
                minimumWidth = 0
                setPadding(0, 0, 0, 0)
                layoutParams = LinearLayout.LayoutParams(dp(42), dp(44)).apply {
                    marginStart = dp(3)
                }
            }

            val up = smallButton("↑")
            val down = smallButton("↓")
            val remove = smallButton("×")

            up.isEnabled = index > 0
            down.isEnabled = index < neighborhoodNames.lastIndex

            up.setOnClickListener {
                captureNeighborhoodRows()
                if (index > 0) {
                    val temp = neighborhoodNames[index - 1]
                    neighborhoodNames[index - 1] = neighborhoodNames[index]
                    neighborhoodNames[index] = temp
                    renderNeighborhoodRows()
                }
            }

            down.setOnClickListener {
                captureNeighborhoodRows()
                if (index < neighborhoodNames.lastIndex) {
                    val temp = neighborhoodNames[index + 1]
                    neighborhoodNames[index + 1] = neighborhoodNames[index]
                    neighborhoodNames[index] = temp
                    renderNeighborhoodRows()
                }
            }

            remove.setOnClickListener {
                captureNeighborhoodRows()
                if (index in neighborhoodNames.indices) {
                    neighborhoodNames.removeAt(index)
                    renderNeighborhoodRows()
                }
            }

            row.addView(number)
            row.addView(edit)
            row.addView(up)
            row.addView(down)
            row.addView(remove)
            neighborhoodList.addView(row)
        }
    }

    private fun loadNeighborhoodEditor() {
        neighborhoodNames.clear()
        neighborhoodNames.addAll(Prefs.neighborhoods(this))
        renderNeighborhoodRows()
    }

    private fun saveNeighborhoodEditor() {
        captureNeighborhoodRows()

        val cleaned = neighborhoodNames
            .map { it.trim() }
            .filter { it.isNotBlank() }

        if (cleaned.isEmpty()) {
            Prefs.setStatus(this, "Adicione pelo menos um bairro antes de salvar.")
            return
        }

        val seen = mutableSetOf<String>()
        val unique = mutableListOf<String>()
        for (name in cleaned) {
            val key = RouteParser.normalize(name)
            if (key.isNotBlank() && seen.add(key)) unique += name
        }

        Prefs.setNeighborhoods(this, unique)
        RouteParser.configurePriorities(unique)
        neighborhoodNames.clear()
        neighborhoodNames.addAll(unique)
        renderNeighborhoodRows()
        Prefs.setStatus(
            this,
            "Bairros salvos: \${unique.size}. A ordem atual define a prioridade."
        )
    }
'''
if class_anchor not in a:
    raise SystemExit("v55 MainActivity class field anchor missing")
a=a.replace(class_anchor,class_insert,1)

bind_anchor='''        val accessibility = findViewById<Button>(R.id.buttonAccessibility)
        status = findViewById(R.id.textStatus)
'''
bind_new='''        val accessibility = findViewById<Button>(R.id.buttonAccessibility)
        val addNeighborhood = findViewById<Button>(R.id.buttonAddNeighborhood)
        val saveNeighborhoods = findViewById<Button>(R.id.buttonSaveNeighborhoods)
        val restoreNeighborhoods = findViewById<Button>(R.id.buttonRestoreNeighborhoods)
        neighborhoodList = findViewById(R.id.neighborhoodList)
        status = findViewById(R.id.textStatus)
'''
if bind_anchor not in a:
    raise SystemExit("v55 MainActivity binding anchor missing")
a=a.replace(bind_anchor,bind_new,1)

initial_anchor='''        group.setText(Prefs.groupName(this))
        enabled.isChecked = Prefs.isEnabled(this)
'''
if initial_anchor not in a:
    raise SystemExit("v55 MainActivity initial anchor missing")
a=a.replace(
    initial_anchor,
    initial_anchor+'        loadNeighborhoodEditor()\n',
    1
)

access_anchor='''        accessibility.setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
'''
extra=r'''        addNeighborhood.setOnClickListener {
            captureNeighborhoodRows()
            neighborhoodNames += ""
            renderNeighborhoodRows()
            neighborhoodList.getChildAt(neighborhoodList.childCount - 1)
                ?.findViewWithTag<EditText>("name")
                ?.requestFocus()
        }

        saveNeighborhoods.setOnClickListener {
            saveNeighborhoodEditor()
        }

        restoreNeighborhoods.setOnClickListener {
            neighborhoodNames.clear()
            neighborhoodNames.addAll(Prefs.defaultNeighborhoods())
            renderNeighborhoodRows()
            Prefs.setNeighborhoods(this, neighborhoodNames)
            RouteParser.configurePriorities(neighborhoodNames)
            Prefs.setStatus(this, "Bairros padrão restaurados.")
        }

'''
if access_anchor not in a:
    raise SystemExit("v55 accessibility listener anchor missing")
a=a.replace(access_anchor,extra+access_anchor,1)

blob=s+p+r+a+x
checks=[
    'KEY_NEIGHBORHOODS_V55',
    'fun neighborhoods(context: Context)',
    'fun setNeighborhoods(context: Context',
    '@Volatile\n    private var priorities',
    'fun configurePriorities(names: List<String>)',
    'fun matchPriority(text: String)',
    'RouteParser.matchPriority(text)',
    'RouteParser.configurePriorities(Prefs.neighborhoods(this))',
    '"neighborhoods_v55"',
    'id="@+id/neighborhoodList"',
    'buttonAddNeighborhood',
    'buttonSaveNeighborhoods',
    'buttonRestoreNeighborhoods',
    'private fun renderNeighborhoodRows()',
    'private fun saveNeighborhoodEditor()',
]
for m in checks:
    if m not in blob:
        raise SystemExit("v55 verify failed: "+m)

S.write_text(s,encoding="utf-8")
P.write_text(p,encoding="utf-8")
R.write_text(r,encoding="utf-8")
A.write_text(a,encoding="utf-8")
L.write_text(x,encoding="utf-8")
print("v55 EDITABLE NEIGHBORHOODS aplicado: lista persistente, edit/add/delete/reorder, parser cached in-memory, image/text same priorities")
