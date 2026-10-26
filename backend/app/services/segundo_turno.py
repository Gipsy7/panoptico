"""Comparador do 2º turno: quem o eleitor encontra na urna (presidente e, se houver,
governador do estado), com os MESMOS campos para cada candidato e sem juízo.

Regras de neutralidade:
- ordem dos candidatos pelo número na urna, nunca por votos;
- todo campo existe para todos; o que a base não tem vem nulo e o site diz "não informado
  pela fonte";
- doadores pessoas físicas nunca têm nome: só a origem agregada do dinheiro (como o TSE
  classifica a receita).
"""

from datetime import date, timedelta

from sqlalchemy import and_, extract, func, or_, select
from sqlalchemy.orm import Session

from app.models import Candidatura, FonteIngestao, Parlamentar, PessoaVinculo
from app.services import cruzamentos, perfil_unico, tse
from app.services.pessoas import publicavel
from app.services.representantes import UFS

SEGUNDO_TURNO = "2º TURNO"
CARGOS = ("PRESIDENTE", "GOVERNADOR")
CANDIDATOS_POR_DISPUTA = 2
ITENS_DE_BENS = 5
# Página do TSE com o registro de cada candidatura, inclusive a proposta de governo (o
# endereço de cada candidato depende de um código da eleição que a base não guarda).
URL_DIVULGACAND = "https://divulgacandcontas.tse.jus.br/divulga/#/home"
# Cargas que alimentam os registros de punições (CGU) e de condenações (TCU).
FONTES_SANCOES = ("cgu_sancoes", "tcu_condenacoes")
CARGO_LEGIVEL = {"PRESIDENTE": "Presidente", "GOVERNADOR": "Governador"}
FONTE_RESULTADO = "tse_resultado_2_turno"
URL_RESULTADO = "https://resultados.tse.jus.br/"


def data_segundo_turno(ano: int) -> date:
    """Último domingo de outubro (Constituição, art. 77 e art. 28)."""
    dia = date(ano, 10, 31)
    return dia - timedelta(days=(dia.weekday() + 1) % 7)


def _finalista():
    """Quem disputa o 2º turno ou já tem o resultado dele. Depois da votação o TSE troca
    "2º TURNO" por ELEITO/NÃO ELEITO e a data da eleição passa a ser a do 2º turno (o
    último domingo de outubro cai sempre entre 25 e 31; o 1º turno, entre 1º e 7)."""
    return or_(
        Candidatura.situacao_turno == SEGUNDO_TURNO,
        and_(
            Candidatura.situacao_turno.in_(("ELEITO", "NÃO ELEITO")),
            extract("month", Candidatura.data_eleicao) == 10,
            extract("day", Candidatura.data_eleicao) >= 25,
        ),
    )


def _ano(session: Session, hoje: date | None = None) -> int | None:
    """A eleição deste ano, se houver 2º turno nela (no ano seguinte, a página não mostra a
    eleição passada como se fosse a próxima)."""
    return session.scalar(
        select(func.max(Candidatura.ano_eleicao)).where(
            Candidatura.cargo.in_(CARGOS),
            _finalista(),
            Candidatura.ano_eleicao >= (hoje or date.today()).year,
        )
    )


def _em_andamento(ano: int | None, hoje: date | None = None) -> bool:
    return ano is not None and (hoje or date.today()) <= data_segundo_turno(ano)


def _numero(c: Candidatura) -> tuple[int, str]:
    return (int(c.numero), "") if c.numero and c.numero.isdigit() else (10**6, c.nome_urna)


def _finalistas(session: Session, ano: int, cargo: str, uf: str | None) -> list[Candidatura]:
    condicoes = [
        Candidatura.ano_eleicao == ano,
        Candidatura.cargo == cargo,
        _finalista(),
    ]
    if uf:
        condicoes.append(Candidatura.uf == uf)
    return sorted(session.scalars(select(Candidatura).where(*condicoes)), key=_numero)


def _pessoa(session: Session, c: Candidatura) -> int | None:
    return session.scalar(
        select(PessoaVinculo.pessoa_id).where(
            PessoaVinculo.fonte == "candidatura",
            PessoaVinculo.id_externo == f"{c.ano_eleicao}:{c.sq_candidato}",
            publicavel(),
        )
    )


