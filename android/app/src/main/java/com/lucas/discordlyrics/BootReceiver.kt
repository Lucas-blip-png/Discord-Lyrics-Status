package com.lucas.discordlyrics

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Inicia o LyricsService quando o celular liga, se o usuario ativou na tela. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        val action = intent?.action ?: return
        if (action == Intent.ACTION_BOOT_COMPLETED ||
            action == "android.intent.action.QUICKBOOT_POWERON"
        ) {
            if (Prefs.bootStart(context) && Prefs.token(context).isNotBlank()) {
                try {
                    LyricsService.start(context)
                } catch (e: Exception) {
                    // alguns fabricantes/versoes bloqueiam iniciar no boot;
                    // nesse caso e so abrir o app uma vez.
                }
            }
        }
    }
}
