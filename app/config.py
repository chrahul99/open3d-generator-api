from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPEN3D_", env_file=".env")

    storage_dir: Path = Field(default=Path("data"))
    engines_config: Path | None = None
    max_images: int = 12
    max_upload_mb: int = 40
    max_storage_mb: int = 512
    cleanup_max_age_hours: int = 24
    cors_origins: str = "*"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
