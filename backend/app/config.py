import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _com_driver(url: str) -> str:
    """Aceita a URL como o Neon e outros provedores entregam ("postgres://..." ou
    "postgresql://...") e usa o driver psycopg 3."""
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo) :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://panoptico:panoptico@localhost:5432/panoptico"
    test_database_url: str = (
        "postgresql+psycopg://panoptico:panoptico@localhost:5432/panoptico_test"
    )
    cors_origins: list[str] = ["http://localhost:3000"]
    viacep_url: str = "https://viacep.com.br/ws/{cep}/json/"
    # Onde ficam os arquivos brutos. No acervo local pode apontar para um HD externo.
    raw_dir: Path = BACKEND_DIR / "data" / "raw"
    # No acervo, o bruto nunca é apagado (limpar_raw não faz nada).
    preservar_raw: bool = False
    # Em funções serverless (Vercel) cada instância vive pouco: sem pool de conexões.
    serverless: bool = os.environ.get("VERCEL") == "1"

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _driver(cls, url: str) -> str:
        return _com_driver(url)


settings = Settings()
