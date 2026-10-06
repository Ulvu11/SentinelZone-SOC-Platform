from dataclasses import dataclass

ROLES = ("viewer", "analyst", "operator", "admin")

PERMISSIONS = {
    "viewer": {"read"},
    "analyst": {"read", "investigate", "replay"},
    "operator": {"read", "investigate", "transition", "merge", "hunt", "approve", "replay"},
    "admin": {"read", "investigate", "transition", "merge", "hunt", "approve", "admin", "replay"},
}


@dataclass(frozen=True)
class Principal:
    name: str
    role: str
    tenant_id: str = "lab"

    def can(self, perm: str) -> bool:
        return perm in PERMISSIONS.get(self.role, set())  # default DENY
