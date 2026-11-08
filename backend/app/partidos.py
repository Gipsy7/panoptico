"""Sigla de partido padronizada.

As câmaras municipais (SAPL e sites de fornecedores) escrevem a mesma sigla de vários jeitos
("REP", "Rep.", "REPUBL", "Republicanos"); o TSE e a Câmara usam uma forma só. Aqui só se juntam
variações óbvias da MESMA sigla. Siglas de partidos que mudaram de nome ou se fundiram (PMDB, DEM,
PRB, PSL, PPS...) ficam como estão: são o registro da fonte, não um erro de grafia. Sigla que não
está na tabela sai como veio (só sem espaços nas pontas). Ver docs/DECISOES.md, "Siglas de partido".
"""

import unicodedata

SEM_PARTIDO = "Sem partido"

# Forma oficial (como o TSE publica) -> grafias vistas nas fontes.
_GRAFIAS: dict[str, tuple[str, ...]] = {
    "AGIR": ("AG", "AGIR", "AGIR36", "AGIR 36"),
    "AVANTE": ("AV", "AVANTE", "AVT"),
    "CIDADANIA": ("CID", "CIDADANIA"),
    "MDB": ("MDB", "MDB 15"),
    "MOBILIZA": ("MOB", "MOBILIZA"),
    "NOVO": ("NOVO",),
    "PCdoB": ("PCDOB", "PC DO B"),
    "PODE": ("PODE", "PODEMOS"),
    "PP": ("PP", "PROGRESSISTA", "PROGRESSISTAS"),
    "PV": ("PV", "PARTIDO VERDE", "PARTIDO VERDE PV"),
    "REDE": ("REDE", "REDE SUSTENTABILIDADE", "REDE SUSTENTABILIDADE REDE"),
    "REPUBLICANOS": (
        "REP",
        "REP10",
        "REP 10",
        "REPU",
        "REPUB",
        "REPUBL",
        "REPUBLIC",
        "REPUBLICA",
        "REPUBLICAMOS",
        "REPUBLICANO",
        "REPUBLICANOS",
    ),
    "SOLIDARIEDADE": ("SD", "SDD", "SOLIDARIEDADE"),
    "UNIÃO": ("UB", "UBR", "UNI", "UNIAO", "UNIAO BRASIL"),
}


def _chave(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    limpo = "".join(c if c.isalnum() else " " for c in sem_acento.upper())
    return " ".join(limpo.split())


_POR_CHAVE = {_chave(g): oficial for oficial, grafias in _GRAFIAS.items() for g in grafias}
_SEM = {"S PARTIDO", "SEM PARTIDO", "S P"}


def sigla_partido(texto: str | None) -> str | None:
    """Sigla padronizada; None quando vazio. "S/Partido" vira "Sem partido"."""
    if texto is None:
        return None
    bruto = texto.strip()
    if not bruto:
        return None
    chave = _chave(bruto)
    if chave in _SEM:
        return SEM_PARTIDO
    return _POR_CHAVE.get(chave, bruto)
