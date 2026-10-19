"""Cadastro de empresas (razão social, nome fantasia, natureza jurídica, situação e município)
dos CNPJs que aparecem nos nossos dados, da base aberta do CNPJ da Receita Federal.

Fonte: arquivos da Receita no compartilhamento público (WebDAV), uma pasta por mês:
https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/AAAA-MM/
(token de leitura `gn672Ad4CF8N6TK` como usuário, senha vazia). Usados: Empresas0-9.zip (razão
social, natureza jurídica), Estabelecimentos0-9.zip (nome fantasia, situação, UF e município,
em código da Receita) e Municipios.zip e Naturezas.zip (tabelas de códigos). CSV em latin-1,
separador ";" e aspas, sem cabeçalho. A base inteira tem ~7,5 GB compactados.

Modo "interesse" (o único; coleta mínima): lê os arquivos em fluxo (cada zip é baixado, filtrado
e apagado) e guarda SÓ as linhas dos CNPJs que aparecem em tabelas do projeto (fornecedores,
beneficiários de emenda, sancionadas, sócias, entes públicos). O bruto é esse recorte (um zip
com Empresas.csv, Estabelecimentos.csv, Municipios.csv e Naturezas.csv no formato original), em
`data/raw/receita_cnpj/`; `--de-raw` reprocessa sem rede. A base completa (60 milhões de
linhas) pede junção em disco e não cabe na produção: para ela, use o minha-receita ou a Base dos
Dados (docs/DECISOES.md, 18/10/2026).

LGPD: a razão social do empresário individual e do MEI traz o CPF do titular ("JOSE DA SILVA
12345678901"). Quando traz, o nome não é guardado (`nome_omitido`). Nome fantasia passa por
`sem_cpf`. Nunca se guarda CPF nem dado de sócio.

O município vem da Receita (código próprio, não IBGE): ligado ao IBGE por nome + UF com a
tabela `municipio`; o que não casa fica sem município (aviso em `fonte_ingestao.alertas`).

Fallback pontual (--brasilapi): CNPJs de interesse que a base não trouxe (cadastro novo) são
consultados na BrasilAPI, um por vez, com pausa, e entram com referencia = "brasilapi".
"""

import argparse
import csv
import io
import re
import tempfile
import time
import zipfile
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import inspect, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.cnpj import cnpj_valido, normalizar_cnpj
from app.db import SessionLocal
from app.models import Empresa, FonteIngestao, Municipio
from app.textos import limpar_texto, sem_cpf
from ingestion import comum

FONTE = "receita_empresas"
BASE = "https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ"
TOKEN = "gn672Ad4CF8N6TK"
URL = BASE + "/{referencia}/"
URL_BRASILAPI = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
PAUSA_BRASILAPI = 1.5
LOTE = 5_000
ARQUIVOS_EMPRESAS = [f"Empresas{i}.zip" for i in range(10)]
ARQUIVOS_ESTABELECIMENTOS = [f"Estabelecimentos{i}.zip" for i in range(10)]

# (tabela, coluna) que guardam CNPJs de empresas que o site mostra. Tabelas que não existem no
# banco (produção enxuta, acervo desatualizado) são puladas.
INTERESSE = [
    ("pncp_soma", "fornecedor_cnpj"),
    ("pncp_contrato", "fornecedor_cnpj"),
    ("pncp_anual", "fornecedor_cnpj"),
    ("pncp_janela", "fornecedor_cnpj"),
    ("pncp_suspeito", "fornecedor_cnpj"),
    ("pncp_ente_publico", "cnpj"),
    ("despesa_fornecedor", "documento"),
    ("despesa", "cnpj_cpf"),
    ("emenda_transferencia", "beneficiario_cnpj"),
    ("emenda_relator_indicacao", "beneficiario_cnpj"),
    ("emenda_pagamento", "favorecido_codigo"),
    ("partido_despesa_vinculada", "fornecedor_cnpj"),
    ("sancao_empresa", "cnpj"),
    ("socio_pessoa", "cnpj"),
]

# Natureza jurídica em que o nome da empresa é o do titular + CPF (empresário individual, MEI,
# EIRELI): o CPF dentro do nome é regra, não acaso.
NATUREZAS_INDIVIDUAIS = {"2135", "2305", "2313"}


# -- CNPJs de interesse ------------------------------------------------------------------------


