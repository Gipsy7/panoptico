"""Identidade única de pessoa pública: liga candidaturas (TSE), parlamentares federais e
mandatos das câmaras e assembleias à mesma `pessoa`.

Roda depois das cargas que alimenta (TSE, deputados, senadores, SAPL, ALMG, ALESP). Não
baixa nada: lê o banco. O id de cada pessoa é estável entre recargas: um registro que já
estava ligado mantém a pessoa; quando duas pessoas passam a ser a mesma (um título novo
ligou as duas), fica a de menor id e os vínculos e eventos da outra passam para ela.
Só grava o que mudou, para a recarga semanal não reescrever dezenas de milhares de linhas.

Os eventos de eleição não são gravados: a linha do tempo os monta das candidaturas
ligadas (app/services/pessoas.py). A tabela evento fica para fatos que não existem em
outra tabela (sanções, processos, cassações).

Uso: python -m ingestion.pessoas
"""

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import delete, exists, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR
from app.db import SessionLocal
from app.models import (
    Candidatura,
    Evento,
    FonteIngestao,
    MandatoLocal,
    Parlamentar,
    Pessoa,
    PessoaVinculo,
)
from ingestion import comum
from ingestion.identidade import Aresta, Chave, agrupar

FONTE = "pessoas"
FONTES_GERIDAS = ("candidatura", "parlamentar", "mandato_local")
LOTE = 5000


@dataclass
class Registro:
    chave: Chave
    nome: str
    cpf: str | None = None
    titulo: str | None = None
    data_nascimento: date | None = None
    ano: int = 0  # eleição mais recente: o nome e o título dela prevalecem


def _titulo_valido(titulo: str | None) -> str | None:
    return titulo if titulo and titulo.strip("0") else None


def ler(session: Session) -> tuple[dict[Chave, Registro], list[Aresta]]:
    registros: dict[Chave, Registro] = {}
    arestas: list[Aresta] = []
    candidaturas = session.execute(
        select(
            Candidatura.id, Candidatura.ano_eleicao, Candidatura.sq_candidato, Candidatura.cpf,
            Candidatura.titulo, Candidatura.nome, Candidatura.data_nascimento,
            Candidatura.parlamentar_id, Candidatura.nome_urna,
        )
    ).all()  # fmt: skip
    parlamentares = session.execute(
        select(Parlamentar.id, Parlamentar.casa, Parlamentar.id_externo, Parlamentar.cpf,
               Parlamentar.nome_civil, Parlamentar.nome_parlamentar)
    ).all()  # fmt: skip
    mandatos = session.execute(
        select(MandatoLocal.casa, MandatoLocal.uf, MandatoLocal.municipio_ibge,
               MandatoLocal.id_externo, MandatoLocal.nome, MandatoLocal.nome_completo,
               MandatoLocal.candidatura_id)
    ).all()  # fmt: skip

    chave_candidatura: dict[int, Chave] = {}
    chave_parlamentar: dict[int, Chave] = {}
    for p in parlamentares:
        chave = ("parlamentar", f"{p.casa}:{p.id_externo}")
        chave_parlamentar[p.id] = chave
        registros[chave] = Registro(chave, p.nome_civil or p.nome_parlamentar, cpf=p.cpf)
    for c in candidaturas:
        chave = ("candidatura", f"{c.ano_eleicao}:{c.sq_candidato}")
        chave_candidatura[c.id] = chave
        registros[chave] = Registro(
            chave, c.nome, c.cpf, _titulo_valido(c.titulo), c.data_nascimento, c.ano_eleicao
        )
        if c.parlamentar_id in chave_parlamentar:
            # A carga do TSE já ligou esta candidatura ao parlamentar por CPF ou título.
            arestas.append(Aresta(chave_parlamentar[c.parlamentar_id], chave, "tse"))
    nomes_candidatura = {
        c.id: {comum.chave_nome(c.nome), comum.chave_nome(c.nome_urna)} - {""} for c in candidaturas
    }
    recusados = {
        (r["fonte"], r["id_externo"], r["ligado_a"])
        for r in revisoes()
        if r["decisao"] == "recusado"
    }
    for m in mandatos:
        chave = ("mandato_local", f"{m.casa}:{m.uf}:{m.municipio_ibge or ''}:{m.id_externo}")
        registros[chave] = Registro(chave, m.nome_completo or m.nome)
        if m.candidatura_id in chave_candidatura:
            alvo = chave_candidatura[m.candidatura_id]
            if (chave[0], chave[1], f"{alvo[0]}:{alvo[1]}") in recusados:
                continue  # revisão humana disse que não é a mesma pessoa
            # Ligação da carga da casa ao eleito pelo nome, sempre única entre os eleitos da
            # casa. Nome idêntico (de urna ou civil) é forte; aproximado ("Dr Fulano" e
            # "Fulano") é média e só é publicado depois de revisado (ingestion.revisar).
            nomes = {comum.chave_nome(m.nome), comum.chave_nome(m.nome_completo)} - {""}
            regra = (
                "nome_exato_casa" if nomes & nomes_candidatura[m.candidatura_id] else "nome_casa"
            )
            arestas.append(Aresta(alvo, chave, regra))

    for campo, regra in (("cpf", "cpf"), ("titulo", "titulo")):
        por_valor: dict[str, list[Chave]] = defaultdict(list)
        for r in registros.values():
            if valor := getattr(r, campo):
                por_valor[valor].append(r.chave)
        for chaves in por_valor.values():
            arestas += [Aresta(chaves[0], outra, regra) for outra in chaves[1:]]
    return registros, arestas


