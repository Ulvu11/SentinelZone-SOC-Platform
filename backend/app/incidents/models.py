TRANSITIONS = {
    "NEW": {"INVESTIGATING"},
    "INVESTIGATING": {"CONTAINED"},
    "CONTAINED": {"RESOLVED"},
    "RESOLVED": {"CLOSED"},
    "CLOSED": set(),
}
STATUSES = list(TRANSITIONS)


class NotFound(Exception):
    pass


class Conflict(Exception):
    def __init__(self, message: str, current_version: int | None = None):
        super().__init__(message)
        self.current_version = current_version


def parse_incident_id(raw: str) -> int:
    s = raw.upper().removeprefix("SZ-")
    if not s.isdigit():
        raise NotFound(raw)
    return int(s)
