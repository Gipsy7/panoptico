"""Transferências especiais ("emendas Pix"): plano de ação, empenho e relatório de gestão.

API aberta do TransfereGov (PostgREST, sem chave): `plano_acao_especial` traz o número da
emenda (12 dígitos, o mesmo `codigo` da tabela `emenda`), o beneficiário e os valores;
`executor_especial` o objeto; `empenho_especial` o valor empenhado (situação "Enviado");
`relatorio_gestao_especial` a prestação de contas do beneficiário. A API pagina em 1.000
linhas; o bruto guardado é só o recorte das emendas da base.
"""

import argparse
import gzip
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Emenda, EmendaTransferencia, FonteIngestao
from ingestion import comum
from ingestion.proposicoes_comum import INICIO_LEGISLATURA

FONTE = "transferegov_especiais"
BASE = "https://api.transferegov.gestao.gov.br/transferenciasespeciais"
URL = BASE + "/plano_acao_especial"
PAGINA = 1000
EMPENHO_ENVIADO = 4
CAMPOS_PLANO = (
    "id_plano_acao",
    "codigo_plano_acao",
    "situacao_plano_acao",
    "cnpj_beneficiario_plano_acao",
    "nome_beneficiario_plano_acao",
    "uf_beneficiario_plano_acao",
    "numero_emenda_parlamentar_plano_acao",
    "valor_custeio_plano_acao",
    "valor_investimento_plano_acao",
)


def paginas(client: httpx.Client, tabela: str, params: dict[str, str]) -> list[dict[str, Any]]:
    """Todas as linhas da tabela, em páginas ordenadas pela chave (estáveis entre chamadas)."""
    linhas: list[dict[str, Any]] = []
    while True:
        pagina = comum.get_json(
            client, f"{BASE}/{tabela}", {**params, "limit": PAGINA, "offset": len(linhas)}
        )
        linhas.extend(pagina)
        if len(pagina) < PAGINA:
            return linhas


SITUACOES = {
    "EM_ELABORACAO": "Em elaboração",
    "IMPEDIDO_REJEICAO_PLANO_TRABALHO": "Impedido (plano de trabalho rejeitado)",
}


def humanizar(texto: str | None) -> str | None:
    """EM_ELABORACAO -> "Em elaboração"; o que não está no dicionário vira frase."""
    if not texto:
        return None
    if texto in SITUACOES:
        return SITUACOES[texto]
    texto = texto.replace("_", " ").strip()
    return texto[:1].upper() + texto[1:].lower()


def baixar_recorte(client: httpx.Client, codigos: set[str]) -> dict[str, list[dict[str, Any]]]:
    ano_minimo = INICIO_LEGISLATURA.year
    planos = [
        p
        for p in paginas(
            client,
            "plano_acao_especial",
            {
                "ano_emenda_parlamentar_plano_acao": f"gte.{ano_minimo}",
                "order": "id_plano_acao",
            },
        )
        if p["numero_emenda_parlamentar_plano_acao"] in codigos
    ]
    planos = [{k: p[k] for k in CAMPOS_PLANO} for p in planos]
    if not planos:
        return {"planos": [], "executores": [], "empenhos": [], "relatorios": []}
    primeiro = {"id_plano_acao": f"gte.{min(p['id_plano_acao'] for p in planos)}"}
    ids = {p["id_plano_acao"] for p in planos}

    def dos_planos(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [x for x in linhas if x["id_plano_acao"] in ids]

    executores = dos_planos(
        paginas(
            client,
            "executor_especial",
            {
                **primeiro,
                "select": "id_plano_acao,id_executor,nome_executor,objeto_executor",
                "order": "id_executor",
            },
        )
    )
    empenhos = dos_planos(
        paginas(
            client,
            "empenho_especial",
            {
                **primeiro,
                "situacao_empenho": f"eq.{EMPENHO_ENVIADO}",
                "select": "id_empenho,id_plano_acao,valor_empenho",
                "order": "id_empenho",
            },
        )
    )
    relatorios = dos_planos(
        paginas(
            client,
            "relatorio_gestao_especial",
            {**primeiro, "select": "id_relatorio_gestao,situacao_relatorio_gestao,id_plano_acao",
             "order": "id_relatorio_gestao"},
        )
    )  # fmt: skip
    return {"planos": planos, "executores": executores, "empenhos": empenhos,
            "relatorios": relatorios}  # fmt: skip


def normalizar(recorte: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    objetos: dict[int, list[str]] = {}
    for e in recorte["executores"]:
        objeto = " ".join((e.get("objeto_executor") or "").split())
        if objeto and objeto not in objetos.setdefault(e["id_plano_acao"], []):
            objetos[e["id_plano_acao"]].append(objeto)
    empenhado: dict[int, Decimal] = {}
    for e in recorte["empenhos"]:
        empenhado[e["id_plano_acao"]] = empenhado.get(e["id_plano_acao"], Decimal(0)) + Decimal(
            str(e["valor_empenho"] or 0)
        )
    relatorio = {  # o mais recente de cada plano
        r["id_plano_acao"]: r["situacao_relatorio_gestao"]
        for r in sorted(recorte["relatorios"], key=lambda r: r["id_relatorio_gestao"])
    }
    linhas = []
    for p in recorte["planos"]:
        codigo = p["numero_emenda_parlamentar_plano_acao"]
        total = Decimal(str(p["valor_custeio_plano_acao"] or 0)) + Decimal(
            str(p["valor_investimento_plano_acao"] or 0)
        )
        linhas.append(
            {
                "tipo": "especial",
                "emenda_codigo": codigo,
                "ano_emenda": int(codigo[:4]),
                "identificador": p["codigo_plano_acao"],
                "situacao": humanizar(p["situacao_plano_acao"]),
                "relatorio_gestao": humanizar(relatorio.get(p["id_plano_acao"])),
                "beneficiario": p["nome_beneficiario_plano_acao"],
                "beneficiario_cnpj": p["cnpj_beneficiario_plano_acao"],
                "uf": p["uf_beneficiario_plano_acao"],
                "objeto": " | ".join(objetos.get(p["id_plano_acao"], []))[:2000] or None,
                "valor_total": total,
                "valor_repassado": empenhado.get(p["id_plano_acao"], Decimal(0)),
            }
        )
    return linhas


def carregar(session: Session, payload: bytes, ingestao: FonteIngestao) -> int:
    recorte = json.loads(gzip.decompress(payload) if payload[:2] == b"\x1f\x8b" else payload)
    if not recorte["planos"]:
        raise ValueError("Nenhum plano de ação das emendas na API; abortando.")
    linhas = [{**r, "ingestao_id": ingestao.id} for r in normalizar(recorte)]
    unicas = {(r["identificador"], r["emenda_codigo"]): r for r in linhas}
    session.execute(delete(EmendaTransferencia).where(EmendaTransferencia.tipo == "especial"))
    lista = list(unicas.values())
    for inicio in range(0, len(lista), 5000):
        session.execute(insert(EmendaTransferencia), lista[inicio : inicio + 5000])
    return len(lista)


def executar(de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> bytes:
        with SessionLocal() as session:
            codigos = set(session.scalars(select(Emenda.codigo).distinct()))
        recorte = baixar_recorte(client, codigos)
        return json.dumps(recorte, ensure_ascii=False, sort_keys=True).encode()

    return comum.executar_ingestao(
        FONTE,
        URL,
        baixar,
        carregar,
        de_raw=de_raw,
        extensao_raw=".json.gz",
        incremental=comum.Incremental(chave=FONTE),  # a API não informa validadores
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} planos de ação ligados a emendas")
