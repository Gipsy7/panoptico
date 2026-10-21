"""Explicador de uma votação nominal do Plenário: o que se votava, resultado, placar,
orientações (lideranças, partidos, blocos e federações) e o voto de cada parlamentar.

Definições (docs/DECISOES.md, 2026-10-18):
- Placar: contagem dos votos nominais publicados (Sim, Não, Abstenção, Obstrução). O placar
  como a fonte publica vai à parte (`placar_oficial`); na votação secreta só ele existe.
- Orientação do partido: a do próprio partido; se ele não orientou sozinho, a do bloco ou da
  federação de que faz parte, quando a fonte publica a composição (`orientacao_por` diz qual).
- "Seguiu a orientação": voto efetivo igual à orientação, contando só orientações Sim, Não ou
  Obstrução (como no alinhamento com o Governo). "Liberado" fica fora.
- Ordem dos partidos: pelo número de parlamentares do partido nesta votação (maior primeiro);
  empate em ordem alfabética.
"""

import unicodedata
from collections import Counter
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Orientacao, Parlamentar, ProposicaoTema, Votacao, Voto
from app.services import discursos_projeto, presenca, projeto_fontes
from app.services.votos import ORIENTACAO_VALIDA, VOTO_EFETIVO, url_votacao
from ingestion.proposicoes_comum import SEM_CLASSIFICACAO

LIDERANCAS = ("Governo", "Maioria", "Minoria", "Oposição")
CADEIRAS = {"camara": 513, "senado": 81}
CHAVE_VOTO = {"Sim": "sim", "Não": "nao", "Abstenção": "abstencao", "Obstrução": "obstrucao"}


def _chave(sigla: str) -> str:
    sem = unicodedata.normalize("NFKD", sigla)
    return "".join(c for c in sem if not unicodedata.combining(c)).upper().strip()


def rotulo_do_registro(codigo: str, secreta: bool = False) -> str:
    """Registro que não é voto efetivo, em linguagem do dia a dia. Na votação secreta da
    Câmara o voto vem em branco para todos os que votaram."""
    if codigo == "Artigo 17" or codigo.startswith("Presidente"):
        return "Presidiu a sessão (não vota)"
    if codigo == "Votou" or (secreta and codigo == ""):
        return "Votou (voto secreto)"
    if codigo in presenca.PRESENTE_SEM_VOTO:
        return "Presente, sem registrar voto"
    if codigo in presenca.JUSTIFICADA:
        return f"Ausente: {presenca.JUSTIFICADA[codigo].lower()}"
    if codigo in presenca.NAO_COMPARECEU:
        return "Ausente: não compareceu"
    if codigo in presenca.FORA_DA_CONTA:
        return "Fora desta votação (dispositivo não citado)"
    return codigo


def _atualizado_em(session: Session, casa: str) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == presenca.FONTES[casa]["fonte"], FonteIngestao.status == "ok"
        )
    )


def url_dados(votacao: Votacao) -> str:
    """Endereço oficial dos dados da votação."""
    if votacao.casa == "camara":
        return f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{votacao.id_externo}"
    return presenca.FONTES["senado"]["url"]


