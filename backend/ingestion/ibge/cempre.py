"""Cadastro Central de Empresas (CEMPRE) do IBGE: empresas, pessoas ocupadas, assalariados e
salário médio por município, estado e Brasil (tabela 9509, 2022 em diante), e as pessoas
ocupadas por seção de atividade (CNAE 2.0) no último ano (tabela 9510), para "onde a cidade
trabalha" e as vocações.

API de agregados v3. Totais: um ano por consulta com todos os municípios. Seções: um estado por
consulta, só as 21 seções (letras A a U) e o total. "-" é zero, "X" é valor protegido pelo
sigilo (poucas empresas: o IBGE não divulga) e não é guardado. O CEMPRE cobre empresas e
órgãos com CNPJ: não inclui o trabalho informal.
"""

import argparse
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import EmpregoIbge, EmpregoSetor, FonteIngestao
from ingestion import comum
from ingestion.ibge.pam import CODIGOS_UF

FONTE = "ibge_cempre"
BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"
URL = BASE + "/9509/metadados"
TOTAIS = {"367": "empresas", "707": "pessoal_ocupado", "708": "assalariados",
          "10143": "salario_medio", "1606": "salario_medio_sm"}  # fmt: skip
CNAE = "12762"
AUSENTE = {"...", "..", "X", "", "-"}


def _secoes(client: httpx.Client) -> dict[str, str]:
    """id da categoria -> nome, só as seções (letra + espaço) da tabela 9510."""
    categorias = comum.get_json(client, BASE + "/9510/metadados")["classificacoes"][0]["categorias"]
    return {str(c["id"]): c["nome"] for c in categorias if re.match(r"^[A-U] ", c["nome"])}


def baixar(client: httpx.Client) -> dict[str, Any]:
    periodo = comum.get_json(client, URL)["periodicidade"]
    anos = range(int(periodo["inicio"]), int(periodo["fim"]) + 1)
    recorte: dict[str, Any] = {"totais": {}, "setores": {}, "ano_setores": int(periodo["fim"])}
    for ano in anos:
        for nivel in ("N6[all]", "N3[all]", "N1[all]"):
            corpo = comum.get_json(
                client,
                f"{BASE}/9509/periodos/{ano}/variaveis/{'|'.join(TOTAIS)}",
                {"localidades": nivel},
            )
            for v in corpo:
                por = recorte["totais"].setdefault(f"{ano}:{v['id']}", {})
                for s in v["resultados"][0]["series"]:
                    por[s["localidade"]["id"]] = s["serie"].get(str(ano), "")
    secoes = _secoes(client)
    ano = recorte["ano_setores"]
    for nivel in [f"N6[N3[{uf}]]" for uf in CODIGOS_UF] + ["N3[all]", "N1[all]"]:
        corpo = comum.get_json(
            client,
            f"{BASE}/9510/periodos/{ano}/variaveis/707",
            {"localidades": nivel, "classificacao": f"{CNAE}[{','.join(secoes)}]"},
        )
        for item in corpo[0]["resultados"]:
            nome = next(iter(item["classificacoes"][0]["categoria"].values()))
            por = recorte["setores"].setdefault(nome, {})
            for s in item["series"]:
                por[s["localidade"]["id"]] = s["serie"].get(str(ano), "")
    return recorte


def _valor(texto: str) -> Decimal | None:
    texto = (texto or "").strip()
    return None if texto in AUSENTE else Decimal(texto)


def normalizar(recorte: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    totais: dict[tuple[str, int], dict[str, Any]] = {}
    for chave, por_local in recorte["totais"].items():
        ano_txt, variavel = chave.split(":")
        coluna = TOTAIS.get(variavel)
        if coluna is None:
            continue
        for codigo, texto in por_local.items():
            linha = totais.setdefault(
                (codigo, int(ano_txt)),
                {"codigo": codigo, "ano": int(ano_txt), **dict.fromkeys(TOTAIS.values())},
            )
            linha[coluna] = _valor(texto)
    setores = []
    ano = int(recorte["ano_setores"])
    for nome, por_local in recorte["setores"].items():
        secao, _, descricao = nome.partition(" ")
        for codigo, texto in por_local.items():
            valor = _valor(texto)
            if valor:
                setores.append({"codigo": codigo, "ano": ano, "secao": secao,
                                "nome": descricao.strip(), "pessoal_ocupado": valor})  # fmt: skip
    linhas = [r for r in totais.values() if r["pessoal_ocupado"] is not None]
    return linhas, setores


def conferir(totais: list[dict[str, Any]]) -> None:
    """Pessoal ocupado: a soma dos municípios fecha com o Brasil em cada ano (0,5%)."""
    for ano in sorted({r["ano"] for r in totais}):
        brasil = sum(r["pessoal_ocupado"] for r in totais if r["ano"] == ano and r["codigo"] == "1")
        municipios = sum(
            r["pessoal_ocupado"] for r in totais if r["ano"] == ano and len(r["codigo"]) == 7
        )
        if not brasil or abs(municipios - brasil) > brasil * Decimal("0.005"):
            raise ValueError(f"CEMPRE {ano} não fecha: Brasil {brasil}, municípios {municipios}.")


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    totais, setores = normalizar(payload)
    if len({r["codigo"] for r in totais if len(r["codigo"]) == 7}) < 5000:
        raise ValueError("CEMPRE com menos de 5 mil municípios; abortando.")
    conferir(totais)
    session.execute(delete(EmpregoSetor))
    session.execute(delete(EmpregoIbge))
    for tabela, lista in ((EmpregoIbge, totais), (EmpregoSetor, setores)):
        linhas = [{**r, "ingestao_id": ingestao.id} for r in lista]
        for inicio in range(0, len(linhas), 5000):
            session.execute(insert(tabela), linhas[inicio : inicio + 5000])
    return len(totais) + len(setores)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} linhas (totais e seções de atividade)")