REVISOES = BACKEND_DIR.parent / "data" / "vinculos_revisados.csv"
COLUNAS_REVISAO = [
    "fonte",
    "id_externo",
    "ligado_a",
    "decisao",
    "revisado_por",
    "revisado_em",
    "observacao",
]


def revisoes(caminho: Path | None = None) -> list[dict[str, str]]:
    """Decisões humanas sobre vínculos por nome aproximado (data/vinculos_revisados.csv),
    reaplicadas a cada carga: "aceito" publica, "recusado" desfaz a ligação."""
    caminho = caminho or REVISOES
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [
            {k: (v or "").strip() for k, v in linha.items()}
            for linha in csv.DictReader(arquivo)
            if (linha.get("decisao") or "").strip() in ("aceito", "recusado")
        ]


def aplicar_aceites(session: Session) -> int:
    """Marca como revisados os vínculos aceitos, se ainda ligam à mesma pessoa do registro
    indicado em "ligado_a" (se a ligação mudou, a decisão antiga não vale mais)."""
    marcados = 0
    for r in revisoes():
        if r["decisao"] != "aceito":
            continue
        fonte_alvo, _, id_alvo = r["ligado_a"].partition(":")
        pessoa_alvo = session.scalar(
            select(PessoaVinculo.pessoa_id).where(
                PessoaVinculo.fonte == fonte_alvo, PessoaVinculo.id_externo == id_alvo
            )
        )
        resultado = session.execute(
            update(PessoaVinculo)
            .where(
                PessoaVinculo.fonte == r["fonte"],
                PessoaVinculo.id_externo == r["id_externo"],
                PessoaVinculo.pessoa_id == pessoa_alvo,
                PessoaVinculo.revisado.is_(False),
            )
            .values(revisado=True)
        )
        marcados += resultado.rowcount
    return marcados


def _atributos(membros: list[Registro]) -> dict:
    """Nome, nascimento, CPF e título da pessoa: da eleição mais recente; sem eleição, do
    cadastro da casa."""
    ordem = sorted(membros, key=lambda r: (r.ano, r.chave[0] == "parlamentar"), reverse=True)
    nome = next((r.nome for r in ordem if r.nome), "")
    return {
        "nome": nome[:200],
        "chave_nome": comum.chave_nome(nome)[:200],
        "data_nascimento": next((r.data_nascimento for r in ordem if r.data_nascimento), None),
        "cpf": next((r.cpf for r in ordem if r.cpf), None),
        "titulo": next((r.titulo for r in ordem if r.titulo), None),
    }


