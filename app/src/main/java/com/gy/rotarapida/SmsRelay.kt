package com.gy.rotarapida

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.SystemClock
import android.telephony.SmsManager
import android.util.Log
import androidx.core.content.ContextCompat

/** Envia a mensagem completa via SMS, somente com autorizacao explicita. */
object SmsRelay {
    private const val TAG = "RotaRapidaSMS"
    private const val DEDUP_MS = 30_000L
    private const val FILE = "rota_rapida_sms_relay"

    fun normalizePhone(raw: String): String? {
        val cleaned = raw.trim().replace(Regex("[\\s()\\-]"), "")
        if (!Regex("\\+?[0-9]{10,15}").matches(cleaned)) return null
        return cleaned
    }

    fun sendIfEnabled(context: Context, message: String) {
        if (!Prefs.smsEnabled(context)) return
        val phone = normalizePhone(Prefs.smsPhone(context))
        if (phone == null) {
            Prefs.setSmsStatus(context, "SMS nao enviado: configure o numero do iPhone.")
            return
        }
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.SEND_SMS)
            != PackageManager.PERMISSION_GRANTED) {
            Prefs.setSmsStatus(context, "SMS nao enviado: falta permissao SMS.")
            return
        }

        val prefs = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
        val now = SystemClock.elapsedRealtime()
        val key = "$phone|$message"
        synchronized(this) {
            val last = prefs.getLong("last_time", 0L)
            if (prefs.getString("last_message", "") == key &&
                now >= last && now - last < DEDUP_MS) return
            prefs.edit().putString("last_message", key).putLong("last_time", now).commit()
        }

        try {
            @Suppress("DEPRECATION")
            val manager = SmsManager.getDefault()
            val parts = manager.divideMessage(message)
            if (parts.size > 1) {
                manager.sendMultipartTextMessage(phone, null, parts, null, null)
            } else {
                manager.sendTextMessage(phone, null, message, null, null)
            }
            Prefs.setSmsStatus(context, "Pedido de SMS iniciado (" + parts.size + " parte(s)). Confira o recebimento.")
        } catch (ex: Exception) {
            Log.e(TAG, "Falha ao solicitar envio", ex)
            Prefs.setSmsStatus(context, "Falha SMS: " + ex.javaClass.simpleName)
        }
    }
}
