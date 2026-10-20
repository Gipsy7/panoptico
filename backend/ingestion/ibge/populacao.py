"""População residente do IBGE (SIDRA): Brasil, estados e municípios.

- Estimativas anuais: tabela 6579, variável 9324 (2019, 2020, 2021, 2024, 2025...).
- 2022: Censo, tabela 9514, variável 93, só o total (sexo, idade e forma de declaração
  "Total"). O IBGE não publicou estimativa para 2023 (salto do Censo 2022 para a
  estimativa de 2024): 2023 fica sem valor, não se interpola.

A API do SIDRA devolve uma lista cuja primeira linha é o cabeçalho; valores ausentes vêm
como "...", "-" ou "X" e não são guardados. Conferência: a soma das UFs e a soma dos
municípios devem fechar com o Brasil em cada ano (falha aborta a carga).
"""

import argparse
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, PopulacaoIbge
from ingestion import comum

FONTE = "ibge_populacao"
BASE = "https://apisidra.ibge.gov.br/values"
ANOS_ESTIMATIVA = [2019, 2020, 2021, 2024, 2025]
ANO_CENSO = 2022
NIVEIS = ("n1", "n3", "n6")
AUSENTE = {"...", "..", "-", "X", ""}


def url(nivel: str, ano: int) -> str:
    if ano == ANO_CENSO:
        return f"{BASE}/t/9514/{nivel}/all/v/93/p/{ano}/c2/6794/c287/100362/c286/113635"
    return f"{BASE}/t/6579/{nivel}/all/v/9324/p/{ano}"


def normalizar(payload: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """{'n6_2024': [cabeçalho, linhas...]} -> registros (codigo, ano, valor, origem)."""
    registros: dict[tuple[str, int], dict[str, Any]] = {}
    for chave, linhas in payload.items():
        ano = int(chave.rsplit("_", 1)[1])
        for linha in linhas[1:]:  # a primeira é o cabeçalho
            if linha["V"].strip() in AUSENTE:
                continue
            codigo = linha["D1C"].strip()
            registros[(codigo, ano)] = {
                "codigo": codigo,
                "ano": ano,
                "valor": int(linha["V"]),
                "origem": "censo" if ano == ANO_CENSO else "estimativa",
            }
    return list(registros.values())


def conferir(registros: list[dict[str, Any]]) -> None:
    """Soma das UFs e dos municípios = Brasil, por ano."""
    for ano in sorted({r["ano"] for r in registros}):
        do_ano = [r for r in registros if r["ano"] == ano]
        brasil = sum(r["valor"] for r in do_ano if r["codigo"] == "1")
        ufs = sum(r["valor"] for r in do_ano if len(r["codigo"]) == 2)
        municipios = sum(r["valor"] for r in do_ano if len(r["codigo"]) == 7)
        if not brasil or ufs != brasil or municipios != brasil:
            raise ValueError(
                f"População {ano} não fecha: Brasil {brasil}, UFs {ufs}, municípios {municipios}."
            )


def baixar(client, anos: list[int]) -> dict[str, list[dict[str, Any]]]:
    payload: dict[str, list[dict[str, Any]]] = {}
    for ano in anos:
        for nivel in NIVEIS:
            linhas = comum.get_json(client, url(nivel, ano))
            if len(linhas) > 1:  # ano sem publicação vem só com o cabeçalho: fica de fora
                payload[f"{nivel}_{ano}"] = linhas
            else:
                print(f"  {ano} {nivel}: sem dados publicados; ignorado", flush=True)
    return payload


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    registros = normalizar(payload)
    if not registros:
        raise ValueError("Nenhuma população recebida; abortando.")
    conferir(registros)
    anos = sorted({r["ano"] for r in registros})
    session.execute(delete(PopulacaoIbge).where(PopulacaoIbge.ano.in_(anos)))
    for inicio in range(0, len(registros), 2000):
        session.execute(insert(PopulacaoIbge), registros[inicio : inicio + 2000])
    return len(registros)


def anos_padrao() -> list[int]:
    # Anos além de 2025 entram quando o IBGE publicar (sem dados, são ignorados).
    return [*sorted([*ANOS_ESTIMATIVA, ANO_CENSO]), *range(2026, date.today().year + 1)]


def executar(anos: list[int] | None = None, de_raw: Path | None = None) -> int:
    anos = anos or anos_padrao()
    return comum.executar_ingestao(
        FONTE,
        f"{BASE}/t/6579/n6/all/v/9324/p/{max(anos)}",
        lambda client: baixar(client, anos),
        carregar,
        de_raw=de_raw,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", help="Padrão: 2019-2022, 2024 em diante")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(args.ano, de_raw=args.de_raw)} valores")
