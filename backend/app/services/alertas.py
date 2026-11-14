"""Alertas de operação por e-mail ao dono: fluxo grande de visitas e falhas.

Roda na VPS a cada 5 minutos (`python -m app.alertas`, agenda `panoptico-alertas`). Cada
verificação devolve no máximo um alerta, com uma chave e uma janela (o dia ou a hora): o mesmo
alerta só é enviado uma vez por janela (tabela `alerta_enviado`), então uma falha que dura horas
não vira dezenas de mensagens.

O que é conferido:
- fluxo: visitas de hoje (contagem anônima, `metrica_diaria`) acima de N vezes a média dos 7 dias
  anteriores. Uma vez por dia. Robôs não entram nessa contagem.
- ingestao: cargas que terminaram com erro nas últimas 24 horas. Uma vez por dia.
- saude: a API ou o site não respondem por dentro da rede. Uma vez por hora.
- disco: disco acima do limite. Uma vez por dia.

Se a VPS inteira cair, nada daqui roda: quem avisa nesse caso é o Worker de troca
(infra/cloudflare/troca), que vive fora dela.

Nenhum dado pessoal entra no e-mail: só totais, nomes de fontes e endereços internos.
"""

import logging
import shutil
import smtplib
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.alerta import AlertaEnviado
from app.models.fonte_ingestao import FonteIngestao
from app.models.metrica import MetricaDiaria
from app.services.metricas import FUSO

log = logging.getLogger("panoptico.alertas")

DIAS_BASE = 7
PRAZO_HTTP_S = 8


@dataclass(frozen=True)
class Alerta:
    chave: str
    janela: str
    assunto: str
    linhas: tuple[str, ...]

    @property
    def texto(self) -> str:
        return "\n".join(self.linhas)


def _dia(agora: datetime) -> str:
    return agora.astimezone(FUSO).date().isoformat()


def _hora(agora: datetime) -> str:
    return agora.astimezone(FUSO).strftime("%Y-%m-%dT%H")


