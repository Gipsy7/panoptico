"""Bancadas: quantos parlamentares de cada partido, por casa legislativa.

Só contagem literal (partido e número de cadeiras). Sem juízo: nada de "maior" ou "menor".
`hoje` é quem está no cargo; `a_partir_2027` junta os eleitos de 2026, que tomam posse em
fevereiro de 2027 (ver `eleitos_futuros`).
"""

from collections import Counter
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Candidatura, FonteIngestao, MandatoLocal, Parlamentar, PartidoContaSoma
from app.partidos import SEM_PARTIDO, sigla_partido
from app.services import camaras, eleitos_futuros, tse

FONTE_CAMARA = (
    "camara_deputados",
    "Câmara dos Deputados (dados abertos)",
    "https://dadosabertos.camara.leg.br/",
)
FONTE_SENADO = (
    "senado_senadores",
    "Senado Federal (dados abertos)",
    "https://legis.senado.leg.br/dadosabertos/",
)
ELEITO = Candidatura.situacao_turno.like("ELEITO%")
CARGOS_ESTADUAIS = ("DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL")


def contar(partidos) -> list[dict]:
    """[{partido, n}] por n decrescente e sigla; partido vazio vira 'Sem partido'."""
    c = Counter(sigla_partido(p) or SEM_PARTIDO for p in partidos)
    return [{"partido": p, "n": n} for p, n in sorted(c.items(), key=lambda x: (-x[1], x[0]))]


def _data_fonte(session: Session, fontes: list[str]) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte.in_(fontes), FonteIngestao.status == "ok"
        )
    )


def _bloco(itens: list[dict], fonte_nome: str, fonte_url: str, atualizado_em, origem: str) -> dict:
    return {
        "itens": itens,
        "total": sum(i["n"] for i in itens),
        "fonte_nome": fonte_nome,
        "fonte_url": fonte_url,
        "atualizado_em": atualizado_em,
        "origem": origem,
    }


def _federal(session: Session, casa: str, uf: str | None = None) -> dict:
    chave, nome, url = FONTE_CAMARA if casa == "camara" else FONTE_SENADO
    cond = [Parlamentar.casa == casa, Parlamentar.em_exercicio]
    if uf:
        cond.append(Parlamentar.uf == uf)
    partidos = list(session.scalars(select(Parlamentar.partido).where(*cond)))
    return _bloco(contar(partidos), nome, url, _data_fonte(session, [chave]), casa)


def _eleitos_tse(session: Session, *cond) -> tuple[int | None, list[str | None]]:
    """Partidos dos eleitos da eleição mais recente já empossada que atende às condições."""
    ano = session.scalar(
        select(func.max(Candidatura.ano_eleicao)).where(*cond, ELEITO, tse.mandato_em_curso())
    )
    if ano is None:
        return None, []
    return ano, list(
        session.scalars(
            select(Candidatura.partido).where(*cond, ELEITO, Candidatura.ano_eleicao == ano)
        )
    )


def _tse_bloco(session: Session, ano: int | None, partidos: list, padrao: int) -> dict:
    return _bloco(
        contar(partidos),
        f"{tse.FONTE_NOME}: eleitos de {ano or padrao}",
        tse.URL_CANDIDATOS.format(ano=ano or padrao),
        tse._atualizado_em(session),
        "tse",
    )


def do_estado(session: Session, uf: str) -> dict:
    uf = uf.upper()
    mandatos = list(
        session.scalars(
            select(MandatoLocal).where(
                MandatoLocal.casa == "assembleia", MandatoLocal.uf == uf, MandatoLocal.em_exercicio
            )
        )
    )
    if mandatos:
        url = mandatos[0].sapl_url or ""
        assembleia = _bloco(
            contar(m.partido for m in mandatos),
            camaras._fonte("assembleia", uf, url)[1],
            url,
            camaras._atualizado_em(session, "assembleia", uf),
            "assembleia",
        )
    else:
        ano, partidos = _eleitos_tse(
            session, Candidatura.cargo.in_(CARGOS_ESTADUAIS), Candidatura.uf == uf
        )
        assembleia = _tse_bloco(session, ano, partidos, 2022)
    return {
        "uf": uf,
        "assembleia": assembleia,
        "camara_uf": _federal(session, "camara", uf),
        "senado_uf": _federal(session, "senado", uf),
    }


def do_municipio(session: Session, ibge: str) -> dict:
    mandatos = list(
        session.scalars(
            select(MandatoLocal).where(
                MandatoLocal.casa == "camara",
                MandatoLocal.municipio_ibge == ibge,
                MandatoLocal.em_exercicio,
            )
        )
    )
    if mandatos:
        url = mandatos[0].sapl_url or ""
        uf = mandatos[0].uf
        return _bloco(
            contar(m.partido for m in mandatos),
            camaras._fonte("camara", uf, url)[1],
            url,
            camaras._atualizado_em(session, "camara", uf),
            "camara",
        )
    ano, partidos = _eleitos_tse(
        session, Candidatura.cargo == "VEREADOR", Candidatura.municipio_ibge == ibge
    )
    return _tse_bloco(session, ano, partidos, 2024)


