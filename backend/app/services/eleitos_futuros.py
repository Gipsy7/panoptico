"""Eleitos que ainda não tomaram posse (hoje, a eleição de 2026), separados de quem está no cargo.

`tse.mandato_em_curso()` faz o site mostrar só quem já assumiu. Aqui fica o outro lado: a
eleição mais recente, cuja posse é no ano seguinte. Nunca se mistura com o cargo de hoje.
"""

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Candidatura, Parlamentar
from app.services import tse

SEGUNDO_TURNO = "2º TURNO"
# Data do 2º turno por ano de eleição (o TSE só traz a data do turno que decidiu).
DATA_SEGUNDO_TURNO = {2026: date(2026, 10, 25)}
CARGOS_POSSE_1_1 = {"PRESIDENTE", "VICE-PRESIDENTE", "GOVERNADOR", "VICE-GOVERNADOR"}
# Cargos que o site mostra antes da posse (os municipais só são eleitos em 2028 e 2032).
CARGOS = (
    "PRESIDENTE",
    "GOVERNADOR",
    "SENADOR",
    "DEPUTADO FEDERAL",
    "DEPUTADO ESTADUAL",
    "DEPUTADO DISTRITAL",
)
CARGO_LEGIVEL = {
    "PRESIDENTE": "Presidente",
    "GOVERNADOR": "Governador",
    "SENADOR": "Senador",
    "DEPUTADO FEDERAL": "Deputado federal",
    "DEPUTADO ESTADUAL": "Deputado estadual",
    "DEPUTADO DISTRITAL": "Deputado distrital",
}


def pendente():
    """Eleição cuja posse ainda não aconteceu: o oposto de `tse.mandato_em_curso()`."""
    return Candidatura.ano_eleicao >= date.today().year


def _decidido_ou_segundo_turno():
    return or_(
        Candidatura.situacao_turno.like("ELEITO%"), Candidatura.situacao_turno == SEGUNDO_TURNO
    )


def data_posse(cargo: str, ano: int) -> date:
    """Presidente e governador tomam posse em 1º/1; Congresso e assembleias em 1º/2."""
    return date(ano + 1, 1 if cargo in CARGOS_POSSE_1_1 else 2, 1)


def _item(c: Candidatura, em_exercicio: set[int], vice: str | None = None) -> dict:
    segundo = c.situacao_turno == SEGUNDO_TURNO
    return {
        "id": c.id,
        "nome_urna": c.nome_urna,
        "partido": c.partido,
        "numero": c.numero,
        "uf": c.uf,
        "cargo": CARGO_LEGIVEL.get(c.cargo, c.cargo.capitalize()),
        "unidade": c.unidade,
        "ano_eleicao": c.ano_eleicao,
        "situacao": "Disputa o 2º turno" if segundo else tse._situacao(c.situacao_turno),
        "situacao_tse": c.situacao_turno,
        "segundo_turno": segundo,
        "data_segundo_turno": DATA_SEGUNDO_TURNO.get(c.ano_eleicao) if segundo else None,
        "posse": data_posse(c.cargo, c.ano_eleicao),
        "votos": c.votos,
        "parlamentar_id": c.parlamentar_id,
        # Já exerce hoje um mandato federal (por exemplo, reeleito).
        "ja_no_cargo": c.parlamentar_id in em_exercicio,
        "vice": vice,
    }


def _em_exercicio(session: Session, candidaturas: list[Candidatura]) -> set[int]:
    ids = [c.parlamentar_id for c in candidaturas if c.parlamentar_id]
    if not ids:
        return set()
    return set(
        session.scalars(
            select(Parlamentar.id).where(Parlamentar.id.in_(ids), Parlamentar.em_exercicio)
        )
    )


def _itens(session: Session, candidaturas: list[Candidatura]) -> list[dict]:
    atuais = _em_exercicio(session, candidaturas)
    titulares = [c.id for c in candidaturas if c.cargo in ("GOVERNADOR", "PRESIDENTE")]
    vices: dict[int, str] = {}
    if titulares:
        vices = dict(
            session.execute(
                select(Candidatura.chapa_titular_id, Candidatura.nome_urna).where(
                    Candidatura.chapa_titular_id.in_(titulares)
                )
            ).all()
        )
    return [_item(c, atuais, vices.get(c.id)) for c in candidaturas]


