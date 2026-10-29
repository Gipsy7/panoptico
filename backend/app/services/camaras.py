"""Câmaras municipais e assembleias com dados da própria casa (SAPL): quem está no cargo
hoje."""

from datetime import datetime
from decimal import Decimal
from itertools import combinations
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Candidatura,
    FonteIngestao,
    Foto,
    GastoLocal,
    GastoLocalFora,
    MandatoLocal,
    ProjetoLocal,
    VotacaoLocal,
    VotoLocal,
)
from app.services import eleitos_futuros, media_casa, tse

FONTES = {
    "camara": ("sapl_camaras", "Sistema legislativo da câmara (SAPL)"),
    "assembleia": ("sapl_assembleias", "Sistema legislativo da assembleia (SAPL)"),
}
# Assembleias com conector próprio (não usam o SAPL).
FONTES_PROPRIAS = {
    "MG": ("almg", "Dados abertos da Assembleia de Minas Gerais (ALMG)"),
    "SC": (
        "alesc",
        "E-Legis e Transparência da Assembleia Legislativa de Santa Catarina (ALESC)",
    ),
    "PR": ("alep", "Site e Portal da Transparência da Assembleia Legislativa do Paraná (ALEP)"),
    "SP": ("alesp", "Dados abertos da Assembleia de São Paulo (ALESP)"),
    "RJ": ("alerj", "Site da Assembleia Legislativa do Rio de Janeiro (ALERJ)"),
    "RS": ("alrs", "Portais da Assembleia Legislativa do Rio Grande do Sul (ALRS)"),
    "BA": ("alba", "Dados abertos da Assembleia Legislativa da Bahia (ALBA)"),
    "ES": ("ales", "Dados abertos da Assembleia Legislativa do Espírito Santo (ALES)"),
    "CE": ("alece", "Site da Assembleia Legislativa do Ceará (ALECE)"),
    "PA": ("alepa", "Site da Assembleia Legislativa do Pará (ALEPA)"),
    "MT": ("almt", "Site da Assembleia Legislativa de Mato Grosso (ALMT)"),
    "MA": ("alema", "Site e API pública da Assembleia Legislativa do Maranhão (ALEMA)"),
    "MS": (
        "alems",
        "Site e portal da transparência da Assembleia Legislativa de Mato Grosso do Sul (ALEMS)",
    ),
    "RN": (
        "alrn",
        "Site e API da Transparência Legislativa da Assembleia Legislativa do RN (ALRN)",
    ),
    "SE": ("alese", "Site e Processo Legislativo da Assembleia Legislativa de Sergipe (ALESE)"),
    "AP": ("alap", "Site e portal do eLegis da Assembleia Legislativa do Amapá (ALAP)"),
    "GO": ("alego", "Portais da Assembleia Legislativa de Goiás (ALEGO)"),
}


# Assembleias cujos gastos vêm de um portal à parte, com carga própria (ingestion/assembleias/
# gastos_*.py): fonte em fonte_ingestao, nome e endereço mostrados no rodapé da seção de gastos.
FONTES_GASTOS = {
    "BA": (
        "alba_gastos",
        "Verbas indenizatórias no site da Assembleia Legislativa da Bahia (ALBA)",
        "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias",
    ),
    "PE": (
        "alepe_gastos",
        "Verba indenizatória no portal da transparência da ALEPE",
        "https://transparencia.alepe.pe.gov.br/financas",
    ),
    "ES": (
        "ales_gastos",
        "Cotas parlamentares no portal da transparência da ALES",
        "https://www.al.es.gov.br/Transparencia/CotasParlamentares",
    ),
    "AM": (
        "aleam_gastos",
        "Controle de cota parlamentar no portal da transparência da ALEAM",
        "https://www.aleam.gov.br/transparencia/controle-de-cota-parlamentar/",
    ),
    "PB": (
        "alpb_gastos",
        "Verba indenizatória (VIAP) no portal da transparência da ALPB",
        "https://www.al.pb.leg.br/transparencia/deputados/viap-v2",
    ),
    "RO": (
        "alero_gastos",
        "Verba indenizatória no portal da transparência da ALERO",
        "https://transparencia.al.ro.leg.br/Deputados/VerbaIndenizatoria/",
    ),
}


