"""Emendas parlamentares estaduais (hoje, só Santa Catarina; `emenda_estadual`).

São outra esfera: o dinheiro é do orçamento do Estado, indicado por deputados estaduais, e
**nunca se soma** às emendas federais (`emendas.py`). Três números que não se somam entre si:
- **previsto**: valor da emenda na Lei Orçamentária, uma vez por emenda (a mesma emenda pode
  ter várias propostas), sem as propostas canceladas ou recusadas;
- **empenhado**: reservado no orçamento para a transferência (razão financeiro da CGE/SC);
- **pago**: repassado pelo Estado ao beneficiário, como o SC Transferências mostra.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EmendaEstadual, FonteIngestao, MandatoLocal, Municipio, PessoaVinculo
from app.models.pessoa import REGRAS_FORTES
from ingestion import comum
from ingestion.emendas_estaduais import sc

FONTES = {"SC": sc.FONTE}
FONTE_NOME = {
    "SC": "Emendas impositivas no SC Transferências (Controladoria-Geral do Estado de SC)"
}
FONTE_URL = {"SC": sc.PAGINA}
CASA = {"SC": "Assembleia Legislativa de Santa Catarina (ALESC)"}
# Propostas que não vão adiante: o previsto delas não entra.
SITUACOES_FORA = ("Cancelada", "Desfavorável", "Não Homologado")
DESCRICAO = (
    "Emendas de deputados estaduais ao orçamento do Estado. São outra esfera: o dinheiro é do "
    "Estado, não da União, e por isso não é somado às emendas federais."
)
RECORTE = (
    "Só as emendas executadas por convênio ou termo de fomento no SC Transferências, quase "
    "todas para entidades sem fins lucrativos (hospitais, APAEs, clubes, associações). "
    "Repasses da saúde fundo a fundo e transferências diretas às prefeituras não passam por "
    "esse sistema e ficam de fora. O município é o do beneficiário."
)
TERMOS = (
    "Previsto: valor da emenda na Lei Orçamentária (emenda impositiva), contado uma vez. "
    "Empenhado: reservado no orçamento para o convênio. Pago: repassado pelo Estado."
)
MEDIA_DESCRICAO = (
    "Média dos {n} deputados estaduais em exercício na {casa}, pelo mesmo critério e no mesmo "
    "período; quem não tem emenda paga entra com zero."
)
LIMITE_FAVORECIDOS = 10
LIMITE_ITENS = 40
LIMITE_MUNICIPIOS = 15


def _atualizado(session: Session, uf: str) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTES[uf], FonteIngestao.status == "ok"
        )
    )


def _conta_previsto(linha: EmendaEstadual) -> bool:
    return not (linha.situacao_proposta or "").startswith(SITUACOES_FORA)


def _previsto(linhas: list[EmendaEstadual]) -> Decimal:
    """Uma vez por emenda: o maior valor entre as propostas que seguem."""
    por_emenda: dict[str, Decimal] = {}
    for x in linhas:
        if _conta_previsto(x):
            por_emenda[x.codigo] = max(por_emenda.get(x.codigo, Decimal(0)), x.valor_previsto)
    return sum(por_emenda.values(), start=Decimal(0))


def _somas(linhas: list[EmendaEstadual]) -> dict:
    return {
        "previsto": _previsto(linhas),
        "empenhado": sum((x.valor_empenhado or 0 for x in linhas), start=Decimal(0)),
        "pago": sum((x.valor_pago for x in linhas), start=Decimal(0)),
        "emendas": len({x.codigo for x in linhas}),
    }


def _por_ano(linhas: list[EmendaEstadual]) -> list[dict]:
    anos: dict[int, list[EmendaEstadual]] = {}
    for x in linhas:
        anos.setdefault(x.ano, []).append(x)
    return [{"ano": a, **_somas(anos[a])} for a in sorted(anos)]


def _publicavel():
    return PessoaVinculo.regra.in_(REGRAS_FORTES) | PessoaVinculo.revisado.is_(True)


def _mandatos(session: Session, uf: str) -> list[tuple[MandatoLocal, int | None]]:
    """Deputados estaduais da Casa (como ela publica) com a pessoa de cada um, se houver
    vínculo publicável."""
    return list(
        session.execute(
            select(MandatoLocal, PessoaVinculo.pessoa_id)
            .outerjoin(
                PessoaVinculo,
                (PessoaVinculo.fonte == "mandato_local")
                & (
                    PessoaVinculo.id_externo
                    == func.concat(
                        MandatoLocal.casa, ":", MandatoLocal.uf, "::", MandatoLocal.id_externo
                    )
                )
                & _publicavel(),
            )
            .where(MandatoLocal.casa == "assembleia", MandatoLocal.uf == uf)
        ).all()
    )


def _do_mandato(
    linhas: list[EmendaEstadual], mandato: MandatoLocal, pessoa_id: int | None
) -> list[EmendaEstadual]:
    """Emendas do deputado: pela pessoa ligada ou, sem pessoa na emenda, pelo nome idêntico ao
    que a própria Casa publica (nome parlamentar ou completo)."""
    chaves = {comum.chave_nome(mandato.nome), comum.chave_nome(mandato.nome_completo)} - {""}
    return [
        x
        for x in linhas
        if x.tipo == "individual"
        and (
            (pessoa_id is not None and x.pessoa_id == pessoa_id)
            or (x.pessoa_id is None and bool(chaves & set(sc.nomes_do_autor(x.autor_nome))))
        )
    ]


def bloco_municipio(session: Session, municipio: Municipio) -> dict | None:
    """Bloco `estaduais` de `/municipios/{ibge}/emendas`. Nulo onde o estado não tem fonte."""
    uf = municipio.uf
    if uf not in FONTES or _atualizado(session, uf) is None:
        return None
    linhas = list(
        session.scalars(
            select(EmendaEstadual).where(EmendaEstadual.municipio_ibge == municipio.ibge)
        ).all()
    )
    em_exercicio = [(m, p) for m, p in _mandatos(session, uf) if m.em_exercicio]

    def mandato_do_autor(linha: EmendaEstadual) -> int | None:
        """O deputado no cargo hoje, pelo mesmo critério da página do deputado (único)."""
        ids = {m.id for m, p in em_exercicio if _do_mandato([linha], m, p)}
        return ids.pop() if len(ids) == 1 else None

    autores: dict[tuple[str, str, int | None], list[EmendaEstadual]] = {}
    for x in linhas:
        autores.setdefault((x.autor_nome, x.tipo, x.pessoa_id), []).append(x)
    por_autor = []
    for (nome, tipo, pessoa), itens in autores.items():
        mandato_id = mandato_do_autor(itens[0])
        por_autor.append(
            {
                "autor_nome": comum.nome_proprio(nome) or nome,
                "tipo": tipo,
                "pessoa_id": pessoa,
                "mandato_id": mandato_id,
                "em_exercicio": mandato_id is not None,
                **_somas(itens),
            }
        )
    por_autor.sort(key=lambda a: (a["pago"], a["previsto"]), reverse=True)
    favorecidos: dict[tuple[str | None, str | None], list[EmendaEstadual]] = {}
    for x in linhas:
        favorecidos.setdefault((x.favorecido_nome, x.favorecido_cnpj), []).append(x)
    lista_favorecidos = sorted(
        (
            {"nome": nome or "Pessoa física", "cnpj": cnpj, **_somas(itens)}
            for (nome, cnpj), itens in favorecidos.items()
        ),
        key=lambda f: (f["pago"], f["previsto"]),
        reverse=True,
    )
    somas = _somas(linhas)
    return {
        "uf": uf,
        "casa": CASA[uf],
        "total_previsto": somas["previsto"],
        "total_empenhado": somas["empenhado"],
        "total_pago": somas["pago"],
        "emendas": somas["emendas"],
        "por_autor": por_autor,
        "por_ano": _por_ano(linhas),
        "favorecidos": lista_favorecidos[:LIMITE_FAVORECIDOS],
        "numero_favorecidos": len(lista_favorecidos),
        "somado_ao_federal": False,
        "descricao": DESCRICAO,
        "recorte": RECORTE,
        "termos": TERMOS,
        "fonte_nome": FONTE_NOME[uf],
        "fonte_url": FONTE_URL[uf],
        "atualizado_em": _atualizado(session, uf),
    }


def deputado(session: Session, mandato: MandatoLocal) -> dict | None:
    """Emendas estaduais de um deputado estadual no cargo, com a média da Casa."""
    uf = mandato.uf
    if mandato.casa != "assembleia" or uf not in FONTES or _atualizado(session, uf) is None:
        return None
    todas = list(session.scalars(select(EmendaEstadual).where(EmendaEstadual.uf == uf)).all())
    mandatos = _mandatos(session, uf)
    pessoa_id = next((p for m, p in mandatos if m.id == mandato.id), None)
    linhas = _do_mandato(todas, mandato, pessoa_id)
    em_exercicio = [(m, p) for m, p in mandatos if m.em_exercicio]
    pagos = [
        sum((x.valor_pago for x in _do_mandato(todas, m, p)), start=Decimal(0))
        for m, p in em_exercicio
    ]
    media = sum(pagos, start=Decimal(0)) / len(pagos) if pagos else None
    municipios: dict[tuple[str | None, str], list[EmendaEstadual]] = {}
    for x in linhas:
        municipios.setdefault((x.municipio_ibge, x.municipio_nome), []).append(x)
    nomes = dict(
        session.execute(
            select(Municipio.ibge, Municipio.nome).where(
                Municipio.ibge.in_([i for i, _ in municipios if i])
            )
        ).all()
    )
    por_municipio = sorted(
        (
            {"ibge": ibge, "nome": nomes.get(ibge) or nome, **_somas(itens)}
            for (ibge, nome), itens in municipios.items()
        ),
        key=lambda m: (m["pago"], m["previsto"]),
        reverse=True,
    )
    itens = sorted(linhas, key=lambda x: (x.ano, x.valor_pago), reverse=True)
    somas = _somas(linhas)
    anos = [x.ano for x in todas]
    return {
        "mandato_id": mandato.id,
        "nome": mandato.nome,
        "uf": uf,
        "casa": CASA[uf],
        "periodo": {"inicio": min(anos, default=None), "fim": max(anos, default=None)},
        "total_previsto": somas["previsto"],
        "total_empenhado": somas["empenhado"],
        "total_pago": somas["pago"],
        "emendas": somas["emendas"],
        "media_casa_pago": round(media, 2) if media is not None else None,
        "deputados_na_media": len(pagos),
        "media_descricao": MEDIA_DESCRICAO.format(n=len(pagos), casa=CASA[uf]),
        "por_ano": _por_ano(linhas),
        "por_municipio": por_municipio[:LIMITE_MUNICIPIOS],
        "numero_municipios": len(por_municipio),
        "itens": [
            {
                "codigo": x.codigo,
                "ano": x.ano,
                "municipio_ibge": x.municipio_ibge,
                "municipio_nome": nomes.get(x.municipio_ibge) or x.municipio_nome,
                "favorecido": x.favorecido_nome or "Pessoa física",
                "orgao": x.orgao,
                "objeto": x.objeto,
                "situacao": x.situacao_transferencia or x.situacao_proposta,
                "previsto": x.valor_previsto if _conta_previsto(x) else Decimal(0),
                "empenhado": x.valor_empenhado,
                "pago": x.valor_pago,
            }
            for x in itens[:LIMITE_ITENS]
        ],
        "numero_itens": len(itens),
        "descricao": DESCRICAO,
        "recorte": RECORTE,
        "termos": TERMOS,
        "fonte_nome": FONTE_NOME[uf],
        "fonte_url": FONTE_URL[uf],
        "atualizado_em": _atualizado(session, uf),
    }
