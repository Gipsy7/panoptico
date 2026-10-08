"""Contas anuais dos municípios no SICONFI (Tesouro Nacional), Declaração de Contas Anuais.

A API (apidatalake.tesouro.gov.br) só responde por ente: uma consulta por município, anexo
e ano (cerca de 0,8 s cada). Guardamos por município e ano: a receita realizada (Anexo I-C,
total), a despesa paga e a despesa paga por função de governo (Anexo I-E, só o primeiro
nível, ex.: "10 - Saúde"). O bruto guardado já é só o recorte usado.

Os dados são anuais (entregues até abril do ano seguinte): a carga roda uma vez por mês.
"""

import argparse
import re
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ContasMunicipio, FonteIngestao, Municipio
from ingestion import comum

FONTE = "siconfi_contas"
URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca"
FUNCAO = re.compile(r"^(\d{2}) - (.+)$")  # "10 - Saúde" (subfunções têm "10.301 - ...")


def _consultar(client: httpx.Client, ibge: str, ano: int, anexo: str) -> list[dict]:
    try:
        dados = comum.get_json(
            client, URL, params={"an_exercicio": ano, "no_anexo": anexo, "id_ente": ibge}
        )
    except httpx.HTTPError:
        return []
    return dados.get("items", [])


def recortar(ibge: str, receitas: list[dict], despesas: list[dict]) -> dict[str, Any] | None:
    """Do que a API devolve, só o que guardamos (o bruto fica pequeno)."""
    if not receitas and not despesas:
        return None
    receita = next(
        (
            r["valor"]
            for r in receitas
            if r["cod_conta"] == "TotalReceitas" and r["coluna"] == "Receitas Brutas Realizadas"
        ),
        None,
    )
    pagas = [d for d in despesas if d["coluna"] == "Despesas Pagas"]
    por_area: dict[str, float] = {}
    for d in pagas:
        if achado := FUNCAO.match(d["conta"].strip()):
            area = achado.group(2).strip()
            por_area[area] = por_area.get(area, 0) + float(d["valor"] or 0)
    # O total é a soma das funções (o código "TotalDespesas" se repete em várias linhas).
    total = round(sum(por_area.values()), 2) if por_area else None
    populacao = next(
        (x.get("populacao") for x in [*despesas, *receitas] if x.get("populacao")), None
    )
    return {
        "ibge": ibge,
        "populacao": populacao,
        "receita_total": receita,
        "despesa_paga": total,
        "despesa_por_area": por_area,
    }


def baixar(client: httpx.Client, ano: int, ibges: list[str]) -> list[dict]:
    def um(ibge: str) -> dict | None:
        return recortar(
            ibge,
            _consultar(client, ibge, ano, "DCA-Anexo I-C"),
            _consultar(client, ibge, ano, "DCA-Anexo I-E"),
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        return [r for r in pool.map(um, ibges) if r]


def executar(ano: int, de_raw: Path | None = None) -> int:
    with SessionLocal() as session:
        ibges = list(session.scalars(select(Municipio.ibge).order_by(Municipio.ibge)))

    def carregar(session: Session, payload: list[dict], ingestao: FonteIngestao) -> int:
        if len(payload) < len(ibges) // 2:  # API fora do ar ou ano ainda não entregue
            raise ValueError(f"Só {len(payload)} municípios com contas de {ano}; abortando.")
        session.execute(delete(ContasMunicipio).where(ContasMunicipio.ano == ano))
        linhas = [
            {
                "municipio_ibge": c["ibge"],
                "ano": ano,
                "populacao": c["populacao"],
                "receita_total": Decimal(str(c["receita_total"]))
                if c["receita_total"] is not None
                else None,
                "despesa_paga": Decimal(str(c["despesa_paga"]))
                if c["despesa_paga"] is not None
                else None,
                "despesa_por_area": c["despesa_por_area"],
            }
            for c in payload
        ]
        for inicio in range(0, len(linhas), 2000):
            session.execute(insert(ContasMunicipio), linhas[inicio : inicio + 2000])
        return len(linhas)

    return comum.executar_ingestao(
        FONTE,
        URL,
        lambda client: baixar(client, ano, ibges),
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{ano}_",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", help="Padrão: os dois últimos anos fechados")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    anos = args.ano or [a - 1 for a in comum.anos_padrao()]
    for ano in anos:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} municípios")
