from pathlib import Path

S=Path("app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt")
P=Path("app/src/main/java/com/gy/rotarapida/Prefs.kt")
A=Path("app/src/main/java/com/gy/rotarapida/MainActivity.kt")
L=Path("app/src/main/res/layout/activity_main.xml")

s=S.read_text(encoding="utf-8")
p=P.read_text(encoding="utf-8")
a=A.read_text(encoding="utf-8")
x=L.read_text(encoding="utf-8")

if 'KEY_MESSAGE_NAME_V56' not in p:
    anchor='    private const val KEY_NEIGHBORHOODS_V55 = "neighborhoods_v55"\n'
    if anchor not in p:
        raise SystemExit("v56 prefs anchor missing")

    p=p.replace(
        anchor,
        anchor+
        '    private const val KEY_MESSAGE_NAME_V56 = "message_name_v56"\n'
        '    private const val KEY_MESSAGE_ID_V56 = "message_id_v56"\n'
        '    private const val KEY_MESSAGE_MODAL_V56 = "message_modal_v56"\n',
        1
    )

    insert_pos=p.rfind('\n}')
    if insert_pos<0:
        raise SystemExit("v56 prefs end missing")

    helper=r'''

    fun messageName(context: Context): String =
        prefs(context).getString(
            KEY_MESSAGE_NAME_V56,
            "Felipe lima de Castilho"
        )?.trim().orEmpty().ifBlank { "Felipe lima de Castilho" }

    fun messageId(context: Context): String =
        prefs(context).getString(
            KEY_MESSAGE_ID_V56,
            "1347515"
        )?.trim().orEmpty().ifBlank { "1347515" }

    fun messageModal(context: Context): String =
        prefs(context).getString(
            KEY_MESSAGE_MODAL_V56,
            "Passeio"
        )?.trim().orEmpty().ifBlank { "Passeio" }

    fun setMessageProfile(
        context: Context,
        name: String,
        id: String,
        modal: String
    ) {
        fun clean(value: String): String =
            value
                .replace("\n", " ")
                .replace("\r", " ")
                .trim()

        prefs(context).edit()
            .putString(KEY_MESSAGE_NAME_V56, clean(name))
            .putString(KEY_MESSAGE_ID_V56, clean(id))
            .putString(KEY_MESSAGE_MODAL_V56, clean(modal))
            .apply()
    }
'''
    p=p[:insert_pos]+helper+p[insert_pos:]

state_anchor='''    private var floatingWindowManagerV52: android.view.WindowManager? = null

    private val floatingPrefsV52 by lazy {
'''
if state_anchor not in s:
    raise SystemExit("v56 service state anchor missing")

state_new='''    private var floatingWindowManagerV52: android.view.WindowManager? = null

    @Volatile private var messageNameV56 = "Felipe lima de Castilho"
    @Volatile private var messageIdV56 = "1347515"
    @Volatile private var messageModalV56 = "Passeio"

    private fun refreshMessageProfileV56() {
        messageNameV56 = Prefs.messageName(this)
        messageIdV56 = Prefs.messageId(this)
        messageModalV56 = Prefs.messageModal(this)
    }

    private val floatingPrefsV52 by lazy {
'''
s=s.replace(state_anchor,state_new,1)

listener_anchor='''                "neighborhoods_v55" ->
                    handler.post {
                        RouteParser.configurePriorities(Prefs.neighborhoods(this))
                    }
'''
listener_new='''                "neighborhoods_v55" ->
                    handler.post {
                        RouteParser.configurePriorities(Prefs.neighborhoods(this))
                    }
                "message_name_v56", "message_id_v56", "message_modal_v56" ->
                    handler.post { refreshMessageProfileV56() }
'''
if listener_anchor not in s:
    raise SystemExit("v56 service prefs listener anchor missing")
s=s.replace(listener_anchor,listener_new,1)

connect_anchor='''    override fun onServiceConnected() {
        super.onServiceConnected()
        RouteParser.configurePriorities(Prefs.neighborhoods(this))
'''
connect_new='''    override fun onServiceConnected() {
        super.onServiceConnected()
        RouteParser.configurePriorities(Prefs.neighborhoods(this))
        refreshMessageProfileV56()
'''
if connect_anchor not in s:
    raise SystemExit("v56 service connected anchor missing")
