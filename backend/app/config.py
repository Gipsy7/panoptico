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
    # Contagem anônima de acessos e painel privado. Só grava com AMBIENTE=producao: o release usa
    # o mesmo banco e não pode somar ao total (docs/DECISOES.md, 2026-10-31). Desligados: as rotas
    # de contagem respondem 204 sem tocar no banco e o painel responde 503.
    metricas_ativas: bool = False
    painel_usuario: str = ""
    # "scrypt:N:r:p:sal:hash" (de `python -m app.painel_senha`); sem "$", que o compose interpreta.
    painel_senha_hash: str = ""
    painel_segredo: str = ""
    # Alertas de operação por e-mail ao dono (app/services/alertas.py, `python -m app.alertas`).
    # Sem ALERTAS_ATIVOS, ALERTA_EMAIL_PARA, SMTP_USUARIO e SMTP_SENHA, a verificação roda e só
    # escreve no log. A senha é uma senha de aplicativo do provedor de e-mail, nunca a da conta.
    alertas_ativos: bool = False
    alerta_email_para: str = ""
    smtp_host: str = "smtp.zoho.com"
    smtp_porta: int = 465
    smtp_usuario: str = ""
    smtp_senha: str = ""
    # Fluxo grande: visitas de hoje acima de FATOR vezes a média dos 7 dias anteriores, e nunca
    # abaixo do PISO (um dia parado seguido de um dia normal não é fluxo grande).
    alerta_fluxo_fator: float = 3.0
    alerta_fluxo_piso: int = 300
    alerta_disco_pct: int = 85
    # Endereços conferidos por dentro da rede do compose, separados por vírgula.
    alerta_urls: str = "http://api:8000/saude,http://web:3000/"
    viacep_url: str = "https://viacep.com.br/ws/{cep}/json/"
    # Onde ficam os arquivos brutos. No acervo local pode apontar para um HD externo.
    raw_dir: Path = BACKEND_DIR / "data" / "raw"
    # No acervo, o bruto nunca é apagado (limpar_raw não faz nada).
    preservar_raw: bool = False
    # Em funções serverless (Vercel) cada instância vive pouco: sem pool de conexões.
    # SERVERLESS=1 faz o mesmo na reserva (Docker + PgBouncer em modo transação).
    serverless: bool = os.environ.get("VERCEL") == "1" or os.environ.get("SERVERLESS") == "1"
    # Tempo máximo de cada consulta das rotas da API, em milissegundos (0 desliga). Vale só para
    # a sessão das rotas (app/db.py): ingestão e migrações não têm teto.
    api_statement_timeout_ms: int = 30000

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _driver(cls, url: str) -> str:
        return _com_driver(url)


settings = Settings()
