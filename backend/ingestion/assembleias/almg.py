"""Assembleia Legislativa de Minas Gerais (ALMG): deputados no cargo hoje, projetos,
requerimentos e gastos do gabinete (verba indenizatória), pela API de dados abertos.

A ALMG não usa o SAPL, mas os dados vão para as mesmas tabelas das outras casas
(`mandato_local` com casa "assembleia", `projeto_local`, `gasto_local`), pela mesma
gravação do conector SAPL. O que a API não traz: o voto de cada deputado e a lista de
presença (as reuniões de Plenário só têm o resultado de cada matéria).

Armadilhas da API (ver docs/FONTES_DE_DADOS.md):
- a pesquisa de proposições devolve no máximo 100 por página (`tp`), em `resultado`;
- a autoria vem como texto ("Deputado Fulano   PT\\nDeputada Beltrana   PV") e como
  `matricula` ("12552\\n26105"), na mesma ordem; o primeiro é o autor principal, e a
  matrícula é o id do deputado na API;
- proposições de outros autores (Governador, Tribunal de Justiça) vêm sem matrícula;
- os gastos têm um índice dos meses fechados (`/datas`), para não pedir meses vazios.
"""

import argparse
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "almg"
API = "https://dadosabertos.almg.gov.br/api/v2/"
SITE = "https://www.almg.gov.br/"
PAUSA = 0.3
# Projetos guardados com a ementa; os demais tipos viram só contagem.
PROJETOS = {
    "PL": "Projeto de Lei",
    "PLC": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PRE": "Projeto de Resolução",
}
CONTAGEM = {"RQN": "Requerimento", "IND": "Indicação"}


def _get(client: httpx.Client, caminho: str, **params: Any) -> Any:
    time.sleep(PAUSA)
    return comum.get_json(client, API + caminho, params={**params, "formato": "json"})


def _data(valor: Any) -> str | None:
    """Datas vêm como "2025-02-03" ou {"@class": "sql-timestamp", "$": "2025-02-03"}."""
    if isinstance(valor, dict):
        valor = valor.get("$")
    return str(valor)[:10] if valor else None


def proposicoes(client: httpx.Client, tipo: str, ano: int) -> list[dict]:
    itens, pagina = [], 1
    while True:
        dados = _get(
            client, "proposicoes/pesquisa/direcionada", tipo=tipo, ano=ano, tp=100, p=pagina
        )
        resultado = dados.get("resultado", {})
        itens += resultado.get("listaItem", [])
        if pagina * 100 >= int(resultado.get("noOcorrencias") or 0):
            return itens
        pagina += 1


def autores(item: dict) -> list[str]:
    """Matrículas dos autores, na ordem (o primeiro é o autor principal)."""
    return [m.strip() for m in (item.get("matricula") or "").split("\n") if m.strip()]


def distribuir(itens_por_tipo: dict[str, list[dict]], ids: set[str]) -> dict[str, dict]:
    """Para cada deputado: contagem por tipo e os projetos (com ementa)."""
    por_deputado: dict[str, dict] = {i: {"contagem": {}, "projetos": []} for i in ids}
    for sigla, itens in itens_por_tipo.items():
        nome_tipo = PROJETOS.get(sigla) or CONTAGEM[sigla]
        for item in itens:
            for ordem, matricula in enumerate(autores(item)):
                if matricula not in por_deputado:
                    continue
                dep = por_deputado[matricula]
                dep["contagem"][nome_tipo] = dep["contagem"].get(nome_tipo, 0) + 1
                if sigla in PROJETOS:
                    numero, ano = item.get("numero"), item.get("ano")
                    dep["projetos"].append(
                        {
                            "id_externo": f"{sigla}-{numero}-{ano}",
                            "tipo": nome_tipo,
                            "numero": int(numero) if numero else None,
                            "ano": int(ano),
                            "ementa": " ".join((item.get("ementa") or "").split()),
                            "data_apresentacao": _data(item.get("dataPublicacao")),
                            "em_tramitacao": None,
                            "primeiro_autor": ordem == 0,
                            "url": f"{SITE}projetos-de-lei/{sigla}/{numero}/{ano}",
                        }
                    )
    return por_deputado


def gastos(client: httpx.Client, deputado: int, anos: set[int]) -> list[dict]:
    meses = [
        _data(m.get("dataReferencia"))
        for m in _get(
            client, f"prestacao_contas/verbas_indenizatorias/deputados/{deputado}/datas"
        ).get("listaFechamentoVerba", [])
    ]
    resultado = []
    for referencia in meses:
        if not referencia or int(referencia[:4]) not in anos:
            continue
        ano, mes = int(referencia[:4]), int(referencia[5:7])
        dados = _get(
            client, f"prestacao_contas/verbas_indenizatorias/deputados/{deputado}/{ano}/{mes}"
        )
        for item in dados.get("list", []):
            resultado.append(
                {
                    "ano": ano,
                    "mes": mes,
                    "categoria": (item.get("descTipoDespesa") or "Outros").strip()[:200],
                    "valor": Decimal(str(item.get("valor") or 0)),
                }
            )
    return resultado


def coletar(hoje: date) -> dict:
    anos = {hoje.year, hoje.year - 1}
    with comum.criar_cliente() as client:
        lista = _get(client, "deputados/em_exercicio").get("list", [])
        ids = {str(d["id"]) for d in lista}
        itens = {
            sigla: [i for ano in sorted(anos) for i in proposicoes(client, sigla, ano)]
            for sigla in [*PROJETOS, *CONTAGEM]
        }
        autoria = distribuir(itens, ids)
        deputados = []
        for resumo in lista:
            detalhe = _get(client, f"deputados/{resumo['id']}").get("deputado", {})
            emails = [e.get("endereco") for e in detalhe.get("emails", []) if e.get("endereco")]
            deputados.append(
                {
                    "id_externo": str(resumo["id"]),
                    "nome": resumo["nome"].strip(),
                    "nome_completo": (detalhe.get("nomeServidor") or "").title() or None,
                    "partido": resumo.get("partido"),
                    "foto_url": None,  # a foto vem do TSE, pela ligação ao eleito
                    "email": f"{emails[0]}@almg.gov.br"
                    if emails and "@" not in emails[0]
                    else (emails[0] if emails else None),
                    "telefone": None,
                    "titular": (detalhe.get("tipoMandato") or "Efetivo") == "Efetivo",
                    "em_exercicio": True,
                    "inicio": _data(detalhe.get("inicioSituacao")),
                    "fim": None,
                    "proposicoes_por_tipo": autoria[str(resumo["id"])]["contagem"],
                    "projetos": autoria[str(resumo["id"])]["projetos"],
                    "sessoes": None,
                    "presencas": None,
                    "gastos": gastos(client, resumo["id"], anos),
                }
            )
    return {"base": SITE, "legislatura": None, "vereadores": deputados, "votacoes": [], "votos": []}


def executar() -> int:
    casa = coletar(date.today())
    if len(casa["vereadores"]) < 50:  # a ALMG tem 77 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALMG; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="MG")
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url=API,
                arquivo_raw="(não guardado)",
                registros=total,
                status="ok",
                concluido_em=datetime.now(UTC),
            )
        )
        session.commit()
    print(f"ALMG: {total} deputados", flush=True)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
