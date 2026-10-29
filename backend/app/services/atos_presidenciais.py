"""Medidas provisórias e vetos do Presidente da República no mandato em curso.

Só o titular do mandato atual (eleito em 2022, de 1º/1/2023 a 31/12/2026): vice, ex-presidentes
e candidatos de outras eleições não recebem o bloco. Sem nota nem comparação (cargo único): só a
contagem por situação, literal da fonte, e a lista (docs/DECISOES.md, "Medidas provisórias e
vetos do Presidente").
"""

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AtoPresidencial, Candidatura, FonteIngestao
from ingestion.congresso.atos_presidente import FONTE

ANO_ELEICAO_MANDATO = 2022
INICIO_MANDATO = date(ANO_ELEICAO_MANDATO + 1, 1, 1)
FIM_MANDATO = date(ANO_ELEICAO_MANDATO + 4, 12, 31)
POR_PAGINA = 20
FONTE_NOME = "Congresso Nacional (dados abertos do Senado Federal)"
FONTE_URL = {
    "mpv": "https://www.congressonacional.leg.br/materias/medidas-provisorias",
    "veto": "https://www.congressonacional.leg.br/materias/vetos",
}

# chave -> (como o cidadão lê, termo oficial)
GRUPOS_MPV = {
    "em_tramitacao": ("Ainda em análise no Congresso", "Em tramitação"),
    "aprovada": ("Aprovada pelo Congresso", "Transformada em norma jurídica"),
    "perdeu_eficacia": ("Perdeu a validade sem ser votada a tempo", "Perdeu a eficácia (caducou)"),
    "revogada": ("Cancelada por outro ato", "Revogada"),
    "rejeitada": ("Rejeitada pelo Congresso", "Rejeitada"),
    "outra": ("Outra situação", "Situação registrada pelo Congresso"),
}
GRUPOS_VETO = {
    "pendente": ("Esperando decisão do Congresso", "Veto pendente"),
    "mantido": ("Congresso manteve o veto", "Veto mantido"),
    "derrubado": ("Congresso derrubou o veto", "Veto rejeitado"),
    "mantido_em_parte": ("Congresso manteve o veto em parte", "Veto parcialmente mantido"),
    "prejudicado": ("Perdeu o objeto", "Prejudicado"),
    "outra": ("Outra situação", "Situação registrada pelo Congresso"),
}
GRUPOS = {"mpv": GRUPOS_MPV, "veto": GRUPOS_VETO}
DECISAO_VETO = {
    "MANTIDA_MATE": "mantido",
    "REJEITADO_PLENARIO": "derrubado",
    "MANTIDO_PARCIALMENTE": "mantido_em_parte",
    "PREJUDICADO": "prejudicado",
}
EXPLICACAO = {
    "mpv": (
        "Medida provisória é uma norma que o Presidente edita sozinho, em caso de urgência, e "
        "que vale como lei desde o dia em que sai. O Congresso tem até 120 dias (sem contar o "
        "recesso) para votá-la; se não votar, ela perde a validade."
    ),
    "veto": (
        "Veto é quando o Presidente recusa um projeto de lei já aprovado pelo Congresso, no "
        "todo (veto total) ou em parte (veto parcial). Depois o Congresso decide se mantém ou "
        "derruba o veto."
    ),
}
MOTIVO_NAO_TITULAR = (
    "Medidas provisórias e vetos são atos do Presidente da República; esta página não é do "
    "presidente do mandato atual (2023 a 2026)."
)


def eh_titular_do_mandato(c: Candidatura) -> bool:
    return (
        c.cargo == "PRESIDENTE"
        and c.ano_eleicao == ANO_ELEICAO_MANDATO
        and (c.situacao_turno or "").upper().startswith("ELEITO")
    )


