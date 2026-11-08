"""Resultado das eleições (Frente 5), a partir de `resultado_candidato` e `resultado_totais`.

Percentuais sempre sobre os votos válidos da disputa (como o TSE divulga); brancos e nulos
sobre quem compareceu. Nenhum juízo: só votos, percentuais e a situação que o TSE registrou.
Ver docs/DECISOES.md, "Eleições completas".
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Candidatura, FonteIngestao, Municipio, ResultadoCandidato, ResultadoTotais
from app.services.camaras import populacao_cidade
from ingestion.tse.resultados import EXTERIOR, MAJORITARIOS_GERAIS, PROPORCIONAIS_GERAIS

MUNICIPAIS = {"PREFEITO", "VEREADOR"}
FONTE_NOME = "TSE, dados abertos: votação por município e zona e detalhe da votação"
FONTE_URL = "https://dadosabertos.tse.jus.br/dataset/?groups=resultados"
LIMITE_PADRAO = 50


def _atualizado(session: Session):
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte.in_(("tse_resultados", "tse_comparecimento")),
            FonteIngestao.status == "ok",
        )
    )


def _fonte(session: Session) -> dict:
    return {"fonte_nome": FONTE_NOME, "fonte_url": FONTE_URL, "atualizado_em": _atualizado(session)}


def _pct(parte: int, todo: int) -> float | None:
    return round(100 * parte / todo, 2) if todo else None


def eleito(situacao: str | None) -> bool:
    return bool(situacao) and situacao.startswith("ELEITO")


def _municipio(session: Session, ibge: str | None) -> dict | None:
    if not ibge:
        return None
    m = session.execute(select(Municipio.nome, Municipio.uf).where(Municipio.ibge == ibge)).first()
    return {"ibge": ibge, "nome": m.nome, "uf": m.uf} if m else None


def _escopo(
    cargo: str, uf: str | None, municipio: str | None
) -> tuple[str, str | None, str | None]:
    """(abrangência, UF, município) da tabela pedida."""
    if cargo in MUNICIPAIS:
        return "disputa", None, municipio
    if municipio and cargo in MAJORITARIOS_GERAIS:
        return "municipio", None, municipio
    if cargo == "PRESIDENTE":
        return "disputa", "BR", None
    return "disputa", uf, None


def _totais(session: Session, ano: int, cargo: str, turno: int, uf, municipio) -> dict | None:
    filtro = [
        ResultadoTotais.ano == ano,
        ResultadoTotais.cargo == cargo,
        ResultadoTotais.turno == turno,
    ]
    if municipio:
        filtro.append(ResultadoTotais.municipio_ibge == municipio)
    elif uf and uf != "BR":
        filtro.append(ResultadoTotais.uf == uf)
    campos = ("aptos", "comparecimento", "abstencoes", "brancos", "nulos", "validos")
    linha = session.execute(
        select(*(func.sum(getattr(ResultadoTotais, c)) for c in campos)).where(*filtro)
    ).one()
    if linha[0] is None:
        return None
    t = dict(zip(campos, (int(v) for v in linha), strict=True))
    t["exterior_incluido"] = not municipio and (uf == "BR")
    t["pct_comparecimento"] = _pct(t["comparecimento"], t["aptos"])
    t["pct_brancos"] = _pct(t["brancos"], t["comparecimento"])
    t["pct_nulos"] = _pct(t["nulos"], t["comparecimento"])
    return t


def _candidatos(
    session: Session, ano, cargo, turno, abrangencia, uf, municipio, limite
) -> tuple[list[dict], int, int]:
    filtro = [
        ResultadoCandidato.ano == ano,
        ResultadoCandidato.cargo == cargo,
        ResultadoCandidato.turno == turno,
        ResultadoCandidato.abrangencia == abrangencia,
    ]
    if municipio:
        filtro.append(ResultadoCandidato.municipio_ibge == municipio)
    else:
        filtro += [ResultadoCandidato.uf == uf, ResultadoCandidato.municipio_ibge.is_(None)]
    total, soma = session.execute(
        select(func.count(), func.coalesce(func.sum(ResultadoCandidato.votos), 0)).where(*filtro)
    ).one()
    linhas = session.execute(
        select(ResultadoCandidato, Candidatura.id)
        .outerjoin(
            Candidatura,
            (Candidatura.ano_eleicao == ResultadoCandidato.ano)
            & (Candidatura.sq_candidato == ResultadoCandidato.sq_candidato),
        )
        .where(*filtro)
        .order_by(ResultadoCandidato.votos.desc(), ResultadoCandidato.nome_urna)
        .limit(limite)
    ).all()
    itens = [
        {
            "nome_urna": r.nome_urna,
            "numero": r.numero,
            "partido": r.partido,
            "votos": r.votos,
            "situacao": r.situacao,
            "eleito": eleito(r.situacao),
            "candidatura_id": cid,
        }
        for r, cid in linhas
    ]
    return itens, int(total), int(soma)


def _anteriores(session: Session, ano, cargo, abrangencia, uf, municipio) -> list[dict]:
    """Quem se elegeu, eleição a eleição, na mesma disputa (anos já carregados)."""
    filtro = [
        ResultadoCandidato.ano != ano,
        ResultadoCandidato.cargo == cargo,
        ResultadoCandidato.abrangencia == abrangencia,
        ResultadoCandidato.situacao.like("ELEITO%"),
    ]
    if municipio:
        filtro.append(ResultadoCandidato.municipio_ibge == municipio)
    else:
        filtro += [ResultadoCandidato.uf == uf, ResultadoCandidato.municipio_ibge.is_(None)]
    linhas = session.scalars(
        select(ResultadoCandidato)
        .where(*filtro)
        .order_by(
            ResultadoCandidato.ano.desc(),
            ResultadoCandidato.turno.desc(),
            ResultadoCandidato.votos.desc(),
        )
    ).all()
    por_ano: dict[int, dict] = {}
    for r in linhas:
        grupo = por_ano.setdefault(r.ano, {"ano": r.ano, "turno": r.turno, "eleitos": []})
        if r.turno != grupo["turno"]:
            continue
        grupo["eleitos"].append({"nome_urna": r.nome_urna, "partido": r.partido, "votos": r.votos})
    return list(por_ano.values())


def disponiveis(session: Session, cargo: str | None = None) -> list[dict]:
    """Anos, cargos e turnos carregados (para os seletores da página)."""
    filtro = [ResultadoTotais.cargo == cargo] if cargo else []
    linhas = session.execute(
        select(ResultadoTotais.ano, ResultadoTotais.cargo, ResultadoTotais.turno)
        .where(*filtro)
        .distinct()
        .order_by(ResultadoTotais.ano.desc(), ResultadoTotais.cargo, ResultadoTotais.turno)
    ).all()
    saida: dict[tuple[int, str], dict] = {}
    for ano, c, turno in linhas:
        saida.setdefault((ano, c), {"ano": ano, "cargo": c, "turnos": []})["turnos"].append(turno)
    return list(saida.values())


def resultado(
    session: Session,
    ano: int,
    cargo: str,
    turno: int | None = None,
    uf: str | None = None,
    municipio: str | None = None,
    limite: int = LIMITE_PADRAO,
) -> dict | None:
    cargo = cargo.upper()
    abrangencia, uf_escopo, mun_escopo = _escopo(cargo, uf, municipio)
    if cargo in MUNICIPAIS and not mun_escopo:
        return None
    if abrangencia == "disputa" and not mun_escopo and not uf_escopo:
        return None
    turnos = session.scalars(
        select(ResultadoTotais.turno)
        .where(ResultadoTotais.ano == ano, ResultadoTotais.cargo == cargo)
        .distinct()
        .order_by(ResultadoTotais.turno)
    ).all()
    if not turnos:
        return None
    if turno is None:
        turno = max(turnos)
    totais = _totais(session, ano, cargo, turno, uf_escopo, mun_escopo)
    itens, total, soma = _candidatos(
        session, ano, cargo, turno, abrangencia, uf_escopo, mun_escopo, limite
    )
    if not itens:
        # Turno 2 só existe em algumas disputas (municípios grandes, alguns estados).
        if turno != min(turnos):
            return resultado(session, ano, cargo, min(turnos), uf, municipio, limite)
        return None
    # Percentual sobre os válidos da disputa; no recorte de deputado (só os 10 mais votados), a
    # soma dos itens não é o total, então vale o total do TSE.
    base = totais["validos"] if totais else soma
    for item in itens:
        item["pct"] = _pct(item["votos"], base)
    proporcional = cargo in PROPORCIONAIS_GERAIS or cargo == "VEREADOR"
    return {
        "ano": ano,
        "cargo": cargo,
        "turno": turno,
        "turnos": list(turnos),
        "abrangencia": abrangencia,
        "uf": uf_escopo or (_municipio(session, mun_escopo) or {}).get("uf"),
        "municipio": _municipio(session, mun_escopo),
        "proporcional": proporcional,
        "totais": totais,
        "candidatos": itens,
        "total_candidatos": total,
        "anteriores": _anteriores(session, ano, cargo, abrangencia, uf_escopo, mun_escopo),
        **_fonte(session),
    }


def resultado_da_candidatura(session: Session, candidatura_id: int) -> dict | None:
    """A tabela da eleição de uma candidatura (para a carreira e o perfil do eleito)."""
    c = session.get(Candidatura, candidatura_id)
    if c is None or not c.cargo:
        return None
    cargo = c.cargo.upper()
    if cargo.startswith("VICE") or "SUPLENTE" in cargo:
        return None
    r = resultado(
        session,
        c.ano_eleicao,
        cargo,
        uf=c.uf,
        municipio=c.municipio_ibge if cargo in MUNICIPAIS else None,
    )
    if r is not None:
        r["destaque_candidatura_id"] = c.id
    return r


def mais_votados(session: Session, ibge: str, ano: int | None = None) -> dict | None:
    """Os 10 deputados (federal e estadual/distrital) mais votados no município e quanto dos
    votos daqui foram para quem se elegeu."""
    if ano is None:
        ano = session.scalar(
            select(func.max(ResultadoCandidato.ano)).where(
                ResultadoCandidato.abrangencia == "municipio",
                ResultadoCandidato.municipio_ibge == ibge,
                ResultadoCandidato.cargo.in_(PROPORCIONAIS_GERAIS),
            )
        )
    if ano is None:
        return None
    cargos = []
    for cargo in ("DEPUTADO FEDERAL", "DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL"):
        linhas = session.execute(
            select(ResultadoCandidato, Candidatura.id)
            .outerjoin(
                Candidatura,
                (Candidatura.ano_eleicao == ResultadoCandidato.ano)
                & (Candidatura.sq_candidato == ResultadoCandidato.sq_candidato),
            )
            .where(
                ResultadoCandidato.ano == ano,
                ResultadoCandidato.cargo == cargo,
                ResultadoCandidato.abrangencia == "municipio",
                ResultadoCandidato.municipio_ibge == ibge,
            )
            .order_by(ResultadoCandidato.votos.desc(), ResultadoCandidato.nome_urna)
        ).all()
        if not linhas:
            continue
        tot = session.execute(
            select(ResultadoTotais.nominais, ResultadoTotais.votos_em_eleitos).where(
                ResultadoTotais.ano == ano,
                ResultadoTotais.cargo == cargo,
                ResultadoTotais.turno == 1,
                ResultadoTotais.municipio_ibge == ibge,
            )
        ).first()
        nominais, em_eleitos = (tot.nominais, tot.votos_em_eleitos) if tot else (None, None)
        cargos.append(
            {
                "cargo": cargo,
                "nominais": nominais,
                "votos_em_eleitos": em_eleitos,
                "pct_em_eleitos": _pct(em_eleitos, nominais) if em_eleitos is not None else None,
                "itens": [
                    {
                        "posicao": i + 1,
                        "nome_urna": r.nome_urna,
                        "partido": r.partido,
                        "votos": r.votos,
                        "pct": _pct(r.votos, nominais or 0),
                        "situacao": r.situacao,
                        "eleito": eleito(r.situacao),
                        "candidatura_id": cid,
                    }
                    for i, (r, cid) in enumerate(linhas)
                ],
            }
        )
    if not cargos:
        return None
    return {"ano": ano, "municipio": _municipio(session, ibge), "cargos": cargos, **_fonte(session)}


def eleitores(session: Session, ibge: str) -> dict | None:
    """Moradores, eleitores aptos e quem votou na eleição mais recente carregada."""
    linha = session.execute(
        select(
            ResultadoTotais.ano,
            ResultadoTotais.turno,
            ResultadoTotais.cargo,
            ResultadoTotais.aptos,
            ResultadoTotais.comparecimento,
        )
        .where(ResultadoTotais.municipio_ibge == ibge, ResultadoTotais.turno == 1)
        .order_by(ResultadoTotais.ano.desc(), ResultadoTotais.aptos.desc())
        .limit(1)
    ).first()
    if linha is None or ibge == EXTERIOR:
        return None
    pop = populacao_cidade(session, ibge)
    return {
        "municipio": _municipio(session, ibge),
        "ano": linha.ano,
        "cargo_referencia": linha.cargo,
        "eleitores": linha.aptos,
        "votaram": linha.comparecimento,
        "pct_votaram": _pct(linha.comparecimento, linha.aptos),
        "populacao": pop,
        "eleitores_por_100_moradores": (
            round(100 * linha.aptos / pop["valor"]) if pop and pop["valor"] else None
        ),
        **_fonte(session),
    }


def antecessores(
    session: Session, cargo: str, uf: str | None = None, municipio: str | None = None
) -> dict | None:
    """Quem se elegeu para o cargo, eleição a eleição, na mesma cidade ou estado (só nome,
    partido e período), pelo resultado do TSE. Vereador: a lista de cada legislatura."""
    cargo = cargo.upper()
    filtro = [
        ResultadoCandidato.cargo == cargo,
        ResultadoCandidato.abrangencia == "disputa",
        ResultadoCandidato.situacao.like("ELEITO%"),
    ]
    if cargo in MUNICIPAIS:
        if not municipio:
            return None
        filtro.append(ResultadoCandidato.municipio_ibge == municipio)
    elif cargo == "PRESIDENTE":
        filtro.append(ResultadoCandidato.uf == "BR")
    elif uf:
        filtro += [ResultadoCandidato.uf == uf, ResultadoCandidato.municipio_ibge.is_(None)]
    else:
        return None
    linhas = session.execute(
        select(ResultadoCandidato, Candidatura.id)
        .outerjoin(
            Candidatura,
            (Candidatura.ano_eleicao == ResultadoCandidato.ano)
            & (Candidatura.sq_candidato == ResultadoCandidato.sq_candidato),
        )
        .where(*filtro)
        .order_by(ResultadoCandidato.ano.desc(), ResultadoCandidato.nome_urna)
    ).all()
    duracao = 8 if cargo == "SENADOR" else 4
    por_ano: dict[int, dict] = {}
    vistos: set[tuple[int, str]] = set()
    for r, cid in linhas:
        if (r.ano, r.sq_candidato) in vistos:
            continue
        vistos.add((r.ano, r.sq_candidato))
        grupo = por_ano.setdefault(
            r.ano, {"ano": r.ano, "inicio": r.ano + 1, "fim": r.ano + duracao, "pessoas": []}
        )
        grupo["pessoas"].append({"nome": r.nome_urna, "partido": r.partido, "candidatura_id": cid})
    if not por_ano:
        return None
    return {
        "cargo": cargo,
        "uf": uf,
        "municipio": _municipio(session, municipio),
        "mandatos": list(por_ano.values()),
        **_fonte(session),
    }
