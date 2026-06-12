package com.lucas.discordlyrics

import android.content.Context

object Prefs {
    private fun sp(c: Context) = c.getSharedPreferences("cfg", Context.MODE_PRIVATE)

    fun token(c: Context): String = sp(c).getString("token", "") ?: ""
    fun setToken(c: Context, v: String) = sp(c).edit().putString("token", v.trim()).apply()

    fun interval(c: Context): Int = sp(c).getInt("interval", 5).coerceIn(2, 3600)
    fun setInterval(c: Context, v: Int) = sp(c).edit().putInt("interval", v.coerceIn(2, 3600)).apply()
}