s=s.replace(connect_anchor,connect_new,1)

old_message='''    private fun buildMessage(cage: String): String =
        """
        Felipe lima de Castilho
        1347515
        Passeio
        Gaiola: $cage
        """.trimIndent()
'''
new_message='''    private fun buildMessage(cage: String): String =
        "Nome: $messageNameV56\\n" +
            "ID: $messageIdV56\\n" +
            "Modal: $messageModalV56\\n" +
            "Gaiola: $cage"
'''
if old_message not in s:
    raise SystemExit("v56 buildMessage anchor missing")
s=s.replace(old_message,new_message,1)

layout_anchor='''        <Button
            android:id="@+id/buttonRestoreNeighborhoods"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="6dp"
            android:text="Restaurar bairros padrão" />

        <TextView
            android:id="@+id/textLastMessage"
'''
layout_insert='''        <Button
            android:id="@+id/buttonRestoreNeighborhoods"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="6dp"
            android:text="Restaurar bairros padrão" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="24dp"
            android:text="Mensagem"
            android:textStyle="bold" />

        <TextView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="4dp"
            android:text="Nome, ID e Modal são editáveis. A Gaiola é preenchida automaticamente."
            android:textSize="13sp" />

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="10dp"
            android:hint="Nome">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/editMessageName"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:singleLine="true" />
        </com.google.android.material.textfield.TextInputLayout>

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="6dp"
            android:hint="ID">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/editMessageId"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:singleLine="true" />
        </com.google.android.material.textfield.TextInputLayout>

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="6dp"
            android:hint="Modal">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/editMessageModal"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:singleLine="true" />
        </com.google.android.material.textfield.TextInputLayout>

        <Button
            android:id="@+id/buttonSaveMessage"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:text="Salvar mensagem" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="12dp"
            android:text="Prévia"
            android:textStyle="bold" />

        <TextView
            android:id="@+id/textMessagePreview"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="4dp"
            android:text="Nome:&#10;ID:&#10;Modal:&#10;Gaiola: [automática]"
            android:textIsSelectable="true"
            android:textSize="14sp" />

        <TextView
            android:id="@+id/textLastMessage"
'''
if layout_anchor not in x:
    raise SystemExit("v56 layout anchor missing")
x=x.replace(layout_anchor,layout_insert,1)

if 'import android.text.TextWatcher' not in a:
    a=a.replace(
        'import android.provider.Settings\n',
        'import android.provider.Settings\nimport android.text.Editable\nimport android.text.TextWatcher\n',
        1
    )

bind_anchor='''        val restoreNeighborhoods = findViewById<Button>(R.id.buttonRestoreNeighborhoods)
        neighborhoodList = findViewById(R.id.neighborhoodList)
        status = findViewById(R.id.textStatus)
'''
bind_new='''        val restoreNeighborhoods = findViewById<Button>(R.id.buttonRestoreNeighborhoods)
        val messageName = findViewById<TextInputEditText>(R.id.editMessageName)
        val messageId = findViewById<TextInputEditText>(R.id.editMessageId)
        val messageModal = findViewById<TextInputEditText>(R.id.editMessageModal)
        val saveMessage = findViewById<Button>(R.id.buttonSaveMessage)
        val messagePreview = findViewById<TextView>(R.id.textMessagePreview)
        neighborhoodList = findViewById(R.id.neighborhoodList)
        status = findViewById(R.id.textStatus)
'''
if bind_anchor not in a:
    raise SystemExit("v56 MainActivity binding anchor missing")
a=a.replace(bind_anchor,bind_new,1)

