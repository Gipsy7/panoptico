"""Votações nominais do Plenário da Câmara (arquivos anuais em CSV).

Baixa votações e votos do ano e grava os dois CSVs num único .zip bruto, para que a
carga seja uma transação só. Só entram votações do Plenário que têm votos
registrados (as simbólicas não têm). O arquivo de votos só lista quem votou.
"""

import argparse
import csv
import io
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import FonteIngestao
from ingestion import comum
from ingestion import votacoes_comum as vc

FONTE = "camara_votacoes"
CASA = "camara"
URL_VOTACOES = "https://dadosabertos.camara.leg.br/arquivos/votacoes/csv/votacoes-{ano}.csv"
URL_VOTOS = "https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/csv/votacoesVotos-{ano}.csv"


def baixar(client: httpx.Client, ano: int) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("votacoes.csv", comum.get_bytes(client, URL_VOTACOES.format(ano=ano)))
        z.writestr("votos.csv", comum.get_bytes(client, URL_VOTOS.format(ano=ano)))
    return buffer.getvalue()


def _csv(z: zipfile.ZipFile, nome: str):
    return csv.DictReader(io.StringIO(z.read(nome).decode("utf-8-sig")), delimiter=";")


def normalizar(conteudo: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
            }
            for linha in _csv(z, "votos.csv")
            if linha["idVotacao"] in plenario
        ]
    nominais = {v["id_externo_votacao"] for v in votos}
    return [v for k, v in plenario.items() if k in nominais], votos


def executar(ano: int, de_raw: Path | None = None) -> int:
    def carregar(session: Session, conteudo: bytes, ingestao: FonteIngestao) -> int:
        votacoes, votos = normalizar(conteudo)
        deputados = comum.mapa_parlamentares(session, CASA)
        votos = [
            {**v, "parlamentar_id": deputados[v["id_deputado"]]}
            for v in votos
            if v["id_deputado"] in deputados
        ]
        return vc.recarregar_votacoes(session, CASA, ano, votacoes, votos, ingestao)

    return comum.executar_ingestao(
        FONTE,
        URL_VOTACOES.format(ano=ano),
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
