package com.lucas.discordlyrics

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.media.MediaMetadata
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/** Servico em primeiro plano: le a musica tocando, busca a letra e atualiza o Discord. */
class LyricsService : Service() {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var job: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(1, buildNotification())
        if (job == null) job = scope.launch { loop() }
        return START_STICKY
    }

    override fun onDestroy() {
        job?.cancel()
        val token = Prefs.token(this)
        if (token.isNotBlank()) Net.updateStatus(token, null)
        super.onDestroy()
    }

    private suspend fun loop() {
        val token = Prefs.token(this)
        val minIntervalMs = Prefs.interval(this) * 1000L
        val msm = getSystemService(Context.MEDIA_SESSION_SERVICE) as MediaSessionManager
        val comp = ComponentName(this, MediaListenerService::class.java)

        var currentSong = ""
        var lines: List<Net.Line> = emptyList()
        var sent: String? = null
        var lastSent = 0L

        while (scope.isActive) {
            var desired: String? = null
            try {
                val controllers = msm.getActiveSessions(comp)
                val ctrl = controllers.firstOrNull {
                    it.playbackState?.state == PlaybackState.STATE_PLAYING
                }
                if (ctrl != null) {
                    val md = ctrl.metadata
                    val title = md?.getString(MediaMetadata.METADATA_KEY_TITLE).orEmpty()
                    val artist = md?.getString(MediaMetadata.METADATA_KEY_ARTIST).orEmpty()
                    val pos = (ctrl.playbackState?.position ?: 0L) / 1000.0
                    val song = "$title|$artist"
                    if (song != currentSong) {
                        currentSong = song
                        lines = Net.fetchLyrics(title, artist)
                    }
                    var active: String? = null
                    for (l in lines) {
                        if (l.time <= pos + 0.5) active = l.text else break
                    }
                    desired = if (!active.isNullOrBlank()) {
                        "🎵 $active"
                    } else {
                        ("🎵 $title - $artist").take(100)
                    }
                }
            } catch (e: SecurityException) {
                // falta o "acesso a notificacoes" -> nao da pra ler a midia
            } catch (e: Exception) {
                // ignora e tenta de novo
            }

            val now = System.currentTimeMillis()
            if (desired != sent && now - lastSent >= minIntervalMs) {
                sent = desired
                lastSent = now
                if (token.isNotBlank()) Net.updateStatus(token, desired)
            }
            delay(1000)
        }
    }

    private fun buildNotification(): Notification {
        val ch = "lyrics"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(ch, "Discord Lyrics", NotificationManager.IMPORTANCE_LOW)
            (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).createNotificationChannel(channel)
        }
        return NotificationCompat.Builder(this, ch)
            .setContentTitle("Discord Lyrics")
            .setContentText("Sincronizando a letra com o seu status")
            .setSmallIcon(R.drawable.ic_note)
            .setOngoing(true)
            .build()
    }

    companion object {
        fun start(ctx: Context) {
            val i = Intent(ctx, LyricsService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) ctx.startForegroundService(i)
            else ctx.startService(i)
        }

        fun stop(ctx: Context) {
            ctx.stopService(Intent(ctx, LyricsService::class.java))
        }
    }
}
