"""Obras federais do Obrasgov.br (Ministério da Gestão e da Inovação), pela API pública
nova (https://api-publica.obrasgov.gestao.gov.br/obras, sem chave):

- `projeto-investimento`: cada obra ou projeto, com situação, datas, valor previsto por
  fonte de recurso, órgão responsável e executor (~155 mil);
- `geometria`: o lugar de cada obra, com o código do IBGE do município (~241 mil; uma obra
  pode ter mais de uma geometria e mais de um município);
- `execucao-fisica`: o percentual executado (~74 mil; até dois registros por obra, vale o
  de atualização mais recente).

Armadilhas (docs/FONTES_DE_DADOS.md): a página tem no máximo 200 itens; a API antiga
(api.obrasgov.gestao.gov.br) não traz o município e o seu `totalElements` só repete o
tamanho da página. O bruto guarda só os campos usados (sem as descrições longas).
"""

import argparse
import gzip
import json
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, ObraFederal, ObraFederalMunicipio
from ingestion import comum

FONTE = "obrasgov_obras"
BASE = "https://api-publica.obrasgov.gestao.gov.br/obras"
URL = BASE + "/projeto-investimento"
PAGINA = 200
PAUSA = 0.15
LOTE = 5000

CAMPOS_PROJETO = (
    "id_projeto_investimento",
    "desc_nome",
    "situacao",
    "natureza_intervencao",
    "especie_intervencao",
    "uf_principal",
    "dt_inicial_prevista",
    "dt_final_prevista",
    "dt_inicial_efetiva",
    "dt_final_efetiva",
    "dt_cadastro",
    "organizacao_resp",
    "executores",
    "investimentos_previstos",
    "eixos_tipos",
)


def paginas(client: httpx.Client, recurso: str, campos: tuple[str, ...] | None = None):
    """Todas as linhas do recurso, página a página (1, 2, ... até `total_pages`)."""
    linhas: list[dict[str, Any]] = []
    pagina, total = 1, 1
    while pagina <= total:
        corpo = comum.get_json(
            client, f"{BASE}/{recurso}", {"pagina": pagina, "tamanho_da_pagina": PAGINA}
        )
        total = int(corpo.get("total_pages") or 0)
        for item in corpo.get("data") or []:
            linhas.append({k: item.get(k) for k in campos} if campos else item)
        pagina += 1
        time.sleep(PAUSA)
    return linhas


def baixar_tudo(client: httpx.Client) -> dict[str, list[dict[str, Any]]]:
    projetos = paginas(client, "projeto-investimento", CAMPOS_PROJETO)
    geometrias = paginas(client, "geometria", ("id_projeto_investimento", "cod_ibge"))
    execucoes = paginas(
        client,
        "execucao-fisica",
        ("id_projeto_investimento", "percentual_execucao_fisica", "dt_atualizacao_execucao"),
    )
    return {"projetos": projetos, "geometrias": geometrias, "execucoes": execucoes}


def _data(valor: str | None) -> date | None:
    try:
        return date.fromisoformat(valor[:10]) if valor else None
    except ValueError:
        return None


def _texto(valor: Any, limite: int) -> str | None:
    texto = " ".join(str(valor or "").split())
    return texto[:limite] or None


def normalizar(recorte: dict[str, list[dict[str, Any]]]) -> tuple[list[dict], list[dict]]:
    """Bruto -> (obras, ligações obra-município). Obra repetida entre páginas fica uma só."""
    execucao: dict[str, tuple[str, Any]] = {}  # id -> (data de atualização, percentual)
    for e in recorte["execucoes"]:
        chave = e["id_projeto_investimento"]
        quando = e.get("dt_atualizacao_execucao") or ""
        if chave and (chave not in execucao or quando >= execucao[chave][0]):
            execucao[chave] = (quando, e.get("percentual_execucao_fisica"))

    obras: dict[str, dict[str, Any]] = {}
    for p in recorte["projetos"]:
        chave = p["id_projeto_investimento"]
        if not chave or not p.get("desc_nome"):
            continue
        previstos = p.get("investimentos_previstos") or []
        total = sum(Decimal(str(i.get("vl_investimento_previsto") or 0)) for i in previstos)
        federal = sum(
            Decimal(str(i.get("vl_investimento_previsto") or 0))
            for i in previstos
            if (i.get("desc_nome_fonte_recurso") or "").lower() == "federal"
        )
        executores = p.get("executores") or []
        tipos = p.get("eixos_tipos") or []
        quando, percentual = execucao.get(chave, ("", None))
        obras[chave] = {
            "id_unico": chave,
            "nome": _texto(p["desc_nome"], 400),
            "situacao": _texto(p.get("situacao"), 40),
            "natureza": _texto(p.get("natureza_intervencao"), 60),
            "especie": _texto(p.get("especie_intervencao"), 60),
            "tipo": _texto(tipos[0].get("tipo"), 120) if tipos else None,
            "uf": (p.get("uf_principal") or "")[:2] or None,
            "data_inicial_prevista": _data(p.get("dt_inicial_prevista")),
            "data_final_prevista": _data(p.get("dt_final_prevista")),
            "data_inicial_efetiva": _data(p.get("dt_inicial_efetiva")),
            "data_final_efetiva": _data(p.get("dt_final_efetiva")),
            "data_cadastro": _data(p.get("dt_cadastro")),
            "valor_previsto": total if previstos else None,
            "valor_previsto_federal": federal if previstos else None,
            "responsavel": _texto(p.get("organizacao_resp"), 300),
            "executor": _texto(executores[0].get("organizacao_executor"), 300)
            if executores
            else None,
            "percentual_execucao": Decimal(str(percentual)) if percentual is not None else None,
            "execucao_atualizada_em": _data(quando),
        }

    ligacoes = {
        (g["id_projeto_investimento"], str(g["cod_ibge"]).zfill(7))
        for g in recorte["geometrias"]
        if g.get("cod_ibge") and g.get("id_projeto_investimento") in obras
    }
    municipios = [{"obra_id": o, "municipio_ibge": m} for o, m in sorted(ligacoes)]
    return list(obras.values()), municipios


def carregar(session: Session, payload: bytes, ingestao: FonteIngestao) -> int:
    recorte = json.loads(gzip.decompress(payload) if payload[:2] == b"\x1f\x8b" else payload)
    obras, municipios = normalizar(recorte)
    if not obras:
        raise ValueError("Nenhuma obra na API do Obrasgov; abortando.")
    sem_municipio = len(obras) - len({m["obra_id"] for m in municipios})
    print(f"  {len(obras)} obras; {len(municipios)} ligações a município; "
          f"{sem_municipio} sem município na geometria")  # fmt: skip
    session.execute(delete(ObraFederalMunicipio))
    session.execute(delete(ObraFederal))
    linhas = [{**o, "ingestao_id": ingestao.id} for o in obras]
    for inicio in range(0, len(linhas), LOTE):
        session.execute(insert(ObraFederal), linhas[inicio : inicio + LOTE])
    for inicio in range(0, len(municipios), LOTE):
        session.execute(insert(ObraFederalMunicipio), municipios[inicio : inicio + LOTE])
    return len(obras)


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
        incremental=comum.Incremental(chave=FONTE),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} obras federais")
