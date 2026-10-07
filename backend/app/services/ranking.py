"""Lista de parlamentares com filtros e ordenação por um critério factual por vez.

Não há nota composta nem posição: a ordem padrão é alfabética e cada critério vem com
a sua definição, para o leitor saber exatamente o que está sendo ordenado.
"""

from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Parlamentar, ResumoParlamentar
from ingestion.comum import chave_nome

CRITERIOS = {
    "nome": {
        "nome": "Nome",
        "definicao": "Ordem alfabética pelo nome parlamentar.",
    },
    "gastos": {
        "nome": "Gastos do gabinete",
        "definicao": "Total reembolsado pela cota parlamentar no ano (CEAP na Câmara, CEAPS "
        "no Senado), incluindo restituições.",
    },
    "presenca": {
        "nome": "Presença em votações",
        "definicao": "Percentual das votações nominais do Plenário em que registrou voto, "
        "desde o início do ano ou do mandato atual, o que vier depois.",
    },
    "projetos": {
        "nome": "Projetos como autor principal",
        "definicao": "PL, PLP, PEC e PDL apresentados desde fevereiro de 2023 em que é o "
        "autor principal. Na Câmara, sem homenagens e datas comemorativas.",
    },
    "normas": {
        "nome": "Projetos que viraram lei ou norma",
        "definicao": "Projetos do mesmo grupo cuja situação oficial é 'transformado em "
        "norma jurídica'.",
    },
    "emendas": {
        "nome": "Emendas pagas",
        "definicao": "Valor de emendas individuais (orçamentos de 2023 em diante) pago a "
        "prefeituras, fundos municipais e entidades sem fins lucrativos.",
    },
    "governo": {
        "nome": "Votou como o Governo orientou",
        "definicao": "Percentual das votações em que o Governo orientou Sim, Não ou Obstrução "
        "e o deputado votou igual. Só Câmara.",
    },
}
POR_PAGINA = 50


def _pct(iguais: int, total: int) -> float | None:
    return round(100 * iguais / total, 1) if total else None


def _item(p: Parlamentar, r: ResumoParlamentar) -> dict:
    return {
        "id": p.id,
        "casa": p.casa,
        "nome_parlamentar": p.nome_parlamentar,
        "partido": p.partido,
        "uf": p.uf,
        "foto_url": p.foto_url,
        "gastos": float(r.gastos),
        "presenca_votou": r.presenca_votou,
        "presenca_total": r.presenca_total,
        "presenca": _pct(r.presenca_votou, r.presenca_total),
        "governo_iguais": r.governo_iguais,
        "governo_total": r.governo_total,
        "governo": _pct(r.governo_iguais, r.governo_total) if p.casa == "camara" else None,
        "partido_iguais": r.partido_iguais,
        "partido_total": r.partido_total,
        "partido_pct": _pct(r.partido_iguais, r.partido_total),
        "projetos": r.projetos,
        "homenagens": r.homenagens,
        "normas": r.normas,
        "emendas": float(r.emendas_pagas),
    }


def anos_disponiveis(session: Session) -> list[int]:
    return sorted(session.scalars(select(ResumoParlamentar.ano).distinct()), reverse=True)


def resumo_de(session: Session, parlamentar: Parlamentar, ano: int) -> dict | None:
    r = session.get(ResumoParlamentar, (parlamentar.id, ano))
    return _item(parlamentar, r) if r else None


def medias(itens: list[dict]) -> dict[str, dict[str, float | None]]:
    """Média de cada critério por casa, entre os parlamentares em exercício."""
    resultado = {}
    for casa in ("camara", "senado"):
        da_casa = [i for i in itens if i["casa"] == casa]

        def media(campo: str, itens_casa: list[dict] = da_casa) -> float | None:
            valores = [i[campo] for i in itens_casa if i[campo] is not None]
            return round(mean(valores), 1) if valores else None

        resultado[casa] = {c: media(c) for c in CRITERIOS if c != "nome"}
    return resultado


def media_partido(session: Session, casa: str, ano: int) -> float | None:
    """Média do percentual 'votou como a maioria do partido' entre os parlamentares da casa."""
    linhas = session.execute(
        select(ResumoParlamentar.partido_iguais, ResumoParlamentar.partido_total)
        .join(Parlamentar, Parlamentar.id == ResumoParlamentar.parlamentar_id)
        .where(
            Parlamentar.casa == casa,
            Parlamentar.em_exercicio,
            ResumoParlamentar.ano == ano,
            ResumoParlamentar.partido_total > 0,
        )
    ).all()
    return round(mean(100 * i / t for i, t in linhas), 1) if linhas else None


def listar(
    session: Session,
    *,
    ano: int,
    busca: str | None = None,
    casa: str | None = None,
    uf: str | None = None,
    partido: str | None = None,
    ordenar: str = "nome",
    ordem: str = "asc",
    pagina: int = 1,
) -> dict:
    linhas = session.execute(
        select(Parlamentar, ResumoParlamentar)
        .join(ResumoParlamentar, ResumoParlamentar.parlamentar_id == Parlamentar.id)
        .where(Parlamentar.em_exercicio, ResumoParlamentar.ano == ano)
    ).all()
    todos = [_item(p, r) for p, r in linhas]

    filtrados = todos
    if casa:
        filtrados = [i for i in filtrados if i["casa"] == casa]
    if uf:
        filtrados = [i for i in filtrados if i["uf"] == uf.upper()]
    if partido:
        filtrados = [i for i in filtrados if (i["partido"] or "").upper() == partido.upper()]
    if busca:
        alvo = chave_nome(busca)
        nomes = {p.id: chave_nome(f"{p.nome_parlamentar} {p.nome_civil or ''}") for p, _ in linhas}
        filtrados = [i for i in filtrados if alvo in nomes[i["id"]]]

    desc = ordem == "desc"
    if ordenar == "nome":
        filtrados.sort(key=lambda i: chave_nome(i["nome_parlamentar"]), reverse=desc)
    else:
        # Quem não tem o dado (ex.: senador no critério "governo") vai sempre para o fim.
        com = [i for i in filtrados if i[ordenar] is not None]
        sem = [i for i in filtrados if i[ordenar] is None]
        com.sort(key=lambda i: (i[ordenar], chave_nome(i["nome_parlamentar"])), reverse=desc)
        filtrados = com + sorted(sem, key=lambda i: chave_nome(i["nome_parlamentar"]))

    atualizado_em = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == "resumos", FonteIngestao.status == "ok"
        )
    )
    inicio = (pagina - 1) * POR_PAGINA
    return {
        "ano": ano,
        "anos_disponiveis": anos_disponiveis(session),
        "ordenar": ordenar,
        "ordem": ordem,
        "criterios": [{"id": k, **v} for k, v in CRITERIOS.items()],
        "medias": medias(todos),
        "partidos": sorted({i["partido"] for i in todos if i["partido"]}),
        "total": len(filtrados),
        "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "itens": filtrados[inicio : inicio + POR_PAGINA],
        "atualizado_em": atualizado_em,
    }
