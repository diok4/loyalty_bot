from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения. Источник — .env + переменные окружения."""

    BOT_TOKEN: str

    DATABASE_URL: str
    REDIS_URL: str

    ADMIN_IDS: List[int] = Field(default_factory=list)

    BITRIX_WEBHOOK_URL: str = ""
    BITRIX_ENABLED: bool = False

    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    BARCODE_STORAGE_PATH: str = "storage/barcodes"

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    THROTTLE_RATE_SECONDS: float = 1.0

    # Dev-фича: на каждой новой карте создавать 2-3 фейковых покупки.
    # В проде ОБЯЗАТЕЛЬНО false — иначе клиенты увидят чужие операции.
    SEED_FAKE_HISTORY: bool = False

    # --- Admin auth via /logadmin ---
    ADMIN_USERNAME: str = "manager"
    ADMIN_PASSWORD: str = "manager123"
    ADMIN_SESSION_TTL_SECONDS: int = 86400  # 24 часа

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_ignore_empty=True,  # пустые env → используем default (важно для ADMIN_IDS)
    )

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def _parse_admin_ids(cls, v: object) -> object:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"


settings = Settings()