# Câmaras que saíram do SAPL e têm conector próprio: o endereço de origem diz qual.
FONTES_DE_CAMARA = {
    # Leitores de ingestion.camaras.fornecedores_cobertura (pelo endereço-base de cada sistema).
    "/api/vereadores": ("fornecedores_cobertura_camaras", "Site da câmara (API pública do portal)"),
    "acessoinformacao/parlamentares": (
        "fornecedores_cobertura_camaras",
        "Portal da câmara (STS Informática)",
    ),
    "/site/vereadores": ("fornecedores_cobertura_camaras", "Site da câmara (modelo Cespro)"),
    "rs.leg.br/vereadores": ("fornecedores_cobertura_camaras", "Site da câmara (iCamaras)"),
    "mg.leg.br/parlamentares": (
        "fornecedores_cobertura_camaras",
        "Portal da câmara (Portal Fácil)",
    ),
    "mg.gov.br/parlamentares": (
        "fornecedores_cobertura_camaras",
        "Portal da câmara (Portal Fácil)",
    ),
    "index.php?sessao=": ("fornecedores_cobertura_camaras", "Site da câmara (Ingá Digital)"),
    # Leitores de ingestion.camaras.fornecedores_alfred (antes dos demais: "leg.br/vereadores"
    # também casaria com o endereço de Santa Maria do Cambucá).
    "camarasempapel.com.br": ("fornecedores_alfred_camaras", "Site da câmara (Câmara Sem Papel)"),
    "nopapercloud.com.br": ("fornecedores_alfred_camaras", "Site da câmara (NoPaperCloud)"),
    "varjaodeminas.mg.leg.br": ("fornecedores_alfred_camaras", "Site da câmara (Varjão de Minas)"),
    "nortelandia.mt.leg.br": ("fornecedores_alfred_camaras", "Site da câmara (Nortelândia)"),
    "santamariadocambuca.pe.leg.br": (
        "fornecedores_alfred_camaras",
        "Portal da transparência da câmara (Santa Maria do Cambucá)",
    ),
    "alvorada.to.leg.br": ("fornecedores_alfred_camaras", "Site da câmara (Alvorada)"),
    "senadorguiomard.ac.leg.br": (
        "fornecedores_robin_camaras",
        "Site da câmara (Senador Guiomard)",
    ),
    "praiagrande.sp.leg.br": (
        "fornecedores_robin_camaras",
        "Site da câmara (Praia Grande, e-Solution)",
    ),
    "palmas.to.leg.br": ("sistemas_camaras", "Site da câmara (Palmas)"),
    "teofilootoni.mg.leg.br": ("sistemas_camaras", "Site da câmara (Teófilo Otoni)"),
    "frutal.siscam.com.br": ("sistemas_camaras", "Portal da câmara (Siscam)"),
    "cittatec.com.br": ("cittatec_camaras", "Portal legislativo da câmara (Cittatec)"),
    "queimadanova.pi.leg.br": ("aos_camaras", "Site da câmara (AOS Software)"),
    "leg.br/vereador/": ("nucleogov_camaras", "Portal da câmara (Nucleogov / 7Focus)"),
    "processo-legislativo/parlamentares": (
        "portal_modelo_camaras",
        "Portal da câmara (Portal Modelo do Interlegis)",
    ),
    "leg.br/vereadores": ("portal_php_camaras", "Site da câmara (página de vereadores)"),
    "portalcr2.com.br": ("cr2_camaras", "Portal da Transparência da câmara (CR2)"),
    "pimentabueno.ro.leg.br": ("fornecedores_batgirl_camaras", "Site da câmara (Pimenta Bueno)"),
    "perdoes.mg.leg.br": ("fornecedores_batgirl_camaras", "Site da câmara (Perdões)"),
    "santacruz.pe.leg.br": ("fornecedores_batgirl_camaras", "Site da câmara (Santa Cruz)"),
}


