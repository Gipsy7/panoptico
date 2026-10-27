"""Montagem de dados para os testes de projetos, votações locais e pauta."""

from datetime import date, datetime

from app.models import (
    FonteIngestao,
    MandatoLocal,
    Municipio,
    Parlamentar,
    ProjetoLocal,
    Proposicao,
    Votacao,
    VotacaoLocal,
    Voto,
    VotoLocal,
)

_contador = {"n": 0}


def _proximo() -> int:
    _contador["n"] += 1
    return _contador["n"]


def ingestao(session, fonte: str, dia: date = date(2026, 10, 20)) -> FonteIngestao:
    ing = FonteIngestao(
        fonte=fonte,
        url="https://exemplo",
        arquivo_raw="x.json",
        status="ok",
        concluido_em=datetime(dia.year, dia.month, dia.day, 12, 0),
    )
    session.add(ing)
    session.flush()
    return ing


def parlamentar(session, nome: str, uf: str, partido: str, casa: str = "camara") -> Parlamentar:
    n = _proximo()
    p = Parlamentar(
        casa=casa,
        id_externo=str(9000 + n),
        nome_parlamentar=nome,
        partido=partido,
        uf=uf,
        fonte_url="https://exemplo",
        atualizado_em=datetime(2026, 10, 1),
    )
    session.add(p)
    session.flush()
    return p


def proposicao(
    session,
    id_externo: str,
    sigla: str = "PL",
    numero: int = 1,
    ano: int = 2025,
    ementa: str = "Dispõe sobre algo.",
    casa: str = "camara",
    **campos,
) -> Proposicao:
    p = Proposicao(
        casa=casa,
        id_externo=id_externo,
        sigla_tipo=sigla,
        numero=numero,
        ano=ano,
        ementa=ementa,
        data_apresentacao=campos.pop("data_apresentacao", date(ano, 3, 1)),
        url=f"https://exemplo/{id_externo}",
        **campos,
    )
    session.add(p)
    session.flush()
    return p


def votacao(
    session,
    id_externo: str,
    pid: str | None,
    data: date,
    votos: dict[int, str] | None = None,
    rotulo: str | None = None,
    ementa: str | None = None,
    descricao: str = "Aprovado o texto-base.",
    casa: str = "camara",
    **campos,
) -> Votacao:
    v = Votacao(
        casa=casa,
        id_externo=id_externo,
        data=data,
        descricao=descricao,
        proposicao=rotulo,
        proposicao_id_externo=pid,
        proposicao_ementa=ementa,
        **campos,
    )
    session.add(v)
    session.flush()
    for parlamentar_id, voto in (votos or {}).items():
        session.add(Voto(votacao_id=v.id, parlamentar_id=parlamentar_id, voto=voto))
    session.flush()
    return v


def municipio(session, ibge: str = "4205407", nome: str = "Florianópolis", uf: str = "SC"):
    m = session.get(Municipio, ibge)
    if m is None:
        m = Municipio(ibge=ibge, nome=nome, uf=uf, nome_chave=nome.upper())
        session.add(m)
        session.flush()
    return m


def mandato_local(
    session, nome: str, casa: str = "camara", uf: str = "SC", ibge: str | None = "4205407",
    partido: str = "PXX",
) -> MandatoLocal:  # fmt: skip
    if casa == "camara":
        municipio(session, ibge or "4205407")
    m = MandatoLocal(
        casa=casa,
        uf=uf,
        municipio_ibge=ibge if casa == "camara" else None,
        id_externo=str(_proximo()),
        nome=nome,
        sapl_url="https://camara.exemplo/parlamentar",
        partido=partido,
    )
    session.add(m)
    session.flush()
    return m


def projeto_local(
    session, mandato: MandatoLocal, tipo: str = "Projeto de Lei Ordinária", numero: int = 7,
    ano: int = 2026, ementa: str = "Institui a semana da saúde mental.",
) -> ProjetoLocal:  # fmt: skip
    p = ProjetoLocal(
        municipio_ibge=mandato.municipio_ibge,
        mandato_id=mandato.id,
        id_externo=str(_proximo()),
        tipo=tipo,
        numero=numero,
        ano=ano,
        ementa=ementa,
        data_apresentacao=date(ano, 2, 1),
        em_tramitacao=True,
        url="https://camara.exemplo/projeto/1",
    )
    session.add(p)
    session.flush()
    return p


def votacao_local(
    session, casa: str = "camara", uf: str = "SC", ibge: str | None = "4205407",
    materia: str = "Requerimento nº 62 de 2025", data: date = date(2026, 9, 1),
    votos: dict[int, str] | None = None, **campos,
) -> VotacaoLocal:  # fmt: skip
    if casa == "camara":
        municipio(session, ibge or "4205407")
    v = VotacaoLocal(
        casa=casa,
        uf=uf,
        municipio_ibge=ibge if casa == "camara" else None,
        id_externo=str(_proximo()),
        materia=materia,
        resultado=campos.pop("resultado", "Aprovado"),
        sim=campos.pop("sim", 8),
        nao=campos.pop("nao", 2),
        abstencoes=campos.pop("abstencoes", 0),
        data=data,
        url="https://camara.exemplo/votacao/1",
        **campos,
    )
    session.add(v)
    session.flush()
    for mandato_id, voto in (votos or {}).items():
        session.add(VotoLocal(votacao_id=v.id, mandato_id=mandato_id, voto=voto))
    session.flush()
    return v
