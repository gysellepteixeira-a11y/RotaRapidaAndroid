"""Patch SMS do iPhone para a build V66.4 MODAL PIXELS TEST.
Executar APOS patch_modal_color_v66_4.py. Nao altera OCR/filtro Modal.
"""
from pathlib import Path

BASE = Path("app/src/main")
MAN = BASE / "AndroidManifest.xml"
S = BASE / "java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt"
P = BASE / "java/com/gy/rotarapida/Prefs.kt"
A = BASE / "java/com/gy/rotarapida/MainActivity.kt"
L = BASE / "res/layout/activity_main.xml"
STR = BASE / "res/values/strings.xml"


def replace_once(src, old, new, name):
    count = src.count(old)
    if count != 1:
        raise RuntimeError("SMS iPhone: marcador " + name + " encontrado " + str(count) + " vez(es)")
    return src.replace(old, new, 1)


manifest = MAN.read_text(encoding="utf-8")
service = S.read_text(encoding="utf-8")
prefs = P.read_text(encoding="utf-8")
activity = A.read_text(encoding="utf-8")
layout = L.read_text(encoding="utf-8")
strings = STR.read_text(encoding="utf-8")

manifest = replace_once(manifest,
    "    <application",
    '    <uses-permission android:name="android.permission.SEND_SMS" />\n\n    <application',
    "manifest")

idx = prefs.rfind("\n}")
if idx < 0:
    raise RuntimeError("Prefs sem fechamento")
prefs = prefs[:idx] + """
    private const val KEY_SMS_ENABLED = "sms_iphone_enabled"
    private const val KEY_SMS_PHONE = "sms_iphone_phone"
    private const val KEY_SMS_STATUS = "sms_iphone_status"

    fun smsEnabled(context: Context): Boolean =
        prefs(context).getBoolean(KEY_SMS_ENABLED, false)

    fun setSmsEnabled(context: Context, enabled: Boolean) {
        prefs(context).edit().putBoolean(KEY_SMS_ENABLED, enabled).apply()
    }

    fun smsPhone(context: Context): String =
        prefs(context).getString(KEY_SMS_PHONE, "")?.trim().orEmpty()

    fun setSmsPhone(context: Context, number: String) {
        prefs(context).edit().putString(KEY_SMS_PHONE, number).apply()
    }

    fun smsStatus(context: Context): String =
        prefs(context).getString(KEY_SMS_STATUS, "SMS ao iPhone desativado.").orEmpty()

    fun setSmsStatus(context: Context, message: String) {
        prefs(context).edit().putString(KEY_SMS_STATUS, message).apply()
    }
""" + prefs[idx:]

end = layout.rfind("    </LinearLayout>")
if end < 0:
    raise RuntimeError("UI sem LinearLayout externo")
layout = layout[:end] + """        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="22dp"
            android:text="SMS para iPhone"
            android:textStyle="bold" />

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:hint="Numero do iPhone (ex.: +5527999999999)">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/editSmsPhone"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:inputType="phone"
                android:singleLine="true" />
        </com.google.android.material.textfield.TextInputLayout>

        <Button
            android:id="@+id/buttonSaveSmsPhone"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="6dp"
            android:text="Salvar numero do iPhone" />

        <androidx.appcompat.widget.SwitchCompat
            android:id="@+id/switchSmsIphone"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="10dp"
            android:text="Enviar SMS alem do WhatsApp" />

        <TextView
            android:id="@+id/textSmsStatus"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:text="SMS ao iPhone desativado."
            android:textSize="13sp" />

""" + layout[end:]

activity = replace_once(activity, "        setContentView(R.layout.activity_main)",
"""        setContentView(R.layout.activity_main)

        val smsPhone = findViewById<TextInputEditText>(R.id.editSmsPhone)
        val smsSave = findViewById<Button>(R.id.buttonSaveSmsPhone)
        val smsToggle = findViewById<SwitchCompat>(R.id.switchSmsIphone)
        val smsStatus = findViewById<TextView>(R.id.textSmsStatus)
        smsPhone.setText(Prefs.smsPhone(this))
        smsStatus.text = Prefs.smsStatus(this)
        smsToggle.isChecked = Prefs.smsEnabled(this)

        smsSave.setOnClickListener {
            val phone = SmsRelay.normalizePhone(smsPhone.text?.toString().orEmpty())
            if (phone == null) {
                Prefs.setSmsStatus(this, "Numero invalido; use DDD, preferencialmente +55.")
            } else {
                Prefs.setSmsPhone(this, phone)
                Prefs.setSmsStatus(this, "Numero do iPhone salvo: " + phone)
            }
            smsStatus.text = Prefs.smsStatus(this)
        }

        smsToggle.setOnCheckedChangeListener { _, checked ->
            if (!checked) {
                Prefs.setSmsEnabled(this, false)
                Prefs.setSmsStatus(this, "Envio por SMS desativado.")
            } else {
                val phone = SmsRelay.normalizePhone(smsPhone.text?.toString().orEmpty())
                if (phone == null) {
                    smsToggle.isChecked = false
                    Prefs.setSmsStatus(this, "Salve o numero do iPhone antes de ativar.")
                } else if (androidx.core.content.ContextCompat.checkSelfPermission(
                        this, android.Manifest.permission.SEND_SMS
                    ) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    smsToggle.isChecked = false
                    androidx.core.app.ActivityCompat.requestPermissions(
                        this, arrayOf(android.Manifest.permission.SEND_SMS), 8101
                    )
                    Prefs.setSmsStatus(this, "Autorize SMS e ative o botao novamente.")
                } else {
                    Prefs.setSmsPhone(this, phone)
                    Prefs.setSmsEnabled(this, true)
                    Prefs.setSmsStatus(this, "SMS ativado para " + phone)
                }
            }
            smsStatus.text = Prefs.smsStatus(this)
        }
""", "MainActivity UI")

activity = replace_once(activity, "\n    override fun onResume() {",
"""
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 8101) {
            val granted = grantResults.isNotEmpty() &&
                grantResults[0] == android.content.pm.PackageManager.PERMISSION_GRANTED
            Prefs.setSmsStatus(this, if (granted)
                "Permissao SMS concedida. Ative o botao novamente."
                else "Permissao SMS recusada. SMS permanece desativado.")
            findViewById<TextView>(R.id.textSmsStatus).text = Prefs.smsStatus(this)
        }
    }

    override fun onResume() {""", "MainActivity permission")

service = replace_once(service,
    "    private fun markSent(route: RouteResult) {",
    """    private fun markSent(route: RouteResult) {
        SmsRelay.sendIfEnabled(this, buildMessage(route.cage))""",
    "post-send route confirmation")

for marker in ["ModalFilter.filter(", "private fun sendRouteInCurrentChat(route: RouteResult)",
               "private fun buildMessage(cage: String)", "R.id.switchIncludeFake"]:
    if marker not in service + activity:
        raise RuntimeError("Base V66.4 com modal nao encontrada: " + marker)

strings = strings.replace("Rota Rápida (TESTE MODAL 2)",
                          "Rota Rápida (MODAL + SMS iPhone)")

for path, data in [(MAN, manifest), (S, service), (P, prefs),
                   (A, activity), (L, layout), (STR, strings)]:
    path.write_text(data, encoding="utf-8")
print("SMS opt-in incorporado; OCR, modal e WhatsApp preservados")