def _fonte(casa: str, uf: str, url: str = "") -> tuple[str, str]:
    if casa == "assembleia" and uf in FONTES_PROPRIAS:
        return FONTES_PROPRIAS[uf]
    if casa == "camara":
        for dominio, fonte in FONTES_DE_CAMARA.items():
            if dominio in url:
                return fonte
    return FONTES[casa]


def _atualizado_em(session: Session, casa: str, uf: str = "") -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == _fonte(casa, uf)[0], FonteIngestao.status == "ok"
        )
    )


# Marcador no alerta da carga que manteve os gastos da carga anterior (a fonte das verbas não
# respondeu): essa carga não atualiza os gastos, então a data deles é a de uma carga sem ele.
MARCA_GASTOS_MANTIDOS = "[gastos_mantidos]"


def _gastos_atualizado_em(session: Session, casa: str, uf: str = "") -> datetime | None:
    """Data da última carga `ok` que de fato atualizou os gastos (sem o marcador de gastos
    mantidos nos alertas). Sem nenhuma, cai na data da última carga ok. Assembleia com gastos
    em carga própria (`FONTES_GASTOS`) usa a data dessa carga."""
    proprio = FONTES_GASTOS.get(uf) if casa == "assembleia" else None
    fonte = proprio[0] if proprio else _fonte(casa, uf)[0]
    cargas = session.execute(
        select(FonteIngestao.concluido_em, FonteIngestao.alertas)
        .where(FonteIngestao.fonte == fonte, FonteIngestao.status == "ok")
        .order_by(FonteIngestao.concluido_em.desc())
    ).all()
    for concluido_em, alertas in cargas:
        if not any(MARCA_GASTOS_MANTIDOS in str(a) for a in (alertas or [])):
            return concluido_em
    if proprio:
        return cargas[0][0] if cargas else None
    return _atualizado_em(session, casa, uf)


# O que o valor publicado significa, quando não é "reembolsado" (o texto padrão do site).
# Vem da própria página da Casa (ver docs/FONTES_DE_DADOS.md).
VALOR_DOS_GASTOS = {
    "ES": (
        "Valor solicitado (reservado) pelo gabinete à cota, como a ALES publica; "
        "não é necessariamente o valor pago."
    ),
    "AM": "Valor líquido (já descontada a glosa), como a ALEAM publica.",
    "RO": "Valor pago, como a ALERO publica.",
}


def _fonte_dos_gastos(m: MandatoLocal) -> dict:
    """Nome e endereço da fonte dos gastos, quando não é a mesma do resto do perfil, e o
    que o valor significa, quando a Casa publica outra coisa que não o reembolso."""
    if m.casa != "assembleia":
        return {}
    extra: dict = {}
    if m.uf in FONTES_GASTOS:
        extra |= {"fonte_nome": FONTES_GASTOS[m.uf][1], "fonte_url": FONTES_GASTOS[m.uf][2]}
    if m.uf in VALOR_DOS_GASTOS:
        extra["sobre_valor"] = VALOR_DOS_GASTOS[m.uf]
    return extra


POR_PAGINA = 20
# Registros de voto que não são voto: a pessoa estava na lista mas não votou.
NAO_VOTOU = ("não votou", "nao votou", "ausente")


def _votou() -> Any:
    return func.lower(VotoLocal.voto).not_in(NAO_VOTOU)


def _da_mesma_casa(m: MandatoLocal) -> Any:
    if m.casa == "camara":
        return MandatoLocal.municipio_ibge == m.municipio_ibge
    return (MandatoLocal.casa == "assembleia") & (MandatoLocal.uf == m.uf)


def _contar_votos(session: Session, ids: list[int]) -> dict[int, int]:
    return dict(
        session.execute(
            select(VotoLocal.mandato_id, func.count())
            .where(VotoLocal.mandato_id.in_(ids), _votou())
            .group_by(VotoLocal.mandato_id)
        ).all()
    )