def grupo_de(tipo: str, decisao: str | None, tramitando: bool) -> str:
    """Grupo de leitura de um ato, pelo código de decisão do Congresso e por `tramitando`."""
    d = decisao or ""
    if tipo == "veto":
        if not d:
            return "pendente" if tramitando else "outra"
        return DECISAO_VETO.get(d, "outra")
    if d == "PERDA_EFICACIA":
        return "perdeu_eficacia"
    if d == "REVOGADO":
        return "revogada"
    if d.startswith("REJEIT"):
        return "rejeitada"
    if d.startswith("APROVADO"):
        return "aprovada"
    return "em_tramitacao" if tramitando and not d else "outra"


def _atualizado(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTE, FonteIngestao.status == "ok"
        )
    )


def _contagem(session: Session, tipo: str) -> dict[str, int]:
    linhas = session.execute(
        select(AtoPresidencial.decisao, AtoPresidencial.tramitando, func.count())
        .where(AtoPresidencial.tipo == tipo)
        .group_by(AtoPresidencial.decisao, AtoPresidencial.tramitando)
    ).all()
    contagem: dict[str, int] = {}
    for decisao, tramitando, n in linhas:
        g = grupo_de(tipo, decisao, tramitando)
        contagem[g] = contagem.get(g, 0) + n
    return contagem


def _periodo() -> dict:
    return {"inicio": INICIO_MANDATO, "fim": FIM_MANDATO}


def bloco(session: Session, tipo: str) -> dict:
    """Bloco do painel (`BlocoPainel`) de MPV ou veto, para o titular do mandato."""
    contagem = _contagem(session, tipo)
    total = sum(contagem.values())
    if not total:
        nome = "medidas provisórias" if tipo == "mpv" else "vetos"
        return {
            "disponivel": False,
            "motivo": f"As {nome} do Congresso Nacional ainda não foram carregadas no site.",
        }
    dados: dict = {
        "periodo": _periodo(),
        "total": total,
        "grupos": [
            {"chave": k, "rotulo": r, "termo_oficial": o, "quantidade": contagem[k]}
            for k, (r, o) in GRUPOS[tipo].items()
            if contagem.get(k)
        ],
        "explicacao": EXPLICACAO[tipo],
    }
    if tipo == "veto":
        totais = dict(
            session.execute(
                select(AtoPresidencial.veto_total, func.count())
                .where(AtoPresidencial.tipo == "veto")
                .group_by(AtoPresidencial.veto_total)
            ).all()
        )
        dados["total_integral"] = totais.get(True, 0)
        dados["total_parcial"] = totais.get(False, 0)
    return {
        "disponivel": True,
        "dados": dados,
        "rota": None,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL[tipo],
        "atualizado_em": _atualizado(session),
    }


def lista(session: Session, tipo: str, grupo: str | None, pagina: int) -> dict:
    """Atos do tipo, do mais recente para o mais antigo, `POR_PAGINA` por página."""
    linhas = session.scalars(
        select(AtoPresidencial)
        .where(AtoPresidencial.tipo == tipo)
        .order_by(AtoPresidencial.data.desc(), AtoPresidencial.numero.desc())
    ).all()
    grupos = GRUPOS[tipo]
    itens = []
    for a in linhas:
        g = grupo_de(tipo, a.decisao, a.tramitando)
        if grupo and g != grupo:
            continue
        itens.append(
            {
                "identificacao": a.identificacao,
                "ementa": a.ementa,
                "apelido": a.apelido,
                "data": a.data,
                "data_decisao": a.data_decisao,
                "grupo": g,
                "rotulo": grupos[g][0],
                "termo_oficial": grupos[g][1],
                "situacao": a.situacao,
                "veto": None if a.veto_total is None else ("Total" if a.veto_total else "Parcial"),
                "norma_gerada": a.norma_gerada,
                "url": a.url,
            }
        )
    inicio = (pagina - 1) * POR_PAGINA
    return {
        "tipo": tipo,
        "grupo": grupo,
        "total": len(itens),
        "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "itens": itens[inicio : inicio + POR_PAGINA],
        "periodo": _periodo(),
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL[tipo],
        "atualizado_em": _atualizado(session),
    }
