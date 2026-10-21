"""Página de um projeto federal (GET /projetos/{casa}/{id_externo}): ficha, votações nominais,
quem votou, discursos, caminho da tramitação e pauta, cada bloco com fonte e data.

Regras (docs/DECISOES.md, 2026-10-21):
- Votação principal: a última votação nominal do texto, isto é, a mais recente cuja descrição
  não fala em "Requerimento", "Destaque" ou "Emenda"; se todas falam, a última de todas.
- Grupos de quem votou sempre na ordem Sim, Não, outros registros; pessoas em ordem
  alfabética; partidos e estados do maior para o menor número, depois alfabética.
- Discursos: ligados ao projeto e ao dia, agrupados pelo voto do orador na última votação
  nominal do projeto no dia (app/services/discursos_projeto.py). Os discursos do dia que a
  ingestão não ligou a nenhum projeto não são atribuídos: só contamos quantos são.
"""

import re
from collections import Counter, defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Autoria,
    Parlamentar,
    PautaItem,
    Proposicao,
    ProposicaoTema,
    Tramitacao,
    Votacao,
    Voto,
)
from app.services import discursos_projeto, projeto_fontes, texto_busca, votacao_detalhe
from app.services.projeto_etapas import etapa_do_passo
from app.services.votos import VOTO_EFETIVO, url_votacao
from ingestion.proposicoes_comum import SEM_CLASSIFICACAO

ROTULO_RE = re.compile(r"^\s*([A-Za-z]+)\s+0*(\d+)\s*/\s*(\d{4})")
NAO_PRINCIPAL = re.compile(r"\b(requerimento|destaque|emenda)")

AVISO_SEM_VOTACAO = (
    "Ainda não teve votação nominal no Plenário. Pode ter sido votado de forma simbólica, "
    "que não registra o voto de cada um."
)
AVISO_DISCURSOS = {
    "camara": (
        "Resumo publicado pela Câmara; leia o discurso completo no link. Os discursos aparecem "
        "agrupados pelo voto que cada deputado registrou na votação, sem juízo sobre o que disse."
    ),
    "senado": (
        "Resumo publicado pelo Senado, que descreve o pronunciamento e nem sempre traz o "
        "argumento; leia o discurso completo no link. Os discursos aparecem agrupados pelo voto "
        "que cada senador registrou na votação, sem juízo sobre o que disse."
    ),
}
AVISO_DO_DIA = (
    "Discursos de Plenário nos dias de votação do projeto que a Casa não liga a um projeto "
    "específico (citam três ou mais matérias, ou mais de uma votada no mesmo dia). Não são "
    "atribuídos a este projeto."
)
REGRA_PRINCIPAL = (
    "Última votação nominal do texto: a mais recente cuja descrição não fala em requerimento, "
    "destaque ou emenda; se todas falam, a última de todas."
)


def _link_votacao(casa: str, id_externo: str) -> str:
    return f"/votacao/{casa}/{id_externo}"


def _contagens(session: Session, ids: list[int]) -> dict[int, Counter]:
    resultado: dict[int, Counter] = defaultdict(Counter)
    if not ids:
        return resultado
    for votacao_id, voto, n in session.execute(
        select(Voto.votacao_id, Voto.voto, func.count())
        .where(Voto.votacao_id.in_(ids))
        .group_by(Voto.votacao_id, Voto.voto)
    ):
        resultado[votacao_id][voto] += n
    return resultado


def _item_votacao(v: Votacao, contagem: Counter) -> dict:
    sim, nao = contagem["Sim"], contagem["Não"]
    abstencao, obstrucao = contagem["Abstenção"], contagem["Obstrução"]
    efetivos = sum(contagem[k] for k in VOTO_EFETIVO)
    publicado = (
        {"sim": v.placar_sim, "nao": v.placar_nao, "abstencao": v.placar_abstencao}
        if v.placar_sim is not None or v.placar_nao is not None
        else None
    )
    return {
        "id_externo": v.id_externo,
        "data": v.data,
        "descricao": v.descricao,
        "resultado": v.resultado,
        "secreta": v.secreta,
        "placar_publicado": publicado,
        "placar_contado": {
            "sim": sim,
            "nao": nao,
            "abstencao": abstencao,
            "obstrucao": obstrucao,
            "outros": sum(contagem.values()) - efetivos,
        },
        "link": _link_votacao(v.casa, v.id_externo),
    }