def presenca(session: Session, m: MandatoLocal) -> dict | None:
    """Sessões com presença registrada durante o mandato, e a média da casa: a média do
    percentual de presença entre quem está em exercício (quem não tem sessão no período
    não entra, porque não havia como estar presente)."""
    if not m.sessoes:
        return None
    colegas = session.execute(
        select(MandatoLocal.sessoes, MandatoLocal.presencas).where(
            _da_mesma_casa(m), MandatoLocal.em_exercicio, MandatoLocal.sessoes > 0
        )
    ).all()
    percentuais = [100 * (p or 0) / s for s, p in colegas]
    return {
        "sessoes": m.sessoes,
        "presencas": m.presencas or 0,
        "media_casa": round(sum(percentuais) / len(percentuais), 1) if percentuais else None,
    }


def gastos(session: Session, m: MandatoLocal) -> dict | None:
    """Gastos do gabinete no ano mais recente com dados, por categoria, e a média da casa
    (entre quem está em exercício; quem não gastou nada entra com zero)."""
    ano = session.scalar(select(func.max(GastoLocal.ano)).where(GastoLocal.mandato_id == m.id))
    fora = session.execute(
        select(
            GastoLocalFora.ano,
            func.sum(GastoLocalFora.linhas),
            func.sum(GastoLocalFora.valor),
            func.sum(GastoLocalFora.linhas_valor_ilegivel),
            func.min(GastoLocalFora.motivo),
        )
        .where(GastoLocalFora.mandato_id == m.id)
        .group_by(GastoLocalFora.ano)
        .order_by(GastoLocalFora.ano.desc())
    ).all()
    if ano is None and not fora:
        return None
    atualizado = _gastos_atualizado_em(session, m.casa, m.uf)
    if ano is None:  # só há o que ficou fora da soma: a seção diz isso, sem número de gasto
        a, linhas, valor, ilegiveis, motivo = fora[0]
        return {
            "ano": a,
            "ate_mes": None,
            "total": Decimal(0),
            "media_casa": None,
            "por_categoria": [],
            "fora_da_soma": _fora(linhas, valor, ilegiveis, motivo),
            "atualizado_em": atualizado,
            **_fonte_dos_gastos(m),
        }
    do_ano = next((f for f in fora if f[0] == ano), None)
    categorias = session.execute(
        select(GastoLocal.categoria, func.sum(GastoLocal.valor))
        .where(GastoLocal.mandato_id == m.id, GastoLocal.ano == ano)
        .group_by(GastoLocal.categoria)
        .order_by(func.sum(GastoLocal.valor).desc())
    ).all()
    meses = session.scalar(
        select(func.max(GastoLocal.mes)).where(GastoLocal.mandato_id == m.id, GastoLocal.ano == ano)
    )
    colegas = session.scalars(
        select(MandatoLocal.id).where(_da_mesma_casa(m), MandatoLocal.em_exercicio)
    ).all()
    somas = dict(
        session.execute(
            select(GastoLocal.mandato_id, func.sum(GastoLocal.valor))
            .where(GastoLocal.mandato_id.in_(colegas), GastoLocal.ano == ano)
            .group_by(GastoLocal.mandato_id)
        ).all()
    )
    # "Consta" = tem linha na planilha do ano (inclusive só as que ficaram fora da soma).
    constam_ids = set(somas) | set(
        session.scalars(
            select(GastoLocalFora.mandato_id).where(
                GastoLocalFora.mandato_id.in_(colegas), GastoLocalFora.ano == ano
            )
        )
    )
    media = media_casa.calcular(
        [somas.get(i, Decimal(0)) for i in colegas],
        [i in constam_ids for i in colegas],
        (m.casa, m.uf) in media_casa.GASTOS_PARCIAIS,
    )
    quem, onde = media_casa.GASTOS_PARCIAIS.get((m.casa, m.uf), ("parlamentares", "na fonte"))
    return {
        "ano": ano,
        "ate_mes": meses,
        "total": sum((v for _, v in categorias), Decimal(0)),
        "media_casa": media.media,
        "media_parcial": media.parcial,
        "media_descricao": media_casa.descricao_parcial(media, quem=quem, fonte=onde),
        "por_categoria": [{"categoria": c, "valor": v} for c, v in categorias],
        "fora_da_soma": _fora(*do_ano[1:]) if do_ano else None,
        "atualizado_em": atualizado,
        **_fonte_dos_gastos(m),
    }


