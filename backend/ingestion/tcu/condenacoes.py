"""Condenações do TCU a pessoas físicas, só das pessoas que já temos, gravadas como
eventos da linha do tempo:

- contas julgadas irregulares (lista pública de responsáveis, a mesma das certidões);
- inabilitados para cargo em comissão ou função de confiança na administração federal.

As duas listas trazem CPF completo, e a ligação é só por CPF. Os licitantes inidôneos
são todos empresas e ficam de fora por enquanto (coleta mínima). Rode depois de
ingestion.pessoas.
"""

import argparse
import json
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import Evento, FonteIngestao, Pessoa, PessoaVinculo
from ingestion import comum

FONTE = "tcu_condenacoes"
URL_IRREGULARES = (
    "https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-contas-irregulares-com-paginacao"
)
URL_INABILITADOS = "https://contas.tcu.gov.br/ords/condenacao/consulta/inabilitados"
URL_PAGINA = "https://contasirregulares.tcu.gov.br/"
URL_LISTA_INABILITADOS = (
    "https://portal.tcu.gov.br/carta-de-servicos/certidoes/lista-de-inabilitados"
)
POR_PAGINA = 1000
PAUSA = 0.5
COLEGIADOS = {"PL": "Plenário", "1C": "1ª Câmara", "2C": "2ª Câmara"}


def _cpf(valor: str | None) -> str | None:
    digitos = re.sub(r"\D", "", valor or "")
    return digitos if len(digitos) == 11 else None


