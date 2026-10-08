"""Candidaturas registradas no TSE (consulta_cand), ligadas aos parlamentares pelo CPF.

Para cada parlamentar guardamos todas as candidaturas com o mesmo CPF, em qualquer cargo:
um senador eleito em 2018 que disputou o governo em 2022 tem a declaração de bens mais
recente nessa candidatura a governador.

De onde vem o CPF:
- deputados: da API da Câmara (detalhe do deputado), uma vez; fica guardado em parlamentar.cpf;
- senadores: o Senado não publica o CPF, então casamos nome civil + UF + cargo de senador
  ou suplente no próprio arquivo do TSE, aceitando só correspondência exata e única.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Candidatura, FonteIngestao, Municipio, Parlamentar
from ingestion import comum
from ingestion.transparencia.emendas import resolver_municipios
from ingestion.tse import comum_tse

FONTE = "tse_candidaturas"
URL = f"{comum_tse.BASE}/consulta_cand/consulta_cand_{{ano}}.zip"
URL_DEPUTADO = "https://dadosabertos.camara.leg.br/api/v2/deputados/{id}"
CARGOS_SENADO = {"SENADOR", "1º SUPLENTE", "2º SUPLENTE"}
CARGOS_LOCAIS = {"VEREADOR", "DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL"}
# Nomes do TSE que diferem do IBGE além do que a comparação aproximada resolve.
GRAFIAS_TSE = {
    ("RN", "BOA SAUDE"): "Januário Cicco",
    ("RR", "SAO LUIZ"): "São Luiz do Anauá",
}


def normalizar(linhas: Any) -> list[dict[str, Any]]:
    """Uma linha por candidatura. Quem disputou dois turnos aparece duas vezes no arquivo;
    fica a linha do último turno, que tem o resultado final."""
    por_sq: dict[str, tuple[int, dict[str, Any]]] = {}
    for linha in linhas:
        sq = linha["SQ_CANDIDATO"].strip()
        turno = int(linha.get("NR_TURNO") or 1)
        if sq in por_sq and por_sq[sq][0] >= turno:
            continue
        por_sq[sq] = (
            turno,
            {
                "ano_eleicao": int(linha["ANO_ELEICAO"]),
                "sq_candidato": sq,
                "cargo": linha["DS_CARGO"].strip().upper(),
                "uf": linha["SG_UF"].strip(),
                "unidade": comum.nome_proprio(linha["NM_UE"].strip()) or "",
                "codigo_ue": linha["SG_UE"].strip(),
                "nome": comum.nome_proprio(linha["NM_CANDIDATO"].strip()) or "",
                "nome_urna": comum.nome_proprio(linha["NM_URNA_CANDIDATO"].strip()) or "",
                "partido": comum_tse.texto(linha.get("SG_PARTIDO")),
                "numero": comum_tse.texto(linha.get("NR_CANDIDATO")),
                "situacao_turno": comum_tse.texto(linha.get("DS_SIT_TOT_TURNO")),
                "situacao_candidatura": comum_tse.texto(linha.get("DS_SITUACAO_CANDIDATURA")),
                "cpf": comum_tse.cpf(linha.get("NR_CPF_CANDIDATO")),
            },
        )
    return [registro for _, registro in por_sq.values()]


def cpfs_de_senadores(
    registros: list[dict[str, Any]], senadores: list[tuple[int, str, str]]
) -> dict[int, str]:
    """id do senador -> CPF, por nome civil + UF entre candidatos a senador ou suplente.
    Só aceita quando o nome aponta para um único CPF."""
    por_chave: dict[tuple[str, str], set[str]] = {}
    for r in registros:
        if r["cargo"] in CARGOS_SENADO and r["cpf"]:
            por_chave.setdefault((r["uf"], comum.chave_nome(r["nome"])), set()).add(r["cpf"])
    resultado = {}
    for id_, uf, nome_civil in senadores:
        cpfs = por_chave.get((uf, comum.chave_nome(nome_civil)), set())
        if len(cpfs) == 1:
            resultado[id_] = next(iter(cpfs))
    return resultado


def completar_cpfs_deputados() -> int:
    """Busca na API da Câmara o CPF dos deputados que ainda não o têm. Roda uma vez por
    deputado: depois o CPF fica guardado."""
    with SessionLocal() as session:
        faltam = session.execute(
            select(Parlamentar.id, Parlamentar.id_externo).where(
                Parlamentar.casa == "camara", Parlamentar.cpf.is_(None)
            )
        ).all()
        if not faltam:
            return 0
        with comum.criar_cliente() as client:

            def buscar(par: tuple[int, str]) -> tuple[int, str | None]:
                try:
                    dados = comum.get_json(client, URL_DEPUTADO.format(id=par[1]))["dados"]
                except httpx.HTTPError:
                    return par[0], None
                return par[0], comum_tse.cpf(dados.get("cpf"))

            with ThreadPoolExecutor(max_workers=4) as pool:
                encontrados = [(i, c) for i, c in pool.map(buscar, faltam) if c]
        for id_, valor_cpf in encontrados:
            session.execute(update(Parlamentar).where(Parlamentar.id == id_).values(cpf=valor_cpf))
        session.commit()
        return len(encontrados)


def carregar_registros(
    session: Session, registros: list[dict[str, Any]], ano: int, ingestao_id: int
) -> int:
    # Senadores sem CPF: tenta pelo nome neste arquivo.
    senadores = session.execute(
        select(Parlamentar.id, Parlamentar.uf, Parlamentar.nome_civil).where(
            Parlamentar.casa == "senado",
            Parlamentar.cpf.is_(None),
            Parlamentar.nome_civil.is_not(None),
        )
    ).all()
    for id_, valor_cpf in cpfs_de_senadores(registros, senadores).items():
        session.execute(update(Parlamentar).where(Parlamentar.id == id_).values(cpf=valor_cpf))

    por_cpf = dict(
        session.execute(
            select(Parlamentar.cpf, Parlamentar.id).where(Parlamentar.cpf.is_not(None))
        ).all()
    )
    escolhidos = [r for r in registros if r["cpf"] in por_cpf or eleito_local(r)]
    if not escolhidos:
        return 0
    municipios = mapa_municipios(session, [r for r in escolhidos if r["cargo"] == "VEREADOR"])
    linhas = [
        {
            **{k: v for k, v in r.items() if k != "codigo_ue"},
            "municipio_ibge": municipios.get((r["uf"], r["codigo_ue"])),
            "parlamentar_id": por_cpf.get(r["cpf"]) if r["cpf"] else None,
            "ingestao_id": ingestao_id,
        }
        for r in escolhidos
    ]
    for inicio in range(0, len(linhas), 2000):
        lote = linhas[inicio : inicio + 2000]
        stmt = insert(Candidatura).values(lote)
        colunas = {c: stmt.excluded[c] for c in lote[0] if c not in ("ano_eleicao", "sq_candidato")}
        session.execute(
            stmt.on_conflict_do_update(index_elements=["ano_eleicao", "sq_candidato"], set_=colunas)
        )
    # Candidaturas do ano que deixaram de ser de interesse (ex.: parlamentar saiu).
    novas = {r["sq_candidato"] for r in linhas}
    existentes = session.scalars(
        select(Candidatura.sq_candidato).where(Candidatura.ano_eleicao == ano)
    ).all()
    sobram = [sq for sq in existentes if sq not in novas]
    for inicio in range(0, len(sobram), 5000):
        session.execute(
            delete(Candidatura).where(
                Candidatura.ano_eleicao == ano,
                Candidatura.sq_candidato.in_(sobram[inicio : inicio + 5000]),
            )
        )
    return len(linhas)


def eleito_local(registro: dict[str, Any]) -> bool:
    """Eleitos para câmara municipal ou assembleia (os suplentes ficam de fora: são dezenas
    por vaga e o TSE não diz quem assumiu depois)."""
    return registro["cargo"] in CARGOS_LOCAIS and (registro["situacao_turno"] or "").startswith(
        "ELEITO"
    )


def mapa_municipios(
    session: Session, registros: list[dict[str, Any]]
) -> dict[tuple[str, str], str]:
    """(UF, código do TSE) -> código IBGE. O TSE usa um código próprio de município; a
    ligação é pelo nome + UF, como nas emendas (mesmas grafias antigas)."""
    unicos = {(r["uf"], r["codigo_ue"]): r["unidade"] for r in registros}
    municipios = session.execute(select(Municipio.ibge, Municipio.uf, Municipio.nome_chave)).all()
    resolvidos, fora = resolver_municipios(
        [
            {
                "uf": uf,
                "municipio_nome": GRAFIAS_TSE.get((uf, comum.chave_nome(nome)), nome),
                "chave": (uf, codigo),
            }
            for (uf, codigo), nome in unicos.items()
        ],
        municipios,
    )
    if fora:
        print(f"Aviso: {fora} municípios do TSE sem correspondência no IBGE")
    return {r["chave"]: r["municipio_ibge"] for r in resolvidos}


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> bytes:
        return comum.get_bytes(client, URL.format(ano=ano))

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        registros = normalizar(comum_tse.linhas(payload, "consulta_cand_"))
        if not registros:
            raise ValueError(f"Arquivo de candidaturas de {ano} vazio")
        return carregar_registros(session, registros, ano, ingestao.id)

    return comum.executar_ingestao(
        FONTE, URL.format(ano=ano), baixar, carregar, de_raw=de_raw, prefixo_raw=f"{ano}_"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=[2018, 2022])
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    print(f"CPFs de deputados obtidos na Câmara: {completar_cpfs_deputados()}")
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} candidaturas")
