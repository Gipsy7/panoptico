"""Emendas recebidas por um município.

Três números que não se somam (docs/DECISOES.md, 2026-10-18, "Resgate de cobertura"):
- **pago** (arquivo por favorecido da CGU, `emenda_pagamento`): o que prefeitura, fundos
  municipais e entidades da cidade receberam, de todos os anos do arquivo e de todos os
  tipos. Os campos antigos da resposta (`total`, `parlamentares`, `por_ano`...) seguem só
  com as emendas individuais (com destino definido e Pix); `tipos` e `total_geral` trazem
  também bancada, comissão e relator e, desde 20/10/2026, os pagamentos sem código de
  emenda (`emenda_pagamento_sem_codigo`: tipo da fonte, sem autor nem ano), que também
  aparecem à parte em `sem_identificacao`;
- **previsto** (planos de ação das transferências especiais, TransfereGov): só os planos sem
  pagamento na CGU com a mesma chave (código da emenda + CNPJ do beneficiário) aparecem como
  "ainda sem pagamento registrado"; os outros já estão no pago;
- **convênios** (CGU): valor liberado dos convênios das emendas cujo convenente é da cidade,
  sem os que já têm pagamento na CGU com a mesma chave (pagos direto à prefeitura).
"""

import re
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    ContasMunicipio,
    Emenda,
    EmendaPagamento,
    EmendaPagamentoSemCodigo,
    EmendaTransferencia,
    FonteIngestao,
    Municipio,
    Parlamentar,
)
from app.services import emendas_estaduais
from app.services.destino_emendas import LINK_CONVENIO, LINK_ESPECIAL
from app.textos import sem_cpf
from ingestion.proposicoes_comum import INICIO_LEGISLATURA
from ingestion.transparencia.emendas import TIPOS_INDIVIDUAIS

FONTE_NOME = "Emendas parlamentares por favorecido (Portal da Transparência, CGU)"
FONTE_URL = "https://portaldatransparencia.gov.br/emendas"
FONTE_ESPECIAIS = "Planos de ação das transferências especiais (TransfereGov)"
FONTE_CONVENIOS = "Convênios das emendas (Portal da Transparência, CGU)"

SEM_AREA = "Área não informada"
VARIAS_AREAS = "Mais de uma área"

# (rótulo do dia a dia, termo oficial), na ordem de exibição.
TIPOS = {
    "individual": ("Emenda individual com destino definido",
                   "Emenda Individual - Transferências com Finalidade Definida"),
    "especial": ("Emenda Pix (transferência especial)",
                 "Emenda Individual - Transferências Especiais"),
    "bancada": ("Emenda da bancada do estado", "Emenda de Bancada"),
    "comissao": ("Emenda de comissão", "Emenda de Comissão"),
    "relator": ("Emenda do relator-geral do orçamento", "Emenda de Relator"),
}  # fmt: skip
SEM_CODIGO = (
    "Alguns pagamentos aparecem no arquivo da CGU sem o código da emenda (são emendas de "
    "2014 a 2020 que a base da CGU não identifica). A fonte informa o tipo de emenda e o mês "
    "do pagamento, mas não quem é o autor nem o ano da emenda. Esses valores estão somados "
    "no total e no tipo informado pela fonte, e não são atribuídos a nenhum autor."
)
TIPO_NAO_INFORMADO = "Tipo não informado pela fonte"
PREVISTO_DESCRICAO = (
    "Plano de ação é o valor previsto de uma emenda Pix, registrado no TransfereGov. O valor "
    "só entra no total pago quando o pagamento aparece no arquivo da CGU. Aqui ficam os "
    "planos ainda sem pagamento registrado; os outros já estão somados no pago. Planos que o "
    "TransfereGov marca como impedidos ficam de fora desta conta e aparecem à parte."
)
CONVENIOS_DESCRICAO = (
    "Convênios e contratos de repasse das emendas assinados com a prefeitura ou com entidades "
    'da cidade. "Liberado" é o que o governo federal já repassou ao convênio; o valor de um '
    "convênio pode reunir mais de uma emenda e é contado uma vez. Ficam de fora os convênios "
    "cujo pagamento já aparece no total pago, para não contar duas vezes."
)
LIMITE_PREVISTOS = 30
LIMITE_CONVENIOS = 15