def _n(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


# ---- Verificações ---------------------------------------------------------------------


def fluxo(session: Session, agora: datetime) -> Alerta | None:
    hoje = agora.astimezone(FUSO).date()
    inicio = hoje - timedelta(days=DIAS_BASE)
    por_dia = dict(
        session.execute(
            select(MetricaDiaria.dia, func.sum(MetricaDiaria.total))
            .where(MetricaDiaria.tipo == "visita", MetricaDiaria.dia >= inicio)
            .group_by(MetricaDiaria.dia)
        ).all()
    )
    visitas = int(por_dia.get(hoje, 0))
    # Dia sem registro entra com zero: a média é dos 7 dias, não só dos que tiveram visita.
    media = sum(int(por_dia.get(inicio + timedelta(days=i), 0)) for i in range(DIAS_BASE)) / (
        DIAS_BASE
    )
    limite = max(settings.alerta_fluxo_piso, settings.alerta_fluxo_fator * media)
    if visitas < limite:
        return None
    vezes = f" ({visitas / media:.1f} vezes a média)".replace(".", ",") if media else ""
    return Alerta(
        "fluxo",
        _dia(agora),
        f"Panóptico: fluxo grande hoje, {_n(visitas)} visitas",
        (
            f"Visitas de hoje até agora: {_n(visitas)}{vezes}.",
            f"Média dos {DIAS_BASE} dias anteriores: {_n(media)} por dia.",
            f"O aviso sai quando o dia passa de {_n(limite)} visitas.",
            "",
            "Contagem anônima do próprio site; robôs não entram. Detalhes em /painel.",
        ),
    )


def ingestao(session: Session, agora: datetime) -> Alerta | None:
    desde = agora - timedelta(hours=24)
    fontes = session.execute(
        select(FonteIngestao.fonte, func.count(), func.max(FonteIngestao.iniciado_em))
        .where(FonteIngestao.status == "erro", FonteIngestao.iniciado_em >= desde)
        .group_by(FonteIngestao.fonte)
        .order_by(FonteIngestao.fonte)
    ).all()
    if not fontes:
        return None
    linhas = [f"Cargas com erro nas últimas 24 horas: {len(fontes)} fonte(s).", ""]
    for fonte, vezes, ultima in fontes:
        quando = ultima.astimezone(FUSO).strftime("%d/%m %H:%M")
        linhas.append(f"- {fonte}: {vezes} erro(s), o último em {quando}")
    linhas += ["", "Log na VPS: journalctl -u 'panoptico-*' --since '24 hours ago'"]
    return Alerta(
        "ingestao",
        _dia(agora),
        f"Panóptico: {len(fontes)} carga(s) com erro",
        tuple(linhas),
    )


def _responde(url: str) -> str | None:
    """None se respondeu 200; senão, o motivo em poucas palavras."""
    try:
        resposta = httpx.get(url, timeout=PRAZO_HTTP_S)
    except httpx.HTTPError as erro:
        return type(erro).__name__
    return None if resposta.status_code == 200 else f"HTTP {resposta.status_code}"


def saude(agora: datetime, conferir: Callable[[str], str | None] = _responde) -> Alerta | None:
    urls = [u.strip() for u in settings.alerta_urls.split(",") if u.strip()]
    falhas = [(u, motivo) for u in urls if (motivo := conferir(u))]
    if not falhas:
        return None
    return Alerta(
        "saude",
        _hora(agora),
        f"Panóptico: {len(falhas)} serviço(s) sem responder",
        (
            "Conferido por dentro da VPS:",
            *(f"- {u}: {motivo}" for u, motivo in falhas),
            "",
            "Ver: docker compose ps (em /opt/panoptico/deploy/vps) e journalctl -u 'panoptico-*'.",
        ),
    )


def disco(agora: datetime, uso: Callable[[], tuple[int, int]] | None = None) -> Alerta | None:
    if uso is None:
        d = shutil.disk_usage("/")
        total, usado = d.total, d.used
    else:
        total, usado = uso()
    pct = 100 * usado / total if total else 0
    if pct < settings.alerta_disco_pct:
        return None
    livre_gb = (total - usado) / 1024**3
    return Alerta(
        "disco",
        _dia(agora),
        f"Panóptico: disco em {pct:.0f}%",
        (
            f"Disco usado: {pct:.0f}% (limite do aviso: {settings.alerta_disco_pct}%).",
            f"Livre: {livre_gb:.1f} GB.".replace(".", ",", 1),
        ),
    )


# ---- Envio ----------------------------------------------------------------------------


def configurado() -> bool:
    return bool(
        settings.alertas_ativos
        and settings.alerta_email_para
        and settings.smtp_usuario
        and settings.smtp_senha
    )


def enviar_email(alerta: Alerta) -> None:
    mensagem = EmailMessage()
    mensagem["Subject"] = alerta.assunto
    mensagem["From"] = settings.smtp_usuario
    mensagem["To"] = settings.alerta_email_para
    mensagem.set_content(
        alerta.texto + "\n\nMensagem automática do Panóptico (ambiente: " + settings.ambiente + ")."
    )
    with smtplib.SMTP_SSL(
        settings.smtp_host,
        settings.smtp_porta,
        timeout=20,
        context=ssl.create_default_context(),
    ) as servidor:
        servidor.login(settings.smtp_usuario, settings.smtp_senha)
        servidor.send_message(mensagem)


def ja_enviado(session: Session, alerta: Alerta) -> bool:
    return (
        session.scalar(
            select(AlertaEnviado.id).where(
                AlertaEnviado.chave == alerta.chave, AlertaEnviado.janela == alerta.janela
            )
        )
        is not None
    )


def verificar(session: Session, agora: datetime) -> list[Alerta]:
    """Todas as verificações; uma que falha não impede as outras."""
    achados: list[Alerta] = []
    for nome, checar in (
        ("fluxo", lambda: fluxo(session, agora)),
        ("ingestao", lambda: ingestao(session, agora)),
        ("saude", lambda: saude(agora)),
        ("disco", lambda: disco(agora)),
    ):
        try:
            if alerta := checar():
                achados.append(alerta)
        except Exception:
            log.exception("verificação %s falhou", nome)
            session.rollback()
    return achados


def rodar(
    session: Session,
    agora: datetime,
    enviar: Callable[[Alerta], None] = enviar_email,
) -> dict[str, int]:
    """Verifica, envia o que é novo na janela e registra. Devolve os totais para o log."""
    achados = verificar(session, agora)
    novos = [a for a in achados if not ja_enviado(session, a)]
    enviados = 0
    for alerta in novos:
        if not configurado():
            log.warning("alerta sem envio (e-mail não configurado): %s", alerta.assunto)
            continue
        try:
            enviar(alerta)
        except Exception:
            # Sem registro: tenta de novo na próxima rodada.
            log.exception("falha ao enviar o alerta %s", alerta.chave)
            continue
        session.add(
            AlertaEnviado(
                chave=alerta.chave,
                janela=alerta.janela,
                assunto=alerta.assunto[:200],
                texto=alerta.texto,
            )
        )
        session.commit()
        enviados += 1
    return {"achados": len(achados), "novos": len(novos), "enviados": enviados}
