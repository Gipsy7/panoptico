"""Assembleia Legislativa de Pernambuco (ALEPE): deputados no cargo hoje e as proposições
de cada um (projetos com ementa; indicações e requerimentos só como contagem), pela API de
dados abertos da ALEPE.

Grava nas mesmas tabelas das outras casas, pela gravação do conector SAPL. A API não tem
votos, presença nem gastos do gabinete (ver docs/FONTES_DE_DADOS.md); os deputados vêm só
com nome parlamentar e partido, e o autor das proposições vem pelo mesmo nome.
"""

import argparse
import html
import re
from datetime import UTC, date, datetime
from typing import Any
from xml.etree import ElementTree

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "alepe"
API = "https://dadosabertos.alepe.pe.gov.br/api/v1/"
SITE = "https://www.alepe.pe.gov.br/"
URL_PROPOSICAO = SITE + "proposicao-texto-completo/?docid={docid}"
# Rotas de proposições: as de projetos guardam a ementa; as outras viram só contagem.
TIPOS = {"projetos": "projeto", "indicacoes": "indicacao", "requerimentos": "requerimento"}
CONTAGEM = {"indicacoes": "Indicação", "requerimentos": "Requerimento"}


def _texto(valor: str | None) -> str:
    """A ementa das indicações e requerimentos vem em HTML escapado."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(valor or ""))).split())


def _tipo(valor: str | None) -> str:
    """'PROJETO DE LEI ORDINÁRIA' -> 'Projeto de Lei Ordinária'."""
    texto = comum.nome_proprio((valor or "").strip()) or "Projeto"
    # Artigo e conjunção soltos ficam minúsculos: "Proposta de Emenda a Constituição".
    return re.sub(r"(?<= )(A|À|E)(?= )", lambda m: m.group(1).lower(), texto)


def proposicoes(xml: bytes, rota: str) -> list[dict[str, Any]]:
    """Cada proposição com os autores deputados, na ordem (o primeiro é o principal)."""
    raiz = ElementTree.fromstring(xml)
    resultado = []
    for p in raiz.iter(TIPOS[rota]):
        autores = [
            a.get("nome", "").strip() for a in p.iter("autor") if a.get("tipo") == "DEPUTADO"
        ]
        if not autores:
            continue
        resultado.append({"rota": rota, "docid": p.get("docid"), "numero": p.get("numero"),
                          "ano": p.get("ano"), "tipo": p.get("tipo"), "ementa": p.get("ementa"),
                          "data": p.get("dataPublicacao"), "autores": autores})  # fmt: skip
    return resultado


def _data(valor: str | None) -> str | None:
    try:
        return datetime.strptime((valor or "").strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def distribuir(props: list[dict], nomes: set[str]) -> dict[str, dict]:
    """Nome parlamentar -> contagem por tipo e projetos."""
    chave = {comum.chave_nome(n): n for n in nomes}
    por_deputado: dict[str, dict] = {n: {"contagem": {}, "projetos": []} for n in nomes}
    for p in props:
        for ordem, autor in enumerate(p["autores"]):
            nome = chave.get(comum.chave_nome(autor))
            if nome is None:
                continue
            dep = por_deputado[nome]
            tipo = CONTAGEM.get(p["rota"]) or _tipo(p["tipo"])
            dep["contagem"][tipo] = dep["contagem"].get(tipo, 0) + 1
            if p["rota"] == "projetos":
                dep["projetos"].append(
                    {
                        "id_externo": p["docid"],
                        "tipo": tipo,
                        "numero": int(p["numero"]) if (p["numero"] or "").isdigit() else None,
                        "ano": int(p["ano"]),
                        "ementa": _texto(p["ementa"]),
                        "data_apresentacao": _data(p["data"]),
                        "em_tramitacao": None,
                        "primeiro_autor": ordem == 0,
                        "url": URL_PROPOSICAO.format(docid=p["docid"]),
                    }
                )
    return por_deputado


def coletar(hoje: date) -> dict:
    with comum.criar_cliente() as client:
        lista = comum.get_json(client, API + "parlamentares/")
        props = []
        for ano in (hoje.year - 1, hoje.year):
            for rota in TIPOS:
                xml = comum.get_bytes(client, f"{API}proposicoes/{rota}/?ano={ano}")
                props += proposicoes(xml, rota)
    nomes = {d["nomeParlamentar"].strip() for d in lista}
    autoria = distribuir(props, nomes)
    vereadores = [
        {
            "id_externo": comum.chave_nome(d["nomeParlamentar"])[:20],
            "nome": d["nomeParlamentar"].strip(),
            "nome_completo": None,
            "partido": d.get("partido") or None,
            "foto_url": None,  # a foto vem do TSE, pela ligação ao eleito
            "email": None,
            "telefone": None,
            "titular": True,  # a API não diz se é suplente
            "em_exercicio": True,
            "inicio": None,
            "fim": None,
            "proposicoes_por_tipo": autoria[d["nomeParlamentar"].strip()]["contagem"],
            "projetos": autoria[d["nomeParlamentar"].strip()]["projetos"],
            "sessoes": None,
            "presencas": None,
        }
        for d in lista
    ]
    return {
        "base": SITE,
        "legislatura": None,
        "vereadores": vereadores,
        "votacoes": [],
        "votos": [],
    }


def executar() -> int:
    casa = coletar(date.today())
    if len(casa["vereadores"]) < 40:  # a ALEPE tem 49 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALEPE; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="PE")
        session.add(
            FonteIngestao(fonte=FONTE, url=API, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(f"ALEPE: {total} deputados", flush=True)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
