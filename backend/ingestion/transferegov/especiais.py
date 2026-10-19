"""Transferências especiais ("emendas Pix"): plano de ação, empenho e relatório de gestão.

API aberta do TransfereGov (PostgREST, sem chave): `plano_acao_especial` traz o número da
emenda (12 dígitos, o mesmo `codigo` da tabela `emenda`), o beneficiário e os valores;
`executor_especial` o objeto; `empenho_especial` o valor empenhado (situação "Enviado");
`relatorio_gestao_especial` a prestação de contas do beneficiário. A API pagina em 1.000
linhas. Desde 18/10/2026 baixa todos os planos (desde 2020, ~58 mil), não só os das
emendas da base, para que a página da cidade mostre o plano de quem não está mais no cargo.
Cada plano ganha o município do beneficiário (ingestion.transferegov.municipio).

O plano é o valor **previsto** (situação "CIENTE" = o beneficiário tomou ciência); o valor
**pago** vem do arquivo por favorecido da CGU (`emenda_pagamento`). A página não soma os dois.
Dados bancários do plano (banco, agência, conta) não são guardados.
"""

import argparse
import gzip
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import EmendaTransferencia, FonteIngestao
from ingestion import comum
from ingestion.transferegov import municipio

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


def baixar_tudo(client: httpx.Client) -> dict[str, list[dict[str, Any]]]:
    """Todos os planos, executores, empenhos enviados e relatórios de gestão, e os entes do
    SICONFI para o mapa CNPJ -> município."""
    planos = [
        {k: p[k] for k in CAMPOS_PLANO}
        for p in paginas(client, "plano_acao_especial", {"order": "id_plano_acao"})
    ]
    executores = paginas(
        client,
        "executor_especial",
        {"select": "id_plano_acao,id_executor,nome_executor,objeto_executor",
         "order": "id_executor"},
    )  # fmt: skip
    empenhos = paginas(
        client,
        "empenho_especial",
        {"situacao_empenho": f"eq.{EMPENHO_ENVIADO}",
         "select": "id_empenho,id_plano_acao,valor_empenho", "order": "id_empenho"},
    )  # fmt: skip
    relatorios = paginas(
        client,
        "relatorio_gestao_especial",
        {"select": "id_relatorio_gestao,situacao_relatorio_gestao,id_plano_acao",
         "order": "id_relatorio_gestao"},
    )  # fmt: skip
    return {"planos": planos, "executores": executores, "empenhos": empenhos,
            "relatorios": relatorios, "entes": municipio.baixar_entes(client)}  # fmt: skip


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
        codigo = (p["numero_emenda_parlamentar_plano_acao"] or "").strip()
        if len(codigo) != 12 or not codigo.isdigit():
            continue  # plano sem número de emenda: não há a que ligar
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


def com_municipio(linhas: list[dict[str, Any]], mapa: municipio.Mapa) -> dict[str, int]:
    """Preenche `municipio_ibge` e devolve a contagem por forma de resolução."""
    contagem: dict[str, int] = {}
    for r in linhas:
        ibge, como = mapa.resolver(r["beneficiario_cnpj"], r["uf"], r["beneficiario"])
        r["municipio_ibge"] = ibge
        contagem[como] = contagem.get(como, 0) + 1
    return contagem


def carregar(session: Session, payload: bytes, ingestao: FonteIngestao) -> int:
    recorte = json.loads(gzip.decompress(payload) if payload[:2] == b"\x1f\x8b" else payload)
    if not recorte["planos"]:
        raise ValueError("Nenhum plano de ação das emendas na API; abortando.")
    linhas = [{**r, "ingestao_id": ingestao.id} for r in normalizar(recorte)]
    entes = recorte.get("entes") or []  # brutos anteriores a 18/10/2026 não têm os entes
    contagem = com_municipio(linhas, municipio.montar(session, entes))
    print(f"  planos por forma de achar o município: {contagem}")
    unicas = {(r["identificador"], r["emenda_codigo"]): r for r in linhas}
    session.execute(delete(EmendaTransferencia).where(EmendaTransferencia.tipo == "especial"))
    lista = list(unicas.values())
    for inicio in range(0, len(lista), 5000):
        session.execute(insert(EmendaTransferencia), lista[inicio : inicio + 5000])
    return len(lista)


def executar(de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> bytes:
        return json.dumps(baixar_tudo(client), ensure_ascii=False, sort_keys=True).encode()

    return comum.executar_ingestao(
        FONTE,
        URL,
        baixar,
        carregar,
        de_raw=de_raw,
        extensao_raw=".json.gz",
        # A API não informa validadores; o mapa de fundos vem do arquivo por favorecido.
        incremental=comum.Incremental(chave=FONTE, contexto=municipio.contexto),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} planos de ação de transferências especiais")
