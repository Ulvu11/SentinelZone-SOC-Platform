from functools import lru_cache
from pathlib import Path

import json
import re
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class ProductionConfigError(ValueError):
    """Sanitized startup configuration error; never includes secret values."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    app_env: str = "development"
    debug: bool = False
    allow_fixtures: bool = False
    enable_legacy_mock_routes: bool = False
    default_tenant_id: str = Field(default="lab", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    auth_db_enabled: bool = True
    cors_allow_credentials: bool = True
    allow_test_notifications: bool = False
    # External delivery is restricted to this tenant; shared credentials never serve other tenants.
    notification_tenant_id: str = ""
    test_telegram_chat_id: str = ""
    sensor_expected_intervals: str = "{}"  # JSON: sensor -> expected heartbeat seconds
    sensor_offline_multiplier: int = Field(default=3, ge=2)
    ingest_overlap_seconds: int = Field(default=120, ge=0)
    max_ingest_events: int = Field(default=10000, ge=1, le=100000)
    notification_template_version: str = "1"
    database_url: str = f"sqlite:///{ROOT}/sentinelzone-dev.db"
    auth_tokens: str = ""
    cors_origins: str = "http://localhost:3000"
    fixtures_dir: str = str(ROOT / "fixtures")

    splunk_url: str = ""
    splunk_token: str = ""
    splunk_ca_file: str = ""
    splunk_index: str = "main"
    splunk_bootstrap_hours: int = Field(default=24, ge=1, le=720)
    wazuh_url: str = ""
    wazuh_username: str = ""
    wazuh_password: str = ""
    wazuh_ca_file: str = ""
    wazuh_alerts_path: str = "/alerts"
    cryptoguard_url: str = ""
    cryptoguard_read_key: str = ""
    cryptoguard_ca_file: str = ""
    cryptoguard_events_path: str = "/v1/telemetry"

    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    sms_enabled: bool = False
    legacy_telegram_active: bool = False
    telegram_canary_enabled: bool = False   # when true, Telegram is sent ONLY for incidents on TELEGRAM_CANARY_HOSTS
    telegram_canary_hosts: str = ""
    sms_webhook_url: str = ""
    sms_webhook_token: str = ""
    sms_to: str = ""
    ingest_interval_seconds: int = 0        # 0 = background ingest disabled (use cron/CLI)
    dispatch_interval_seconds: int = 0      # 0 = background notification dispatch disabled

    correlation_window_minutes: int = Field(default=15, ge=1, le=1440)
    connector_timeout_seconds: float = 10.0
    connector_retries: int = 2
    stale_after_minutes: int = 15
    notify_max_attempts: int = 5
    protected_targets: str = ""   # comma-separated hostnames/IPs that must never receive destructive actions
    protected_asset_roles: str = "splunk,wazuh-manager,pfsense,domain-controller,backup,admin-host"


    @field_validator("database_url")
    @classmethod
    def postgres_driver(cls, value):
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator("app_env")
    @classmethod
    def environment(cls, value):
        value = value.strip().lower()
        if value not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test or production")
        return value

    def sensor_intervals(self) -> dict[str, int]:
        try:
            parsed = json.loads(self.sensor_expected_intervals)
            if not isinstance(parsed, dict) or any(
                not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", k) or isinstance(v, bool) or not isinstance(v, int) or v <= 0
                for k, v in parsed.items()
            ):
                raise ValueError
            return parsed
        except (ValueError, TypeError):
            raise ProductionConfigError("SENSOR_EXPECTED_INTERVALS must be a JSON object of sensor names and positive seconds") from None

    def validate_runtime(self):
        self.sensor_intervals()
        if self.app_env != "production":
            return self
        from sqlalchemy.engine import make_url
        try:
            url = make_url(self.database_url)
            valid_db = url.get_backend_name() == "postgresql" and bool(url.database)
        except Exception:
            valid_db = False
        if valid_db and url.drivername != "postgresql+psycopg":
            raise ProductionConfigError("Use the installed synchronous PostgreSQL driver: postgresql+psycopg")
        if valid_db and url.password and "CHANGE_ME" in url.password.upper():
            raise ProductionConfigError("Replace the DATABASE_URL password placeholder")
        if not valid_db:
            raise ProductionConfigError("DATABASE_URL must be PostgreSQL in production")
        if self.allow_fixtures:
            raise ProductionConfigError("ALLOW_FIXTURES must be false in production")
        if self.enable_legacy_mock_routes:
            raise ProductionConfigError("ENABLE_LEGACY_MOCK_ROUTES must be false in production")
        if self.debug:
            raise ProductionConfigError("DEBUG must be false in production")
        if "*" in [s.strip() for s in self.cors_origins.split(",")] and self.cors_allow_credentials:
            raise ProductionConfigError("Wildcard CORS with credentials is forbidden in production")
        if not self.auth_db_enabled and not self.auth_tokens:
            raise ProductionConfigError("Configure AUTH_TOKENS or enable database authentication")
        from app.auth.permissions import parse_tokens
        parsed = parse_tokens(self.auth_tokens, self.default_tenant_id)
        supplied = [x for x in self.auth_tokens.split(";") if x.strip()]
        if len(parsed) != len(supplied) or any(len(token) < 32 or "CHANGE_ME" in token.upper() for token, _ in parsed):
            raise ProductionConfigError("AUTH_TOKENS entries require a valid role/tenant and a random token of at least 32 characters")
        if not re.fullmatch(r"[A-Za-z0-9_*-]+", self.splunk_index):
            raise ProductionConfigError("SPLUNK_INDEX contains unsupported characters")
        for name, creds in (("splunk", (self.splunk_token,)), ("wazuh", (self.wazuh_username, self.wazuh_password)),
                            ("cryptoguard", (self.cryptoguard_read_key,))):
            endpoint = getattr(self, name + "_url")
            if not endpoint:
                if any(creds):
                    raise ProductionConfigError(f"{name.upper()}_URL is required when credentials are configured")
                continue  # disabled connector is visible as not_configured
            u = urlparse(endpoint)
            if u.scheme != "https" or not u.hostname or u.username or u.password or u.query or u.fragment:
                raise ProductionConfigError(f"{name.upper()}_URL must be an HTTPS URL without embedded credentials/query")
            if not all(creds) or any("CHANGE_ME" in c.upper() for c in creds):
                raise ProductionConfigError(f"{name.upper()} credentials must be configured")
        for name in ("wazuh_alerts_path", "cryptoguard_events_path"):
            value = getattr(self, name)
            if not value.startswith("/") or value.startswith("//") or "://" in value:
                raise ProductionConfigError(f"{name.upper()} must be a relative absolute-path")
        if self.telegram_enabled and (not self.telegram_bot_token or not self.telegram_chat_id):
            raise ProductionConfigError("Enabled Telegram requires bot token and chat ID")
        if self.telegram_enabled and "CHANGE_ME" in self.telegram_bot_token.upper():
            raise ProductionConfigError("Replace the Telegram token placeholder")
        if self.sms_enabled and (not self.sms_webhook_url or not self.sms_webhook_token or not self.sms_to):
            raise ProductionConfigError("Enabled SMS requires webhook URL, token and recipient")
        if self.sms_enabled:
            if "CHANGE_ME" in self.sms_webhook_token.upper():
                raise ProductionConfigError("Replace the SMS token placeholder")
            u = urlparse(self.sms_webhook_url)
            if u.scheme != "https" or not u.hostname or u.username or u.password or u.query or u.fragment:
                raise ProductionConfigError("SMS_WEBHOOK_URL must use HTTPS without embedded credentials")
        if self.allow_test_notifications and not self.test_telegram_chat_id:
            raise ProductionConfigError("Test notifications require a separate TEST_TELEGRAM_CHAT_ID")
        if self.allow_test_notifications and self.test_telegram_chat_id == self.telegram_chat_id:
            raise ProductionConfigError("TEST_TELEGRAM_CHAT_ID must differ from the real Telegram destination")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
