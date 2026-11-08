"""IDEB (Índice de Desenvolvimento da Educação Básica) do INEP: a nota observada de cada
edição (2005 a 2025), por município, estado e Brasil, rede de ensino e etapa (anos iniciais e
finais do fundamental, ensino médio).

Arquivos da divulgação (download.inep.gov.br/ideb/resultados/), em xlsx dentro de zip:
`divulgacao_<etapa>_municipios_<ano>.zip` (uma planilha), `divulgacao_regioes_ufs_ideb_<ano>.zip`
e `divulgacao_brasil_ideb_<ano>.zip` (três planilhas, uma por etapa). A planilha traz uma linha
com os códigos das colunas (`VL_OBSERVADO_2025`...) e, abaixo, os dados até a primeira linha
vazia; "-" é sem nota. Rótulos de rede vêm com nota de rodapé ("Total (4)"). As metas
(`VL_PROJECAO_*`) acabaram em 2021, com o fim do 1º ciclo, e não são guardadas.

O servidor do INEP não envia o certificado intermediário (RNP ICPEdu GR46 OV TLS CA 2025, em
08/11/2026): a verificação TLS não é desligada; o intermediário é baixado do endereço que o
próprio certificado indica, como em emendas_estaduais/ba.py.

Os arquivos têm ~70 MB juntos; o bruto guardado é o recorte (só as notas observadas), e o
original continua no INEP.
"""

import argparse
import gzip
import io
import json
import re
import zipfile
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, IdebResultado
from ingestion import comum
from ingestion.emendas_estaduais.ba import contexto_tls

FONTE = "inep_ideb"
EDICAO = 2025
BASE = "https://download.inep.gov.br/ideb/resultados/"
URL = BASE + "divulgacao_anos_iniciais_municipios_{edicao}.zip"
INTERMEDIARIO = "http://secure.globalsign.com/cacert/rnpicpedugr46ovtlsca2025.crt"
ETAPAS = {"anos_iniciais": "iniciais", "anos_finais": "finais", "ensino_medio": "medio"}
# Ordem das planilhas nos arquivos de UF e de Brasil.
ORDEM_ETAPAS = ["iniciais", "finais", "medio"]
REDES = {"total": "total", "pública": "publica", "publica": "publica", "estadual": "estadual",
         "municipal": "municipal", "federal": "federal", "privada": "privada"}  # fmt: skip
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
UFS = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
    "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA",
    "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA",
    "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR",
    "Santa Catarina": "SC", "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO",
    # Abreviações da planilha de UFs (medido em 08/11/2026).
    "M. G. do Sul": "MS", "R. G. do Norte": "RN", "R. G. do Sul": "RS",
}  # fmt: skip


def _linhas(arquivo, textos: list[str]) -> Iterator[list[str]]:
    """Linhas de uma planilha lidas em fluxo (iterparse): a de municípios tem ~14 mil linhas e
    ~120 colunas, e montada inteira na memória derrubava a carga na VPS (4 GB)."""
    for _evento, linha in ElementTree.iterparse(arquivo):
        if linha.tag != f"{NS}row":
            continue
        celulas: dict[int, str] = {}
        for c in linha.findall(f"{NS}c"):
            coluna = 0
            for letra in re.match(r"[A-Z]+", c.get("r", "A"))[0]:
                coluna = coluna * 26 + ord(letra) - 64
            valor = c.find(f"{NS}v")
            if c.get("t") == "s" and valor is not None:
                texto = textos[int(valor.text)]
            elif c.get("t") == "inlineStr":
                texto = "".join(t.text or "" for t in c.iter(f"{NS}t"))
            else:
                texto = valor.text if valor is not None and valor.text else ""
            celulas[coluna - 1] = texto.strip()
        linha.clear()
        largura = max(celulas, default=-1) + 1
        yield [celulas.get(i, "") for i in range(largura)]


def folhas(conteudo: bytes) -> Iterator[Iterator[list[str]]]:
    """Cada planilha de um xlsx (na ordem do arquivo), em fluxo; consuma uma antes da outra."""
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        textos: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            with z.open("xl/sharedStrings.xml") as f:
                for _evento, si in ElementTree.iterparse(f):
                    if si.tag == f"{NS}si":
                        textos.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
                        si.clear()
        nomes = sorted(
            (n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)\.xml$", n)[1]),
        )
        for nome in nomes:
            with z.open(nome) as f:
                yield _linhas(f, textos)


def planilhas(conteudo: bytes) -> list[list[list[str]]]:
    """Todas as planilhas, inteiras (para arquivos pequenos e testes)."""
    return [list(f) for f in folhas(conteudo)]


def _nota(texto: str) -> str | None:
    try:
        return str(Decimal(texto).quantize(Decimal("0.1")))
    except (InvalidOperation, ValueError):
        return None  # "-", vazio, "*"


def _rede(texto: str) -> str | None:
    return REDES.get(re.sub(r"\s*\(\d+\)\s*$", "", texto).strip().lower())


