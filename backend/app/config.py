from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://panoptico:panoptico@localhost:5432/panoptico"
    test_database_url: str = (
        "postgresql+psycopg://panoptico:panoptico@localhost:5432/panoptico_test"
    )
    cors_origins: list[str] = ["http://localhost:3000"]
    viacep_url: str = "https://viacep.com.br/ws/{cep}/json/"


settings = Settings()
