"""Votações nominais da Câmara, no Plenário e nas comissões (arquivos anuais em CSV).

Baixa quatro CSVs do ano (votações, votos, proposições votadas e orientações das
bancadas) e grava todos num único .zip bruto, para que a carga seja uma transação só.
Só entram votações do Plenário que têm votos registrados (as simbólicas não têm).
O arquivo de votos só lista quem votou e traz o partido do deputado no dia.
"""

import argparse
import csv
import io
import zipfile
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.models import FonteIngestao
from ingestion import comum
from ingestion import votacoes_comum as vc

FONTE = "camara_votacoes"
CASA = "camara"
BASE = "https://dadosabertos.camara.leg.br/arquivos"
ARQUIVOS = {
    "votacoes.csv": BASE + "/votacoes/csv/votacoes-{ano}.csv",
    "votos.csv": BASE + "/votacoesVotos/csv/votacoesVotos-{ano}.csv",
    "proposicoes.csv": BASE + "/votacoesProposicoes/csv/votacoesProposicoes-{ano}.csv",
    "orientacoes.csv": BASE + "/votacoesOrientacoes/csv/votacoesOrientacoes-{ano}.csv",
    "orgaos.csv": BASE + "/orgaos/csv/orgaos.csv",  # nome das comissões pela sigla
}
# Quando a votação cita mais de uma proposição, a matéria principal é a que não é
# requerimento nem recurso sobre ela (ex.: "PL 364/2019" e "REC 5/2024").
ACESSORIAS = {"REQ", "REC"}


def baixar(client: httpx.Client, ano: int) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, url in ARQUIVOS.items():
            z.writestr(nome, comum.get_bytes(client, url.format(ano=ano)))
    return buffer.getvalue()


def _csv(z: zipfile.ZipFile, nome: str):
    if nome not in z.namelist():  # brutos antigos têm só votações e votos
        return []
    return csv.DictReader(io.StringIO(z.read(nome).decode("utf-8-sig")), delimiter=";")


def _proposicoes_principais(z: zipfile.ZipFile, votacoes: set[str]) -> dict[str, dict]:
    por_votacao: dict[str, list[dict]] = {}
    for linha in _csv(z, "proposicoes.csv"):
        if linha["idVotacao"] in votacoes:
            por_votacao.setdefault(linha["idVotacao"], []).append(linha)
    principais = {}
    for id_votacao, linhas in por_votacao.items():
        linhas.sort(key=lambda p: p["proposicao_siglaTipo"] in ACESSORIAS)
        p = linhas[0]
        principais[id_votacao] = {
            "proposicao": p["proposicao_titulo"] or None,
            "proposicao_id_externo": p["proposicao_id"] or None,
            "proposicao_ementa": " ".join(p["proposicao_ementa"].split()) or None,
        }
    return principais


def normalizar(conteudo: bytes) -> tuple[list[dict], list[dict], list[dict]]:
    """Devolve (votações, votos, orientações)."""
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        plenario = {
            linha["id"]: {
                "id_externo": linha["id"],
                "data": date.fromisoformat(linha["data"][:10]),
                "descricao": " ".join(linha["descricao"].split()),
                "proposicao": None,
                "secreta": False,
            }
            for linha in _csv(z, "votacoes.csv")
            if linha["siglaOrgao"] == "PLEN" and linha["data"]
        }
        votos = [
            {
                "id_externo_votacao": linha["idVotacao"],
                "id_deputado": linha["deputado_id"],
                "voto": linha["voto"],
                "partido": linha.get("deputado_siglaPartido") or None,
            }
            for linha in _csv(z, "votos.csv")
            if linha["idVotacao"] in plenario
        ]
        nominais = {v["id_externo_votacao"] for v in votos}
        for id_votacao, proposicao in _proposicoes_principais(z, nominais).items():
            plenario[id_votacao].update(proposicao)
        orientacoes = [
            {
                "id_externo_votacao": linha["idVotacao"],
                "bancada": linha["siglaBancada"].strip(),
                "orientacao": linha["orientacao"].strip(),
            }
            for linha in _csv(z, "orientacoes.csv")
            if linha["idVotacao"] in nominais and linha["siglaBancada"].strip() in vc.BANCADAS
        ]
    return [v for k, v in plenario.items() if k in nominais], votos, orientacoes


def normalizar_comissoes(conteudo: bytes) -> tuple[list[dict], list[dict]]:
    """Votações nominais fora do Plenário (comissões e comissões especiais): (votações, votos)."""
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        nomes = {linha["sigla"]: linha["nome"] for linha in _csv(z, "orgaos.csv")}
        comissoes = {
            linha["id"]: {
                "id_externo": linha["id"],
                "orgao_sigla": linha["siglaOrgao"],
                "orgao_nome": nomes.get(linha["siglaOrgao"]),
                "data": date.fromisoformat(linha["data"][:10]),
                "descricao": " ".join(linha["descricao"].split()),
            }
            for linha in _csv(z, "votacoes.csv")
            if linha["siglaOrgao"] not in ("PLEN", "") and linha["data"]
        }
        votos = [
            {
                "id_externo_votacao": linha["idVotacao"],
                "id_deputado": linha["deputado_id"],
                "voto": linha["voto"],
            }
            for linha in _csv(z, "votos.csv")
            if linha["idVotacao"] in comissoes
        ]
        nominais = {v["id_externo_votacao"] for v in votos}
        for id_votacao, proposicao in _proposicoes_principais(z, nominais).items():
            comissoes[id_votacao].update(proposicao)
    return [v for k, v in comissoes.items() if k in nominais], votos


def executar(ano: int, de_raw: Path | None = None) -> int:
    def carregar(session: Session, conteudo: bytes, ingestao: FonteIngestao) -> int:
        votacoes, votos, orientacoes = normalizar(conteudo)
        deputados = comum.mapa_parlamentares(session, CASA)

        def ligar(lista: list[dict]) -> list[dict]:
            return [
                {**v, "parlamentar_id": deputados[v["id_deputado"]]}
                for v in lista
                if v["id_deputado"] in deputados
            ]

        total = vc.recarregar_votacoes(
            session, CASA, ano, votacoes, ligar(votos), ingestao, orientacoes=orientacoes
        )
        comissoes, votos_comissoes = normalizar_comissoes(conteudo)
        return total + vc.recarregar_comissoes(
            session, CASA, ano, comissoes, ligar(votos_comissoes), ingestao
        )

    return comum.executar_ingestao(
        FONTE,
        ARQUIVOS["votacoes.csv"].format(ano=ano),
        lambda client: baixar(client, ano),
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{ano}_",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=comum.anos_padrao())
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} votos")