def _individual() -> ColumnElement[bool]:
    # Linhas anteriores à migração 0047 não têm tipo; só existiam individuais.
    return or_(EmendaPagamento.tipo.is_(None), EmendaPagamento.tipo.in_(TIPOS_INDIVIDUAIS))


def _cnpj(texto: str | None) -> str:
    return re.sub(r"\D", "", texto or "")


def _areas(session: Session, pagamentos: list[EmendaPagamento]) -> list[dict]:
    """Soma o pago por área (função orçamentária da emenda).

    O pagamento não traz a área; ela vem da emenda. Um mesmo código de emenda pode ter
    linhas com áreas diferentes (uma por localidade), então vale a área da linha do próprio
    município; sem ela, a área única do código; e, se ainda houver mais de uma, o valor fica
    em "Mais de uma área" em vez de ser atribuído a uma delas por palpite.
    """
    codigos = {p.emenda_codigo for p in pagamentos}
    linhas = session.execute(
        select(Emenda.codigo, Emenda.municipio_ibge, Emenda.funcao).where(
            Emenda.codigo.in_(codigos)
        )
    ).all()
    por_codigo: dict[str, set[str]] = {}
    por_codigo_e_municipio: dict[tuple[str, str | None], set[str]] = {}
    for codigo, ibge, funcao in linhas:
        area = funcao or SEM_AREA
        por_codigo.setdefault(codigo, set()).add(area)
        por_codigo_e_municipio.setdefault((codigo, ibge), set()).add(area)

    somas: dict[str, Decimal] = {}
    for p in pagamentos:
        candidatas = por_codigo_e_municipio.get(
            (p.emenda_codigo, p.municipio_ibge)
        ) or por_codigo.get(p.emenda_codigo, {SEM_AREA})
        area = next(iter(candidatas)) if len(candidatas) == 1 else VARIAS_AREAS
        somas[area] = somas.get(area, Decimal(0)) + p.valor
    total = sum(somas.values(), start=Decimal(0))
    return [
        {"area": area, "total": valor, "percentual": round(100 * valor / total, 1) if total else 0}
        for area, valor in sorted(somas.items(), key=lambda item: item[1], reverse=True)
    ]


def _favorecidos(pagamentos: list[EmendaPagamento], limite: int) -> tuple[list[dict], int]:
    """Quem recebeu (prefeitura, fundos, entidades), do maior para o menor, com quem enviou."""
    grupos: dict[str, dict] = {}
    for p in pagamentos:
        g = grupos.setdefault(
            p.favorecido_codigo,
            {
                "nome": sem_cpf(p.favorecido),
                "cnpj": p.favorecido_codigo,
                "grupo": p.grupo,
                "total": Decimal(0),
                "autores": {},
            },
        )
        g["total"] += p.valor
        autor = g["autores"].setdefault(
            p.autor_nome, {"autor_nome": p.autor_nome, "parlamentar_id": None}
        )
        if p.parlamentar_id:
            autor["parlamentar_id"] = p.parlamentar_id
    ordenados = sorted(grupos.values(), key=lambda g: g["total"], reverse=True)
    for g in ordenados:
        g["autores"] = sorted(g["autores"].values(), key=lambda a: a["autor_nome"])
    return ordenados[:limite], len(ordenados)


MEDIA_UF_DESCRICAO = (
    "Média simples, entre os municípios do estado com população conhecida, das emendas "
    "recebidas desde {desde} divididas pela população; quem não recebeu entra com zero. "
    "Ficam de fora os municípios sem população nas contas do Tesouro."
)


def _populacao(session: Session, municipio: Municipio) -> int | None:
    return session.scalar(
        select(ContasMunicipio.populacao)
        .where(ContasMunicipio.municipio_ibge == municipio.ibge, ContasMunicipio.populacao > 0)
        .order_by(ContasMunicipio.ano.desc())
        .limit(1)
    )