def cnpjs_de_interesse(session: Session) -> set[str]:
    """Todo CNPJ (14 posições, numérico ou alfanumérico) que aparece nas tabelas de INTERESSE.
    CPF e texto que não tem a forma de CNPJ ficam de fora."""
    existentes = set(inspect(session.get_bind()).get_table_names())
    achados: set[str] = set()
    for tabela, coluna in INTERESSE:
        if tabela not in existentes:
            continue
        for (valor,) in session.execute(
            text(f'SELECT DISTINCT "{coluna}" FROM "{tabela}" WHERE "{coluna}" IS NOT NULL')
        ):
            cnpj = normalizar_cnpj(str(valor))
            if cnpj:
                achados.add(cnpj)
    return achados


# -- leitura dos arquivos da Receita -----------------------------------------------------------


def _linhas(caminho: Path) -> Iterator[bytes]:
    """Linhas (bytes, latin-1 como a Receita grava) do primeiro arquivo dentro do zip."""
    with zipfile.ZipFile(caminho) as z:
        with z.open(z.namelist()[0]) as f:
            yield from f


def _cnpj_da_linha_estab(linha: bytes) -> str:
    """CNPJ completo (raiz + ordem + dígitos) de uma linha de Estabelecimentos: as três
    primeiras colunas têm largura fixa (8, 4 e 2) e vêm entre aspas."""
    return (linha[1:9] + linha[12:16] + linha[19:21]).decode("ascii", "replace")


def filtrar_estabelecimentos(linhas: Iterable[bytes], cnpjs: set[str], saida) -> int:
    """Grava em `saida` as linhas de estabelecimentos cujo CNPJ completo está em `cnpjs`."""
    raizes = {c[:8] for c in cnpjs}
    n = 0
    for linha in linhas:
        if linha[1:9].decode("ascii", "replace") in raizes and _cnpj_da_linha_estab(linha) in cnpjs:
            saida.write(linha if linha.endswith(b"\n") else linha + b"\n")
            n += 1
    return n


def filtrar_empresas(linhas: Iterable[bytes], raizes: set[str], saida) -> int:
    """Grava em `saida` as linhas de empresas cuja raiz (8 primeiras posições) está em `raizes`."""
    n = 0
    for linha in linhas:
        if linha[1:9].decode("ascii", "replace") in raizes:
            saida.write(linha if linha.endswith(b"\n") else linha + b"\n")
            n += 1
    return n


def _csv(conteudo: bytes) -> Iterator[list[str]]:
    texto = io.StringIO(conteudo.decode("latin-1"), newline="")
    yield from csv.reader(texto, delimiter=";", quotechar='"')


def razao_social_segura(razao: str | None, natureza: str | None) -> tuple[str | None, bool]:
    """(razão social sem CPF, nome omitido). Empresário individual/MEI com CPF no nome: o nome
    todo é omitido (o que sobra seria só o nome da pessoa). Em outras naturezas, só o número é
    cortado (um telefone ou código dentro do nome não é motivo para sumir com ele)."""
    limpa = limpar_texto(razao)
    if not limpa:
        return None, False
    segura = sem_cpf(limpa)
    if segura == limpa:
        return limpa, False
    if natureza in NATUREZAS_INDIVIDUAIS:
        return None, True
    return segura, False


def normalizar(
    empresas: bytes,
    estabelecimentos: bytes,
    municipios: bytes,
    naturezas: bytes | None = None,
) -> list[dict[str, Any]]:
    """Junta empresas (razão social, natureza) e estabelecimentos (fantasia, situação, UF,
    município) por CNPJ. `municipio_ibge` fica vazio aqui (depende do banco): vai em
    `municipio_receita` + `uf`, resolvido por `ligar_ibge`."""
    por_raiz: dict[str, tuple[str, str]] = {}
    for c in _csv(empresas):
        if len(c) >= 3:
            por_raiz[c[0]] = (c[1], c[2].zfill(4))
    nomes_municipio = {c[0]: c[1] for c in _csv(municipios) if len(c) >= 2}
    linhas = []
    for c in _csv(estabelecimentos):
        if len(c) < 21:
            continue
        cnpj = normalizar_cnpj(c[0] + c[1] + c[2])
        if cnpj is None or c[0] not in por_raiz:
            continue
        razao, natureza = por_raiz[c[0]]
        razao, omitido = razao_social_segura(razao, natureza)
        fantasia = sem_cpf(limpar_texto(c[4]))
        linhas.append(
            {
                "cnpj": cnpj,
                "razao_social": razao[:300] if razao else None,
                "nome_omitido": omitido,
                "nome_fantasia": fantasia[:300] if fantasia else None,
                "natureza_juridica": natureza,
                "uf": c[19] or None,
                "situacao": c[5] or None,
                "municipio_receita": nomes_municipio.get(c[20]),
            }
        )
    return linhas


