package com.lucas.discordlyrics

import android.service.notification.NotificationListenerService

/**
 * Servico vazio de proposito. So existe para o app poder receber "acesso a
 * notificacoes", o que e o que permite ler a sessao de midia ativa via
 * MediaSessionManager.getActiveSessions().
 */
class MediaListenerService : NotificationListenerService()
