package com.lucas.discordlyrics

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Android 13+: permissao para mostrar a notificacao do servico
        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 1)
        }

        val token = findViewById<EditText>(R.id.token)
        val interval = findViewById<EditText>(R.id.interval)
        token.setText(Prefs.token(this))
        interval.setText(Prefs.interval(this).toString())

        findViewById<Button>(R.id.grant).setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }

        findViewById<Button>(R.id.start).setOnClickListener {
            Prefs.setToken(this, token.text.toString())
            Prefs.setInterval(this, interval.text.toString().toIntOrNull() ?: 5)
            if (Prefs.token(this).isBlank()) {
                Toast.makeText(this, "Cole o token primeiro", Toast.LENGTH_SHORT).show()
            } else {
                LyricsService.start(this)
                Toast.makeText(this, "Iniciado", Toast.LENGTH_SHORT).show()
            }
        }

        findViewById<Button>(R.id.stop).setOnClickListener {
            LyricsService.stop(this)
            Toast.makeText(this, "Parado", Toast.LENGTH_SHORT).show()
        }
    }
}
