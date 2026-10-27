"""Regras comuns aos discursos em Plenário das duas casas.

Recorte (docs/DECISOES.md, 2026-10-21): só discursos de Plenário de um dia em que a casa teve
votação nominal (tabela `votacao`) e cujo sumário cita ao menos uma matéria. Nunca a transcrição.

Ligação: ao projeto e ao dia, nunca a uma votação específica (acerto por votação ficou em 78% na
Câmara, abaixo do limite de 90%). `proposicao_id_externo` só é preenchido quando o discurso cita
1 ou 2 matérias e exatamente uma delas foi votada naquele dia; com 3 ou mais matérias citadas, ou
sem casamento único, fica nulo (vira "discurso do dia").
"""

import html
import re
import unicodedata
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Discurso, FonteIngestao, Votacao

# Com 3 ou mais matérias citadas o discurso é um balanço, não fala de um projeto.
MAX_MATERIAS_LIGADAS = 2

_TIPOS = [
    (r"projetos? de (?:lei )?complementar", "PLP"),
    (r"projetos? de lei de conversao", "PLV"),
    (r"projetos? de decreto legislativo", "PDL"),
    (r"projetos? de resolucao", "PRC"),
    (r"propostas? de emenda (?:a|à) constituicao", "PEC"),
    (r"medidas? provisorias?", "MPV"),
    (r"projetos? de lei", "PL"),
]
# "nº 74, de 2026", "n° 5.063 de 2023", "223/2023", com a sigla entre parênteses opcional.
_NUM = (
    r"(?:\s*\([A-Z]+\))?(?:\s|&nbsp;)*(?:n[ºo°]\.?|n\.|numero)?(?:\s|&nbsp;)*"
    r"([\d\.]+)\s*(?:,?\s*de\s*|/)\s*(\d{4})"
)
_RX_LONGO = [(re.compile(t + _NUM, re.I), sigla) for t, sigla in _TIPOS]
_RX_CURTO = re.compile(
    r"\b(PLP|PLV|PDL|PRC|PEC|MPV|MP|PL)\s*(?:n[ºo°]\.?\s*)?([\d\.]+)\s*(?:/|,?\s*de\s+)\s*(\d{2,4})\b"
)
_RX_ROTULO = re.compile(r"^([A-Z]+) (\d+)/(\d{4})")


def limpar_texto(texto: str | None) -> str | None:
    """Resumo oficial como texto simples: a fonte às vezes manda HTML (`&nbsp;`, `<p>`). Converte
    entidades, tira marcações e junta os espaços; vazio vira None."""
    if not texto:
        return None
    sem_tags = re.sub(r"<[^>]+>", " ", html.unescape(html.unescape(texto)))
    return " ".join(sem_tags.replace(" ", " ").split()) or None


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def citacoes(texto: str | None) -> set[str]:
    """Matérias citadas no texto, no rótulo canônico ("PL 759/2015", "MPV 1300/2025").

    Reconhece o nome por extenso ("Projeto de Lei Complementar nº 74, de 2026") e a sigla
    ("PL 2.215/2024", "PL nº 5.063 de 2023"). Citação sem ano não conta."""
    t = _sem_acento((texto or "").replace("&nbsp;", " "))
    achou: set[str] = set()
    usados: list[tuple[int, int]] = []
    for rx, sigla in _RX_LONGO:
        for m in rx.finditer(t):
            if any(a <= m.start() < b for a, b in usados):
                continue
            usados.append((m.start(), m.end()))
            achou.add(f"{sigla} {int(m.group(1).replace('.', ''))}/{m.group(2)}")
    for m in _RX_CURTO.finditer(t):
        sigla = "MPV" if m.group(1) == "MP" else m.group(1)
        ano = m.group(3)
        ano = "20" + ano if len(ano) == 2 else ano
        achou.add(f"{sigla} {int(m.group(2).replace('.', ''))}/{ano}")
    return achou


def rotulo(titulo: str | None) -> str | None:
    """ "PL 2159/2021 (Nº Anterior: ...)" -> "PL 2159/2021"."""
    m = _RX_ROTULO.match(titulo or "")
    return f"{m.group(1)} {int(m.group(2))}/{m.group(3)}" if m else None