def gravar(session: Session, registros: dict[Chave, Registro], pessoas: list) -> int:
    """Grava pessoas e vínculos mantendo os ids; devolve quantas pessoas mudaram."""
    existentes = {
        (fonte, id_externo): pessoa_id
        for fonte, id_externo, pessoa_id in session.execute(
            select(PessoaVinculo.fonte, PessoaVinculo.id_externo, PessoaVinculo.pessoa_id).where(
                PessoaVinculo.fonte.in_(FONTES_GERIDAS)
            )
        )
    }
    fundidas: dict[int, int] = {}
    alvo: list[int | None] = []
    for membros in pessoas:
        ids = sorted({existentes[c] for c, _ in membros if c in existentes})
        alvo.append(ids[0] if ids else None)
        for outro in ids[1:]:
            fundidas[outro] = ids[0]
    for de, para in fundidas.items():
        session.execute(
            update(PessoaVinculo).where(PessoaVinculo.pessoa_id == de).values(pessoa_id=para)
        )
        session.execute(update(Evento).where(Evento.pessoa_id == de).values(pessoa_id=para))
    if fundidas:
        session.execute(delete(Pessoa).where(Pessoa.id.in_(list(fundidas))))

    atributos = [_atributos([registros[c] for c, _ in membros]) for membros in pessoas]
    novas = [i for i, pessoa_id in enumerate(alvo) if pessoa_id is None]
    for inicio in range(0, len(novas), LOTE):
        lote = novas[inicio : inicio + LOTE]
        ids = session.scalars(
            insert(Pessoa).returning(Pessoa.id, sort_by_parameter_order=True),
            [atributos[i] for i in lote],
        ).all()
        for i, pessoa_id in zip(lote, ids, strict=True):
            alvo[i] = pessoa_id
    campos = ("nome", "chave_nome", "data_nascimento", "cpf", "titulo")
    atuais = {
        linha.id: {c: getattr(linha, c) for c in campos}
        for linha in session.execute(select(Pessoa.id, *(getattr(Pessoa, c) for c in campos)))
    }
    novas_set = set(novas)
    antigas = [
        {"id": alvo[i], **atributos[i]}
        for i in range(len(pessoas))
        if i not in novas_set and atuais.get(alvo[i]) != atributos[i]
    ]
    for inicio in range(0, len(antigas), LOTE):
        session.execute(update(Pessoa), antigas[inicio : inicio + LOTE])

    vinculos = [
        {"pessoa_id": alvo[i], "fonte": chave[0], "id_externo": chave[1], "regra": regra}
        for i, membros in enumerate(pessoas)
        for chave, regra in membros
    ]
    for inicio in range(0, len(vinculos), LOTE):
        stmt = insert(PessoaVinculo).values(vinculos[inicio : inicio + LOTE])
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=["fonte", "id_externo"],
                set_={"pessoa_id": stmt.excluded.pessoa_id, "regra": stmt.excluded.regra},
                where=(PessoaVinculo.pessoa_id != stmt.excluded.pessoa_id)
                | (PessoaVinculo.regra != stmt.excluded.regra),
            )
        )
    # Registros que sumiram das fontes (candidatura removida, vereador que saiu).
    presentes = {chave for membros in pessoas for chave, _ in membros}
    sumiram = [c for c in existentes if c not in presentes]
    for fonte in FONTES_GERIDAS:
        ids_externos = [i for f, i in sumiram if f == fonte]
        for inicio in range(0, len(ids_externos), LOTE):
            session.execute(
                delete(PessoaVinculo).where(
                    PessoaVinculo.fonte == fonte,
                    PessoaVinculo.id_externo.in_(ids_externos[inicio : inicio + LOTE]),
                )
            )
    session.execute(delete(Pessoa).where(~exists().where(PessoaVinculo.pessoa_id == Pessoa.id)))
    return len(novas) + len(antigas) + len(fundidas)


def processar(session: Session) -> tuple[dict[Chave, Registro], list, list, int]:
    """Lê, agrupa e grava (sem commit). Devolve registros, pessoas, ligações recusadas e
    quantas pessoas mudaram."""
    registros, arestas = ler(session)
    if not registros:
        raise RuntimeError("Nenhum registro para ligar: rode antes as cargas do TSE e das casas.")
    pessoas, recusadas = agrupar({c: r.cpf for c, r in registros.items()}, arestas)
    mudaram = gravar(session, registros, pessoas)
    aplicar_aceites(session)
    return registros, pessoas, recusadas, mudaram


def executar() -> int:
    with SessionLocal() as session:
        ingestao = FonteIngestao(fonte=FONTE, url="(banco)", arquivo_raw="(não guardado)")
        session.add(ingestao)
        session.flush()
        registros, pessoas, recusadas, mudaram = processar(session)
        ingestao.registros = len(pessoas)
        ingestao.status = "ok"
        ingestao.concluido_em = datetime.now(UTC)
        session.commit()
    regras = defaultdict(int)
    for membros in pessoas:
        for _, regra in membros:
            regras[regra] += 1
    print(
        f"{len(registros)} registros -> {len(pessoas)} pessoas ({mudaram} novas ou alteradas); "
        f"{len(recusadas)} ligações recusadas por CPF diferente"
    )
    print("  por regra: " + ", ".join(f"{r} {n}" for r, n in sorted(regras.items())))
    return len(pessoas)


if __name__ == "__main__":
    executar()