def ligar_ibge(session: Session, linhas: list[dict[str, Any]]) -> int:
    """Preenche `municipio_ibge` por nome + UF (só correspondência exata e única). Devolve
    quantos nomes de município da Receita ficaram sem código IBGE."""
    por_nome: dict[tuple[str, str], set[str]] = {}
    for ibge, nome, uf in session.execute(select(Municipio.ibge, Municipio.nome, Municipio.uf)):
        por_nome.setdefault((comum.chave_nome(nome), uf), set()).add(ibge)
    sem = 0
    for linha in linhas:
        nome = linha.pop("municipio_receita", None)
        candidatos = por_nome.get((comum.chave_nome(nome), linha["uf"] or ""), set())
        linha["municipio_ibge"] = next(iter(candidatos)) if len(candidatos) == 1 else None
        if nome and linha["municipio_ibge"] is None:
            sem += 1
    return sem


# -- download ----------------------------------------------------------------------------------


def ultima_referencia(client: httpx.Client) -> str:
    """Mês mais recente publicado na pasta da Receita ("2026-10")."""
    resposta = client.request("PROPFIND", BASE + "/", headers={"Depth": "1"}, timeout=60)
    resposta.raise_for_status()
    meses = re.findall(r"/CNPJ/(\d{4}-\d{2})/", resposta.text)
    if not meses:
        raise RuntimeError("Nenhuma pasta AAAA-MM na listagem da Receita")
    return max(meses)


def baixar(client: httpx.Client, referencia: str, cnpjs: set[str]) -> Path:
    """Baixa os zips da Receita um a um, filtra e apaga. Devolve o zip do recorte (bruto)."""
    raizes = {c[:8] for c in cnpjs}
    base = URL.format(referencia=referencia)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        recorte = Path(tmp.name)
    with zipfile.ZipFile(recorte, "w", zipfile.ZIP_DEFLATED) as saida:
        for nome in ("Municipios.zip", "Naturezas.zip"):
            arquivo = comum.baixar_para_arquivo(client, base + nome)
            try:
                with zipfile.ZipFile(arquivo) as z:
                    saida.writestr(nome.replace(".zip", ".csv"), z.read(z.namelist()[0]))
            finally:
                arquivo.unlink(missing_ok=True)
        for alvo, arquivos, filtro, dados in (
            ("Estabelecimentos.csv", ARQUIVOS_ESTABELECIMENTOS, filtrar_estabelecimentos, cnpjs),
            ("Empresas.csv", ARQUIVOS_EMPRESAS, filtrar_empresas, raizes),
        ):
            with saida.open(alvo, "w", force_zip64=True) as destino:
                for nome in arquivos:
                    inicio = time.time()
                    arquivo = comum.baixar_para_arquivo(client, base + nome)
                    try:
                        n = filtro(_linhas(arquivo), dados, destino)
                    finally:
                        arquivo.unlink(missing_ok=True)
                    print(
                        f"  {nome}: {n} linhas de interesse ({time.time() - inicio:.0f}s)",
                        flush=True,
                    )
        saida.writestr("referencia.txt", f"{referencia}\n{len(cnpjs)}\n")
    return recorte


# -- carga -------------------------------------------------------------------------------------


def ler_recorte(payload: bytes | Path) -> tuple[list[dict[str, Any]], str, int]:
    """(linhas, referência, CNPJs de interesse) a partir do zip do recorte."""
    origem = io.BytesIO(payload) if isinstance(payload, bytes) else payload
    with zipfile.ZipFile(origem) as z:
        referencia, _, interesse = z.read("referencia.txt").decode().partition("\n")
        linhas = normalizar(
            z.read("Empresas.csv"),
            z.read("Estabelecimentos.csv"),
            z.read("Municipios.csv"),
        )
    return linhas, referencia, int(interesse.strip() or 0)


def gravar(session: Session, linhas: list[dict[str, Any]], referencia: str) -> int:
    """Upsert por CNPJ em lotes. Não apaga o que não veio (outras cargas, BrasilAPI)."""
    agora = datetime.now(UTC)
    colunas = (
        "razao_social",
        "nome_omitido",
        "nome_fantasia",
        "natureza_juridica",
        "municipio_ibge",
        "uf",
        "situacao",
        "referencia",
        "atualizado_em",
    )
    for i in range(0, len(linhas), LOTE):
        lote = [
            {**x, "referencia": referencia, "atualizado_em": agora} for x in linhas[i : i + LOTE]
        ]
        stmt = insert(Empresa).values(lote)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=["cnpj"], set_={c: stmt.excluded[c] for c in colunas}
            )
        )
    return len(linhas)


