"""Votações nominais da Câmara, no Plenário e nas comissões (arquivos anuais em CSV).

Baixa quatro CSVs do ano (votações, votos, proposições votadas e orientações das
bancadas), a lista de blocos da legislatura (API, com os partidos de cada bloco) e grava
tudo num único .zip bruto, para que a carga seja uma transação só.
Só entram votações do Plenário que têm votos registrados (as simbólicas não têm).
O arquivo de votos só lista quem votou e traz o partido do deputado no dia.

Orientações: o CSV traz lideranças (Governo, Maioria...), partidos (com `uriBancada`, às vezes
com a sigla cortada: "Solidaried"), federações ("Fdr PT-PCdoB-PV") e blocos com o nome
truncado ("Bl UniPpPsd..."). A sigla do partido vem do id em `uriBancada`, pelo arquivo de
votos. Bloco e federação ficam com o nome como a fonte publica; a composição só é anotada
quando o rótulo casa com um único bloco da lista oficial (docs/DECISOES.md, 2026-10-18).
"""

import argparse
import csv
import io
import json
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
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
API = "https://dadosabertos.camara.leg.br/api/v2"
RESULTADOS = {"1": "aprovada", "0": "rejeitada"}


def legislatura(ano: int) -> int:
    """Número da legislatura que contém o ano (a 57ª vai de 2023 a 2026)."""
    return 50 + (ano - 1995) // 4


def _blocos(client: httpx.Client, ano: int) -> list[dict]:
    """Blocos e federações da legislatura, com as siglas dos partidos de cada um. A Câmara só
    publica a composição atual (sem datas); por isso o uso é restrito (ver `decompor`)."""
    resposta = comum.get_json(
        client, f"{API}/blocos", params={"idLegislatura": legislatura(ano), "itens": 100}
    )
    blocos = []
    for b in resposta.get("dados", []):
        # Bloco já desfeito vem com a lista vazia; aí `decompor` usa o nome oficial, que é
        # a própria lista de siglas ("AVANTE, SOLIDARIEDADE, PRD").
        partidos = comum.get_json(client, f"{API}/blocos/{b['id']}/partidos").get("dados", [])
        blocos.append(
            {"id": str(b["id"]), "nome": b["nome"], "federacao": bool(b.get("federacao")),
             "partidos": [p["sigla"] for p in partidos]}
        )  # fmt: skip
    return blocos


def baixar(client: httpx.Client, ano: int) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, url in ARQUIVOS.items():
            z.writestr(nome, comum.get_bytes(client, url.format(ano=ano)))
        try:
            blocos = _blocos(client, ano)
        except httpx.HTTPError as erro:
            # A composição dos blocos é complemento: sem ela, o bloco aparece só pelo nome.
            print(f"[aviso] blocos da legislatura indisponíveis: {erro!r}", flush=True)
            blocos = []
        z.writestr("blocos.json", json.dumps(blocos, ensure_ascii=False))
    return buffer.getvalue()


def _chave(texto: str) -> str:
    """Sigla sem acento e em maiúsculas, para comparar "União" com "UNIÃO"."""
    sem = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem if not unicodedata.combining(c)).upper().strip()


def _siglas_do_nome(nome: str) -> list[str]:
    """Siglas do nome oficial de um bloco ("AVANTE, SOLIDARIEDADE, PRD"); vazio se algum
    pedaço não for uma sigla só (ex.: "Federação PSDB CIDADANIA")."""
    pedacos = [p.strip() for p in nome.split(",")]
    return pedacos if all(p and " " not in p for p in pedacos) else []