def inicio_incremental(
    session: Session, fonte: str, margem_dias: int, piso: date, hoje: date | None = None
) -> tuple[date, bool]:
    """Início da janela: a última carga `ok` menos a margem (as casas publicam com atraso),
    nunca antes do `piso`. Devolve (início, completa); completa = não há carga anterior."""
    hoje = hoje or date.today()
    ultima = session.scalar(
        select(FonteIngestao.concluido_em)
        .where(FonteIngestao.fonte == fonte, FonteIngestao.status == "ok")
        .order_by(FonteIngestao.concluido_em.desc())
        .limit(1)
    )
    if ultima is None:
        return piso, True
    inicio = max(piso, ultima.astimezone(UTC).date() - timedelta(days=margem_dias))
    return min(inicio, hoje), False


def votadas_por_dia(
    session: Session, casa: str, inicio: date, fim: date
) -> tuple[set[date], dict[date, dict[str, str]]]:
    """Dias com votação nominal na janela e, por dia, rótulo -> id da matéria votada."""
    dias: set[date] = set()
    mapa: dict[date, dict[str, str]] = defaultdict(dict)
    linhas = session.execute(
        select(Votacao.data, Votacao.proposicao, Votacao.proposicao_id_externo).where(
            Votacao.casa == casa, Votacao.data >= inicio, Votacao.data <= fim
        )
    )
    for dia, proposicao, id_externo in linhas:
        dias.add(dia)
        r = rotulo(proposicao)
        if r and id_externo:
            mapa[dia].setdefault(r, id_externo)
    return dias, mapa


def ligar(citadas: set[str], votadas_do_dia: dict[str, str]) -> str | None:
    """Id da matéria votada no dia a que o discurso se refere, ou None (discurso do dia)."""
    if not citadas or len(citadas) > MAX_MATERIAS_LIGADAS:
        return None
    casadas = {votadas_do_dia[r] for r in citadas if r in votadas_do_dia}
    return casadas.pop() if len(casadas) == 1 else None


def recarregar_discursos(
    session: Session,
    casa: str,
    inicio: date,
    fim: date,
    discursos: list[dict[str, Any]],
    ingestao: FonteIngestao,
    completa: bool = False,
) -> int:
    """Substitui os discursos da casa na janela [inicio, fim].

    Cada discurso traz `data`, `parlamentar_id`, `citadas` (conjunto de rótulos) e as colunas
    da tabela. Ficam só os de dia com votação nominal que citam alguma matéria. Lista vazia:
    na carga completa é erro (a fonte falhou ou as votações não foram carregadas); na
    incremental, a janela pode estar mesmo sem discursos (recesso), e nada é apagado."""
    dias, votadas = votadas_por_dia(session, casa, inicio, fim)
    linhas: dict[str, dict[str, Any]] = {}
    for d in discursos:
        citadas = d["citadas"]
        if not citadas or d["data"] not in dias or not (inicio <= d["data"] <= fim):
            continue
        linha = {k: v for k, v in d.items() if k != "citadas"}
        linha["materias_citadas"] = len(citadas)
        linha["proposicao_id_externo"] = ligar(citadas, votadas.get(d["data"], {}))
        linhas[linha["id_externo"]] = linha | {"casa": casa, "ingestao_id": ingestao.id}
    if not linhas:
        if completa:
            raise ValueError(
                f"Nenhum discurso de {casa} em dia de votação; abortando a carga completa."
            )
        return 0
    session.execute(
        delete(Discurso).where(Discurso.casa == casa, Discurso.data >= inicio, Discurso.data <= fim)
    )
    lista = list(linhas.values())
    for i in range(0, len(lista), 2000):
        session.execute(insert(Discurso), lista[i : i + 2000])
    return len(lista)


def hora(texto: str | None) -> datetime | None:
    """ "2025-02-04T15:36" -> datetime; só a data (ou nada) -> None."""
    if not texto or len(texto) < 16:
        return None
    try:
        return datetime.fromisoformat(texto[:16])
    except ValueError:
        return None
