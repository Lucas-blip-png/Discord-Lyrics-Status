package com.lucas.discordlyrics

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLEncoder

object Net {
    private val client = OkHttpClient()
    private val JSON = "application/json".toMediaType()

    data class Line(val time: Double, val text: String)

    fun parseLrc(lrc: String?): List<Line> {
        if (lrc.isNullOrBlank()) return emptyList()
        val re = Regex("""\[(\d+):(\d+(?:\.\d+)?)]\s*(.*)""")
        val out = ArrayList<Line>()
        for (line in lrc.lines()) {
            val m = re.find(line) ?: continue
            val mm = m.groupValues[1].toIntOrNull() ?: continue
            val ss = m.groupValues[2].toDoubleOrNull() ?: continue
            out.add(Line(mm * 60 + ss, m.groupValues[3].trim()))
        }
        out.sortBy { it.time }
        return out
    }

    /** Busca a letra sincronizada no lrclib.net. Lista vazia se nao achar. */
    fun fetchLyrics(title: String, artist: String): List<Line> {
        return try {
            val q = URLEncoder.encode("$title $artist", "UTF-8")
            val req = Request.Builder()
                .url("https://lrclib.net/api/search?q=$q")
                .header("User-Agent", "DiscordLyricsAndroid (github.com/Lucas-blip-png)")
                .build()
            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) return emptyList()
                val arr = JSONArray(resp.body?.string() ?: "[]")
                for (i in 0 until arr.length()) {
                    val synced = arr.getJSONObject(i).optString("syncedLyrics", "")
                    if (synced.isNotBlank()) return parseLrc(synced)
                }
                emptyList()
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    /** Atualiza (ou limpa, com text=null) o status customizado do Discord. */
    fun updateStatus(token: String, text: String?) {
        try {
            val custom: Any = if (text != null) JSONObject().put("text", text) else JSONObject.NULL
            val body = JSONObject().put("custom_status", custom).toString()
            val req = Request.Builder()
                .url("https://discord.com/api/v9/users/@me/settings")
                .patch(body.toRequestBody(JSON))
                .header("authorization", token)
                .header("content-type", "application/json")
                .build()
            client.newCall(req).execute().use { }
        } catch (e: Exception) {
        }
    }
}
