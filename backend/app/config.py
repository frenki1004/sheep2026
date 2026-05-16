from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./sheep2026.db"
    spatialite_path: str | None = None
    gee_project_id: str | None = None
    cesium_ion_token: str | None = None
    anthropic_api_key: str | None = None

    pilot_name: str = "znjan"
    pilot_bbox_minx: float = 16.4750
    pilot_bbox_miny: float = 43.5050
    pilot_bbox_maxx: float = 16.5050
    pilot_bbox_maxy: float = 43.5200

    @property
    def pilot_bbox(self) -> tuple[float, float, float, float]:
        return (
            self.pilot_bbox_minx,
            self.pilot_bbox_miny,
            self.pilot_bbox_maxx,
            self.pilot_bbox_maxy,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings(_env_file=Path(__file__).resolve().parent.parent / ".env")
