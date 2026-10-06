from app.config import Settings
from app.notifications.sms import WebhookSmsProvider
from app.notifications.telegram import TelegramSender


def build_senders(settings: Settings):
    tg = TelegramSender(settings.telegram_bot_token, settings.telegram_chat_id)
    sms = WebhookSmsProvider(settings.sms_webhook_url, settings.sms_webhook_token, settings.sms_to) if settings.sms_webhook_url else None
    return tg, sms