def _bens(session: Session, c: Candidatura, carreira: list[dict] | None) -> dict | None:
    if not tse._tem_bens(session, c.id):
        return None
    dados = tse._bens(session, c, None)
    anterior = None
    for item in carreira or []:
        if item["ano"] < c.ano_eleicao and item["bens_declarados"]:
            anterior = {
                "ano": item["ano"],
                "cargo": item["cargo"],
                "total": item["bens_total"],
            }
            break
    return {
        "ano": c.ano_eleicao,
        "total": dados["total"],
        "quantidade": dados["quantidade"],
        "maiores": dados["itens"][:ITENS_DE_BENS],
        "anterior": anterior,
        "fonte_url": dados["fonte_url"],
    }


def _campanha(session: Session, c: Candidatura) -> dict | None:
    dados = tse._campanha(session, c)
    if dados is None:
        return None
    return {
        "receitas_total": dados["receitas_total"],
        "despesas_total": dados["despesas_total"],
        "receitas_por_origem": sorted(dados["receitas_por_origem"], key=lambda x: -x["valor"]),
        "numero_doadores": dados["numero_doadores"],
        "fonte_url": dados["fonte_url"],
    }


def _foto(session: Session, c: Candidatura) -> dict:
    ref = perfil_unico.fotos(session, [c]).get(c.id)
    return {
        "foto": ref is not None,
        "foto_de": ref[0] if ref and ref[1] else None,
        "foto_ano": ref[1] if ref else None,
    }


def _vice(session: Session, c: Candidatura) -> dict | None:
    vice = session.scalars(
        select(Candidatura).where(Candidatura.chapa_titular_id == c.id).order_by(Candidatura.id)
    ).first()
    if vice is None:
        return None
    return {
        "id": vice.id,
        "nome_urna": vice.nome_urna,
        "partido": vice.partido,
        **_foto(session, vice),
    }


def _candidato(session: Session, c: Candidatura) -> dict:
    pessoa_id = _pessoa(session, c)
    carreira = cruzamentos.carreira(session, pessoa_id) if pessoa_id else None
    sancoes = cruzamentos.sancoes(session, pessoa_id) if pessoa_id else None
    itens_carreira = carreira["itens"] if carreira else None
    foto_parlamentar = (
        session.scalar(select(Parlamentar.foto_url).where(Parlamentar.id == c.parlamentar_id))
        if c.parlamentar_id
        else None
    )
    return {
        "id": c.id,
        "nome_urna": c.nome_urna,
        "numero": c.numero,
        "partido": c.partido,
        **_foto(session, c),
        "foto_url": foto_parlamentar,
        "vice": _vice(session, c),
        # A coluna guarda os votos do último turno disputado: antes do resultado, os do 1º
        # turno; depois, os do 2º. Nunca se mistura um com o outro.
        "votos_1turno": c.votos if c.situacao_turno == SEGUNDO_TURNO else None,
        "votos_2turno": c.votos if c.situacao_turno != SEGUNDO_TURNO else None,
        "eleito": None if c.situacao_turno == SEGUNDO_TURNO else c.situacao_turno == "ELEITO",
        "bens": _bens(session, c, itens_carreira),
        "campanha": _campanha(session, c),
        # Nulo quando a candidatura não está ligada a uma pessoa por vínculo seguro: aí
        # não dá para dizer quais cargos teve nem se há registros (é diferente de "nenhum").
        "carreira": [
            {
                "ano": i["ano"],
                "cargo": i["cargo"],
                "unidade": i["unidade"],
                "partido": i["partido"],
                "situacao": i["situacao"],
                "eleito": i["eleito"],
            }
            for i in itens_carreira
            if i["ano"] < c.ano_eleicao
        ]
        if itens_carreira is not None
        else None,
        "sancoes": [
            {
                "data": s["data"],
                "tipo": s["tipo"],
                "descricao": s["descricao"],
                "orgao": s["orgao"],
                "situacao": s["situacao"],
                "fonte_url": s["fonte_url"],
            }
            for s in sancoes["itens"]
        ]
        if sancoes
        else None,
        "pessoa_id": pessoa_id,
        # O perfil de quem já está no cargo, se houver; senão a página da candidatura.
        "perfil": perfil_unico.principais(session, [c], qualquer_situacao=True).get(
            c.id, f"/eleito/{c.id}"
        ),
    }


