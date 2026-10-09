"""Câmara Legislativa do Distrito Federal (CLDF): deputados distritais no cargo hoje e as
proposições de cada um, pela API pública do Processo Legislativo Eletrônico (PLE), sem
autenticação e documentada no catálogo de dados abertos da CLDF.

Grava nas mesmas tabelas das assembleias, com UF "DF", pela gravação do conector SAPL.
- Deputados: autores do tipo PARLAMENTAR com situação ATIVO (24, todas as cadeiras), com
  o nome como o PLE escreve ("Deputado Fábio Felix"); o partido não vem preenchido (o perfil
  mostra o do eleito no TSE).
- Proposições do ano atual e do anterior; a autoria vem em texto ("Deputado X, Deputada
  Y"). Projetos guardam a ementa; indicações, moções e requerimentos viram contagem.
- Votos e presença não estão na API. As verbas indenizatórias (XLSX no catálogo) ficam para
  depois.
"""

import argparse
import calendar
import re
import time
from datetime import UTC, date, datetime
from typing import Any

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "cldf"
API = "https://ple.cl.df.gov.br/pleservico/api/public"
SITE = "https://ple.cl.df.gov.br/#/proposicao/buscar"
POR_PAGINA = 100
PAUSA = 0.3
TITULO = re.compile(r"^Deputad[oa]\s+", re.I)
PROJETO = re.compile(r"^(projeto|proposta de emenda)", re.I)


def nome_sem_titulo(nome: str | None) -> str:
    """'Deputado Fábio Felix ' -> 'Fábio Felix'."""
    return TITULO.sub("", (nome or "").strip()).strip()


def autores_de(autoria: str | None) -> list[str]:
    """'Deputado Martins Machado, Deputada Paula Belmonte' -> nomes sem título, sem repetir."""
    nomes = []
    for parte in (autoria or "").split(","):
        nome = nome_sem_titulo(parte)
        if nome and nome not in nomes:
            nomes.append(nome)
    return nomes


def _numero(sigla_numero_ano: str | None) -> int | None:
    """'REQ 3090/2026' -> 3090."""
    achado = re.search(r"(\d+)/\d{4}", sigla_numero_ano or "")
    return int(achado.group(1)) if achado else None


def distribuir(props: list[dict], nomes: set[str]) -> dict[str, dict]:
    chave = {comum.chave_nome(n): n for n in nomes}
    por_deputado: dict[str, dict] = {n: {"contagem": {}, "projetos": []} for n in nomes}
    for p in props:
        tipo = (p.get("tipoProposicao") or "").strip() or "Proposição"
        for ordem, autor in enumerate(autores_de(p.get("autoria"))):
            nome = chave.get(comum.chave_nome(autor))
            if nome is None:
                continue
            dep = por_deputado[nome]
            dep["contagem"][tipo] = dep["contagem"].get(tipo, 0) + 1
            if PROJETO.match(tipo):
                dep["projetos"].append(
                    {
                        "id_externo": str(p["id"]),
                        "tipo": tipo,
                        "numero": _numero(p.get("siglaNumeroAno")),
                        "ano": int(p["dataLeitura"][:4]) if p.get("dataLeitura") else None,
                        "ementa": " ".join((p.get("ementa") or "").split()),
                        "data_apresentacao": p.get("dataLeitura"),
                        "em_tramitacao": None,
                        "primeiro_autor": ordem == 0,
                        "url": f"{API}/proposicao/{p['id']}",
                    }
                )
    return por_deputado


def proposicoes(client: Any, ano: int, ate: date) -> list[dict]:
    """As proposições lidas no ano, mês a mês (consultas pequenas), parando pelo total de
    páginas que a API informa (o indicador de última página não é confiável)."""
    resultado = []
    for mes in range(1, 13):
        inicio = date(ano, mes, 1)
        if inicio > ate:
            break
        fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
        corpo = {"ano": str(ano), "dataInicio": inicio.isoformat(), "dataFim": fim.isoformat()}
        pagina = 0
        while True:
            time.sleep(PAUSA)
            resposta = client.post(
                f"{API}/proposicao/filter",
                params={"page": pagina, "size": POR_PAGINA, "sort": "id,ASC"},
                json=corpo,
            )
            dados = resposta.raise_for_status().json()
            resultado += dados.get("content", [])
            pagina += 1
            if pagina >= dados.get("totalPages", 0):
                break
    return resultado


def coletar(hoje: date) -> dict:
    with comum.criar_cliente() as client:
        autores = comum.get_json(client, f"{API}/autor/listar")
        props = proposicoes(client, hoje.year - 1, hoje) + proposicoes(client, hoje.year, hoje)
    ativos = [
        a for a in autores if a.get("tipoAutor") == "PARLAMENTAR" and a.get("situacao") == "ATIVO"
    ]
    nomes = {nome_sem_titulo(a["nome"]) for a in ativos}
    autoria = distribuir(props, nomes)
    vereadores = [
        {
            "id_externo": str(a["id"]),
            "nome": nome_sem_titulo(a["nome"]),
            "nome_completo": None,
            "partido": a.get("partidoPoliticoSigla") or None,
            "foto_url": None,  # a foto vem do TSE, pela ligação ao eleito
            "email": a.get("email") or None,
            "telefone": None,
            "titular": True,
            "em_exercicio": True,
            "inicio": None,
            "fim": None,
            "proposicoes_por_tipo": autoria[nome_sem_titulo(a["nome"])]["contagem"],
            "projetos": autoria[nome_sem_titulo(a["nome"])]["projetos"],
            "sessoes": None,
            "presencas": None,
        }
        for a in ativos
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
    if len(casa["vereadores"]) < 20:  # a CLDF tem 24 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na CLDF; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="DF")
        session.add(
            FonteIngestao(fonte=FONTE, url=API, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(f"CLDF: {total} deputados distritais", flush=True)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