def _por_cargo(session: Session, cargos: tuple[str, ...], uf: str | None) -> list[Candidatura]:
    condicoes = [Candidatura.cargo.in_(cargos), pendente(), _decidido_ou_segundo_turno()]
    if uf:
        condicoes.append(Candidatura.uf == uf)
    return list(
        session.scalars(select(Candidatura).where(*condicoes).order_by(Candidatura.nome_urna))
    )


def do_estado(session: Session, uf: str) -> dict:
    grupos = {
        "presidente": _por_cargo(session, ("PRESIDENTE",), None),
        "governador": _por_cargo(session, ("GOVERNADOR",), uf.upper()),
        "senadores": _por_cargo(session, ("SENADOR",), uf.upper()),
        "deputados_federais": _por_cargo(session, ("DEPUTADO FEDERAL",), uf.upper()),
        "deputados_estaduais": _por_cargo(
            session, ("DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL"), uf.upper()
        ),
    }
    anos = {c.ano_eleicao for lista in grupos.values() for c in lista}
    ano = max(anos) if anos else None
    return {
        "ano_eleicao": ano,
        **{nome: _itens(session, lista) for nome, lista in grupos.items()},
        "fonte_nome": tse.FONTE_NOME,
        "fonte_url": tse.URL_CANDIDATOS.format(ano=ano or date.today().year),
        "atualizado_em": tse._atualizado_em(session),
    }


def da_pessoa(
    session: Session,
    *,
    parlamentar_id: int | None = None,
    titulo: str | None = None,
    candidatura: Candidatura | None = None,
) -> dict | None:
    """A candidatura eleita (ou no 2º turno) da eleição recente de uma pessoa, ligada pelo
    parlamentar, pelo título de eleitor ou dada diretamente. Nulo se não houver."""
    if candidatura is not None and candidatura.ano_eleicao >= date.today().year:
        situacao = candidatura.situacao_turno or ""
        if situacao.startswith("ELEITO") or situacao == SEGUNDO_TURNO:
            return _itens(session, [candidatura])[0]
        return None
    ligacao = []
    if parlamentar_id:
        ligacao.append(Candidatura.parlamentar_id == parlamentar_id)
    if titulo:
        ligacao.append(Candidatura.titulo == titulo)
    if not ligacao:
        return None
    achadas = list(
        session.scalars(
            select(Candidatura).where(
                or_(*ligacao),
                pendente(),
                Candidatura.cargo.in_(CARGOS),
                _decidido_ou_segundo_turno(),
            )
        )
    )
    if not achadas:
        return None
    # Prefere a candidatura já decidida à que ainda disputa o 2º turno, e a mais recente.
    achadas.sort(key=lambda c: (c.situacao_turno == SEGUNDO_TURNO, -c.ano_eleicao))
    return _itens(session, [achadas[0]])[0]


def para_busca(session: Session, palavras: list[str], casa, limite: int) -> list[dict]:
    """Eleitos recentes (e quem está no 2º turno) achados pelo nome. `casa` é a função de
    correspondência de nomes da busca."""
    candidaturas = list(
        session.scalars(
            select(Candidatura)
            .where(
                Candidatura.cargo.in_(CARGOS),
                pendente(),
                _decidido_ou_segundo_turno(),
                casa(Candidatura.nome_urna, palavras) | casa(Candidatura.nome, palavras),
            )
            .order_by(Candidatura.nome_urna)
            .limit(limite)
        )
    )
    resultado = []
    for item in _itens(session, candidaturas):
        rotulo = (
            f"disputa o 2º turno de {item['ano_eleicao']}"
            if item["segundo_turno"]
            else f"eleito em {item['ano_eleicao']}"
        )
        resultado.append(
            {
                "nome": item["nome_urna"],
                "nome_completo": None,
                "cargo": f"{item['cargo']}, {rotulo}",
                "partido": item["partido"],
                "lugar": "Brasil" if item["cargo"] == "Presidente" else item["uf"],
                "caminho": f"/parlamentar/{item['parlamentar_id']}"
                if item["parlamentar_id"]
                else f"/eleito/{item['id']}",
            }
        )
    return resultado