def _fora(linhas, valor, ilegiveis, motivo) -> dict:
    return {
        "linhas": int(linhas),
        "valor": valor or Decimal(0),
        "linhas_valor_ilegivel": int(ilegiveis or 0),
        "motivo": motivo,
    }


def votacoes(session: Session, m: MandatoLocal, pagina: int = 1) -> dict:
    """Como votou nas votações nominais da casa, das mais recentes para as mais antigas."""
    total = session.scalar(select(func.count()).where(VotoLocal.mandato_id == m.id)) or 0
    votou = session.scalar(select(func.count()).where(VotoLocal.mandato_id == m.id, _votou())) or 0
    linhas = session.execute(
        select(VotacaoLocal, VotoLocal.voto)
        .join(VotoLocal, VotoLocal.votacao_id == VotacaoLocal.id)
        .where(VotoLocal.mandato_id == m.id)
        .order_by(VotacaoLocal.data.desc().nulls_last(), VotacaoLocal.id.desc())
        .offset((pagina - 1) * POR_PAGINA)
        .limit(POR_PAGINA)
    ).all()
    da_casa = session.scalar(
        select(func.count())
        .select_from(VotacaoLocal)
        .where(
            VotacaoLocal.municipio_ibge == m.municipio_ibge
            if m.casa == "camara"
            else (VotacaoLocal.casa == "assembleia") & (VotacaoLocal.uf == m.uf)
        )
    )
    return {
        "casa_registra": bool(da_casa),
        "total": total,
        "votou": votou,
        "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "itens": [
            {
                "data": v.data,
                "materia": v.materia,
                "resultado": v.resultado,
                "sim": v.sim,
                "nao": v.nao,
                "abstencoes": v.abstencoes,
                "voto": voto,
                "url": v.url,
            }
            for v, voto in linhas
        ],
        "fonte_nome": _fonte(m.casa, m.uf, m.sapl_url)[1],
        "fonte_url": m.sapl_url,
        "atualizado_em": _atualizado_em(session, m.casa, m.uf),
    }


def _item(m: MandatoLocal, projetos: int, com_foto_tse: set[int], votos: int = 0) -> dict:
    return {
        "sessoes": m.sessoes,
        "presencas": m.presencas,
        "votacoes": votos,
        "id": m.id,
        "nome": m.nome,
        "partido": m.partido,
        "foto_url": m.foto_url,
        "foto_tse": m.candidatura_id in com_foto_tse if m.candidatura_id else False,
        "titular": m.titular,
        "em_exercicio": m.em_exercicio,
        "candidatura_id": m.candidatura_id,
        "proposicoes": sum(m.proposicoes_por_tipo.values()),
        "projetos": projetos,
    }


def camara(session: Session, ibge: str) -> dict | None:
    return _casa(session, "camara", MandatoLocal.municipio_ibge == ibge)


def assembleia(session: Session, uf: str) -> dict | None:
    return _casa(
        session, "assembleia", (MandatoLocal.casa == "assembleia") & (MandatoLocal.uf == uf)
    )


def _casa(session: Session, casa: str, filtro: Any) -> dict | None:
    mandatos = session.scalars(
        select(MandatoLocal).where(filtro, MandatoLocal.em_exercicio).order_by(MandatoLocal.nome)
    ).all()
    if not mandatos:
        return None
    projetos = dict(
        session.execute(
            select(ProjetoLocal.mandato_id, func.count())
            .where(ProjetoLocal.mandato_id.in_([m.id for m in mandatos]))
            .group_by(ProjetoLocal.mandato_id)
        ).all()
    )
    votos = _contar_votos(session, [m.id for m in mandatos])
    candidaturas = [m.candidatura_id for m in mandatos if m.candidatura_id]
    com_foto = set(
        session.scalars(select(Foto.candidatura_id).where(Foto.candidatura_id.in_(candidaturas)))
    )
    return {
        "sapl_url": mandatos[0].sapl_url,
        "itens": [_item(m, projetos.get(m.id, 0), com_foto, votos.get(m.id, 0)) for m in mandatos],
        "fonte_nome": _fonte(casa, mandatos[0].uf, mandatos[0].sapl_url)[1],
        "fonte_url": mandatos[0].sapl_url,
        "atualizado_em": _atualizado_em(session, casa, mandatos[0].uf),
    }


