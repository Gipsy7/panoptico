"""Peças comuns dos conectores de assembleias que leem páginas e APIs próprias: o registro de
deputado no formato que `sapl.gravar` espera e o atalho de gravação (`ple.gravar`)."""

import html
import re
from typing import Any

from ingestion import comum
from ingestion.assembleias.ple import gravar  # noqa: F401  (reexportado)


def limpo(trecho: str | None) -> str:
    """Texto de um trecho de HTML: sem tags, com entidades resolvidas e espaços normalizados."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", trecho or "")).split())


def registro(
    d: dict[str, Any],
    *,
    projetos: list[dict] | None = None,
    por_tipo: dict[str, int] | None = None,
    gastos: list[dict] | None = None,
    sessoes: int | None = None,
    presencas: int | None = None,
) -> dict[str, Any]:
    """Deputado em exercício (`id`, `nome`, opcionais `partido`, `foto`, `civil`, `email`,
    `telefone`) com o que a casa publica de projetos, gastos e presença."""
    nome = d["nome"].strip()
    return {
        "id_externo": str(d["id"]),
        "nome": comum.nome_proprio(nome) if nome.isupper() else nome,
        "nome_completo": comum.nome_proprio(d["civil"]) if d.get("civil") else None,
        "partido": d.get("partido") or None,
        "foto_url": d.get("foto") or None,
        "email": (d.get("email") or "").strip().lower() or None,
        "telefone": d.get("telefone") or None,
        "titular": True,
        "em_exercicio": True,
        "inicio": None,
        "fim": None,
        "proposicoes_por_tipo": por_tipo or {},
        "projetos": projetos or [],
        "gastos": gastos or [],
        "sessoes": sessoes,
        "presencas": presencas,
    }


def casa(base: str, deputados: list[dict]) -> dict:
    return {"base": base, "legislatura": None, "vereadores": deputados, "votacoes": [], "votos": []}


def projeto(
    sigla: str, tipo: str, numero: str | int, ano: int, ementa: str, data: str | None, url: str
) -> dict:
    return {
        "id_externo": f"{sigla}-{numero}-{ano}"[:20],
        "tipo": tipo,
        "numero": int(numero) if str(numero).isdigit() else None,
        "ano": ano,
        "ementa": " ".join((ementa or "").split()),
        "data_apresentacao": data,
        "em_tramitacao": None,
        "primeiro_autor": True,
        "url": url,
    }
