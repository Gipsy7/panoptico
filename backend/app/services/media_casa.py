"""Média da Casa quando a fonte não cobre todos os parlamentares em exercício.

Regra única (ver docs/DECISOES.md, 27/10/2026): a fonte é *parcial* quando está declarada
parcial (`GASTOS_PARCIAIS`, ou `FONTE_PARCIAL` no adaptador de emendas estaduais) E há
parlamentares em exercício sem nenhuma linha dela no período. Nesse caso a média sai só entre
quem consta na fonte, e o texto diz "X dos Y". Fonte completa não muda: quem não tem nada
entra com zero. "Gastou zero" é diferente de "não consta": só vale como ausência a falta de
linha, nunca um valor zero.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

# (casa, UF) cujos gastos do gabinete vêm de fonte que não traz todos os deputados:
# a planilha de verbas indenizatórias da CLDF não cobre todos os distritais.
# Valor: (quem, onde aparecem), para o texto.
# Também as assembleias de gastos em carga própria (ingestion/assembleias/gastos_*.py): o portal
# escreve alguns nomes diferente da lista da Casa e eles esperam revisão humana (apelidos); até
# lá esses deputados "não constam", em vez de entrarem com zero.
GASTOS_PARCIAIS: dict[tuple[str, str], tuple[str, str]] = {
    ("assembleia", "DF"): ("deputados distritais", "na planilha da CLDF"),
    ("assembleia", "BA"): ("deputados", "nas verbas indenizatórias da ALBA"),
    ("assembleia", "PE"): ("deputados", "na verba indenizatória da ALEPE"),
    ("assembleia", "ES"): ("deputados", "nas cotas parlamentares da ALES"),
    ("assembleia", "AM"): ("deputados", "na cota parlamentar da ALEAM"),
    ("assembleia", "RO"): ("deputados", "na verba indenizatória da ALERO"),
    ("assembleia", "PB"): ("deputados", "nas planilhas da VIAP da ALPB"),
}


@dataclass(frozen=True)
class MediaCasa:
    media: Decimal | None
    na_media: int  # quantos entraram na média
    em_exercicio: int  # quantos estão no cargo hoje
    parcial: bool  # a média saiu só de quem consta na fonte


def calcular(valores: Sequence[Decimal], constam: Sequence[bool], fonte_parcial: bool) -> MediaCasa:
    """`valores[i]` e `constam[i]` são do i-ésimo parlamentar em exercício. Fonte completa:
    todos entram (os sem linha com zero). Fonte parcial: só entram os que constam; se todos
    constam, a fonte não deixou ninguém de fora e nada muda."""
    total = len(valores)
    if total == 0:
        return MediaCasa(None, 0, 0, False)
    entram = [v for v, c in zip(valores, constam, strict=True) if c or not fonte_parcial]
    parcial = fonte_parcial and len(entram) < total
    if not entram:  # fonte parcial sem ninguém em exercício nela: não há média a mostrar
        return MediaCasa(None, 0, total, True)
    return MediaCasa(sum(entram, start=Decimal(0)) / len(entram), len(entram), total, parcial)


def descricao_parcial(m: MediaCasa, *, quem: str, fonte: str) -> str | None:
    """Texto da média quando parcial (nulo quando não é). `quem` no plural ("deputados
    distritais"); `fonte` com artigo ("na planilha da CLDF")."""
    if not m.parcial:
        return None
    fora = m.em_exercicio - m.na_media
    return (
        f"Média entre os {m.na_media} dos {m.em_exercicio} {quem} que aparecem {fonte}; "
        f"{'o outro não consta' if fora == 1 else f'os outros {fora} não constam'} da fonte."
    )