def vereador(session: Session, mandato: MandatoLocal) -> dict:
    projetos = session.scalars(
        select(ProjetoLocal)
        .where(ProjetoLocal.mandato_id == mandato.id)
        .order_by(ProjetoLocal.data_apresentacao.desc().nulls_last())
    ).all()
    com_foto = (
        set(
            session.scalars(
                select(Foto.candidatura_id).where(Foto.candidatura_id == mandato.candidatura_id)
            )
        )
        if mandato.candidatura_id
        else set()
    )
    origem = session.get(Candidatura, mandato.candidatura_id) if mandato.candidatura_id else None
    futuro = (
        eleitos_futuros.da_pessoa(
            session,
            parlamentar_id=origem.parlamentar_id,
            titulo=origem.titulo,
            cpf=origem.cpf,
        )
        if origem
        else None
    )
    return {
        **_item(
            mandato,
            len(projetos),
            com_foto,
            _contar_votos(session, [mandato.id]).get(mandato.id, 0),
        ),
        # Eleito para outro cargo (ou no 2º turno) numa eleição cuja posse não aconteceu: o
        # perfil de quem está no cargo hoje é este, e a eleição nova aparece nele.
        "eleito_2026": futuro,
        "eleicao_recente": tse.eleicao_recente(session, futuro, origem),
        "presenca": presenca(session, mandato),
        "gastos": gastos(session, mandato),
        "casa": mandato.casa,
        "uf": mandato.uf,
        "municipio_ibge": mandato.municipio_ibge,
        "nome_completo": mandato.nome_completo,
        "email": mandato.email,
        "telefone": mandato.telefone,
        "inicio": mandato.inicio,
        "fim": mandato.fim,
        "proposicoes_por_tipo": [
            {"tipo": tipo, "total": total}
            for tipo, total in sorted(
                mandato.proposicoes_por_tipo.items(), key=lambda item: item[1], reverse=True
            )
        ],
        "lista_projetos": [
            {
                "tipo": p.tipo,
                "numero": p.numero,
                "ano": p.ano,
                "ementa": p.ementa,
                "data_apresentacao": p.data_apresentacao,
                "em_tramitacao": p.em_tramitacao,
                "primeiro_autor": p.primeiro_autor,
                "url": p.url,
            }
            for p in projetos
        ],
        "sapl_url": mandato.sapl_url,
        "fonte_nome": _fonte(mandato.casa, mandato.uf, mandato.sapl_url)[1],
        "fonte_url": mandato.sapl_url,
        "atualizado_em": _atualizado_em(session, mandato.casa, mandato.uf),
    }


def mesma_casa(a: MandatoLocal, b: MandatoLocal) -> bool:
    if a.casa != b.casa:
        return False
    return a.municipio_ibge == b.municipio_ibge if a.casa == "camara" else a.uf == b.uf


def _lado(session: Session, m: MandatoLocal) -> dict:
    projetos = session.scalar(select(func.count()).where(ProjetoLocal.mandato_id == m.id)) or 0
    candidatura = session.get(Candidatura, m.candidatura_id) if m.candidatura_id else None
    com_foto = (
        set(
            session.scalars(
                select(Foto.candidatura_id).where(Foto.candidatura_id == m.candidatura_id)
            )
        )
        if m.candidatura_id
        else set()
    )
    return {
        **_item(m, projetos, com_foto, _contar_votos(session, [m.id]).get(m.id, 0)),
        "presenca": presenca(session, m),
        "proposicoes_por_tipo": m.proposicoes_por_tipo,
        "pessoais": tse._pessoais(session, [candidatura]) if candidatura else None,
        "votos_recebidos": candidatura.votos if candidatura else None,
    }


