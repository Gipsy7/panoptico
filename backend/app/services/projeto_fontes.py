"""Fonte e data de cada bloco das páginas de projetos, votações e pauta.

A data de cada bloco vem da última carga `ok` em `fonte_ingestao` (a mais antiga entre as
fontes do bloco, que é até quando tudo está em dia)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao

CASA_NOME = {"camara": "Câmara dos Deputados", "senado": "Senado Federal"}

# Bloco -> (nome mostrado, url, fontes de ingestão) por Casa federal.
BLOCOS = {
    "ficha": {
        "camara": (
            "Proposições (Dados Abertos da Câmara)",
            "https://dadosabertos.camara.leg.br/",
            ["camara_proposicoes", "camara_proposicoes_votadas"],
        ),
        "senado": (
            "Processos legislativos (Dados Abertos do Senado)",
            "https://legis.senado.leg.br/dadosabertos/docs/",
            ["senado_proposicoes"],
        ),
    },
    "votacoes": {
        "camara": (
            "Votações nominais do Plenário (Dados Abertos da Câmara)",
            "https://www.camara.leg.br/busca-portal/votacoes",
            ["camara_votacoes"],
        ),
        "senado": (
            "Votações nominais do Plenário (Dados Abertos do Senado)",
            "https://www25.senado.leg.br/web/atividade/votacoes",
            ["senado_votacoes"],
        ),
    },
    "discursos": {
        "camara": (
            "Discursos em Plenário (Dados Abertos da Câmara)",
            "https://dadosabertos.camara.leg.br/",
            ["camara_discursos"],
        ),
        "senado": (
            "Pronunciamentos em Plenário (Dados Abertos do Senado)",
            "https://legis.senado.leg.br/dadosabertos/docs/",
            ["senado_discursos"],
        ),
    },
    "caminho": {
        "camara": (
            "Tramitação das proposições (Dados Abertos da Câmara)",
            "https://dadosabertos.camara.leg.br/",
            ["camara_tramitacoes"],
        ),
        "senado": (
            "Tramitação dos processos (Dados Abertos do Senado)",
            "https://legis.senado.leg.br/dadosabertos/docs/",
            ["senado_tramitacoes"],
        ),
    },
    "pauta": {
        "camara": (
            "Pauta do Plenário (Dados Abertos da Câmara)",
            "https://dadosabertos.camara.leg.br/",
            ["camara_pauta"],
        ),
        "senado": (
            "Agenda do Plenário (Dados Abertos do Senado)",
            "https://legis.senado.leg.br/dadosabertos/docs/",
            ["senado_pauta"],
        ),
    },
}

# Fontes das votações e projetos de câmaras municipais e assembleias.
FONTES_LOCAIS = [
    "sapl_camaras",
    "sapl_assembleias",
    "alesc",
    "alep",
    "alrs",
    "almg",
    "alesp",
    "alepe",
    "cittatec_camaras",
]
NOME_LOCAL = "Portal legislativo da própria casa (câmara municipal ou assembleia)"


def atualizado_em(session: Session, fontes: list[str]) -> datetime | None:
    datas = []
    for fonte in fontes:
        data = session.scalar(
            select(func.max(FonteIngestao.concluido_em)).where(
                FonteIngestao.fonte == fonte, FonteIngestao.status == "ok"
            )
        )
        if data is not None:
            datas.append(data)
    return min(datas) if datas else None


def fonte_do_bloco(session: Session, bloco: str, casa: str) -> dict:
    nome, url, fontes = BLOCOS[bloco][casa]
    return {
        "fonte_nome": nome,
        "fonte_url": url,
        "atualizado_em": atualizado_em(session, fontes),
    }


def fonte_local(session: Session, url: str | None) -> dict:
    return {
        "fonte_nome": NOME_LOCAL,
        "fonte_url": url or "",
        "atualizado_em": atualizado_em(session, FONTES_LOCAIS),
    }