def _data_br(valor: str | None) -> date | None:
    try:
        return datetime.strptime((valor or "").strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _data_iso(valor: str | None) -> date | None:
    return date.fromisoformat(valor[:10]) if valor else None


def acordao(numero: str | None) -> str | None:
    """'4206/2023-2C' ou 'AC-000738/2022-PL' -> 'Acórdão 4206/2023 – 2ª Câmara'."""
    achado = re.search(r"(\d+)/(\d{4})-(\w+)", numero or "")
    if not achado:
        return (numero or "").strip() or None
    colegiado = COLEGIADOS.get(achado.group(3), achado.group(3))
    return f"Acórdão {int(achado.group(1))}/{achado.group(2)} – {colegiado}"


def normalizar_irregulares(paginas: list[dict]) -> list[dict[str, Any]]:
    registros = []
    for pagina in paginas:
        for e in pagina.get("elementos", []):
            cpf = _cpf(e.get("numeroRegistro")) if e.get("tipoRegistro") == "CPF" else None
            if not cpf:
                continue
            registros.append(
                {
                    "lista": "irregulares",
                    "cpf": cpf,
                    "processo": (e.get("numeroProcessoFormatado") or "").strip(),
                    "acordao": acordao(e.get("numeroAcordaoFormatado")),
                    "transito": _data_br(e.get("dataTransitoEmJulgado")),
                    "fim": None,
                    "url": e.get("linkDeliberacoesProcesso") or URL_PAGINA,
                }
            )
    return registros


def normalizar_inabilitados(itens: list[dict]) -> list[dict[str, Any]]:
    registros = []
    for item in itens:
        cpf = _cpf(item.get("cpf"))
        if not cpf:
            continue
        registros.append(
            {
                "lista": "inabilitados",
                "cpf": cpf,
                "processo": (item.get("processo") or "").strip(),
                "acordao": acordao(item.get("deliberacao")),
                "transito": _data_iso(item.get("data_transito_julgado")),
                "fim": _data_iso(item.get("data_final")),
                "url": URL_LISTA_INABILITADOS,
            }
        )
    return registros


def descricao(r: dict[str, Any]) -> str:
    acordao_texto = f", {r['acordao']}" if r["acordao"] else ""
    transito = f", com trânsito em julgado em {r['transito']:%d/%m/%Y}" if r["transito"] else ""
    if r["lista"] == "irregulares":
        return (
            f"O TCU julgou irregulares contas sob responsabilidade desta pessoa "
            f"(processo TC {r['processo']}{acordao_texto}){transito}."
        )
    return (
        f"O TCU declarou a inabilitação para cargo em comissão ou função de confiança na "
        f"administração pública federal (processo TC {r['processo']}{acordao_texto}){transito}."
    )


def situacao(r: dict[str, Any], hoje: date) -> str | None:
    if r["lista"] == "irregulares":
        return f"na lista do TCU em {hoje:%d/%m/%Y}"
    if r["fim"] is None:
        return None
    if r["fim"] < hoje:
        return f"encerrada em {r['fim']:%d/%m/%Y}"
    return f"inabilitação até {r['fim']:%d/%m/%Y}"


def gravar(
    session: Session, registros: list[dict[str, Any]], ingestao_id: int | None, hoje: date
) -> int:
    """Substitui os vínculos e eventos desta fonte. Só por CPF igual ao de uma pessoa."""
    por_cpf = dict(
        session.execute(select(Pessoa.cpf, Pessoa.id).where(Pessoa.cpf.is_not(None))).all()
    )
    session.execute(delete(PessoaVinculo).where(PessoaVinculo.fonte == FONTE))
    vistos: set[str] = set()
    for r in registros:
        pessoa_id = por_cpf.get(r["cpf"])
        id_externo = f"{r['lista']}:{r['processo']}:{r['cpf']}"
        if pessoa_id is None or id_externo in vistos:
            continue
        vistos.add(id_externo)
        vinculo_id = session.scalar(
            insert(PessoaVinculo)
            .values(pessoa_id=pessoa_id, fonte=FONTE, id_externo=id_externo, regra="cpf")
            .returning(PessoaVinculo.id)
        )
        session.execute(
            insert(Evento).values(
                pessoa_id=pessoa_id,
                vinculo_id=vinculo_id,
                data=r["transito"],
                tipo="tcu_contas_irregulares"
                if r["lista"] == "irregulares"
                else "tcu_inabilitacao",
                descricao=descricao(r),
                orgao="Tribunal de Contas da União",
                numero_processo=f"TC {r['processo']}"[:40],
                situacao=situacao(r, hoje),
                fonte=FONTE,
                id_externo=id_externo,
                fonte_url=r["url"],
                ingestao_id=ingestao_id,
            )
        )
    return len(vistos)


def baixar(client: httpx.Client) -> bytes:
    """As duas listas inteiras, uma página por vez, num JSON (gravado comprimido)."""
    irregulares, pagina = [], 1
    while True:
        time.sleep(PAUSA)
        resposta = client.post(
            URL_IRREGULARES,
            params={"paginaAtual": pagina, "tamanhoPagina": POR_PAGINA},
            json={},
        )
        dados = resposta.raise_for_status().json()
        irregulares.append(dados)
        if pagina >= dados.get("totalPaginas", 0):
            break
        pagina += 1
    inabilitados, deslocamento = [], 0
    while True:
        time.sleep(PAUSA)
        dados = comum.get_json(
            client, URL_INABILITADOS, params={"limit": 500, "offset": deslocamento}
        )
        inabilitados += dados.get("items", [])
        if not dados.get("hasMore"):
            break
        deslocamento += 500
    dados = {"irregulares": irregulares, "inabilitados": inabilitados}
    return json.dumps(dados, ensure_ascii=False).encode("utf-8")


def executar(de_raw: Path | None = None) -> int:
    hoje = date.today()

    def carregar(session: Session, bruto: bytes, ingestao: FonteIngestao) -> int:
        payload = json.loads(bruto)
        registros = normalizar_irregulares(payload["irregulares"]) + normalizar_inabilitados(
            payload["inabilitados"]
        )
        total_lista = (
            payload["irregulares"][0].get("totalElementos") if payload["irregulares"] else 0
        )
        lidos = sum(len(p.get("elementos", [])) for p in payload["irregulares"])
        if not registros or lidos != total_lista:
            raise RuntimeError(
                f"Lista do TCU incompleta ({lidos} de {total_lista} registros): nada alterado."
            )
        total = gravar(session, registros, ingestao.id, hoje)
        print(f"  {len(registros)} condenações a pessoas físicas; {total} de pessoas que temos")
        return total

    return comum.executar_ingestao(
        FONTE, URL_PAGINA, baixar, carregar, de_raw=de_raw, extensao_raw=".json.gz"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} condenações ligadas")