def _media_uf(
    session: Session, municipio: Municipio, filtro: ColumnElement[bool] | None
) -> tuple[float | None, int]:
    """Média por habitante dos municípios da UF (quem não recebeu entra com zero).

    Sem filtro (todos os tipos), soma também os pagamentos sem código de emenda, como o
    `total_geral` de cada município."""
    ultimo = (
        select(
            ContasMunicipio.municipio_ibge.label("ibge"),
            func.max(ContasMunicipio.ano).label("ano"),
        )
        .where(ContasMunicipio.populacao > 0)
        .group_by(ContasMunicipio.municipio_ibge)
        .subquery()
    )
    linhas_q = select(
        EmendaPagamento.municipio_ibge.label("ibge"), EmendaPagamento.valor.label("valor")
    )
    if filtro is not None:
        linhas_q = linhas_q.where(filtro)
    else:
        linhas_q = linhas_q.union_all(
            select(
                EmendaPagamentoSemCodigo.municipio_ibge.label("ibge"),
                EmendaPagamentoSemCodigo.valor.label("valor"),
            )
        )
    linhas = linhas_q.subquery()
    pago = (
        select(linhas.c.ibge.label("ibge"), func.sum(linhas.c.valor).label("total"))
        .group_by(linhas.c.ibge)
        .subquery()
    )
    razao = func.coalesce(pago.c.total, 0) / ContasMunicipio.populacao
    media, n = session.execute(
        select(func.avg(razao), func.count())
        .select_from(Municipio)
        .join(ultimo, ultimo.c.ibge == Municipio.ibge)
        .join(
            ContasMunicipio,
            (ContasMunicipio.municipio_ibge == ultimo.c.ibge)
            & (ContasMunicipio.ano == ultimo.c.ano),
        )
        .outerjoin(pago, pago.c.ibge == Municipio.ibge)
        .where(Municipio.uf == municipio.uf)
    ).one()
    return (round(float(media), 2) if media is not None else None), n


def _autores_das_emendas(session: Session, codigos: set[str]) -> dict[str, tuple[str, int | None]]:
    """Código da emenda -> (nome do autor, parlamentar_id), do cadastro de emendas."""
    if not codigos:
        return {}
    saida: dict[str, tuple[str, int | None]] = {}
    lista = sorted(codigos)
    for inicio in range(0, len(lista), 5000):
        for codigo, nome, pid in session.execute(
            select(Emenda.codigo, Emenda.autor_nome, Emenda.parlamentar_id)
            .where(Emenda.codigo.in_(lista[inicio : inicio + 5000]))
            .order_by(Emenda.codigo, Emenda.id)
        ):
            saida.setdefault(codigo, (nome, pid))
    return saida


def _em_exercicio(session: Session, ids: set[int]) -> set[int]:
    if not ids:
        return set()
    return set(
        session.scalars(
            select(Parlamentar.id).where(Parlamentar.id.in_(ids), Parlamentar.em_exercicio)
        )
    )


def _atualizado(session: Session, fonte: str) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte, FonteIngestao.status == "ok"
        )
    )


def _impedido(situacao: str | None) -> bool:
    """Plano que a fonte marca como impedido (o TransfereGov usa IMPEDIDO e
    IMPEDIDO_REJEICAO_PLANO_TRABALHO; o outro valor é CIENTE) ou cancelado: não é previsão
    válida, então fica fora do previsto e do "com pagamento"."""
    return (situacao or "").strip().lower().startswith(("impedido", "cancelad"))


