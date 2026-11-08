"""Indicadores dos 27 estados para o mapa da home (protótipo A): cada um com os anos que tem,
calculado do mesmo jeito para todos (por morador com a população do IBGE do mesmo ano ou a última
anterior; dinheiro em reais do último ano completo do IPCA). Consultas agrupadas: uma por base."""

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ContasEstado,
    HomicidioSim,
    IdebResultado,
    InternetFixa,
    Municipio,
    PibIbge,
    PopulacaoIbge,
    SaneamentoCenso,
    SaudeCnes,
)
from app.services.pib import CODIGO_UF
from app.services.tempo import fatores_ipca

UF_DO_CODIGO = {c: uf for uf, c in CODIGO_UF.items()}
NOTA_GASTO = (
    "Despesa paga pelo governo do estado (sem as prefeituras), corrigida pela inflação (IPCA)."
)


def _populacoes(session: Session) -> dict[str, list[tuple[int, int]]]:
    pops: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for codigo, ano, valor in session.execute(
        select(PopulacaoIbge.codigo, PopulacaoIbge.ano, PopulacaoIbge.valor)
        .where(PopulacaoIbge.codigo.in_(list(UF_DO_CODIGO)))
        .order_by(PopulacaoIbge.ano)
    ):
        pops[codigo].append((ano, valor))
    return pops


def _pop(pops: dict, codigo: str, ano: int) -> int | None:
    validas = [v for a, v in pops.get(codigo, []) if a <= ano]
    return validas[-1] if validas else None


def _ind(
    id_, tema, grupo, rotulo, titulo, unidade, responsavel, fonte, valores, decimais=1, nota=None
):  # noqa: E501
    anos = sorted({a for por_ano in valores.values() for a in por_ano})
    return {
        "id": id_,
        "tema": tema,
        "grupo": grupo,
        "rotulo": rotulo,
        "titulo": titulo,
        "unidade": unidade,
        "responsavel": responsavel,
        "decimais": decimais,
        "fonte_nome": fonte,
        "nota": nota,
        "anos": anos,
        "valores": {
            uf: [{"ano": a, "valor": v} for a, v in sorted(por_ano.items()) if v is not None]
            for uf, por_ano in valores.items()
        },
    }


