"""Assembleia Legislativa do Rio Grande do Sul (ALRS): deputados no cargo hoje, proposições
de autoria, votos em plenário, presença e verba de gabinete (cota parlamentar).

Não há arquivos em lote nem documentação, mas os sites da ALRS alimentam as próprias telas
por endereços abertos, que usamos como o navegador usa:

- Deputados: `ww4.al.rs.gov.br:5000/listarDestaqueDeputados` (JSON com nome, partido, e-mail,
  telefone e foto dos 55 em exercício).
- Proposições: `ww4.al.rs.gov.br/legislativo/pesquisa/dados?anoProposicao=AAAA` (JSON com
  todas as proposições do ano, ementa e data de protocolo; leva alguns minutos para responder).
  O proponente vem como "Deputado(a) Nome"; o que é do Executivo ou de outros fica de fora.
- Votos, presença e cota: o Portal da Transparência (`transparencia.al.rs.gov.br/parlamentares/...`)
  devolve, por deputado, uma página com os registros em `data-item` (JSON): um voto por
  linha (data, proposição, voto, resultado), a presença por mês e os gastos da cota por mês.

Uma requisição por vez, com pausa. Grava nas mesmas tabelas das outras casas, pela gravação
do conector SAPL. Os totais de uma votação (sim, não, abstenções) são contados entre os
deputados em exercício, que são os que a casa publica.
"""

import argparse
import html
import json
import re
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "alrs"
DEPUTADOS = "https://ww4.al.rs.gov.br:5000/listarDestaqueDeputados"
PROPOSICOES = "https://ww4.al.rs.gov.br/legislativo/pesquisa/dados"
SITE = "https://ww4.al.rs.gov.br/"
TRANSPARENCIA = "https://transparencia.al.rs.gov.br/parlamentares"
PAUSA = 0.4
LEITURA = httpx.Timeout(30.0, read=420.0)  # a pesquisa do ano inteiro leva alguns minutos
PROJETOS = {
    "PL": "Projeto de Lei",
    "PLC": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PDL": "Projeto de Decreto Legislativo",
    "PR": "Projeto de Resolução",
}
CONTAGEM = {
    "REQ": "Requerimento",
    "RC": "Requerimento Comum",
    "RDI": "Requerimentos Diversos",
    "RGE": "Requerimento de Grande Expediente Especial",
    "RCE": "Requerimento de Comissão Especial",
}
TITULO = re.compile(r"^Deputad[oa](?:\(a\))?\s+", re.I)
OUTROS = re.compile(
    r"\s*\+\s*\d+\s+Deputad.*$", re.I
)  # "Fulano + 3 Deputado(s)": os outros não vêm nomeados
DATA_ITEM = re.compile(r"data-item='(.*?)'>", re.S)
GASTO = re.compile(
    r'responsive-value\s+justify-content-center"[^>]*>([^<]+?):</span><br>\s*'
    r"<span[^>]*>\s*-?\s*R\$\s*([\d.]+,\d{2})</span>"
)


def _itens(pagina: str) -> list[dict[str, Any]]:
    """Os registros `data-item` (JSON escapado em HTML) de uma página da transparência."""
    return [json.loads(html.unescape(bruto)) for bruto in DATA_ITEM.findall(pagina)]


def deputados(lista: dict) -> list[dict[str, Any]]:
    return [
        {
            "id": str(d["idDeputado"]),
            "nome": " ".join(d["nomeDeputado"].split()),
            "partido": d.get("siglaPartido"),
            "email": d.get("emailDeputado"),
            "telefone": d.get("telefoneDeputado"),
            "foto": d.get("fotoGrandeDeputado"),
        }
        for d in lista.get("lista", [])
        if d.get("codStatus", 1) == 1
    ]