def escolher_principal(votacoes: list[Votacao]) -> Votacao | None:
    """`votacoes` em ordem cronológica. Ver a regra no topo do módulo."""
    if not votacoes:
        return None
    textos = [v for v in votacoes if not NAO_PRINCIPAL.search(texto_busca.normalizar(v.descricao))]
    return (textos or votacoes)[-1]


def _grupos_quem_votou(parlamentares: list[dict]) -> list[dict]:
    definicao = [("sim", "Sim"), ("nao", "Não"), ("outros", "Outros registros")]
    grupos: dict[str, list[dict]] = {chave: [] for chave, _ in definicao}
    for p in parlamentares:
        chave = "sim" if p["voto"] == "Sim" else "nao" if p["voto"] == "Não" else "outros"
        grupos[chave].append(
            {
                "parlamentar_id": p["parlamentar_id"],
                "nome": p["nome"],
                "partido": p["partido"],
                "uf": p["uf"],
                "registro": p["registro"],
            }
        )
    resultado = []
    for chave, rotulo in definicao:
        pessoas = sorted(grupos[chave], key=lambda p: (p["nome"], p["parlamentar_id"]))
        partidos = Counter(p["partido"] for p in pessoas)
        resultado.append(
            {
                "chave": chave,
                "rotulo": rotulo,
                "quantidade": len(pessoas),
                "partidos": [
                    {"partido": partido, "quantidade": n}
                    for partido, n in sorted(partidos.items(), key=lambda t: (-t[1], t[0]))
                ],
                "pessoas": pessoas,
            }
        )
    return resultado


def _ficha(
    session: Session,
    casa: str,
    id_externo: str,
    proposicao: Proposicao | None,
    votacoes: list[Votacao],
) -> dict:
    autores = []
    if proposicao is not None:
        autores = [
            {
                "parlamentar_id": pid,
                "nome": nome,
                "partido": partido,
                "uf": uf,
                "primeiro_autor": primeiro,
            }
            for pid, nome, partido, uf, primeiro in session.execute(
                select(
                    Parlamentar.id,
                    Parlamentar.nome_parlamentar,
                    Parlamentar.partido,
                    Parlamentar.uf,
                    Autoria.primeiro_autor,
                )
                .join(Autoria, Autoria.parlamentar_id == Parlamentar.id)
                .where(Autoria.proposicao_id == proposicao.id)
                .order_by(Autoria.primeiro_autor.desc(), Parlamentar.nome_parlamentar)
            )
        ]
    temas = list(
        session.scalars(
            select(ProposicaoTema.tema)
            .where(
                ProposicaoTema.casa == casa,
                ProposicaoTema.proposicao_id_externo == id_externo,
                ProposicaoTema.tema != SEM_CLASSIFICACAO,
            )
            .order_by(ProposicaoTema.tema)
        )
    )
    ultima = votacoes[-1] if votacoes else None
    return {
        "temas": temas,
        "autores": autores,
        "autor_descricao": proposicao.autor_descricao if proposicao else None,
        "situacao": proposicao.situacao if proposicao else None,
        "virou_lei": proposicao.virou_lei if proposicao else None,
        "relator": proposicao.relator if proposicao else None,
        "relator_parlamentar_id": proposicao.relator_parlamentar_id if proposicao else None,
        "url_oficial": proposicao.url if proposicao else (url_votacao(ultima) if ultima else None),
        "origem": proposicao.origem if proposicao else None,
        "data_apresentacao": proposicao.data_apresentacao if proposicao else None,
        **projeto_fontes.fonte_do_bloco(session, "ficha", casa),
    }