def detalhe(session: Session, casa: str, id_externo: str) -> dict | None:
    votacao = session.scalars(
        select(Votacao).where(Votacao.casa == casa, Votacao.id_externo == id_externo)
    ).one_or_none()
    if votacao is None:
        return None

    linhas = session.execute(
        select(Parlamentar.id, Parlamentar.nome_parlamentar, Parlamentar.uf, Parlamentar.partido,
               Voto.partido, Voto.voto)
        .join(Voto, Voto.parlamentar_id == Parlamentar.id)
        .where(Voto.votacao_id == votacao.id)
        .order_by(Parlamentar.nome_parlamentar)
    ).all()  # fmt: skip
    orientacoes = session.execute(
        select(Orientacao.bancada, Orientacao.orientacao, Orientacao.tipo, Orientacao.partidos)
        .where(Orientacao.votacao_id == votacao.id)
        .order_by(Orientacao.bancada)
    ).all()

    lideranca: dict[str, str] = {}
    do_partido: dict[str, str] = {}
    outras: list[dict] = []
    for bancada, orientacao, tipo, partidos in orientacoes:
        if (tipo or "lideranca") == "lideranca":
            lideranca[bancada] = orientacao
        elif tipo == "partido":
            do_partido[_chave(bancada)] = orientacao
        else:
            outras.append(
                {"bancada": bancada, "tipo": tipo, "orientacao": orientacao,
                 "partidos": partidos.split(",") if partidos else []}
            )  # fmt: skip
    # Partido sem orientação própria herda a do bloco ou federação que o inclui.
    pelo_grupo: dict[str, tuple[str, str]] = {}
    for grupo in sorted(outras, key=lambda g: g["tipo"] != "federacao"):
        for sigla in grupo["partidos"]:
            pelo_grupo.setdefault(_chave(sigla), (grupo["orientacao"], grupo["bancada"]))

    placar: Counter = Counter()
    outros: Counter = Counter()
    por_partido: dict[str, dict] = {}
    parlamentares = []
    governo = lideranca.get("Governo")
    seguiu_governo = Placar()
    seguiu_partido = Placar()
    for pid, nome, uf, partido_atual, partido_dia, voto in linhas:
        partido = partido_dia or partido_atual or "Sem partido"
        efetivo = voto in VOTO_EFETIVO
        if efetivo:
            placar[CHAVE_VOTO[voto]] += 1
        else:
            outros[rotulo_do_registro(voto, votacao.secreta)] += 1
        grupo = por_partido.setdefault(
            partido,
            {"partido": partido, "parlamentares": 0, "sim": 0, "nao": 0, "abstencao": 0,
             "obstrucao": 0, "outros": 0},
        )  # fmt: skip
        grupo["parlamentares"] += 1
        grupo[CHAVE_VOTO[voto] if efetivo else "outros"] += 1
        orientacao, _ = _orientacao_do_partido(partido, do_partido, pelo_grupo)
        if efetivo and not votacao.secreta:
            if governo in ORIENTACAO_VALIDA:
                seguiu_governo.somar(voto == governo)
            if orientacao in ORIENTACAO_VALIDA:
                seguiu_partido.somar(voto == orientacao)
        parlamentares.append(
            {"parlamentar_id": pid, "nome": nome, "partido": partido, "uf": uf, "voto": voto,
             "registro": voto if efetivo else rotulo_do_registro(voto, votacao.secreta),
             "efetivo": efetivo}
        )  # fmt: skip

    partidos = []
    for grupo in sorted(por_partido.values(), key=lambda g: (-g["parlamentares"], g["partido"])):
        orientacao, por = _orientacao_do_partido(grupo["partido"], do_partido, pelo_grupo)
        seguiram = (
            grupo[CHAVE_VOTO[orientacao]]
            if orientacao in ORIENTACAO_VALIDA and not votacao.secreta
            else None
        )
        efetivos = grupo["sim"] + grupo["nao"] + grupo["abstencao"] + grupo["obstrucao"]
        partidos.append(
            grupo | {"orientacao": orientacao, "orientacao_por": por, "seguiram": seguiram,
                     "votos_efetivos": efetivos}
        )  # fmt: skip

    temas = (
        list(
            session.scalars(
                select(ProposicaoTema.tema)
                .where(
                    ProposicaoTema.casa == casa,
                    ProposicaoTema.proposicao_id_externo == votacao.proposicao_id_externo,
                    ProposicaoTema.tema != SEM_CLASSIFICACAO,
                )
                .order_by(ProposicaoTema.tema)
            )
        )
        if votacao.proposicao_id_externo
        else []
    )
    fonte = presenca.FONTES[casa]
    por_uf = _por_uf(parlamentares)
    tem_oficial = votacao.placar_sim is not None or votacao.placar_nao is not None
    return {
        "casa": casa,
        "id_externo": votacao.id_externo,
        "data": votacao.data,
        "descricao": votacao.descricao,
        "proposicao": votacao.proposicao,
        "proposicao_ementa": votacao.proposicao_ementa,
        "proposicao_url": url_votacao(votacao),
        "temas": temas,
        "secreta": votacao.secreta,
        "resultado": votacao.resultado,
        "placar": {k: placar[k] for k in CHAVE_VOTO.values()},
        "outros_registros": [
            {"rotulo": r, "quantidade": n} for r, n in sorted(outros.items(), key=lambda t: -t[1])
        ],
        "placar_oficial": {
            "sim": votacao.placar_sim,
            "nao": votacao.placar_nao,
            "abstencao": votacao.placar_abstencao,
        }
        if tem_oficial
        else None,
        "registros": len(linhas),
        "cadeiras": CADEIRAS[casa],
        "liderancas": [
            {"bancada": b, "orientacao": lideranca[b] or None} for b in LIDERANCAS if b in lideranca
        ],
        "outras_bancadas": outras,
        "seguiram_governo": seguiu_governo.como_dict(),
        "seguiram_partido": seguiu_partido.como_dict(),
        "partidos": partidos,
        "parlamentares": parlamentares,
        "fonte_nome": fonte["nome"],
        "fonte_url": url_dados(votacao),
        "atualizado_em": _atualizado_em(session, casa),
        "por_uf": por_uf,
        "discursos": _discursos(session, votacao),
    }


