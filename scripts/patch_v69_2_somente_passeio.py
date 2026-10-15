from pathlib import Path
S=Path('app/src/main/java/com/gy/rotarapida/WhatsRouteAccessibilityService.kt')
B=Path('app/src/main/java/com/gy/rotarapida/RyzenOcrBridgeV68.kt')
P=Path('app/src/main/java/com/gy/rotarapida/Prefs.kt')
M=Path('app/src/main/java/com/gy/rotarapida/MainActivity.kt')
def once(s,old,new,label):
    n=s.count(old)
    if n!=1:raise SystemExit('v69.2 '+label+': '+str(n))
    return s.replace(old,new,1)
s=S.read_text(encoding='utf-8')
s=once(s,'    private fun readMediaOriginal(media: MediaImage) {','''    private var authorizedPasseioKeyV692: String? = null
    private fun passeioKeyV692(route: RouteResult): String =
        RouteParser.normalize(route.neighborhood) + "|" + route.cage.trim().uppercase(java.util.Locale.ROOT)
    private fun readMediaOriginal(media: MediaImage) {''','field')
s=once(s,'RyzenOcrBridgeV68.reconhecer(jpg, Prefs.neighborhoods(this))',
       'RyzenOcrBridgeV68.reconhecer(jpg, Prefs.neighborhoods(this), Prefs.onlyPasseioV692(this))','bridge')
s=once(s,'''        if (!Prefs.pcOcrEnabledV68(this)) {
            readMediaLocalV68(media)
            return
        }''','''        if (!Prefs.pcOcrEnabledV68(this)) {
            if (Prefs.onlyPasseioV692(this)) {
                finishFileOnlyFailure("Somente PASSEIO exige OCR Ryzen USB ativo; nao enviei.")
            } else {
                readMediaLocalV68(media)
            }
            return
        }''','no PC')
s=once(s,'''                    if (resultado == null) {
                        Prefs.setStatus(this, "Ryzen offline/sem resultado; usando OCR local v66.")
                        readMediaLocalV68(media)
                        return@post
                    }''','''                    if (resultado == null) {
                        if (Prefs.onlyPasseioV692(this)) {
                            finishFileOnlyFailure("Modal PASSEIO nao confirmado pelo Ryzen; nao enviei.")
                        } else {
                            Prefs.setStatus(this, "Ryzen offline/sem resultado; usando OCR local v66.")
                            readMediaLocalV68(media)
                        }
                        return@post
                    }''','result absent')
s=once(s,'''                    sendRouteInCurrentChat(rotas.first())''','''                    if (Prefs.onlyPasseioV692(this)) {
                        authorizedPasseioKeyV692 = passeioKeyV692(rotas.first())
                    }
                    sendRouteInCurrentChat(rotas.first())''','authorize')
s=once(s,'''        } catch (_: Throwable) {
            readMediaLocalV68(media)
        }
    }

    private fun readMediaLocalV68(media: MediaImage)''','''        } catch (_: Throwable) {
            if (Prefs.onlyPasseioV692(this)) {
                finishFileOnlyFailure("Falha USB; Modal nao confirmado; nao enviei.")
            } else {
                readMediaLocalV68(media)
            }
        }
    }

    private fun readMediaLocalV68(media: MediaImage)''','executor fail')
s=once(s,'''    private fun sendRouteInCurrentChat(route: RouteResult) {''','''    private fun sendRouteInCurrentChat(route: RouteResult) {
        // Sem Modal confirmado, inclusive rota de texto, NAO enviar.
        if (Prefs.onlyPasseioV692(this) &&
            passeioKeyV692(route) != authorizedPasseioKeyV692) {
            finishFileOnlyFailure("Somente PASSEIO: modalidade nao confirmada; nao enviei.")
            return
        }''','global gate')
s=once(s,'''    private fun markSent(route: RouteResult) {''','''    private fun markSent(route: RouteResult) {
        authorizedPasseioKeyV692 = null''','reset')
S.write_text(s,encoding='utf-8')
p=P.read_text(encoding='utf-8')
p=once(p,'object Prefs {','''object Prefs {
    fun onlyPasseioV692(context: Context): Boolean =
        context.getSharedPreferences("rota_rapida", Context.MODE_PRIVATE)
            .getBoolean("somente_passeio_v692", false)
    fun setOnlyPasseioV692(context: Context, value: Boolean) {
        context.getSharedPreferences("rota_rapida", Context.MODE_PRIVATE)
            .edit().putBoolean("somente_passeio_v692", value).apply()
    }
''','prefs')
P.write_text(p,encoding='utf-8')
m=M.read_text(encoding='utf-8')
old='''        (enabled.parent as? android.view.ViewGroup)?.let { parent ->
            val at = parent.indexOfChild(enabled)
            if (at >= 0) parent.addView(pcSwitchV68, at + 1)
        }'''
new='''        val onlyPasseioV692 = SwitchCompat(this)
        onlyPasseioV692.text = "Somente PASSEIO (ignora FAKE VOLUMOSO)"
        onlyPasseioV692.isChecked = Prefs.onlyPasseioV692(this)
        onlyPasseioV692.setOnCheckedChangeListener { _, checked ->
            Prefs.setOnlyPasseioV692(this, checked)
            Prefs.setStatus(this,
                if (checked) "Somente PASSEIO: nao envia sem confirmar Modal no Ryzen."
                else "Qualquer modalidade: comportamento anterior restaurado.")
        }
        (enabled.parent as? android.view.ViewGroup)?.let { parent ->
            val at = parent.indexOfChild(enabled)
            if (at >= 0) {
                parent.addView(pcSwitchV68, at + 1)
                parent.addView(onlyPasseioV692, at + 2)
            }
        }'''
m=once(m,old,new,'switch')
M.write_text(m,encoding='utf-8')
b=B.read_text(encoding='utf-8')
b=once(b,'''    fun reconhecer(jpg: ByteArray, ordemBairros: List<String>): Result? {''',
       '''    fun reconhecer(jpg: ByteArray, ordemBairros: List<String>, somentePasseio: Boolean): Result? {''','signature')
b=once(b,'''.put("prioridades", JSONArray(ordemBairros))''',
       '''.put("prioridades", JSONArray(ordemBairros))
                    .put("somente_passeio", somentePasseio)''','meta')
b=once(b,'''                if (result.optString("estado") != "OK") return null''',
       '''                if (result.optString("estado") != "OK") return null
                if (somentePasseio && result.optString("modal") != "PASSEIO") return null''','modal verified')
B.write_text(b,encoding='utf-8')
print('V69.2: filtro modal no APK e falhas bloqueadas')
