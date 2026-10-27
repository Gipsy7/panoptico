"""Um perfil só por pessoa: a candidatura de uma eleição cuja posse ainda não aconteceu
(hoje, 2026) aponta para o perfil de quem já está no cargo, em vez de abrir uma página
repetida. Também empresta a foto de outra candidatura da mesma pessoa a quem não tem foto.

A ligação entre candidaturas é a que o projeto já usa em `depois` e `eleito_2026`: o título de
eleitor, o CPF ou o parlamentar federal (campos internos, nunca expostos na API).
"""

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Candidatura, Foto, MandatoLocal

SEGUNDO_TURNO = "2º TURNO"


CARGOS_POSSE_1_1 = {"PRESIDENTE", "VICE-PRESIDENTE", "GOVERNADOR", "VICE-GOVERNADOR"}
# Cargos da eleição geral: só entre eles a página do mandato anterior passa a apontar para o novo.
CARGOS_GERAIS = (
    "PRESIDENTE",
    "GOVERNADOR",
    "SENADOR",
    "DEPUTADO FEDERAL",
    "DEPUTADO ESTADUAL",
    "DEPUTADO DISTRITAL",
)


def hoje() -> date:
    """Um ponto só para o dia de hoje (os testes trocam por uma data simulada)."""
    return date.today()


def data_posse(cargo: str, ano: int) -> date:
    """Presidente e governador tomam posse em 1º/1; Congresso e assembleias em 1º/2."""
    return date(ano + 1, 1 if cargo in CARGOS_POSSE_1_1 else 2, 1)


def tomou_posse(c: Candidatura) -> bool:
    return data_posse(c.cargo, c.ano_eleicao) <= hoje()


def _vencedora(c: Candidatura) -> bool:
    return (c.situacao_turno or "").startswith("ELEITO")


def pendente(c: Candidatura) -> bool:
    """Eleição cuja posse ainda não aconteceu, com o candidato eleito ou no 2º turno."""
    return (_vencedora(c) or c.situacao_turno == SEGUNDO_TURNO) and not tomou_posse(c)


def _ligacao(candidaturas: list[Candidatura]):
    """Condição SQL: candidaturas da mesma pessoa que alguma das dadas."""
    condicoes = []
    for coluna in (Candidatura.titulo, Candidatura.cpf, Candidatura.parlamentar_id):
        valores = {getattr(c, coluna.key) for c in candidaturas if getattr(c, coluna.key)}
        if valores:
            condicoes.append(coluna.in_(valores))
    return or_(*condicoes) if condicoes else None


def _mesma_pessoa(a: Candidatura, b: Candidatura) -> bool:
    return any(
        getattr(a, campo) and getattr(a, campo) == getattr(b, campo)
        for campo in ("titulo", "cpf", "parlamentar_id")
    )


def _caminho(c: Candidatura, mandatos: dict[int, MandatoLocal]) -> str | None:
    """A página que o site abre hoje para uma candidatura vencedora (ou None se não há)."""
    from app.services import tse

    if c.parlamentar_id:
        return f"/parlamentar/{c.parlamentar_id}"
    mandato = mandatos.get(c.id)
    if mandato:
        return f"/{'vereador' if mandato.casa == 'camara' else 'deputado-estadual'}/{mandato.id}"
    if c.cargo in tse.CARGOS_COM_PERFIL:
        return f"/eleito/{c.id}"
    return None


def principais(
    session: Session, candidaturas: list[Candidatura], qualquer_situacao: bool = False
) -> dict[int, str]:
    """O caminho do perfil principal de cada candidatura que tem outro perfil da mesma pessoa
    para onde mandar (as demais ficam fora do resultado e mantêm a própria página).

    - Antes da posse: a candidatura nova (eleita ou no 2º turno) aponta para o mandato em
      exercício, o mais recente que tem página. `qualquer_situacao` inclui quem não foi eleito
      (os finalistas do comparador do 2º turno).
    - Depois da posse: a página `/eleito` de um mandato anterior (eleição geral) aponta para o
      mandato novo da mesma pessoa. Perfis de parlamentar, vereador e deputado estadual não
      são redirecionados.
    """
    resultado: dict[int, str] = {}
    pend, antigos = [], []
    for c in candidaturas:
        if pendente(c) or (qualquer_situacao and not tomou_posse(c)):
            pend.append(c)
        elif _vencedora(c) and tomou_posse(c) and c.cargo in CARGOS_GERAIS:
            antigos.append(c)
    sem_direto = []
    for c in pend:
        # Já é parlamentar federal em exercício: o perfil de parlamentar é o principal.
        if c.parlamentar_id:
            resultado[c.id] = f"/parlamentar/{c.parlamentar_id}"
        else:
            sem_direto.append(c)
    alvos = sem_direto + antigos
    ligacao = _ligacao(alvos)
    if ligacao is None:
        return resultado
    vencidas = [
        v
        for v in session.scalars(
            select(Candidatura)
            .where(ligacao, Candidatura.situacao_turno.like("ELEITO%"))
            .order_by(Candidatura.ano_eleicao.desc(), Candidatura.id.desc())
        )
        if tomou_posse(v)
    ]
    if not vencidas:
        return resultado
    mandatos = {
        m.candidatura_id: m
        for m in session.scalars(
            select(MandatoLocal).where(MandatoLocal.candidatura_id.in_([v.id for v in vencidas]))
        )
    }
    for c in sem_direto:
        for anterior in vencidas:
            if _mesma_pessoa(c, anterior):
                caminho = _caminho(anterior, mandatos)
                if caminho:
                    resultado[c.id] = caminho
                    break
    for c in antigos:
        propria = _caminho(c, mandatos)
        if propria != f"/eleito/{c.id}":
            continue  # parlamentar, vereador e deputado estadual: sem redirecionamento
        for nova in vencidas:
            if nova.ano_eleicao > c.ano_eleicao and nova.cargo in CARGOS_GERAIS:
                if _mesma_pessoa(c, nova):
                    caminho = _caminho(nova, mandatos)
                    if caminho and caminho != propria:
                        resultado[c.id] = caminho
                    break
    return resultado


def fotos(session: Session, candidaturas: list[Candidatura]) -> dict[int, tuple[int, int | None]]:
    """Para cada candidatura com foto: (candidatura dona da foto, ano da foto se for de outra
    candidatura da mesma pessoa, senão None). Quem não tem foto própria usa a mais recente da
    mesma pessoa; quem não tem nenhuma fica fora do resultado."""
    if not candidaturas:
        return {}
    ids = [c.id for c in candidaturas]
    proprias = set(session.scalars(select(Foto.candidatura_id).where(Foto.candidatura_id.in_(ids))))
    resultado: dict[int, tuple[int, int | None]] = {i: (i, None) for i in proprias}
    sem = [c for c in candidaturas if c.id not in proprias]
    ligacao = _ligacao(sem)
    if ligacao is None:
        return resultado
    outras = session.execute(
        select(Candidatura)
        .join(Foto, Foto.candidatura_id == Candidatura.id)
        .where(ligacao)
        .order_by(Candidatura.ano_eleicao.desc(), Candidatura.id.desc())
    ).scalars()
    outras = list(outras)
    for c in sem:
        for o in outras:
            if _mesma_pessoa(c, o):
                resultado[c.id] = (o.id, o.ano_eleicao)
                break
    return resultado