def _previsto(session: Session, ibge: str, pagos: set[tuple[str, str]]) -> dict | None:
    """Planos das transferências especiais da cidade; os sem pagamento na CGU, à parte."""
    planos = session.scalars(
        select(EmendaTransferencia)
        .where(EmendaTransferencia.tipo == "especial", EmendaTransferencia.municipio_ibge == ibge)
        .order_by(EmendaTransferencia.ano_emenda.desc(), EmendaTransferencia.identificador)
    ).all()
    if not planos:
        return None
    unicos = {(p.identificador, p.emenda_codigo): p for p in planos}.values()
    com, sem, fora = [], [], []
    for p in unicos:
        if _impedido(p.situacao):
            fora.append(p)
            continue
        chave = (p.emenda_codigo, _cnpj(p.beneficiario_cnpj))
        (com if chave in pagos else sem).append(p)
    autores = _autores_das_emendas(session, {p.emenda_codigo for p in sem})
    exercicio = _em_exercicio(session, {pid for _, pid in autores.values() if pid})
    itens = []
    for p in sorted(sem, key=lambda p: p.valor_total or 0, reverse=True):
        nome, pid = autores.get(p.emenda_codigo, (None, None))
        itens.append(
            {
                "identificador": p.identificador,
                "emenda_codigo": p.emenda_codigo,
                "ano": p.ano_emenda,
                "autor_nome": nome,
                "parlamentar_id": pid,
                "com_mandato_atual": pid in exercicio,
                "beneficiario": sem_cpf(p.beneficiario),
                "situacao": p.situacao,
                "valor": p.valor_total or 0,
                "fonte_url": LINK_ESPECIAL.format(codigo=p.identificador),
            }
        )

    def soma(lista: list[EmendaTransferencia]) -> Decimal:
        return sum((p.valor_total or Decimal(0) for p in lista), start=Decimal(0))

    por_motivo: dict[str, list[EmendaTransferencia]] = {}
    for p in fora:
        por_motivo.setdefault(p.situacao or "Sem situação", []).append(p)
    impedidos = (
        {
            "planos": len(fora),
            "valor": soma(fora),
            "motivos": [
                {"situacao": m, "planos": len(ps), "valor": soma(ps)}
                for m, ps in sorted(por_motivo.items())
            ],
        }
        if fora
        else None
    )
    return {
        "planos": len(com) + len(sem),
        "valor_planos": soma(com) + soma(sem),
        "impedidos": impedidos,
        "planos_com_pagamento": len(com),
        "valor_planos_com_pagamento": soma(com),
        "planos_sem_pagamento": len(sem),
        "valor_sem_pagamento": soma(sem),
        "sem_pagamento": itens[:LIMITE_PREVISTOS],
        "descricao": PREVISTO_DESCRICAO,
        "fonte_nome": FONTE_ESPECIAIS,
        "fonte_url": LINK_ESPECIAL.split("?")[0],
        "atualizado_em": _atualizado(session, "transferegov_especiais"),
    }


def _convenios(session: Session, ibge: str, pagos: set[tuple[str, str]]) -> dict | None:
    """Convênios das emendas com convenente da cidade, sem os que já estão no pago."""
    linhas = session.scalars(
        select(EmendaTransferencia).where(
            EmendaTransferencia.tipo == "convenio", EmendaTransferencia.municipio_ibge == ibge
        )
    ).all()
    if not linhas:
        return None
    por_convenio: dict[str, list[EmendaTransferencia]] = {}
    for t in linhas:
        por_convenio.setdefault(t.identificador, []).append(t)
    fora = {
        numero
        for numero, ts in por_convenio.items()
        if any((t.emenda_codigo, _cnpj(t.beneficiario_cnpj)) in pagos for t in ts)
    }
    restantes = {n: ts for n, ts in por_convenio.items() if n not in fora}
    autores = _autores_das_emendas(
        session, {t.emenda_codigo for ts in restantes.values() for t in ts}
    )
    itens = []
    for numero, ts in restantes.items():
        t = ts[0]  # os dados do convênio são os mesmos em todas as linhas
        itens.append(
            {
                "identificador": numero,
                "emendas": sorted({x.emenda_codigo for x in ts}),
                "autores": sorted(
                    {autores[x.emenda_codigo][0] for x in ts if x.emenda_codigo in autores}
                ),
                "beneficiario": sem_cpf(t.beneficiario),
                "situacao": t.situacao,
                "valor_total": t.valor_total or 0,
                "valor_liberado": t.valor_repassado or 0,
            }
        )
    itens.sort(key=lambda i: i["valor_liberado"], reverse=True)
    return {
        "quantidade": len(itens),
        "valor_total": sum((i["valor_total"] for i in itens), start=Decimal(0)),
        "valor_liberado": sum((i["valor_liberado"] for i in itens), start=Decimal(0)),
        "itens": itens[:LIMITE_CONVENIOS],
        "descricao": CONVENIOS_DESCRICAO,
        "fonte_nome": FONTE_CONVENIOS,
        "fonte_url": LINK_CONVENIO,
        "atualizado_em": _atualizado(session, "transferegov_convenios"),
    }