def _data(valor: str | None) -> str | None:
    try:
        return datetime.strptime((valor or "").strip()[:10], "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def distribuir(props: list[dict], nomes: set[str]) -> dict[str, dict]:
    """Nome do deputado -> contagem por tipo e projetos de autoria."""
    chave = {comum.chave_nome(n): n for n in nomes}
    por_deputado: dict[str, dict] = {n: {"contagem": {}, "projetos": []} for n in nomes}
    for p in props:
        proponente = p.get("nomeProponente") or ""
        if not TITULO.match(proponente):
            continue  # Poder Executivo, comissões, entidades
        nome = chave.get(comum.chave_nome(OUTROS.sub("", TITULO.sub("", proponente))))
        sigla = (p.get("siglaTipoProposicao") or "").strip()
        if nome is None or (sigla not in PROJETOS and sigla not in CONTAGEM):
            continue
        tipo = PROJETOS.get(sigla) or CONTAGEM[sigla]
        dep = por_deputado[nome]
        dep["contagem"][tipo] = dep["contagem"].get(tipo, 0) + 1
        if sigla in PROJETOS:
            numero, ano = p.get("nroProposicao"), p.get("anoProposicao")
            dep["projetos"].append(
                {
                    "id_externo": f"{sigla}-{numero}-{ano}"[:20],
                    "tipo": tipo,
                    "numero": int(numero) if str(numero).isdigit() else None,
                    "ano": int(ano),
                    "ementa": " ".join((p.get("ementa") or "").split()),
                    "data_apresentacao": _data(p.get("dthProtocolo")),
                    "em_tramitacao": None,
                    "primeiro_autor": True,
                    "url": f"{SITE}proposicao/{sigla}/{numero}/{ano}/{p['proposicaoId']}",
                }
            )
    return por_deputado


def votos_da_pagina(pagina: str) -> list[dict[str, Any]]:
    """Os votos de um deputado num ano: um por linha, com a proposição votada."""
    resultado = []
    for item in _itens(pagina):
        data = _data(item.get("dataVotacao"))
        sigla = (item.get("tipoProjeto") or "").strip()
        if not data or not sigla:
            continue
        resultado.append(
            {
                "chave": f"{data[2:4]}{data[5:7]}{data[8:10]}{sigla}{item['numProposicao']}"
                f"/{item['anoProposicao']}"[:20],
                "data": data,
                "materia": f"{sigla} {item['numProposicao']}/{item['anoProposicao']}: "
                f"{' '.join((item.get('materia') or '').split())}",
                "resultado": (item.get("resultadoVotacao") or "").strip() or None,
                "voto": (item.get("voto") or "").strip(),
            }
        )
    return resultado


def votacoes(por_deputado: dict[str, list[dict]]) -> tuple[list[dict], list[dict]]:
    """Reúne os votos dos deputados em votações, contando sim, não e abstenções."""
    votacoes: dict[str, dict] = {}
    votos: dict[tuple[str, str], str] = {}
    for deputado, lista in por_deputado.items():
        for v in lista:
            if not v["voto"] or (v["chave"], deputado) in votos:
                continue  # voto repetido na mesma votação (destaques): vale o primeiro
            votos[(v["chave"], deputado)] = v["voto"]
            vot = votacoes.setdefault(
                v["chave"],
                {
                    "id_externo": v["chave"],
                    "materia": v["materia"],
                    "resultado": v["resultado"],
                    "data": v["data"],
                    "sim": 0,
                    "nao": 0,
                    "abstencoes": 0,
                },
            )
            campo = comum.chave_nome(v["voto"])
            if campo == "SIM":
                vot["sim"] += 1
            elif campo == "NAO":
                vot["nao"] += 1
            else:
                vot["abstencoes"] += 1
    return list(votacoes.values()), [
        {"votacao": chave, "parlamentar": deputado, "voto": voto}
        for (chave, deputado), voto in votos.items()
    ]


def presenca_da_pagina(pagina: str) -> tuple[int, int]:
    """(sessões, presenças) somando os meses: sessões = presenças + faltas (justificadas ou
    não). Licenças não contam, porque o deputado não era esperado em plenário."""
    sessoes = presencas = 0
    for mes in _itens(pagina):
        p = int(mes.get("presenca") or 0)
        presencas += p
        sessoes += (
            p + int(mes.get("faltaJustificada") or 0) + int(mes.get("faltaNaoJustificada") or 0)
        )
    return sessoes, presencas


def gastos_da_pagina(pagina: str, ano: int, mes: int) -> list[dict]:
    """Despesas do mês por categoria (a página mostra o total à parte, que não entra)."""
    resultado = []
    for categoria, valor in GASTO.findall(pagina):
        nome = " ".join(html.unescape(categoria).split())
        if nome.lower() == "total":
            continue
        resultado.append(
            {
                "ano": ano,
                "mes": mes,
                "categoria": nome[:200],
                "valor": Decimal(valor.replace(".", "").replace(",", ".")),
            }
        )
    return resultado


def _pagina(client: httpx.Client, url: str, params: dict) -> str:
    time.sleep(PAUSA)
    return comum._get(client, url, params, 4).content.decode("utf-8", errors="replace")


def coletar(hoje: date) -> dict:
    anos = (hoje.year - 1, hoje.year)
    with comum.criar_cliente() as client:
        lista = deputados(comum.get_json(client, DEPUTADOS))
        props: list[dict] = []
        for ano in anos:
            resposta = client.get(PROPOSICOES, params={"anoProposicao": ano}, timeout=LEITURA)
            props += resposta.raise_for_status().json().get("lista", [])
        autoria = distribuir(props, {d["nome"] for d in lista})
        votos: dict[str, list[dict]] = {}
        for d in lista:
            votos[d["id"]] = []
            d["sessoes"] = d["presencas"] = 0
            d["gastos"] = []
            for ano in anos:
                filtro = {"solicitante": d["id"], "ano": ano}
                votos[d["id"]] += votos_da_pagina(
                    _pagina(client, f"{TRANSPARENCIA}/votos-plenario/pesquisa", filtro)
                )
                sessoes, presencas = presenca_da_pagina(
                    _pagina(client, f"{TRANSPARENCIA}/presencas-plenario/pesquisa", filtro)
                )
                d["sessoes"] += sessoes
                d["presencas"] += presencas
                for mes in range(1, (hoje.month if ano == hoje.year else 12) + 1):
                    d["gastos"] += gastos_da_pagina(
                        _pagina(client, f"{TRANSPARENCIA}/gastos/pesquisa", {**filtro, "mes": mes}),
                        ano,
                        mes,
                    )
            print(
                f"  {d['nome']}: {len(votos[d['id']])} votos, {len(d['gastos'])} gastos", flush=True
            )
    votacoes_, votos_ = votacoes(votos)
    vereadores = [
        {
            "id_externo": d["id"],
            "nome": d["nome"],
            "nome_completo": None,
            "partido": d["partido"],
            "foto_url": d["foto"],
            "email": d["email"],
            "telefone": d["telefone"],
            "titular": True,
            "em_exercicio": True,
            "inicio": None,
            "fim": None,
            "proposicoes_por_tipo": autoria[d["nome"]]["contagem"],
            "projetos": autoria[d["nome"]]["projetos"],
            "sessoes": d["sessoes"] or None,
            "presencas": d["presencas"] if d["sessoes"] else None,
            "gastos": d["gastos"],
        }
        for d in lista
    ]
    return {
        "base": SITE,
        "legislatura": None,
        "vereadores": vereadores,
        "votacoes": votacoes_,
        "votos": votos_,
    }


def executar() -> int:
    casa = coletar(date.today())
    if len(casa["vereadores"]) < 45:  # a ALRS tem 55 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALRS; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="RS")
        session.add(
            FonteIngestao(fonte=FONTE, url=SITE, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(
        f"ALRS: {total} deputados, {len(casa['votacoes'])} votações, {len(casa['votos'])} votos",
        flush=True,
    )
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
