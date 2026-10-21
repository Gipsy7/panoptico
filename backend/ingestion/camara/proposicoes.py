"""Projetos de lei apresentados na Câmara (arquivos anuais em CSV).

Duas cargas por ano, nesta ordem: as proposições e depois os autores. Os arquivos
são grandes (dezenas de MB), então o CSV é lido em fluxo e o bruto é gravado em gzip.
"""

import argparse
import csv
import io
import time
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import bindparam, select, update
from sqlalchemy.orm import Session

from app.db import SessionLocal
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
DESCRICAO_MAX = 300
FONTE_VOTADAS = "camara_proposicoes_votadas"
URL_FICHA = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}"
PAUSA = 0.3


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
                "origem": pc.ORIGEM_LEGISLATURA,
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


def normalizar_autores_externos(conteudo: bytes) -> dict[str, str]:
    """Proposições sem nenhum deputado autor -> quem as apresentou ("Poder Executivo",
    "Comissão de ...", "Senado Federal - Fulano"), na ordem de assinatura. O arquivo traz
    o nome do órgão ou da pessoa em `nomeAutor`; deputado nunca entra aqui."""
    com_deputado: set[str] = set()
    outros: dict[str, list[tuple[int, str]]] = {}
    for linha in _linhas(conteudo):
        if linha["codTipoAutor"] == COD_TIPO_DEPUTADO and linha["idDeputadoAutor"]:
            com_deputado.add(linha["idProposicao"])
            continue
        nome = " ".join(linha["nomeAutor"].split())
        if nome:
            ordem = int(linha["ordemAssinatura"] or 0)
            outros.setdefault(linha["idProposicao"], []).append((ordem, nome))
    descricoes = {}
    for id_proposicao, autores in outros.items():
        if id_proposicao in com_deputado:
            continue
        nomes = list(dict.fromkeys(n for _, n in sorted(autores)))
        descricoes[id_proposicao] = "; ".join(nomes)[:DESCRICAO_MAX]
    return descricoes


def normalizar_ficha(ficha: dict[str, Any]) -> dict[str, Any] | None:
    """A ficha de uma proposição (API) no formato da tabela; None se faltar o essencial."""
    if not ficha.get("dataApresentacao") or not ficha.get("numero") or not ficha.get("ano"):
        return None
    situacao = (ficha.get("statusProposicao") or {}).get("descricaoSituacao") or None
    return {
        "id_externo": str(ficha["id"]),
        "sigla_tipo": ficha["siglaTipo"],
        "numero": int(ficha["numero"]),
        "ano": int(ficha["ano"]),
        "ementa": " ".join((ficha.get("ementa") or "").split()),
        "data_apresentacao": date.fromisoformat(ficha["dataApresentacao"][:10]),
        "situacao": situacao,
        "virou_lei": pc.virou_lei(situacao),
        "url": URL_PAGINA.format(id=ficha["id"]),
    }


def baixar_fichas(client: httpx.Client, ids: list[str]) -> dict[str, dict]:
    """Uma chamada por proposição votada que falta (dezenas), com pausa. Ficha que a API
    não tem (404) fica de fora."""
    fichas = {}
    for id_ in ids:
        time.sleep(PAUSA)
        try:
            fichas[id_] = comum.get_json(client, URL_FICHA.format(id=id_))["dados"]
        except httpx.HTTPStatusError as erro:
            if erro.response.status_code != 404:
                raise
    return fichas


def carregar_votadas(session: Session, payload: dict[str, dict], ingestao: FonteIngestao) -> int:
    registros = [r for f in payload.values() if (r := normalizar_ficha(f))]
    return pc.inserir_votadas(session, CASA, registros, ingestao)


def executar_votadas(de_raw: Path | None = None) -> int:
    """Fichas das proposições votadas que não estão na tabela (anteriores a 2023, MPV...).
    Rode depois das cargas anuais: só busca o que ainda falta."""
    with SessionLocal() as session:
        ids = pc.ids_votados_faltantes(session, CASA)
    return comum.executar_ingestao(
        FONTE_VOTADAS,
        URL_FICHA.format(id="{id}"),
        lambda client: baixar_fichas(client, ids),
        carregar_votadas,
        de_raw=de_raw,
    )


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
    _gravar_descricoes(session, proposicoes, ids_do_arquivo, normalizar_autores_externos(conteudo))
    return pc.substituir_autorias(session, alvo, autorias)


def _gravar_descricoes(
    session: Session,
    proposicoes: dict[str, int],
    ids_do_arquivo: set[str],
    descricoes: dict[str, str],
) -> None:
    """`autor_descricao` só das proposições sem deputado autor; quem passou a ter deputado
    volta a ficar sem. O arquivo cita só as proposições que têm autor registrado."""
    parametros = [
        {"alvo": proposicoes[i], "d": d} for i, d in descricoes.items() if i in proposicoes
    ]
    if parametros:
        session.execute(
            update(Proposicao.__table__)
            .where(Proposicao.__table__.c.id == bindparam("alvo"))
            .values(autor_descricao=bindparam("d")),
            parametros,
        )
    com_deputado = [
        proposicoes[i] for i in ids_do_arquivo if i in proposicoes and i not in descricoes
    ]
    for inicio in range(0, len(com_deputado), 5000):
        session.execute(
            update(Proposicao)
            .where(
                Proposicao.id.in_(com_deputado[inicio : inicio + 5000]),
                Proposicao.autor_descricao.is_not(None),
            )
            .values(autor_descricao=None)
        )


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
    parser.add_argument(
        "--votadas",
        action="store_true",
        help="Só as fichas das proposições votadas que faltam na tabela (aceita --de-raw)",
    )
    args = parser.parse_args()
    if args.votadas:
        print(f"{FONTE_VOTADAS}: {executar_votadas(de_raw=args.de_raw)} proposições")
        raise SystemExit
    for ano in args.ano:
        total = executar(ano, de_raw=args.de_raw, de_raw_autores=args.de_raw_autores)
        print(f"camara_proposicoes {ano}: {total} autorias")