def notas(linhas, colunas_chave: int) -> list[list[Any]]:
    """[chave..., rede, {ano: nota}] de cada linha de dados da planilha (lista ou fluxo)."""
    linhas = iter(linhas)
    anos = None
    for r in linhas:
        if any(c.startswith("VL_OBSERVADO_") for c in r):
            anos = {
                i: c.rsplit("_", 1)[1] for i, c in enumerate(r) if c.startswith("VL_OBSERVADO_")
            }
            break
    if anos is None:
        raise ValueError("Planilha do IDEB sem a linha de códigos (VL_OBSERVADO_*)")
    saida = []
    for r in linhas:
        if len(r) <= colunas_chave or not r[0]:
            break  # fim dos dados (depois vêm as notas de rodapé)
        rede = _rede(r[colunas_chave])
        valores = {a: _nota(r[i]) for i, a in anos.items() if i < len(r)}
        valores = {a: v for a, v in valores.items() if v is not None}
        if rede and valores:
            saida.append([*r[:colunas_chave], rede, valores])
    return saida  # fmt: skip


def _xlsx_do_zip(conteudo: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        return z.read(next(n for n in z.namelist() if n.endswith(".xlsx")))


def baixar_tudo(client: httpx.Client, edicao: int = EDICAO) -> dict[str, Any]:
    intermediario = comum.get_bytes(client, INTERMEDIARIO)
    with httpx.Client(
        timeout=httpx.Timeout(60.0, read=300.0),
        headers=client.headers,
        follow_redirects=True,
        transport=httpx.HTTPTransport(local_address="0.0.0.0", verify=contexto_tls(intermediario)),
    ) as seguro:
        return _baixar(seguro, edicao)


def _baixar(client: httpx.Client, edicao: int) -> dict[str, Any]:
    recorte: dict[str, Any] = {"edicao": edicao, "municipios": {}, "ufs": {}, "brasil": {}}
    for nome, etapa in ETAPAS.items():
        x = _xlsx_do_zip(
            comum.get_bytes(client, f"{BASE}divulgacao_{nome}_municipios_{edicao}.zip")
        )
        gerador = folhas(x)  # guardado: descartado, ele fecharia o zip antes da leitura
        linhas = next(gerador)
        # SG_UF, CO_MUNICIPIO, NO_MUNICIPIO, REDE: a chave é o código (coluna 1).
        recorte["municipios"][etapa] = [[r[1], r[3], r[4]] for r in notas(linhas, 3)]
        gerador.close()
        del x
    for arquivo, chave in ((f"divulgacao_regioes_ufs_ideb_{edicao}.zip", "ufs"),
                           (f"divulgacao_brasil_ideb_{edicao}.zip", "brasil")):  # fmt: skip
        planilha = folhas(_xlsx_do_zip(comum.get_bytes(client, BASE + arquivo)))
        for etapa, linhas in zip(ORDEM_ETAPAS, planilha, strict=False):
            recorte[chave][etapa] = [[r[0], r[1], r[2]] for r in notas(linhas, 1)]
    return recorte


def normalizar(recorte: dict[str, Any]) -> list[dict[str, Any]]:
    linhas: dict[tuple, dict[str, Any]] = {}

    def por(abrangencia: str, codigo: str, etapa: str, rede: str, valores: dict[str, str]):
        for ano, nota in valores.items():
            chave = (abrangencia, codigo, etapa, rede, int(ano))
            linhas[chave] = dict(zip(("abrangencia", "codigo", "etapa", "rede", "ano"), chave,
                                     strict=True), valor=Decimal(nota))  # fmt: skip

    for etapa, lista in recorte["municipios"].items():
        for codigo, rede, valores in lista:
            if re.fullmatch(r"\d{7}", codigo):
                por("municipio", codigo, etapa, rede, valores)
    for etapa, lista in recorte["ufs"].items():
        for nome, rede, valores in lista:
            if nome in UFS:  # as regiões ficam de fora
                por("uf", UFS[nome], etapa, rede, valores)
    for etapa, lista in recorte["brasil"].items():
        for _nome, rede, valores in lista:
            por("brasil", "BR", etapa, rede, valores)
    return list(linhas.values())


def carregar(session: Session, payload: bytes, ingestao: FonteIngestao) -> int:
    recorte = json.loads(gzip.decompress(payload) if payload[:2] == b"\x1f\x8b" else payload)
    linhas = normalizar(recorte)
    municipios = {r["codigo"] for r in linhas if r["abrangencia"] == "municipio"}
    if len(municipios) < 5000:
        raise ValueError(f"IDEB com só {len(municipios)} municípios; abortando.")
    session.execute(delete(IdebResultado))
    lista = [{**r, "ingestao_id": ingestao.id} for r in linhas]
    for inicio in range(0, len(lista), 5000):
        session.execute(insert(IdebResultado), lista[inicio : inicio + 5000])
    print(f"  {len(lista)} notas; {len(municipios)} municípios")
    return len(lista)


def executar(de_raw: Path | None = None, edicao: int = EDICAO) -> int:
    def baixar(client: httpx.Client) -> bytes:
        return json.dumps(baixar_tudo(client, edicao), ensure_ascii=False, sort_keys=True).encode()

    return comum.executar_ingestao(
        FONTE,
        URL.format(edicao=edicao),
        baixar,
        carregar,
        de_raw=de_raw,
        extensao_raw=".json.gz",
        incremental=comum.Incremental(chave=FONTE),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    parser.add_argument(
        "--edicao", type=int, default=EDICAO, help="Ano da divulgação (padrão 2025)"
    )
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw, edicao=args.edicao)} notas do IDEB")