def decompor(rotulo: str, blocos: list[dict]) -> list[str] | None:
    """Partidos de um bloco ou federação a partir do rótulo truncado do CSV.

    "Fdr PSDB-CIDADAN" é dividido no hífen; "Bl UniPpPsd..." nas maiúsculas. Cada pedaço tem
    de ser o começo de um partido diferente do bloco oficial, e só um bloco da lista pode
    casar; senão devolve None e o bloco fica só com o nome publicado."""
    corpo = rotulo.removesuffix("...").strip()
    if corpo.startswith("Fdr "):
        pedacos, federacao = [p for p in corpo[4:].split("-") if p], True
    elif corpo.startswith("Bl "):
        pedacos, federacao = re.findall(r"[A-ZÀ-Ý][^A-ZÀ-Ý]*", corpo[3:]), False
    else:
        return None
    if not pedacos:
        return None
    truncado = rotulo.endswith("...")
    candidatos = []
    for bloco in blocos:
        if bloco["federacao"] != federacao:
            continue
        membros = list(bloco["partidos"]) or _siglas_do_nome(bloco["nome"])
        if not membros:
            continue
        livres = list(membros)
        casou = True
        for pedaco in pedacos:
            achado = next((p for p in livres if _chave(p).startswith(_chave(pedaco))), None)
            if achado is None:
                casou = False
                break
            livres.remove(achado)
        if casou and (truncado or not livres):
            candidatos.append(membros)
    return candidatos[0] if len(candidatos) == 1 else None


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
                "resultado": RESULTADOS.get((linha.get("aprovacao") or "").strip()),
                "placar_sim": _inteiro(linha.get("votosSim")),
                "placar_nao": _inteiro(linha.get("votosNao")),
            }
            for linha in _csv(z, "votacoes.csv")
            if linha["siglaOrgao"] == "PLEN" and linha["data"]
        }
        votos: list[dict] = []
        siglas_por_id: dict[str, Counter] = defaultdict(Counter)
        for linha in _csv(z, "votos.csv"):
            if linha["idVotacao"] not in plenario:
                continue
            partido = linha.get("deputado_siglaPartido") or None
            votos.append(
                {"id_externo_votacao": linha["idVotacao"], "id_deputado": linha["deputado_id"],
                 "voto": linha["voto"], "partido": partido}
            )  # fmt: skip
            id_partido = _id_da_uri(linha.get("deputado_uriPartido"))
            if partido and id_partido:
                siglas_por_id[id_partido][partido] += 1
        nominais = {v["id_externo_votacao"] for v in votos}
        for id_votacao, proposicao in _proposicoes_principais(z, nominais).items():
            plenario[id_votacao].update(proposicao)
        # Votação secreta (ex.: escolha de ministro do TCU): o arquivo lista quem votou, com o
        # voto em branco, e só o placar diz o resultado.
        com_voto = {v["id_externo_votacao"] for v in votos if v["voto"]}
        for id_votacao in nominais - com_voto:
            v = plenario[id_votacao]
            v["secreta"] = bool(v.get("placar_sim") or v.get("placar_nao"))
        blocos = json.loads(z.read("blocos.json")) if "blocos.json" in z.namelist() else []
        orientacoes = _orientacoes(
            _csv(z, "orientacoes.csv"),
            nominais,
            {i: c.most_common(1)[0][0] for i, c in siglas_por_id.items()},
            {_chave(v["partido"]): v["partido"] for v in votos if v["partido"]},
            blocos,
        )
    return [v for k, v in plenario.items() if k in nominais], votos, orientacoes


def _inteiro(texto: str | None) -> int | None:
    texto = (texto or "").strip()
    return int(texto) if texto.isdigit() else None


def _id_da_uri(uri: str | None) -> str | None:
    """Id no fim da URI ("https://.../partidos/36844" -> "36844")."""
    final = (uri or "").rstrip("/").rsplit("/", 1)[-1]
    return final if final.isdigit() else None


def _sigla_do_rotulo(rotulo: str, siglas: dict[str, str]) -> str | None:
    """Sigla de partido escrita no rótulo, inteira ou cortada pela fonte ("Solidaried"): só
    quando o começo casa com uma sigla única entre as dos votos do ano."""
    chave = _chave(rotulo)
    if chave in siglas:
        return siglas[chave]
    if len(chave) < 4 or rotulo.startswith(("Fdr ", "Bl ")):
        return None
    casam = [s for c, s in siglas.items() if c.startswith(chave)]
    return casam[0] if len(casam) == 1 else None


def _orientacoes(
    linhas, nominais: set[str], sigla_do_id: dict[str, str], siglas: dict[str, str],
    blocos: list[dict],
) -> list[dict]:  # fmt: skip
    """Classifica cada linha do CSV de orientações (lideranca, partido, federacao, bloco ou
    outra). Partido, bloco ou federação sem orientação ficam de fora (o líder não orientou);
    as lideranças seguem como antes, mesmo em branco."""
    resultado = []
    for linha in linhas:
        if linha["idVotacao"] not in nominais:
            continue
        rotulo = linha["siglaBancada"].strip()
        orientacao = linha["orientacao"].strip()
        registro = {"id_externo_votacao": linha["idVotacao"], "bancada": rotulo,
                    "orientacao": orientacao}  # fmt: skip
        if rotulo in vc.BANCADAS:
            resultado.append(registro | {"tipo": "lideranca"})
            continue
        if not orientacao:
            continue
        id_partido = _id_da_uri(linha.get("uriBancada"))
        sigla = sigla_do_id.get(id_partido or "") or _sigla_do_rotulo(rotulo, siglas)
        if id_partido or sigla:
            resultado.append(registro | {"bancada": sigla or rotulo, "tipo": "partido"})
        elif rotulo.startswith(("Fdr ", "Bl ")):
            partidos = decompor(rotulo, blocos)
            resultado.append(
                registro
                | {"tipo": "federacao" if rotulo.startswith("Fdr ") else "bloco",
                   "partidos": ",".join(siglas.get(_chave(p), p) for p in partidos)
                   if partidos else None}
            )  # fmt: skip
        else:
            resultado.append(registro | {"tipo": "outra"})
    return resultado


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
