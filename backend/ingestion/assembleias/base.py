"""Peças comuns dos conectores de assembleias que leem páginas e APIs próprias: o registro de
deputado no formato que `sapl.gravar` espera e o atalho de gravação (`ple.gravar`)."""

import html
import re
from decimal import Decimal
from typing import Any

from ingestion import comum
from ingestion.assembleias import apelidos
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
    gastos_fora: list[dict] | None = None,
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
        "gastos_fora": gastos_fora or [],
        "sessoes": sessoes,
        "presencas": presencas,
    }


def nomes_do_tse(session: Any, uf: str) -> list[tuple[str, str]]:
    """(nome de urna, nome civil) de cada candidatura a deputado estadual ou distrital na UF."""
    from sqlalchemy import select

    from app.models import Candidatura

    return [
        (urna, civil)
        for urna, civil in session.execute(
            select(Candidatura.nome_urna, Candidatura.nome).where(
                Candidatura.uf == uf,
                Candidatura.cargo.in_(("DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL")),
            )
        )
    ]


def ligar_nomes_exatos(
    chaves: set[str], deputados: list[dict], tse: list[tuple[str, str]]
) -> tuple[dict[str, str], list[str]]:
    """Chave de nome (`comum.chave_nome`) numa planilha de gastos -> nome do deputado, só por
    igualdade exata (sem acento, caixa nem pontuação) com o nome do deputado na lista da Casa
    ou, via TSE, com o nome de urna ou civil de uma candidatura que também bate com o nome da
    lista. Nome aproximado nunca liga ("SERGIO AHUIAR" fica de fora), nem sobrenome solto.
    Devolve também as chaves sem deputado (ex-deputados, erros de digitação)."""
    por_chave: dict[str, set[str]] = {}
    for d in deputados:
        por_chave.setdefault(comum.chave_nome(d["nome"]), set()).add(d["nome"])
    for urna, civil in tse:  # a mesma candidatura vale para os dois nomes
        achados = por_chave.get(comum.chave_nome(urna), set()) | por_chave.get(
            comum.chave_nome(civil), set()
        )
        if len(achados) == 1:
            for n in (urna, civil):
                if n and comum.chave_nome(n) not in por_chave:
                    por_chave[comum.chave_nome(n)] = set(achados)
    ligados, sobras = {}, []
    for chave in sorted(chaves):
        alvo = por_chave.get(chave, set())
        if len(alvo) == 1:
            ligados[chave] = next(iter(alvo))
        else:
            sobras.append(chave)
    return ligados, sobras


def ligar_nomes(
    escopo: str,
    totais: dict[str, tuple[int, Decimal]],
    deputados: list[dict],
    tse: list[tuple[str, str]],
) -> tuple[dict[str, str], list[str]]:
    """Liga por nome idêntico (`ligar_nomes_exatos`), reaplica as decisões humanas já gravadas
    (`apelidos`) e deixa o resto numa fila de revisão (`apelidos_pendentes_<escopo>.csv`), com
    candidatos por semelhança. Nada aproximado liga sem decisão. `totais`: chave de nome na
    planilha -> (linhas, valor). Devolve (ligados, sobras sem decisão)."""
    ligados, sobras = ligar_nomes_exatos(set(totais), deputados, tse)
    sobras = apelidos.aplicar(escopo, sobras, deputados, ligados)
    apelidos.gravar_pendentes(escopo, sobras, deputados, totais)
    return ligados, sobras


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