def _por_uf(parlamentares: list[dict]) -> list[dict]:
    """Placar por estado: Sim, Não e os demais registros. Estados do maior para o menor número
    de registros; empate em ordem alfabética."""
    ufs: dict[str, dict] = {}
    for p in parlamentares:
        grupo = ufs.setdefault(p["uf"], {"uf": p["uf"], "sim": 0, "nao": 0, "outros": 0})
        grupo["sim" if p["voto"] == "Sim" else "nao" if p["voto"] == "Não" else "outros"] += 1
    resultado = [g | {"total": g["sim"] + g["nao"] + g["outros"]} for g in ufs.values()]
    return sorted(resultado, key=lambda g: (-g["total"], g["uf"]))


def _discursos(session: Session, votacao: Votacao) -> dict | None:
    """Discursos do dia sobre o projeto, agrupados pelo voto nesta votação. Só quando esta é a
    última votação nominal do projeto no dia (os discursos se ligam ao projeto e ao dia, não a
    uma votação específica); nas outras do mesmo dia o campo fica vazio."""
    if not votacao.proposicao_id_externo:
        return None
    votacoes = discursos_projeto.votacoes_do_projeto(
        session, votacao.casa, votacao.proposicao_id_externo
    )
    final = discursos_projeto.final_de_cada_dia(votacoes).get(votacao.data)
    if final is None or final.id != votacao.id:
        return None
    dias = discursos_projeto.discursos_por_dia(
        session, votacao.casa, votacao.proposicao_id_externo, votacoes, apenas_dia=votacao.data
    )
    grupos = (
        dias[0]["grupos"]
        if dias
        else [
            {"chave": c, "rotulo": r, "quantidade": 0, "discursos": []}
            for c, r in discursos_projeto.GRUPOS
        ]
    )
    return {
        "total": sum(g["quantidade"] for g in grupos),
        "grupos": grupos,
        **projeto_fontes.fonte_do_bloco(session, "discursos", votacao.casa),
    }


class Placar:
    def __init__(self) -> None:
        self.iguais = 0
        self.total = 0

    def somar(self, igual: bool) -> None:
        self.total += 1
        self.iguais += igual

    def como_dict(self) -> dict:
        pct = round(100 * self.iguais / self.total, 1) if self.total else None
        return {"iguais": self.iguais, "total": self.total, "percentual": pct}


def _orientacao_do_partido(
    partido: str, do_partido: dict[str, str], pelo_grupo: dict[str, tuple[str, str]]
) -> tuple[str | None, str | None]:
    chave = _chave(partido)
    if chave in do_partido:
        return do_partido[chave], None
    if chave in pelo_grupo:
        return pelo_grupo[chave]
    return None, None


def ids_da_pagina(
    session: Session, parlamentar: Parlamentar, ano: int, tema: str | None, pagina: int,
    por_pagina: int,
) -> list[str]:  # fmt: skip
    """Ids externos das votações de uma página da lista de votos do perfil, no mesmo filtro e
    na mesma ordem de `votos.lista_votos` (para o link de cada item ao explicador)."""
    filtro = [
        Voto.parlamentar_id == parlamentar.id,
        Votacao.casa == parlamentar.casa,
        func.extract("year", Votacao.data) == ano,
    ]
    if tema:
        filtro.append(
            Votacao.proposicao_id_externo.in_(
                select(ProposicaoTema.proposicao_id_externo).where(
                    ProposicaoTema.casa == parlamentar.casa, ProposicaoTema.tema == tema
                )
            )
        )
    return list(
        session.scalars(
            select(Votacao.id_externo)
            .join(Voto, Voto.votacao_id == Votacao.id)
            .where(*filtro)
            .order_by(Votacao.data.desc(), Votacao.id.desc())
            .limit(por_pagina)
            .offset((pagina - 1) * por_pagina)
        )
    )


def com_ids(itens: list[dict], ids: list[str]) -> list[dict]:
    """Acrescenta `id_externo` a cada item da página (mesma ordem); se o tamanho não bater,
    não arrisca: deixa sem link."""
    if len(itens) != len(ids):
        return [i | {"id_externo": None} for i in itens]
    return [i | {"id_externo": id_} for i, id_ in zip(itens, ids, strict=True)]