init_anchor='''        enabled.isChecked = Prefs.isEnabled(this)
        loadNeighborhoodEditor()
        floatingOverlay.isChecked = Prefs.floatingOverlayEnabled(this)
'''
init_new='''        enabled.isChecked = Prefs.isEnabled(this)
        loadNeighborhoodEditor()
        floatingOverlay.isChecked = Prefs.floatingOverlayEnabled(this)
        messageName.setText(Prefs.messageName(this))
        messageId.setText(Prefs.messageId(this))
        messageModal.setText(Prefs.messageModal(this))

        fun updateMessagePreview() {
            messagePreview.text =
                "Nome: ${messageName.text?.toString().orEmpty()}\\n" +
                    "ID: ${messageId.text?.toString().orEmpty()}\\n" +
                    "Modal: ${messageModal.text?.toString().orEmpty()}\\n" +
                    "Gaiola: [automática]"
        }

        val messageWatcher = object : TextWatcher {
            override fun beforeTextChanged(
                s: CharSequence?,
                start: Int,
                count: Int,
                after: Int
            ) = Unit

            override fun onTextChanged(
                s: CharSequence?,
                start: Int,
                before: Int,
                count: Int
            ) = updateMessagePreview()

            override fun afterTextChanged(s: Editable?) = Unit
        }

        messageName.addTextChangedListener(messageWatcher)
        messageId.addTextChangedListener(messageWatcher)
        messageModal.addTextChangedListener(messageWatcher)
        updateMessagePreview()
'''
if init_anchor not in a:
    raise SystemExit("v56 MainActivity init anchor missing")
a=a.replace(init_anchor,init_new,1)

listener_anchor='''        restoreNeighborhoods.setOnClickListener {
            neighborhoodNames.clear()
            neighborhoodNames.addAll(Prefs.defaultNeighborhoods())
            renderNeighborhoodRows()
            Prefs.setNeighborhoods(this, neighborhoodNames)
            RouteParser.configurePriorities(neighborhoodNames)
            Prefs.setStatus(this, "Bairros padrão restaurados.")
        }

        accessibility.setOnClickListener {
'''
listener_new='''        restoreNeighborhoods.setOnClickListener {
            neighborhoodNames.clear()
            neighborhoodNames.addAll(Prefs.defaultNeighborhoods())
            renderNeighborhoodRows()
            Prefs.setNeighborhoods(this, neighborhoodNames)
            RouteParser.configurePriorities(neighborhoodNames)
            Prefs.setStatus(this, "Bairros padrão restaurados.")
        }

        saveMessage.setOnClickListener {
            val name = messageName.text?.toString().orEmpty().trim()
            val id = messageId.text?.toString().orEmpty().trim()
            val modal = messageModal.text?.toString().orEmpty().trim()

            if (name.isBlank() || id.isBlank() || modal.isBlank()) {
                Prefs.setStatus(
                    this,
                    "Preencha Nome, ID e Modal antes de salvar a mensagem."
                )
            } else {
                Prefs.setMessageProfile(this, name, id, modal)
                updateMessagePreview()
                Prefs.setStatus(this, "Mensagem salva.")
            }
        }

        accessibility.setOnClickListener {
'''
if listener_anchor not in a:
    raise SystemExit("v56 MainActivity listener anchor missing")
a=a.replace(listener_anchor,listener_new,1)

blob=s+p+a+x
checks=[
    'KEY_MESSAGE_NAME_V56',
    'fun setMessageProfile(',
    'messageNameV56',
    'refreshMessageProfileV56()',
    '"message_name_v56", "message_id_v56", "message_modal_v56"',
    '"Nome: $messageNameV56\\\\n"',
    'id="@+id/editMessageName"',
    'id="@+id/editMessageId"',
    'id="@+id/editMessageModal"',
    'id="@+id/buttonSaveMessage"',
    'id="@+id/textMessagePreview"',
    'fun updateMessagePreview()',
    'Prefs.setMessageProfile(this, name, id, modal)',
]
for m in checks:
    if m not in blob:
        raise SystemExit("v56 verify failed: "+m)

S.write_text(s,encoding="utf-8")
P.write_text(p,encoding="utf-8")
A.write_text(a,encoding="utf-8")
L.write_text(x,encoding="utf-8")
print("v56 EDITABLE MESSAGE aplicado: Nome/ID/Modal editáveis, Gaiola automática, cache em memória, prévia ao vivo")