def detalhe(session: Session, casa: str, id_externo: str, hoje: date | None = None) -> dict | None:
    hoje = hoje or date.today()
    proposicao = session.scalars(
        select(Proposicao).where(Proposicao.casa == casa, Proposicao.id_externo == id_externo)
    ).one_or_none()
    votacoes = discursos_projeto.votacoes_do_projeto(session, casa, id_externo)
    if proposicao is None and not votacoes:
        return None

    # Identificação: da tabela de proposições; senão, do rótulo gravado nas votações.
    sigla = numero = ano = None
    ementa = None
    if proposicao is not None:
        sigla, numero, ano, ementa = (
            proposicao.sigla_tipo,
            proposicao.numero,
            proposicao.ano,
            proposicao.ementa,
        )
        rotulo = f"{sigla} {numero}/{ano}"
    else:
        rotulo_votacao = next((v.proposicao for v in reversed(votacoes) if v.proposicao), None)
        ementa = next(
            (v.proposicao_ementa for v in reversed(votacoes) if v.proposicao_ementa), None
        )
        achou = ROTULO_RE.match(rotulo_votacao or "")
        if achou:
            sigla, numero, ano = achou[1].upper(), int(achou[2]), int(achou[3])
        rotulo = rotulo_votacao or f"Proposição {id_externo}"

    contagens = _contagens(session, [v.id for v in votacoes])
    itens = [_item_votacao(v, contagens[v.id]) for v in reversed(votacoes)]  # mais recente 1º
    bloco_votacoes = {
        "itens": itens,
        "aviso": None if votacoes else AVISO_SEM_VOTACAO,
        **projeto_fontes.fonte_do_bloco(session, "votacoes", casa),
    }

    principal = escolher_principal(votacoes)
    quem_votou = None
    if principal is not None:
        base = votacao_detalhe.detalhe(session, casa, principal.id_externo)
        quem_votou = {
            "votacao": _item_votacao(principal, contagens[principal.id]),
            "regra": REGRA_PRINCIPAL,
            "grupos": _grupos_quem_votou(base["parlamentares"]),
            "por_uf": base["por_uf"],
            "fonte_nome": base["fonte_nome"],
            "fonte_url": base["fonte_url"],
            "atualizado_em": base["atualizado_em"],
        }

    dias = discursos_projeto.discursos_por_dia(session, casa, id_externo, votacoes)
    discursos = {
        "dias": dias,
        "aviso": AVISO_DISCURSOS[casa],
        **projeto_fontes.fonte_do_bloco(session, "discursos", casa),
    }
    do_dia = {
        "quantidade_nao_atribuida": discursos_projeto.nao_atribuidos(session, casa, votacoes),
        "itens": [],
        "aviso": AVISO_DO_DIA,
        **projeto_fontes.fonte_do_bloco(session, "discursos", casa),
    }

    caminho = [
        {
            "data": t.data,
            "orgao": t.orgao,
            "descricao": t.descricao,
            "etapa": etapa_do_passo(t.tipo, t.descricao, t.situacao),
        }
        for t in session.scalars(
            select(Tramitacao)
            .where(Tramitacao.casa == casa, Tramitacao.proposicao_id_externo == id_externo)
            .order_by(Tramitacao.ordem)
        )
    ]
    pauta = session.scalars(
        select(PautaItem)
        .where(
            PautaItem.casa == casa,
            PautaItem.proposicao_id_externo == id_externo,
            PautaItem.data >= hoje,
        )
        .order_by(PautaItem.data, PautaItem.ordem)
        .limit(1)
    ).first()

    return {
        "casa": casa,
        "id_externo": id_externo,
        "rotulo": rotulo,
        "sigla": sigla,
        "numero": numero,
        "ano": ano,
        "ementa": ementa,
        "ficha": _ficha(session, casa, id_externo, proposicao, votacoes),
        "votacoes": bloco_votacoes,
        "votacao_principal": quem_votou,
        "discursos": discursos,
        "discursos_do_dia": do_dia,
        "caminho": {"itens": caminho, **projeto_fontes.fonte_do_bloco(session, "caminho", casa)},
        "pauta": {
            "proxima": {"data": pauta.data, "sessao": pauta.sessao, "url": pauta.url}
            if pauta
            else None,
            **projeto_fontes.fonte_do_bloco(session, "pauta", casa),
        },
    }
