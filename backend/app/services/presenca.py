"""Participação em votações nominais do Plenário.

O período considerado começa no início do ano ou no início do exercício atual do
parlamentar (posse, posse de suplente ou retorno), o que vier depois. Assim quem
assumiu no meio do ano não é comparado com votações de antes de assumir.
"""

from datetime import date, datetime

from sqlalchemy import extract, func, select, text
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Parlamentar, Votacao

# Registrou voto (inclui a presidência da sessão, que não vota por regimento).
VOTOU = {"Sim", "Não", "Abstenção", "Obstrução", "Votou", "Artigo 17"}
PRESENTE_SEM_VOTO = {"P-NRV", ""}
# Códigos do Senado para ausência com justificativa oficial.
JUSTIFICADA = {
    "AP": "Atividade parlamentar",
    "LS": "Licença saúde",
    "MIS": "Missão oficial",
    "LP": "Licença particular",
    "LAP": "Licença paternidade ou adotante",
}
NAO_COMPARECEU = {"NCom"}
FORA_DA_CONTA = {"NA"}  # "dispositivo não citado"

FONTES = {
    "camara": {
        "fonte": "camara_votacoes",
        "nome": "Votações nominais do Plenário (Dados Abertos da Câmara)",
        "url": "https://www.camara.leg.br/busca-portal/votacoes",
    },
    "senado": {
        "fonte": "senado_votacoes",
        "nome": "Votações nominais do Plenário (Dados Abertos do Senado)",
        "url": "https://www25.senado.leg.br/web/atividade/votacoes",
    },
}


def votou(codigo: str) -> bool:
    return codigo in VOTOU or codigo.startswith("Presidente")


def classificar(codigo: str) -> str:
    if votou(codigo):
        return "votou"
    if codigo in PRESENTE_SEM_VOTO:
        return "presente_sem_voto"
    if codigo in JUSTIFICADA:
        return "justificada"
    if codigo in NAO_COMPARECEU:
        return "nao_compareceu"
    if codigo in FORA_DA_CONTA:
        return "fora"
    return "outros"


def inicio_periodo(parlamentar: Parlamentar, ano: int) -> date:
    inicio_ano = date(ano, 1, 1)
    desde = parlamentar.em_exercicio_desde
    return max(inicio_ano, desde) if desde else inicio_ano


def anos_disponiveis(session: Session, casa: str) -> list[int]:
    ano = extract("year", Votacao.data)
    anos = session.scalars(select(ano).where(Votacao.casa == casa).distinct())
    return sorted({int(a) for a in anos}, reverse=True)


# Contagens por parlamentar numa só consulta (usada no resumo e na média da Casa).
_CONTAGENS = text(
    """
    with janela as (
        select p.id as parlamentar_id,
               greatest(make_date(:ano, 1, 1),
                        coalesce(p.em_exercicio_desde, make_date(:ano, 1, 1))) as inicio
        from parlamentar p
        where p.casa = :casa and (p.em_exercicio or p.id = :parlamentar_id)
    )
    select j.parlamentar_id,
           (select count(*) from votacao v
             where v.casa = :casa and extract(year from v.data) = :ano
               and v.data >= j.inicio) as votacoes,
           coalesce((select json_object_agg(t.voto, t.n) from (
               select o.voto, count(*) as n
                 from voto o join votacao v on v.id = o.votacao_id
                where o.parlamentar_id = j.parlamentar_id
                  and extract(year from v.data) = :ano and v.data >= j.inicio
                group by o.voto) t), '{}'::json) as votos
    from janela j
    """
)


def _resumir(casa: str, votacoes: int, votos: dict[str, int]) -> dict:
    grupos = {"votou": 0, "presente_sem_voto": 0, "justificada": 0, "nao_compareceu": 0}
    justificativas: dict[str, int] = {}
    fora = 0
    for codigo, n in votos.items():
        grupo = classificar(codigo)
        if grupo == "fora":
            fora += n
        elif grupo == "justificada":
            grupos["justificada"] += n
            justificativas[JUSTIFICADA[codigo]] = n
        elif grupo == "outros":
            grupos["nao_compareceu"] += n
        else:
            grupos[grupo] += n

    if casa == "camara":
        # A Câmara só publica quem registrou voto; o resto não tem registro.
        total = votacoes
        grupos["nao_compareceu"] = max(0, total - grupos["votou"] - grupos["presente_sem_voto"])
    else:
        # O Senado lista todos os senadores em exercício em cada votação.
        total = sum(votos.values()) - fora

    return {
        "total_votacoes": total,
        **grupos,
        "justificativas": sorted(
            ({"motivo": m, "quantidade": n} for m, n in justificativas.items()),
            key=lambda j: -j["quantidade"],
        ),
        "percentual": round(100 * grupos["votou"] / total, 1) if total else None,
    }


def resumo(session: Session, parlamentar: Parlamentar, ano: int) -> dict:
    casa = parlamentar.casa
    linhas = session.execute(
        _CONTAGENS, {"ano": ano, "casa": casa, "parlamentar_id": parlamentar.id}
    ).all()
    por_parlamentar = {pid: _resumir(casa, votacoes, votos) for pid, votacoes, votos in linhas}
    deste = por_parlamentar[parlamentar.id]

    em_exercicio = set(
        session.scalars(
            select(Parlamentar.id).where(Parlamentar.casa == casa, Parlamentar.em_exercicio)
        )
    )
    percentuais = [
        r["percentual"]
        for pid, r in por_parlamentar.items()
        if pid in em_exercicio and r["percentual"] is not None
    ]

    fonte = FONTES[casa]
    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte["fonte"], FonteIngestao.status == "ok"
        )
    )
    return {
        "ano": ano,
        "anos_disponiveis": anos_disponiveis(session, casa),
        "periodo_inicio": inicio_periodo(parlamentar, ano),
        **deste,
        "media_casa_percentual": (
            round(sum(percentuais) / len(percentuais), 1) if percentuais else None
        ),
        "ausencia_detalhada": casa == "senado",
        "fonte_nome": fonte["nome"],
        "fonte_url": fonte["url"],
        "atualizado_em": atualizado_em,
    }
