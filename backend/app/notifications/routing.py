ROUTES = {
    "low": ["dashboard"],
    "medium": ["dashboard"],
    "high": ["dashboard", "telegram"],
    "critical": ["dashboard", "telegram", "sms"],
}


def channels_for(priority: str) -> list[str]:
    return ROUTES.get(priority, ["dashboard"])
