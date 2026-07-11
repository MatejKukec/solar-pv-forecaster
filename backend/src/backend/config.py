"""Application configuration, loaded from environment variables / .env."""

import sys

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration for the solar PV forecaster backend."""

    open_meteo_base_url: str = Field(default="https://api.open-meteo.com/v1", alias="OPEN_METEO_BASE_URL")
    open_meteo_archive_url: str = Field(default="https://archive-api.open-meteo.com/v1", alias="OPEN_METEO_ARCHIVE_URL")
    pvgis_base_url: str = Field(default="https://re.jrc.ec.europa.eu/api/v5_2", alias="PVGIS_BASE_URL")
    nasa_power_base_url: str = Field(default="https://power.larc.nasa.gov/api/temporal", alias="NASA_POWER_BASE_URL")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.5-flash", alias="GEMINI_MODEL")

    database_url: str = Field(default="sqlite:///./solar_pv.db", alias="DATABASE_URL")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    debug: bool = Field(default=False, alias="DEBUG")

    model_config = {"env_file": ".env", "populate_by_name": True}

    @property
    def cors_origin_list(self) -> list[str]:
        """Split the comma-separated CORS_ORIGINS env var into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


try:
    settings = Settings()
except ValidationError as e:
    for err in e.errors():
        print(f"  {err['loc'][0]}: {err['msg']}")
    sys.exit(1)
