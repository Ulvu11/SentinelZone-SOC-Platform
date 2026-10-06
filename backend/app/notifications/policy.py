"""Single delivery policy reused at enqueue and immediately before dispatch."""
def suppression_reason(settings, incident, channel, current_tenant):
    if incident is None or incident.tenant_id != current_tenant:
        return "POLICY_DENIED"
    if incident.execution_mode == "REPLAY":
        return "POLICY_DENIED"
    if channel == "dashboard":
        return None
    if current_tenant != (settings.notification_tenant_id or settings.default_tenant_id):
        return "POLICY_DENIED"
    if incident.execution_mode == "TEST":
        # Explicit separate test destination; SMS is never a lab delivery channel.
        if (not settings.allow_test_notifications or channel != "telegram" or not settings.test_telegram_chat_id
                or settings.test_telegram_chat_id == settings.telegram_chat_id):
            return "POLICY_DENIED"
    if channel == "telegram":
        if not settings.telegram_enabled:
            return "CHANNEL_DISABLED"
        if settings.legacy_telegram_active:
            return "LEGACY_NOTIFIER_ACTIVE"
        if settings.telegram_canary_enabled and incident.host_id not in {
            h.strip() for h in settings.telegram_canary_hosts.split(",") if h.strip()
        }:
            return "POLICY_DENIED"
    elif channel == "sms":
        if not settings.sms_enabled:
            return "CHANNEL_DISABLED"
    else:
        return "POLICY_DENIED"
    return None