def _disputa(session: Session, ano: int, cargo: str, uf: str | None, unidade: str) -> dict:
    finalistas = _finalistas(session, ano, cargo, uf)
    faltam = max(0, CANDIDATOS_POR_DISPUTA - len(finalistas))
    return {
        "chave": cargo.lower(),
        "cargo": CARGO_LEGIVEL[cargo],
        "unidade": unidade,
        "uf": uf,
        "candidatos": [_candidato(session, c) for c in finalistas],
        "faltam": faltam,
        # Resultado publicado: nenhum finalista segue como "2º TURNO".
        "decidida": bool(finalistas) and all(c.situacao_turno != SEGUNDO_TURNO for c in finalistas),
    }


def _governador_eleito(session: Session, ano: int, uf: str) -> dict | None:
    c = session.scalars(
        select(Candidatura).where(
            Candidatura.ano_eleicao == ano,
            Candidatura.cargo == "GOVERNADOR",
            Candidatura.uf == uf,
            Candidatura.situacao_turno == "ELEITO",
        )
    ).first()
    if c is None:
        return None
    return {
        "id": c.id,
        "nome_urna": c.nome_urna,
        "partido": c.partido,
        "numero": c.numero,
        "perfil": perfil_unico.principais(session, [c], qualquer_situacao=True).get(c.id),
    }


def _resultado_totalizado_em(session: Session):
    """Momento da totalização do TSE da última carga do resultado (a data da carga é a do JSON)."""
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTE_RESULTADO, FonteIngestao.status == "ok"
        )
    )


def comparar(session: Session, uf: str) -> dict:
    """As disputas de 2º turno que um eleitor da UF encontra na urna."""
    uf = uf.upper()
    ano = _ano(session)
    disputas: list[dict] = []
    governador_1turno = None
    if ano is not None:
        presidente = _disputa(session, ano, "PRESIDENTE", None, "Brasil")
        if presidente["candidatos"]:
            disputas.append(presidente)
        governador = _disputa(session, ano, "GOVERNADOR", uf, UFS.get(uf, uf))
        if governador["candidatos"]:
            disputas.append(governador)
        else:
            governador_1turno = _governador_eleito(session, ano, uf)
    sancoes_atualizado = cruzamentos._atualizado(session, FONTES_SANCOES)
    resultado_em = (
        _resultado_totalizado_em(session) if any(d["decidida"] for d in disputas) else None
    )
    return {
        "ano_eleicao": ano,
        "data_segundo_turno": data_segundo_turno(ano) if ano else None,
        "em_andamento": _em_andamento(ano),
        "disputas": disputas,
        "governador_eleito_1turno": governador_1turno,
        "propostas_url": URL_DIVULGACAND,
        "fonte_nome": tse.FONTE_NOME,
        "fonte_url": tse.URL_CANDIDATOS.format(ano=ano or date.today().year),
        "contas_url": tse.URL_CONTAS.format(ano=ano or date.today().year),
        "atualizado_em": tse._atualizado_em(session),
        "resultado_fonte_url": URL_RESULTADO if resultado_em else None,
        "resultado_atualizado_em": resultado_em,
        "sancoes_fonte_nome": "Portal da Transparência (CGU) e Tribunal de Contas da União",
        "sancoes_fonte_url": cruzamentos.URL_SANCOES,
        "sancoes_atualizado_em": sancoes_atualizado,
    }


def agenda(session: Session) -> dict:
    """Se há 2º turno a disputar e onde: serve para o site mostrar o link só nessa época."""
    ano = _ano(session)
    if ano is None:
        return {
            "ano_eleicao": None,
            "data_segundo_turno": None,
            "em_andamento": False,
            "presidente": False,
            "ufs_governador": [],
        }
    ufs = session.scalars(
        select(Candidatura.uf)
        .where(
            Candidatura.ano_eleicao == ano,
            Candidatura.cargo == "GOVERNADOR",
            _finalista(),
        )
        .distinct()
        .order_by(Candidatura.uf)
    ).all()
    presidente = bool(
        session.scalar(
            select(func.count()).where(
                Candidatura.ano_eleicao == ano,
                Candidatura.cargo == "PRESIDENTE",
                _finalista(),
            )
        )
    )
    return {
        "ano_eleicao": ano,
        "data_segundo_turno": data_segundo_turno(ano),
        "em_andamento": _em_andamento(ano),
        "presidente": presidente,
        "ufs_governador": list(ufs),
    }
