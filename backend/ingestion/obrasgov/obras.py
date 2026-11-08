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


def _compacto(item: dict[str, Any], campos: tuple[str, ...]) -> list[Any]:
    """Só os valores usados, em lista (sem os nomes dos campos em cada linha): com dicionários,
    a carga passava de 1,4 GB de memória e caía na VPS (4 GB). Listas aninhadas viram o mínimo:
    executor e tipo, o primeiro; investimentos, [valor, fonte]."""
    linha = []
    for k in campos:
        v = item.get(k)
        if k == "executores":
            v = (v or [{}])[0].get("organizacao_executor") if v else None
        elif k == "eixos_tipos":
            v = (v or [{}])[0].get("tipo") if v else None
        elif k == "investimentos_previstos":
            v = [
                [i.get("vl_investimento_previsto"), i.get("desc_nome_fonte_recurso")]
                for i in v or []
            ]
        linha.append(v)
    return linha


def paginas(client: httpx.Client, recurso: str, campos: tuple[str, ...]):
    """Todas as linhas do recurso, página a página (1, 2, ... até `total_pages`), compactas."""
    linhas: list[list[Any]] = []
    pagina, total = 1, 1
    while pagina <= total:
        corpo = comum.get_json(
            client, f"{BASE}/{recurso}", {"pagina": pagina, "tamanho_da_pagina": PAGINA}
        )
        total = int(corpo.get("total_pages") or 0)
        for item in corpo.get("data") or []:
            linhas.append(_compacto(item, campos))
        pagina += 1
        time.sleep(PAUSA)
    return linhas


def baixar_tudo(client: httpx.Client) -> dict[str, list[dict[str, Any]]]:
    projetos = paginas(client, "projeto-investimento", CAMPOS_PROJETO)
    geometrias = paginas(client, "geometria", CAMPOS_GEOMETRIA)
    execucoes = paginas(client, "execucao-fisica", CAMPOS_EXECUCAO)
    return {
        "formato": 2,
        "colunas": {
            "projetos": CAMPOS_PROJETO,
            "geometrias": CAMPOS_GEOMETRIA,
            "execucoes": CAMPOS_EXECUCAO,
        },
        "projetos": projetos,
        "geometrias": geometrias,
        "execucoes": execucoes,
    }


CAMPOS_GEOMETRIA = ("id_projeto_investimento", "cod_ibge")
CAMPOS_EXECUCAO = (
    "id_projeto_investimento",
    "percentual_execucao_fisica",
    "dt_atualizacao_execucao",
)
GZIP = bytes([0x1F, 0x8B])  # assinatura do gzip: o bruto pode vir comprimido ou não


def _linhas(recorte: dict[str, Any], parte: str):
    """Linhas como dicionário, uma de cada vez: aceita o formato compacto (2) e o antigo."""
    colunas = (recorte.get("colunas") or {}).get(parte)
    for linha in recorte[parte]:
        if colunas is None:  # formato antigo (bruto de 08/11/2026): já vem em dicionário
            yield _antigo(linha) if parte == "projetos" else linha
        else:
            yield dict(zip(colunas, linha, strict=True))


def _antigo(p: dict[str, Any]) -> dict[str, Any]:
    """Projeto do bruto antigo, com as listas aninhadas, na forma do compacto."""
    return {**p, **dict(zip(CAMPOS_PROJETO, _compacto(p, CAMPOS_PROJETO), strict=True))}


def _data(valor: str | None) -> date | None:
    try:
        return date.fromisoformat(valor[:10]) if valor else None
    except ValueError:
        return None


def _texto(valor: Any, limite: int) -> str | None:
    texto = " ".join(str(valor or "").split())
    return texto[:limite] or None