def indicadores(session: Session) -> dict:
    pops = _populacoes(session)
    ref, fat = fatores_ipca(session)
    saida = []

    # Homicídios por 100 mil moradores, por ano (anos com população).
    hom: dict[str, dict[int, float | None]] = defaultdict(dict)
    for codigo, ano, n in session.execute(
        select(HomicidioSim.codigo, HomicidioSim.ano, HomicidioSim.homicidios).where(
            HomicidioSim.codigo.in_(list(UF_DO_CODIGO))
        )
    ):
        p = _pop(pops, codigo, ano)
        if p:
            hom[UF_DO_CODIGO[codigo]][ano] = 1e5 * n / p
    saida.append(_ind("homicidios", "seguranca", "Segurança", "Homicídios por 100 mil",
                      "Homicídios por 100 mil moradores", "por 100 mil moradores", "estado",
                      "Ministério da Saúde, DATASUS (SIM)", hom,
                      nota="Por lugar de residência de quem morreu."))  # fmt: skip

    # Gasto do governo do estado por morador, por área, em reais de hoje.
    gastos: dict[str, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    for c in session.scalars(select(ContasEstado)):
        for area in ("Segurança Pública", "Saúde", "Educação"):
            v = (c.despesa_por_area or {}).get(area)
            if v is not None and c.populacao and c.ano in fat:
                gastos[area][c.uf][c.ano] = float(v) / c.populacao * fat[c.ano]
    fonte_contas = "Tesouro Nacional (SICONFI, contas anuais dos estados)"
    for area, id_, tema, grupo in (
        ("Segurança Pública", "gasto_seguranca", "seguranca", "Segurança"),
        ("Saúde", "gasto_saude", "saude", "Saúde"),
        ("Educação", "gasto_educacao", "escolas", "Escolas"),
    ):
        saida.append(_ind(id_, tema, grupo, f"Gasto em {area.lower()}",
                          f"Gasto do governo do estado em {area.lower()} por morador",
                          f"R$ de {ref} por morador", "estado", fonte_contas, gastos[area],
                          decimais=0, nota=NOTA_GASTO))  # fmt: skip

    # Leitos por mil moradores (CNES, mês mais recente).
    leitos = {}
    for r in session.scalars(select(SaudeCnes).where(SaudeCnes.codigo.in_(list(UF_DO_CODIGO)))):
        p = _pop(pops, r.codigo, r.ano)
        if p:
            leitos[UF_DO_CODIGO[r.codigo]] = {r.ano: 1000 * r.leitos / p}
    saida.append(_ind("leitos", "saude", "Saúde", "Leitos por mil",
                      "Leitos de internação por mil moradores", "por mil moradores",
                      "estado e prefeituras", "Ministério da Saúde, DATASUS (CNES)", leitos,
                      decimais=2, nota="Públicos e privados, no mês mais recente."))  # fmt: skip

    # IDEB das escolas públicas, 1º ao 5º ano.
    ideb: dict[str, dict[int, float]] = defaultdict(dict)
    for uf, ano, v in session.execute(
        select(IdebResultado.codigo, IdebResultado.ano, IdebResultado.valor).where(
            IdebResultado.abrangencia == "uf",
            IdebResultado.etapa == "iniciais",
            IdebResultado.rede == "publica",
        )
    ):
        ideb[uf][ano] = float(v)
    saida.append(_ind("ideb", "escolas", "Escolas", "IDEB 1º ao 5º ano",
                      "IDEB das escolas públicas, 1º ao 5º ano", "de 0 a 10",
                      "estado e prefeituras", "INEP (IDEB)", ideb))  # fmt: skip

    # PIB por morador, em reais de hoje.
    pib: dict[str, dict[int, float]] = defaultdict(dict)
    for codigo, ano, v in session.execute(
        select(PibIbge.codigo, PibIbge.ano, PibIbge.pib).where(
            PibIbge.codigo.in_(list(UF_DO_CODIGO))
        )
    ):
        p = next((x for a, x in pops.get(codigo, []) if a == ano), None)
        if p and ano in fat:
            pib[UF_DO_CODIGO[codigo]][ano] = float(v) * 1000 / p * fat[ano]
    saida.append(_ind("pib", "economia", "Economia", "PIB por morador", "PIB por morador",
                      f"R$ de {ref} por morador", "—", "IBGE (PIB dos Municípios)", pib,
                      decimais=0, nota="Corrigido pela inflação (IPCA)."))  # fmt: skip

    # Esgoto ligado à rede (Censo 2022).
    esgoto = {
        UF_DO_CODIGO[r.codigo]: {r.ano: float(r.esgoto_rede)}
        for r in session.scalars(
            select(SaneamentoCenso).where(SaneamentoCenso.codigo.in_(list(UF_DO_CODIGO)))
        )
        if r.esgoto_rede is not None
    }
    saida.append(_ind("esgoto", "obras", "Infraestrutura", "Esgoto na rede",
                      "% das casas com esgoto ligado à rede", "% das casas", "estado e prefeituras",
                      "IBGE (Censo 2022)", esgoto))  # fmt: skip

    # Internet fixa por 100 moradores (Anatel, mês mais recente), somando as cidades de cada UF.
    net = {}
    for uf, ano, acessos in session.execute(
        select(Municipio.uf, func.max(InternetFixa.ano), func.sum(InternetFixa.acessos))
        .join(Municipio, Municipio.ibge == InternetFixa.codigo)
        .group_by(Municipio.uf)
    ):
        p = _pop(pops, CODIGO_UF.get(uf, ""), ano)
        if p and acessos:
            net[uf] = {ano: 100 * acessos / p}
    saida.append(_ind("internet", "obras", "Infraestrutura", "Internet fixa",
                      "Acessos de internet fixa por 100 moradores", "por 100 moradores", "—",
                      "Anatel", net))  # fmt: skip

    return {"reais_de": ref, "indicadores": [i for i in saida if i["valores"]]}
