package com.gy.rotarapida

import android.content.Context

object Prefs {
    private const val FILE = "rota_rapida"
    private const val KEY_ENABLED = "enabled"
    private const val KEY_GROUP = "group"
    private const val KEY_STATUS = "status"

    private fun prefs(context: Context) =
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE)

    fun isEnabled(context: Context): Boolean =
        prefs(context).getBoolean(KEY_ENABLED, false)

    fun setEnabled(context: Context, value: Boolean) {
        prefs(context).edit().putBoolean(KEY_ENABLED, value).apply()
    }

    fun groupName(context: Context): String =
        prefs(context).getString(KEY_GROUP, "")?.trim().orEmpty()

    fun setGroupName(context: Context, value: String) {
        prefs(context).edit().putString(KEY_GROUP, value.trim()).apply()
    }

    fun status(context: Context): String =
        prefs(context).getString(KEY_STATUS, "Aguardando configuração.").orEmpty()

    fun setStatus(context: Context, value: String) {
        prefs(context).edit().putString(KEY_STATUS, value).apply()
    }
}
