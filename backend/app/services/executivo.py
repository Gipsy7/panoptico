"""Painel do Executivo (presidente, governador, prefeito e vices): em qual ente o cargo existe e
os números-resumo que o projeto já tem para esse ente, cada um com a data da fonte.

Cada bloco diz quando não há dado e por quê (`disponivel` falso + `motivo`): o site mostra o
que falta em vez de esconder. Os números vêm dos mesmos serviços das páginas completas.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AgendaCompromisso,
    Candidatura,
    ContasEstado,
    ContasMunicipio,
    FonteIngestao,
    Municipio,
)
from app.services import atos_presidenciais, contas, contratos_pncp, cruzamentos, emendas
from app.services import pessoas as svc_pessoas
from app.services.representantes import UFS
from ingestion.executivo.eagendas import PAGINA as URL_EAGENDAS

CARGOS = {
    "PRESIDENTE": ("uniao", True),
    "VICE-PRESIDENTE": ("uniao", False),
    "GOVERNADOR": ("estado", True),
    "VICE-GOVERNADOR": ("estado", False),
    "PREFEITO": ("municipio", True),
    "VICE-PREFEITO": ("municipio", False),
}
ROTULOS_AGENDA = {
    "reuniao": "Reunião",
    "evento": "Evento",
    "audiencia": "Audiência",
    "audiencia_publica": "Audiência pública",
    "viagem": "Viagem",
    "presente": "Presente ou hospitalidade",
}
NOTA_AGENDA = (
    "Agenda declarada pelo próprio agente ao e-Agendas (CGU) desde outubro de 2022. Só aparece "
    "quem a fonte publica como agente público federal; participantes de fora do governo "
    "aparecem pela entidade que representam, sem o nome da pessoa. A agenda do presidente da "
    "República não consta nessa base."
)
POR_PAGINA = 30
FONTE_EAGENDAS = "e-Agendas (Controladoria-Geral da União)"
FONTE_VIAGENS = "Portal da Transparência (CGU): viagens a serviço e cartão de pagamento"
FONTE_VIAGENS_URL = "https://portaldatransparencia.gov.br/"
MOTIVO_SO_UNIAO = (
    "Medidas provisórias e vetos desta seção são do Presidente da República (cargo da União)."
)


def _atualizado(session: Session, *fontes: str) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte.in_(fontes), FonteIngestao.status == "ok"
        )
    )


def _ausente(motivo: str) -> dict:
    return {"disponivel": False, "motivo": motivo}


def candidatura_executivo(session: Session, candidatura_id: int) -> Candidatura | None:
    c = session.get(Candidatura, candidatura_id)
    return c if c is not None and c.cargo in CARGOS else None


def _ente(c: Candidatura, municipio: Municipio | None) -> dict:
    tipo = CARGOS[c.cargo][0]
    if tipo == "uniao":
        return {"tipo": "uniao", "nome": "União (governo federal)", "uf": None,
                "municipio_ibge": None}  # fmt: skip
    if tipo == "estado":
        nome = UFS.get(c.uf, c.unidade)
        return {"tipo": "estado", "nome": nome, "uf": c.uf, "municipio_ibge": None}
    return {
        "tipo": "municipio",
        "nome": municipio.nome if municipio else c.unidade,
        "uf": c.uf,
        "municipio_ibge": c.municipio_ibge,
    }


def _bloco_contas(session: Session, ente: dict) -> dict:
    if ente["tipo"] == "uniao":
        return _ausente("As contas da União ainda não são carregadas.")
    if ente["tipo"] == "estado":
        r = contas.resumo_estado(session, ente["uf"])
        rota = f"/estados/{ente['uf']}/contas"
        campos = (
            "ano", "populacao", "receita_total", "despesa_paga", "despesa_por_habitante",
            "media_estados_despesa_por_habitante", "estados_na_media", "estados_sem_dado",
        )  # fmt: skip
    else:
        r = contas.resumo(session, ente["municipio_ibge"]) if ente["municipio_ibge"] else None
        rota = f"/municipios/{ente['municipio_ibge']}/contas"
        campos = (
            "ano", "populacao", "receita_total", "despesa_paga", "despesa_por_habitante",
            "media_uf_despesa_por_habitante", "municipios_na_media",
        )  # fmt: skip
    if r is None:
        # Tabela vazia = carga ainda não feita; não dá para atribuir a falta ao governo.
        tabela = ContasEstado if ente["tipo"] == "estado" else ContasMunicipio
        if session.scalar(select(tabela.ano).limit(1)) is None:
            return _ausente("As contas anuais (SICONFI) ainda não foram carregadas no site.")
        return _ausente("O ente não entregou as contas anuais ao Tesouro (SICONFI) no período.")
    return {
        "disponivel": True,
        "dados": {k: r[k] for k in campos},
        "rota": rota,
        "fonte_nome": r["fonte_nome"],
        "fonte_url": r["fonte_url"],
        "atualizado_em": r["atualizado_em"],
    }


def _bloco_emendas(session: Session, ente: dict, municipio: Municipio | None) -> dict:
    if ente["tipo"] != "municipio":
        return _ausente("O resumo de emendas recebidas existe só por município.")
    if municipio is None:
        return _ausente("Município não encontrado.")
    r = emendas.resumo_municipio(session, municipio, limite_outros=0, limite_favorecidos=0)
    if not r["total_geral"]:
        return _ausente("Nenhuma emenda parlamentar paga ao município no período coberto.")
    return {
        "disponivel": True,
        "dados": {
            "total_geral": r["total_geral"],
            "por_habitante_geral": r["por_habitante_geral"],
            "media_uf_por_habitante_geral": r["media_uf_por_habitante_geral"],
            "municipios_na_media": r["municipios_na_media"],
            "periodo": r["periodo"],
        },
        "rota": f"/municipios/{municipio.ibge}/emendas",
        "fonte_nome": r["fonte_nome"],
        "fonte_url": r["fonte_url"],
        "atualizado_em": r["atualizado_em"],
    }


def _bloco_contratos(session: Session, ente: dict) -> dict:
    if ente["tipo"] != "municipio":
        return _ausente("A soma anual de contratos do PNCP existe só por município.")
    r = contratos_pncp.maiores_do_municipio(session, ente["municipio_ibge"])
    if r is None:
        return _ausente("Sem contratos de órgãos deste município no PNCP.")
    return {
        "disponivel": True,
        "dados": {
            "ano": r["ano"],
            "maiores_fornecedores": len(r["itens"]),
            "valor_dos_maiores": sum(float(i["valor"]) for i in r["itens"]),
            "contratos_com_valor_suspeito": len(r["suspeitos"]),
            "soma_ate": r["soma_ate"],
        },
        "rota": f"/municipios/{ente['municipio_ibge']}/fornecedores-pncp",
        "fonte_nome": r["fonte_nome"],
        "fonte_url": r["fonte_url"],
        "atualizado_em": r["atualizado_em"],
    }


def _bloco_agenda(session: Session, ente: dict, pessoa_id: int | None, candidatura_id: int) -> dict:
    if ente["tipo"] != "uniao":
        return _ausente("O e-Agendas cobre só agentes do governo federal.")
    if pessoa_id is None:
        return _ausente("Pessoa sem vínculo forte com o cadastro da agenda federal.")
    filtro = AgendaCompromisso.pessoa_id == pessoa_id
    total = session.scalar(select(func.count()).select_from(AgendaCompromisso).where(filtro))
    if not total:
        if session.scalar(select(AgendaCompromisso.id).limit(1)) is None:
            return _ausente("A agenda federal (e-Agendas) ainda não foi carregada no site.")
        return _ausente(
            "Não há registros desta pessoa no e-Agendas (a agenda do presidente da República "
            "não consta nessa base)."
        )
    por_tipo = dict(
        session.execute(
            select(AgendaCompromisso.tipo, func.count())
            .where(filtro)
            .group_by(AgendaCompromisso.tipo)
        ).all()
    )
    primeiro, ultimo = session.execute(
        select(func.min(AgendaCompromisso.data_inicio), func.max(AgendaCompromisso.data_inicio))
        .where(filtro)
    ).one()  # fmt: skip
    entidade = func.jsonb_array_elements_text(AgendaCompromisso.entidades_privadas).label("e")
    soltas = (
        select(entidade)
        .where(filtro, func.jsonb_typeof(AgendaCompromisso.entidades_privadas) == "array")
        .subquery()
    )
    entidades = session.execute(
        select(soltas.c.e, func.count())
        .group_by(soltas.c.e)
        .order_by(func.count().desc())
        .limit(10)
    ).all()
    return {
        "disponivel": True,
        "dados": {
            "total": total,
            "por_tipo": {ROTULOS_AGENDA[t]: n for t, n in sorted(por_tipo.items())},
            "primeiro": primeiro,
            "ultimo": ultimo,
            "entidades_mais_citadas": [{"nome": e, "registros": n} for e, n in entidades],
            "nota": NOTA_AGENDA,
        },
        "rota": f"/executivo/{candidatura_id}/agenda",
        "fonte_nome": FONTE_EAGENDAS,
        "fonte_url": URL_EAGENDAS,
        "atualizado_em": _atualizado(session, "eagendas"),
    }


def _bloco_viagens_cartao(session: Session, ente: dict, pessoa_id: int | None) -> dict:
    if ente["tipo"] != "uniao":
        return _ausente("Viagens e cartão de pagamento do governo federal só valem para a União.")
    if pessoa_id is None:
        return _ausente("Pessoa sem vínculo forte com os cadastros do Portal da Transparência.")
    r = cruzamentos.servico_federal(session, pessoa_id)
    if r is None or not (r["viagens_por_ano"] or r["cartao_por_ano_e_orgao"]):
        return _ausente(
            "Sem viagens a serviço nem gastos no cartão de pagamento do governo federal "
            "registrados em nome desta pessoa no Portal da Transparência."
        )
    return {
        "disponivel": True,
        "dados": {
            "viagens_por_ano": r["viagens_por_ano"],
            "cartao_por_ano_e_orgao": r["cartao_por_ano_e_orgao"],
        },
        "rota": f"/pessoas/{pessoa_id}/servico-federal",
        "fonte_nome": r["fonte_nome"],
        "fonte_url": r["fonte_url"],
        "atualizado_em": r["atualizado_em"],
    }


def _bloco_ato(session: Session, ente: dict, c: Candidatura, tipo: str) -> dict:
    """MPV e vetos: só o titular do mandato de presidente em curso (vice e ex-presidentes não)."""
    if ente["tipo"] != "uniao":
        return _ausente(MOTIVO_SO_UNIAO)
    if not atos_presidenciais.eh_titular_do_mandato(c):
        return _ausente(atos_presidenciais.MOTIVO_NAO_TITULAR)
    b = atos_presidenciais.bloco(session, tipo)
    if b["disponivel"]:
        b["rota"] = f"/executivo/{c.id}/atos?tipo={tipo}"
    return b


def painel(session: Session, c: Candidatura) -> dict:
    municipio = session.get(Municipio, c.municipio_ibge) if c.municipio_ibge else None
    ente = _ente(c, municipio)
    pessoa_id = svc_pessoas.pessoa_de(session, "candidatura", c.id)
    return {
        "candidatura_id": c.id,
        "cargo": c.cargo.capitalize(),
        "titular": CARGOS[c.cargo][1],
        "nome_urna": c.nome_urna,
        "ano_eleicao": c.ano_eleicao,
        "ente": ente,
        "pessoa_id": pessoa_id,
        "contas": _bloco_contas(session, ente),
        "emendas": _bloco_emendas(session, ente, municipio),
        "contratos": _bloco_contratos(session, ente),
        "agenda": _bloco_agenda(session, ente, pessoa_id, c.id),
        "viagens_cartao": _bloco_viagens_cartao(session, ente, pessoa_id),
        "medidas_provisorias": _bloco_ato(session, ente, c, "mpv"),
        "vetos": _bloco_ato(session, ente, c, "veto"),
    }


def agenda(
    session: Session, c: Candidatura, tipo: str | None, ano: int | None, pagina: int
) -> dict:
    """Registros da agenda do e-Agendas da pessoa, do mais recente para o mais antigo."""
    pessoa_id = svc_pessoas.pessoa_de(session, "candidatura", c.id)
    filtros = [AgendaCompromisso.pessoa_id == (pessoa_id or -1)]
    if tipo:
        filtros.append(AgendaCompromisso.tipo == tipo)
    if ano:
        filtros.append(func.extract("year", AgendaCompromisso.data_inicio) == ano)
    total = session.scalar(select(func.count()).select_from(AgendaCompromisso).where(*filtros))
    linhas = session.scalars(
        select(AgendaCompromisso)
        .where(*filtros)
        .order_by(
            AgendaCompromisso.data_inicio.desc().nulls_last(),
            AgendaCompromisso.hora_inicio.desc().nulls_last(),
            AgendaCompromisso.id,
        )
        .offset((pagina - 1) * POR_PAGINA)
        .limit(POR_PAGINA)
    ).all()
    return {
        "candidatura_id": c.id,
        "pessoa_id": pessoa_id,
        "total": total or 0,
        "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "itens": [
            {
                "tipo": a.tipo,
                "rotulo": ROTULOS_AGENDA[a.tipo],
                "id_registro": a.id_registro,
                "cargo": a.cargo,
                "orgao": a.orgao,
                "data_inicio": a.data_inicio,
                "data_fim": a.data_fim,
                "hora_inicio": a.hora_inicio,
                "hora_fim": a.hora_fim,
                "forma": a.forma,
                "assunto": a.assunto,
                "local": a.local,
                "origem": a.origem,
                "destino": a.destino,
                "detalhes": a.detalhes,
                "participantes_publicos": a.participantes_publicos or [],
                "n_participantes_publicos": a.n_participantes_publicos,
                "entidades_privadas": a.entidades_privadas or [],
                "n_participantes_privados": a.n_participantes_privados,
                "url": URL_EAGENDAS,
            }
            for a in linhas
        ],
        "nota": NOTA_AGENDA,
        "fonte_nome": FONTE_EAGENDAS,
        "fonte_url": URL_EAGENDAS,
        "atualizado_em": _atualizado(session, "eagendas"),
    }
