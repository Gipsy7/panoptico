"""Projetos de lei apresentados na Câmara (arquivos anuais em CSV).

Duas cargas por ano, nesta ordem: as proposições e depois os autores. Os arquivos
são grandes (dezenas de MB), então o CSV é lido em fluxo e o bruto é gravado em gzip.
"""

import argparse
import csv
import io
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Proposicao
from ingestion import comum
from ingestion import proposicoes_comum as pc

CASA = "camara"
FONTE_PROPOSICOES = "camara_proposicoes"
FONTE_AUTORES = "camara_autores"
URL_PROPOSICOES = (
    "https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv"
)
URL_AUTORES = "https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/csv/proposicoesAutores-{ano}.csv"
URL_PAGINA = "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id}"
COD_TIPO_DEPUTADO = "10000"


def _linhas(conteudo: bytes):
    return csv.DictReader(io.StringIO(conteudo.decode("utf-8-sig")), delimiter=";")


def normalizar_proposicoes(conteudo: bytes) -> list[dict[str, Any]]:
    registros = []
    for linha in _linhas(conteudo):
        if linha["siglaTipo"] not in pc.TIPOS or not linha["dataApresentacao"]:
            continue
        apresentacao = date.fromisoformat(linha["dataApresentacao"][:10])
        if apresentacao < pc.INICIO_LEGISLATURA:
            continue
        situacao = linha["ultimoStatus_descricaoSituacao"] or None
        registros.append(
            {
                "id_externo": linha["id"],
                "sigla_tipo": linha["siglaTipo"],
                "numero": int(linha["numero"]),
                "ano": int(linha["ano"]),
                "ementa": " ".join(linha["ementa"].split()),
                "data_apresentacao": apresentacao,
                "situacao": situacao,
                "virou_lei": pc.virou_lei(situacao),
                "url": URL_PAGINA.format(id=linha["id"]),
            }
        )
    return registros


def normalizar_autores(conteudo: bytes) -> list[dict[str, Any]]:
    return [
        {
            "id_proposicao": linha["idProposicao"],
            "id_deputado": linha["idDeputadoAutor"],
            "primeiro_autor": linha["ordemAssinatura"] == "1",
        }
        for linha in _linhas(conteudo)
        if linha["codTipoAutor"] == COD_TIPO_DEPUTADO and linha["idDeputadoAutor"]
    ]


def carregar_proposicoes(session: Session, conteudo: bytes, ingestao: FonteIngestao) -> int:
    registros = normalizar_proposicoes(conteudo)
    if not registros:
        return 0
    return len(pc.upsert_proposicoes(session, CASA, registros, ingestao))


def carregar_autores(session: Session, conteudo: bytes, ingestao: FonteIngestao) -> int:
    autores = normalizar_autores(conteudo)
    # Todas as proposições da Câmara já carregadas (um IN com o arquivo inteiro estouraria
    # o limite de parâmetros do Postgres).
    proposicoes = {
        id_externo: id_
        for id_externo, id_ in session.execute(
            select(Proposicao.id_externo, Proposicao.id).where(Proposicao.casa == CASA)
        )
    }
    ids_do_arquivo = {a["id_proposicao"] for a in autores}
    deputados = comum.mapa_parlamentares(session, CASA)
    autorias = [
        {
            "proposicao_id": proposicoes[a["id_proposicao"]],
            "parlamentar_id": deputados[a["id_deputado"]],
            "primeiro_autor": a["primeiro_autor"],
        }
        for a in autores
        if a["id_proposicao"] in proposicoes and a["id_deputado"] in deputados
    ]
    alvo = [id_ for id_externo, id_ in proposicoes.items() if id_externo in ids_do_arquivo]
    return pc.substituir_autorias(session, alvo, autorias)


def executar(ano: int, de_raw: Path | None = None, de_raw_autores: Path | None = None) -> int:
    url_p, url_a = URL_PROPOSICOES.format(ano=ano), URL_AUTORES.format(ano=ano)
    kwargs = {"prefixo_raw": f"{ano}_", "extensao_raw": ".csv.gz"}
    comum.executar_ingestao(
        FONTE_PROPOSICOES,
        url_p,
        lambda client: comum.get_bytes(client, url_p),
        carregar_proposicoes,
        de_raw=de_raw,
        **kwargs,
    )
    return comum.executar_ingestao(
        FONTE_AUTORES,
        url_a,
        lambda client: comum.get_bytes(client, url_a),
        carregar_autores,
        de_raw=de_raw_autores,
        **kwargs,
    )


def anos_legislatura() -> list[int]:
    return list(range(pc.INICIO_LEGISLATURA.year, comum.anos_padrao()[-1] + 1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestão: projetos de lei da Câmara")
    parser.add_argument("--ano", type=int, nargs="*", default=comum.anos_padrao())
    parser.add_argument("--de-raw", type=Path, help="Bruto das proposições (um ano só)")
    parser.add_argument("--de-raw-autores", type=Path, help="Bruto dos autores (um ano só)")
    args = parser.parse_args()
    for ano in args.ano:
        total = executar(ano, de_raw=args.de_raw, de_raw_autores=args.de_raw_autores)
        print(f"camara_proposicoes {ano}: {total} autorias")