def _senadores_que_seguem(session: Session, ano_novos: int) -> list[str | None]:
    """Senadores eleitos na eleição anterior (mandato de 8 anos, ainda em curso): o partido de
    hoje, se estão no cargo; senão o da candidatura."""
    cands = list(
        session.scalars(
            select(Candidatura).where(
                Candidatura.cargo == "SENADOR",
                Candidatura.ano_eleicao == ano_novos - 4,
                ELEITO,
            )
        )
    )
    ids = [c.parlamentar_id for c in cands if c.parlamentar_id]
    atuais = (
        dict(
            session.execute(
                select(Parlamentar.id, Parlamentar.partido).where(
                    Parlamentar.id.in_(ids), Parlamentar.em_exercicio
                )
            ).all()
        )
        if ids
        else {}
    )
    return [atuais.get(c.parlamentar_id) or c.partido for c in cands]


def composicao(session: Session, casa: str) -> dict:
    base = _federal(session, casa)
    cargo = "DEPUTADO FEDERAL" if casa == "camara" else "SENADOR"
    novos = list(
        session.scalars(
            select(Candidatura).where(
                Candidatura.cargo == cargo, eleitos_futuros.pendente(), ELEITO
            )
        )
    )
    a_partir = None
    if novos:
        partidos = [c.partido for c in novos]
        if casa == "senado":
            partidos += _senadores_que_seguem(session, max(c.ano_eleicao for c in novos))
        a_partir = contar(partidos)
    ano = max((c.ano_eleicao for c in novos), default=None)
    return {
        "casa": casa,
        "hoje": base["itens"],
        "a_partir_2027": a_partir,
        "total": base["total"],
        "total_2027": sum(i["n"] for i in a_partir) if a_partir else None,
        "fonte_nome": base["fonte_nome"],
        "fonte_url": base["fonte_url"],
        "atualizado_em": base["atualizado_em"],
        "fonte_2027_nome": tse.FONTE_NOME if a_partir else None,
        "fonte_2027_url": tse.URL_CANDIDATOS.format(ano=ano) if a_partir else None,
        "atualizado_2027_em": tse._atualizado_em(session) if a_partir else None,
    }


def cadeiras_por_partido(session: Session) -> dict:
    """Por partido: deputados federais e senadores no cargo hoje, prefeitos e vereadores eleitos
    na última eleição municipal (TSE), e a sigla com que o partido aparece nas contas do TSE (para
    o link). Só partidos com ao menos uma cadeira; siglas padronizadas (`sigla_partido`)."""
    camara = {i["partido"]: i["n"] for i in _federal(session, "camara")["itens"]}
    senado = {i["partido"]: i["n"] for i in _federal(session, "senado")["itens"]}
    ano_mun = session.scalar(
        select(func.max(Candidatura.ano_eleicao)).where(Candidatura.cargo == "PREFEITO", ELEITO)
    )
    municipais: dict[str, Counter] = {"PREFEITO": Counter(), "VEREADOR": Counter()}
    if ano_mun:
        linhas = session.execute(
            select(Candidatura.cargo, Candidatura.partido, func.count())
            .where(
                Candidatura.ano_eleicao == ano_mun,
                Candidatura.cargo.in_(("PREFEITO", "VEREADOR")),
                ELEITO,
            )
            .group_by(Candidatura.cargo, Candidatura.partido)
        ).all()
        for cargo, partido, n in linhas:
            municipais[cargo][sigla_partido(partido) or SEM_PARTIDO] += n
    contas = {
        sigla_partido(p): p for p in session.scalars(select(PartidoContaSoma.partido).distinct())
    }
    siglas = set(camara) | set(senado) | set(municipais["PREFEITO"]) | set(municipais["VEREADOR"])
    itens = [
        {
            "partido": s,
            "camara": camara.get(s, 0),
            "senado": senado.get(s, 0),
            "prefeitos": municipais["PREFEITO"][s],
            "vereadores": municipais["VEREADOR"][s],
            "sigla_contas": contas.get(s),
        }
        for s in siglas
        if s != SEM_PARTIDO
    ]
    itens.sort(key=lambda i: (-i["camara"], -i["senado"], -i["vereadores"], i["partido"]))
    return {
        "itens": itens,
        "total_camara": sum(camara.values()),
        "total_senado": sum(senado.values()),
        "ano_municipal": ano_mun,
        "fontes": [
            {"nome": FONTE_CAMARA[1], "url": FONTE_CAMARA[2],
             "atualizado_em": _data_fonte(session, [FONTE_CAMARA[0]])},
            {"nome": FONTE_SENADO[1], "url": FONTE_SENADO[2],
             "atualizado_em": _data_fonte(session, [FONTE_SENADO[0]])},
            {"nome": tse.FONTE_NOME, "url": tse.URL_CANDIDATOS.format(ano=ano_mun or ""),
             "atualizado_em": tse._atualizado_em(session)},
        ],
    }  # fmt: skip