def _outros_autores(pagamentos: list[EmendaPagamento], exercicio: set[int]) -> list[dict]:
    """Autores individuais sem mandato atual (ex-parlamentares, suplentes que saíram, nome
    sem vínculo), agrupados pela pessoa ou parlamentar quando há vínculo, senão pelo nome."""
    grupos: dict[tuple, dict] = {}
    for p in pagamentos:
        if p.parlamentar_id in exercicio:
            continue
        if p.pessoa_id:
            chave: tuple = ("pessoa", p.pessoa_id)
        elif p.parlamentar_id:
            chave = ("parlamentar", p.parlamentar_id)
        else:
            chave = ("nome", p.autor_nome)
        g = grupos.setdefault(
            chave,
            {"autor_nome": p.autor_nome, "total": Decimal(0), "parlamentar_id": p.parlamentar_id,
             "pessoa_id": p.pessoa_id, "com_mandato_atual": False, "_ano": p.ano_emenda},
        )  # fmt: skip
        g["total"] += p.valor
        if p.ano_emenda > g["_ano"]:  # o nome mais recente
            g["autor_nome"], g["_ano"] = p.autor_nome, p.ano_emenda
    saida = sorted(
        (g for g in grupos.values() if g["total"] > 0), key=lambda g: g["total"], reverse=True
    )
    for g in saida:
        del g["_ano"]
    return saida


def _sem_identificacao(linhas: list[EmendaPagamentoSemCodigo]) -> dict:
    """Pagamentos sem código de emenda da cidade, por tipo informado pela fonte."""
    por_tipo: dict[str | None, dict] = {}
    for p in linhas:
        tipo = p.tipo if p.tipo in TIPOS else None
        t = por_tipo.setdefault(tipo, {"total": Decimal(0), "pagamentos": 0})
        t["total"] += p.valor
        t["pagamentos"] += 1
    ordem = [*TIPOS, None]
    meses = [p.ano_mes for p in linhas]
    return {
        "total": sum((t["total"] for t in por_tipo.values()), start=Decimal(0)),
        "pagamentos": len(linhas),
        "primeiro_pagamento": min(meses) if meses else None,
        "ultimo_pagamento": max(meses) if meses else None,
        "por_tipo": [
            {
                "tipo": tipo,
                "rotulo": TIPOS[tipo][0] if tipo else TIPO_NAO_INFORMADO,
                "rotulo_oficial": TIPOS[tipo][1] if tipo else None,
                **por_tipo[tipo],
            }
            for tipo in ordem
            if tipo in por_tipo
        ],
        "incluido_no_total_geral": True,
        "descricao": SEM_CODIGO,
    }


