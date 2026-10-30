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
    # Registro do chat Argos (frases não entendidas, avaliação, conversa consentida). Desligue com
    # ARGOS_REGISTRO=0: as rotas continuam respondendo 204, mas nada é gravado.
    argos_registro: bool = True
    # Avisos por Web Push. Release e produção dividem o banco: AMBIENTE separa as inscrições.
    # Sem AVISOS_ATIVOS, VAPID_PRIVADA e VAPID_CONTATO (mailto: ou https:), as rotas respondem
    # 503 e a diária não faz nada.
    ambiente: str = "desenvolvimento"
    avisos_ativos: bool = False
    vapid_privada: str = ""
    vapid_contato: str = ""
    avisos_max_inscricoes: int = 10000
    viacep_url: str = "https://viacep.com.br/ws/{cep}/json/"
    # Onde ficam os arquivos brutos. No acervo local pode apontar para um HD externo.
    raw_dir: Path = BACKEND_DIR / "data" / "raw"
    # No acervo, o bruto nunca é apagado (limpar_raw não faz nada).
    preservar_raw: bool = False
    # Em funções serverless (Vercel) cada instância vive pouco: sem pool de conexões.
    # SERVERLESS=1 faz o mesmo na reserva (Docker + PgBouncer em modo transação).
    serverless: bool = os.environ.get("VERCEL") == "1" or os.environ.get("SERVERLESS") == "1"

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _driver(cls, url: str) -> str:
        return _com_driver(url)


settings = Settings()