def _obras(recorte: dict[str, Any]):
    """Cada obra, uma de cada vez (para não montar 155 mil dicionários na memória). Obra
    repetida entre páginas sai uma vez só."""
    execucao: dict[str, tuple[str, Any]] = {}  # id -> (data de atualização, percentual)
    for e in _linhas(recorte, "execucoes"):
        chave = e["id_projeto_investimento"]
        quando = e.get("dt_atualizacao_execucao") or ""
        if chave and (chave not in execucao or quando >= execucao[chave][0]):
            execucao[chave] = (quando, e.get("percentual_execucao_fisica"))

    vistas: set[str] = set()
    for p in _linhas(recorte, "projetos"):
        chave = p["id_projeto_investimento"]
        if not chave or not p.get("desc_nome") or chave in vistas:
            continue
        vistas.add(chave)
        previstos = p.get("investimentos_previstos") or []
        total = sum(Decimal(str(v or 0)) for v, _fonte in previstos)
        federal = sum(
            Decimal(str(v or 0)) for v, fonte in previstos if (fonte or "").lower() == "federal"
        )
        quando, percentual = execucao.get(chave, ("", None))
        yield {
            "id_unico": chave,
            "nome": _texto(p["desc_nome"], 400),
            "situacao": _texto(p.get("situacao"), 40),
            "natureza": _texto(p.get("natureza_intervencao"), 60),
            "especie": _texto(p.get("especie_intervencao"), 60),
            "tipo": _texto(p.get("eixos_tipos"), 120),
            "uf": (p.get("uf_principal") or "")[:2] or None,
            "data_inicial_prevista": _data(p.get("dt_inicial_prevista")),
            "data_final_prevista": _data(p.get("dt_final_prevista")),
            "data_inicial_efetiva": _data(p.get("dt_inicial_efetiva")),
            "data_final_efetiva": _data(p.get("dt_final_efetiva")),
            "data_cadastro": _data(p.get("dt_cadastro")),
            "valor_previsto": total if previstos else None,
            "valor_previsto_federal": federal if previstos else None,
            "responsavel": _texto(p.get("organizacao_resp"), 300),
            "executor": _texto(p.get("executores"), 300),
            "percentual_execucao": Decimal(str(percentual)) if percentual is not None else None,
            "execucao_atualizada_em": _data(quando),
        }


def _municipios(recorte: dict[str, Any], ids: set[str]) -> list[dict[str, str]]:
    ligacoes = {
        (g["id_projeto_investimento"], str(g["cod_ibge"]).zfill(7))
        for g in _linhas(recorte, "geometrias")
        if g.get("cod_ibge") and g.get("id_projeto_investimento") in ids
    }
    return [{"obra_id": o, "municipio_ibge": m} for o, m in sorted(ligacoes)]


def normalizar(recorte: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Bruto -> (obras, ligações obra-município), inteiros (testes e conferência)."""
    obras = list(_obras(recorte))
    return obras, _municipios(recorte, {o["id_unico"] for o in obras})


def carregar(session: Session, payload: bytes, ingestao: FonteIngestao) -> int:
    recorte = json.loads(gzip.decompress(payload) if payload[:2] == GZIP else payload)
    del payload
    session.execute(delete(ObraFederalMunicipio))
    session.execute(delete(ObraFederal))
    ids: set[str] = set()
    lote: list[dict[str, Any]] = []
    for obra in _obras(recorte):
        ids.add(obra["id_unico"])
        lote.append({**obra, "ingestao_id": ingestao.id})
        if len(lote) == LOTE:
            session.execute(insert(ObraFederal), lote)
            lote = []
    if lote:
        session.execute(insert(ObraFederal), lote)
    if not ids:
        raise ValueError("Nenhuma obra na API do Obrasgov; abortando.")
    municipios = _municipios(recorte, ids)
    for inicio in range(0, len(municipios), LOTE):
        session.execute(insert(ObraFederalMunicipio), municipios[inicio : inicio + LOTE])
    sem_municipio = len(ids) - len({m["obra_id"] for m in municipios})
    print(f"  {len(ids)} obras; {len(municipios)} ligações a município; "
          f"{sem_municipio} sem município na geometria")  # fmt: skip
    return len(ids)


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