def resumo_municipio(
    session: Session, municipio: Municipio, limite_outros: int = 20, limite_favorecidos: int = 15
) -> dict:
    do_municipio = EmendaPagamento.municipio_ibge == municipio.ibge
    todos = session.scalars(select(EmendaPagamento).where(do_municipio)).all()
    pagamentos = [p for p in todos if p.tipo is None or p.tipo in TIPOS_INDIVIDUAIS]

    por_grupo: dict[str, Decimal] = {}
    anos: dict[int, Decimal] = {}
    for p in pagamentos:
        por_grupo[p.grupo] = por_grupo.get(p.grupo, Decimal(0)) + p.valor
        anos[p.ano_emenda] = anos.get(p.ano_emenda, Decimal(0)) + p.valor

    tipos: dict[str, dict] = {}

    def no_tipo(tipo: str) -> dict:
        return tipos.setdefault(
            tipo,
            {"total": Decimal(0), "pagamentos": 0,
             "sem_codigo_total": Decimal(0), "sem_codigo_pagamentos": 0},
        )  # fmt: skip

    for p in todos:
        t = no_tipo(p.tipo or "individual")
        t["total"] += p.valor
        t["pagamentos"] += 1

    # Pagamentos sem código de emenda: entram no tipo informado pela fonte e no total geral,
    # nunca num autor; o tipo desconhecido fica só no bloco `sem_identificacao`.
    sem_codigo = session.scalars(
        select(EmendaPagamentoSemCodigo).where(
            EmendaPagamentoSemCodigo.municipio_ibge == municipio.ibge
        )
    ).all()
    for p in sem_codigo:
        if p.tipo in TIPOS:
            t = no_tipo(p.tipo)
            t["total"] += p.valor
            t["pagamentos"] += 1
            t["sem_codigo_total"] += p.valor
            t["sem_codigo_pagamentos"] += 1

    # Parlamentares em exercício: todos, para marcar os cards.
    totais_parlamentar: dict[int, Decimal] = {}
    for p in pagamentos:
        if p.parlamentar_id:
            totais_parlamentar[p.parlamentar_id] = (
                totais_parlamentar.get(p.parlamentar_id, Decimal(0)) + p.valor
            )
    em_exercicio = {
        p.id: p
        for p in session.scalars(
            select(Parlamentar).where(
                Parlamentar.id.in_(list(totais_parlamentar)), Parlamentar.em_exercicio
            )
        )
    }
    com_vinculo = sorted(
        # Saldo zero ou negativo (só estornos no período) não é "autor que mandou dinheiro":
        # fica fora da lista, mas o valor continua nos totais, que são a soma literal da fonte.
        (
            (em_exercicio[i], t)
            for i, t in totais_parlamentar.items()
            if i in em_exercicio and t > 0
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    outros = _outros_autores(pagamentos, set(em_exercicio))

    colegiados: dict[tuple[str, str], Decimal] = {}
    for p in todos:
        if p.tipo and p.tipo not in TIPOS_INDIVIDUAIS:
            chave = (p.autor_nome, p.tipo)
            colegiados[chave] = colegiados.get(chave, Decimal(0)) + p.valor

    favorecidos, numero_favorecidos = _favorecidos(pagamentos, limite_favorecidos)
    pagos = {(p.emenda_codigo, _cnpj(p.favorecido_codigo)) for p in todos}

    inicio, fim = session.execute(
        select(func.min(EmendaPagamento.ano_emenda), func.max(EmendaPagamento.ano_emenda))
    ).one()
    desde = inicio or INICIO_LEGISLATURA.year
    total_geral = sum((t["total"] for t in tipos.values()), start=Decimal(0)) + sum(
        (p.valor for p in sem_codigo if p.tipo not in TIPOS), start=Decimal(0)
    )
    total_individual = sum(por_grupo.values(), start=Decimal(0))
    populacao = _populacao(session, municipio)
    media_uf, n_media = _media_uf(session, municipio, _individual())
    media_uf_geral, _ = _media_uf(session, municipio, None)
    return {
        "municipio": {"ibge": municipio.ibge, "nome": municipio.nome, "uf": municipio.uf},
        "desde": desde,
        "periodo": {"inicio": inicio, "fim": fim},
        "total": total_individual,
        "total_geral": total_geral,
        "tipos": [
            {
                "tipo": tipo,
                "rotulo": TIPOS[tipo][0],
                "rotulo_oficial": TIPOS[tipo][1],
                **tipos[tipo],
            }
            for tipo in TIPOS
            if tipo in tipos
        ],
        "populacao": populacao,
        "por_habitante": round(float(total_individual) / populacao, 2) if populacao else None,
        "por_habitante_geral": round(float(total_geral) / populacao, 2) if populacao else None,
        "media_uf_por_habitante": media_uf,
        "media_uf_por_habitante_geral": media_uf_geral,
        "municipios_na_media": n_media,
        "media_uf_descricao": MEDIA_UF_DESCRICAO.format(desde=desde),
        "total_prefeitura": por_grupo.get("prefeitura", 0),
        "total_entidades": por_grupo.get("entidade", 0),
        "por_ano": [{"ano": a, "total": anos[a]} for a in sorted(anos)],
        "parlamentares": [
            {"parlamentar": p, "total": t, "do_estado": p.uf == municipio.uf}
            for p, t in com_vinculo
        ],
        "outros_autores": outros[:limite_outros],
        "numero_outros_autores": len(outros),
        "autores_com_mandato": len(com_vinculo),
        "autores_sem_mandato": len(outros),
        "numero_autores": len({p.autor_codigo for p in pagamentos}),
        "colegiados": [
            {"autor_nome": nome, "tipo": tipo, "rotulo": TIPOS[tipo][0], "total": total}
            for (nome, tipo), total in sorted(colegiados.items(), key=lambda i: i[1], reverse=True)
        ],
        "por_area": _areas(session, pagamentos) if pagamentos else [],
        "favorecidos": favorecidos,
        "numero_favorecidos": numero_favorecidos,
        "previsto": _previsto(session, municipio.ibge, pagos),
        "convenios": _convenios(session, municipio.ibge, pagos),
        "sem_codigo_descricao": SEM_CODIGO,
        "sem_identificacao": _sem_identificacao(sem_codigo),
        # Esfera estadual: bloco à parte, fora de todos os totais acima.
        "estaduais": emendas_estaduais.bloco_municipio(session, municipio),
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": _atualizado(session, "transparencia_emendas"),
    }