def executar(
    de_raw: Path | None = None,
    referencia: str | None = None,
    brasilapi: bool = False,
    limite_brasilapi: int = 200,
) -> int:
    """Carga do cadastro de empresas de interesse. Sem `de_raw`: baixa a base do mês mais
    recente (ou `referencia`) e grava o recorte como bruto."""
    estado: dict[str, Any] = {}

    def baixar_recorte(client: httpx.Client) -> Path:
        client.auth = httpx.BasicAuth(TOKEN, "")
        with SessionLocal() as session:
            cnpjs = cnpjs_de_interesse(session)
        if not cnpjs:
            raise RuntimeError("Nenhum CNPJ de interesse no banco: nada a buscar")
        ref = referencia or ultima_referencia(client)
        estado["referencia"] = ref
        print(f"Base de {ref}: {len(cnpjs)} CNPJs de interesse", flush=True)
        return baixar(client, ref, cnpjs)

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        linhas, ref, interesse = ler_recorte(payload)
        if not linhas:
            raise RuntimeError("Recorte sem nenhuma empresa: base fora do formato ou vazia")
        sem_municipio = ligar_ibge(session, linhas)
        total = gravar(session, linhas, ref)
        ingestao.url = URL.format(referencia=ref)
        alertas = []
        if interesse and interesse > total:
            alertas.append(f"{interesse - total} CNPJs de interesse sem cadastro na base de {ref}")
        if sem_municipio:
            alertas.append(f"{sem_municipio} municípios da Receita sem código IBGE")
        omitidos = sum(1 for x in linhas if x["nome_omitido"])
        if omitidos:
            alertas.append(f"{omitidos} razões sociais omitidas por conter CPF")
        ingestao.alertas = alertas or None
        return total

    n = comum.executar_ingestao(
        FONTE,
        URL.format(referencia=referencia or "AAAA-MM"),
        baixar_recorte,
        carregar,
        de_raw=de_raw,
        extensao_raw=".zip",
    )
    if brasilapi:
        n += completar_brasilapi(limite_brasilapi)
    return n


# -- fallback pontual: BrasilAPI ---------------------------------------------------------------


def normalizar_brasilapi(resposta: dict) -> dict[str, Any] | None:
    """Uma resposta da BrasilAPI vira linha de `empresa` (mesmas regras de CPF)."""
    cnpj = normalizar_cnpj(str(resposta.get("cnpj") or ""))
    if cnpj is None:
        return None
    natureza = str(resposta.get("codigo_natureza_juridica") or "").zfill(4)
    razao, omitido = razao_social_segura(resposta.get("razao_social"), natureza)
    fantasia = sem_cpf(limpar_texto(resposta.get("nome_fantasia")))
    ibge = str(resposta.get("codigo_municipio_ibge") or "")
    return {
        "cnpj": cnpj,
        "razao_social": razao[:300] if razao else None,
        "nome_omitido": omitido,
        "nome_fantasia": fantasia[:300] if fantasia else None,
        "natureza_juridica": natureza if natureza != "0000" else None,
        "municipio_ibge": ibge if len(ibge) == 7 else None,
        "uf": resposta.get("uf") or None,
        "situacao": str(resposta["situacao_cadastral"]).zfill(2)
        if resposta.get("situacao_cadastral")
        else None,
    }


def completar_brasilapi(limite: int = 200) -> int:
    """Consulta na BrasilAPI os CNPJs de interesse (com dígito verificador válido) que ainda não
    estão em `empresa`. Um por vez, com pausa; o cadastro gravado é o cache."""
    gravados = 0
    with SessionLocal() as session, comum.criar_cliente() as client:
        faltam = sorted(
            c
            for c in cnpjs_de_interesse(session) - set(session.scalars(select(Empresa.cnpj)))
            if cnpj_valido(c)
        )[:limite]
        for cnpj in faltam:
            resposta = client.get(URL_BRASILAPI.format(cnpj=cnpj), timeout=30)
            if resposta.status_code == 200:
                linha = normalizar_brasilapi(resposta.json())
                if linha:
                    gravar(session, [linha], "brasilapi")
                    session.commit()
                    gravados += 1
            elif resposta.status_code == 429:
                print("BrasilAPI pediu para esperar (429): parando por hoje", flush=True)
                break
            time.sleep(PAUSA_BRASILAPI)
    return gravados


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cadastro de empresas (base de CNPJ da Receita)")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa o recorte guardado, sem rede")
    parser.add_argument("--referencia", help="Mês da base (AAAA-MM); padrão: o mais recente")
    parser.add_argument("--brasilapi", action="store_true", help="Completa pela BrasilAPI")
    parser.add_argument("--limite-brasilapi", type=int, default=200)
    args = parser.parse_args()
    print(
        f"{executar(args.de_raw, args.referencia, args.brasilapi, args.limite_brasilapi)} empresas"
    )
