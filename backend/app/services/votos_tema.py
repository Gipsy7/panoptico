"""Votações nominais do Plenário por tema: em quantas o parlamentar votou, com a média da Casa.

Mesmas definições da presença geral (`services/presenca.py`):
- "Votou" é o que `presenca.votou()` aceita (Sim, Não, Abstenção, Obstrução, Votou, Artigo 17
  e a presidência da sessão).
- Votação secreta: o registro com voto em branco conta como "Votou" (e fica fora do
  alinhamento com o Governo).
- O período começa no início do ano ou no início do exercício atual, o que vier depois.
- No Senado, o código "NA" (dispositivo não citado) sai do total, como na presença.
- A média da Casa é a média do percentual entre os parlamentares em exercício; quem não
  votou no tema entra com zero.

O tema é o da própria Casa (`proposicao_tema`). Uma votação com vários temas conta em cada um.
O alinhamento com o Governo usa a mesma regra de `services/votos.py` (voto efetivo contra
orientação Sim, Não ou Obstrução).
"""

from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Parlamentar
from app.services import presenca
from app.services.votos import ORIENTACAO_VALIDA, VOTO_EFETIVO
from ingestion.proposicoes_comum import SEM_CLASSIFICACAO

_SQL_TEMAS = """
    with vt as (
        select v.id, v.data, v.secreta, t.tema
          from votacao v
          join proposicao_tema t
            on t.casa = v.casa and t.proposicao_id_externo = v.proposicao_id_externo
         where v.casa = :casa and extract(year from v.data) = :ano and t.tema <> :sem
    ), janela as (
        select p.id,
               greatest(make_date(:ano, 1, 1),
                        coalesce(p.em_exercicio_desde, make_date(:ano, 1, 1))) as inicio
          from parlamentar p
         where p.casa = :casa and (p.em_exercicio or p.id = :parlamentar_id)
    )
    select j.id as parlamentar_id, vt.tema,
           count(*) as votacoes,
           count(*) filter (where o.voto = any(:votou) or o.voto like 'Presidente%'
                              or (o.voto = '' and vt.secreta)) as votou,
           count(*) filter (where o.voto = 'NA') as fora
      from janela j
      join vt on vt.data >= j.inicio
      left join voto o on o.votacao_id = vt.id and o.parlamentar_id = j.id
     group by j.id, vt.tema
"""
_TEMAS = text(_SQL_TEMAS)

_SQL_GOVERNO = """
    select t.tema,
           count(*) as total,
           count(*) filter (where o.voto = g.orientacao) as iguais
      from voto o
      join votacao v on v.id = o.votacao_id
      join orientacao g on g.votacao_id = v.id and g.bancada = 'Governo'
      join proposicao_tema t
        on t.casa = v.casa and t.proposicao_id_externo = v.proposicao_id_externo
     where o.parlamentar_id = :parlamentar_id and v.casa = :casa
       and extract(year from v.data) = :ano and v.data >= :inicio
       and t.tema <> :sem and not v.secreta
       and o.voto = any(:efetivo) and g.orientacao = any(:orientacoes)
     group by t.tema
"""
_GOVERNO = text(_SQL_GOVERNO)


def _pct(votou: int, total: int) -> float | None:
    return round(100 * votou / total, 1) if total else None


def votos_por_tema(session: Session, parlamentar: Parlamentar, ano: int) -> dict:
    casa = parlamentar.casa
    params = {
        "casa": casa,
        "ano": ano,
        "parlamentar_id": parlamentar.id,
        "sem": SEM_CLASSIFICACAO,
        "votou": sorted(presenca.VOTOU),
    }
    linhas = session.execute(_TEMAS, params).all()

    # Média por tema entre os em exercício (a linha do próprio parlamentar entra só se ele
    # estiver em exercício).
    em_exercicio = set(
        session.scalars(
            select(Parlamentar.id).where(Parlamentar.casa == casa, Parlamentar.em_exercicio)
        )
    )
    soma_pct: dict[str, float] = {}
    soma_votou: dict[str, int] = {}
    pessoas: dict[str, int] = {}
    deste: dict[str, tuple[int, int]] = {}
    for pid, tema, votacoes, votou, fora in linhas:
        total = votacoes - (fora if casa == "senado" else 0)
        if pid == parlamentar.id:
            deste[tema] = (votou, total)
        if pid in em_exercicio and total:
            soma_pct[tema] = soma_pct.get(tema, 0.0) + 100 * votou / total
            soma_votou[tema] = soma_votou.get(tema, 0) + votou
            pessoas[tema] = pessoas.get(tema, 0) + 1

    governo = {
        tema: (iguais, total)
        for tema, total, iguais in session.execute(
            _GOVERNO,
            {
                "parlamentar_id": parlamentar.id,
                "casa": casa,
                "ano": ano,
                "inicio": presenca.inicio_periodo(parlamentar, ano),
                "sem": SEM_CLASSIFICACAO,
                "efetivo": list(VOTO_EFETIVO),
                "orientacoes": list(ORIENTACAO_VALIDA),
            },
        )
    }

    temas = []
    for tema, (votou, total) in deste.items():
        if not total:
            continue
        n = pessoas.get(tema, 0)
        iguais, total_gov = governo.get(tema, (0, 0))
        temas.append(
            {
                "tema": tema,
                "total_votacoes": total,
                "votou": votou,
                "percentual": _pct(votou, total),
                "media_casa_percentual": round(soma_pct[tema] / n, 1) if n else None,
                "media_casa_votou": round(soma_votou[tema] / n, 1) if n else None,
                "governo_iguais": iguais,
                "governo_total": total_gov,
            }
        )
    temas.sort(key=lambda t: (-t["total_votacoes"], t["tema"]))

    fonte = presenca.FONTES[casa]
    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte["fonte"], FonteIngestao.status == "ok"
        )
    )
    return {
        "ano": ano,
        "anos_disponiveis": presenca.anos_disponiveis(session, casa),
        "periodo_inicio": presenca.inicio_periodo(parlamentar, ano),
        "temas": temas,
        "fonte_nome": fonte["nome"],
        "fonte_url": fonte["url"],
        "atualizado_em": atualizado_em,
    }