def comparar(session: Session, a: MandatoLocal, b: MandatoLocal) -> dict:
    """Dois parlamentares da mesma casa lado a lado e as votações nominais em que os dois
    registraram voto: em quantas votaram igual e onde divergiram."""
    va, vb = aliased(VotoLocal), aliased(VotoLocal)
    pares = session.execute(
        select(VotacaoLocal, va.voto, vb.voto)
        .join(va, va.votacao_id == VotacaoLocal.id)
        .join(vb, vb.votacao_id == VotacaoLocal.id)
        .where(
            va.mandato_id == a.id,
            vb.mandato_id == b.id,
            func.lower(va.voto).not_in(NAO_VOTOU),
            func.lower(vb.voto).not_in(NAO_VOTOU),
        )
        .order_by(VotacaoLocal.data.desc().nulls_last(), VotacaoLocal.id.desc())
    ).all()
    divergencias = [(v, x, y) for v, x, y in pares if x != y]
    tipos = sorted(set(a.proposicoes_por_tipo) | set(b.proposicoes_por_tipo))
    return {
        "casa": a.casa,
        "a": _lado(session, a),
        "b": _lado(session, b),
        "proposicoes_por_tipo": [
            {
                "tipo": t,
                "a": a.proposicoes_por_tipo.get(t, 0),
                "b": b.proposicoes_por_tipo.get(t, 0),
            }
            for t in tipos
        ],
        "votacoes_em_comum": len(pares),
        "iguais": len(pares) - len(divergencias),
        "divergencias": [
            {
                "data": v.data,
                "materia": v.materia,
                "resultado": v.resultado,
                "url": v.url,
                "voto_a": x,
                "voto_b": y,
            }
            for v, x, y in divergencias[:20]
        ],  # fmt: skip
        "fonte_nome": _fonte(a.casa, a.uf, a.sapl_url)[1],
        "fonte_url": a.sapl_url,
        "atualizado_em": _atualizado_em(session, a.casa, a.uf),
    }


def comparar_n(session: Session, mandatos: list[MandatoLocal]) -> dict:
    """De 2 a 4 parlamentares da mesma casa (o chamador valida). Uma só consulta de votos
    para todos; a convergência é montada por par (i < j)."""
    ids = [m.id for m in mandatos]
    linhas = session.execute(
        select(VotacaoLocal, VotoLocal.mandato_id, VotoLocal.voto)
        .join(VotoLocal, VotoLocal.votacao_id == VotacaoLocal.id)
        .where(VotoLocal.mandato_id.in_(ids), func.lower(VotoLocal.voto).not_in(NAO_VOTOU))
        .order_by(VotacaoLocal.data.desc().nulls_last(), VotacaoLocal.id.desc())
    ).all()
    por_votacao: dict[int, tuple[VotacaoLocal, dict[int, str]]] = {}
    for votacao, mandato_id, voto in linhas:  # já na ordem das votações
        por_votacao.setdefault(votacao.id, (votacao, {}))[1][mandato_id] = voto

    convergencia = []
    for i, j in combinations(range(len(mandatos)), 2):
        comuns = [
            (v, votos[ids[i]], votos[ids[j]])
            for v, votos in por_votacao.values()
            if ids[i] in votos and ids[j] in votos
        ]
        divergencias = [(v, x, y) for v, x, y in comuns if x != y]
        convergencia.append(
            {
                "i": i,
                "j": j,
                "votacoes_em_comum": len(comuns),
                "iguais": len(comuns) - len(divergencias),
                "divergencias": [
                    {
                        "data": v.data,
                        "materia": v.materia,
                        "resultado": v.resultado,
                        "url": v.url,
                        "voto_a": x,
                        "voto_b": y,
                    }
                    for v, x, y in divergencias[:20]
                ],  # fmt: skip
            }
        )
    tipos = sorted({t for m in mandatos for t in m.proposicoes_por_tipo})
    primeiro = mandatos[0]
    return {
        "casa": primeiro.casa,
        "pessoas": [_lado(session, m) for m in mandatos],
        "proposicoes_por_tipo": [
            {"tipo": t, "valores": [m.proposicoes_por_tipo.get(t, 0) for m in mandatos]}
            for t in tipos
        ],
        "convergencia": convergencia,
        "fonte_nome": _fonte(primeiro.casa, primeiro.uf, primeiro.sapl_url)[1],
        "fonte_url": primeiro.sapl_url,
        "atualizado_em": _atualizado_em(session, primeiro.casa, primeiro.uf),
    }
