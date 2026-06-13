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

    private val NOISE = Regex(
        "(official|videoclip|video|audio|lyric|lyrics|letra|legendado|legenda|" +
            "m/?v|\\bhd\\b|\\bhq\\b|\\b4k\\b|\\b8k\\b|visuali[sz]er|explicit|" +
            "remaster(ed)?|color\\s*coded|nightcore|slowed|reverb|sped\\s*up|" +
            "extended\\s*mix|free\\s*download|download|prod\\.?)",
        RegexOption.IGNORE_CASE,
    )

    private fun stripNoiseBrackets(s: String): String {
        var t = s
        for (p in listOf("\\([^()]*\\)", "\\[[^\\[\\]]*\\]", "【[^】]*】")) {
            t = Regex(p).replace(t) { m -> if (NOISE.containsMatchIn(m.value)) "" else m.value }
        }
        return t
    }

    /** Limpa titulo/artista (YouTube etc.) para melhorar a busca da letra. */
    fun clean(title: String, artist: String): Pair<String, String> {
        val trimChars = charArrayOf(' ', '-', '–', '—', '\'', '"')
        var t = stripNoiseBrackets(title)
        t = t.replace(Regex("\\b(feat\\.?|ft\\.?|featuring)\\b.*$", RegexOption.IGNORE_CASE), "")
        t = t.replace(Regex("\\s*\\|.*$"), "")
        t = t.replace(
            Regex(
                "\\s*\\b(official|music|lyric|lyrics|video|audio|mv|visualizer|hd|hq|4k)\\b" +
                    "(\\s+\\b(official|music|lyric|lyrics|video|audio|mv|visualizer|hd|hq|4k)\\b)*\\s*$",
                RegexOption.IGNORE_CASE,
            ),
            "",
        )
        var a = artist.replace(Regex("\\s*-\\s*topic\\s*$", RegexOption.IGNORE_CASE), "")
        a = a.replace(Regex("\\b(vevo|official)\\b", RegexOption.IGNORE_CASE), "")
        t = t.replace(Regex("\\s+"), " ").trim(*trimChars)
        if (t.contains(" - ")) {
            val parts = t.split(" - ", limit = 2)
            val l = parts[0].trim()
            val r = parts.getOrElse(1) { "" }.trim()
            if (l.isNotEmpty() && r.isNotEmpty()) {
                a = l
                t = r
            }
        }
        t = t.trim(*trimChars)
        a = a.replace(Regex("\\s+"), " ").trim(*trimChars)
        return Pair(t, a)
    }

    /** Busca a letra sincronizada no lrclib.net. Lista vazia se nao achar. */
    fun fetchLyrics(title: String, artist: String): List<Line> {
        return try {
            val (t, a) = clean(title, artist)
            val q = URLEncoder.encode("$t $a".trim(), "UTF-8")
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
