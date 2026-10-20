"""Transferências da União por mês (Portal da Transparência): Fundeb, royalties e as legais,
voluntárias e específicas.

Complementa `ingestion.tesouro.transferencias` (FPE, FPM, IPI-Exp e as obrigatórias, que valem
pelo Tesouro). Entram em `transferencia_uniao` com `fonte = "portal"` e os blocos:
- FUNDEB_UNIAO: ação "Complementação da União ao Fundeb" (0E36 até 2020, 00SB desde 2022);
- ROYALTIES: ações 0A53 (petróleo e gás), 0547 (recursos minerais), 0546 (recursos hídricos) e
  0223 (Itaipu);
- LEGAIS_VOLUNTARIAS: toda a categoria "Legais, Voluntárias e Específicas" (convênios, mas também
  repasses fundo a fundo do SUS, PNAE, salário-educação, auxílios da LC 173/2020 e transferências
  especiais; não é só convênio).

Fonte: `https://portaldatransparencia.gov.br/download-de-dados/transferencias/AAAAMM`, que
redireciona para o zip em `dadosabertos-download.cgu.gov.br` (um CSV, `;`, latin-1, 2 a 7 MB
por mês, 200 a 500 mil linhas). A página `download-de-dados/transferencias` lista os meses
publicados (`arquivos.push({"ano", "mes", "origem"})`; em 20/10/2026 ia até 2026-10).

Armadilhas (conferidas nos arquivos):
- Uma linha por favorecido x ação x localizador; guardamos só a soma por UF x município x bloco x
  mês (recorte). Nome de coluna com acento. Decimal com vírgula e sem milhar.
- O município vem como código SIAFI e nome; a ligação ao IBGE usa a tabela oficial do Tesouro
  (`lista-de-municipios-do-siafi`), nunca o nome. Favorecido estadual vem sem município.
- Ação "-1" (Sem informação) na categoria constitucional: em 2021 são R$ 23,1 bi de repasses que
  o Portal não classifica, entre eles a complementação ao Fundeb. NÃO se adivinha: o Fundeb
  de 2021 fica sem valor (nunca zero) e o total sem ação entra nos alertas.
- Ficam de fora (por bloco, de propósito): FPE, FPM, IPI-Exp e as demais obrigatórias (valem
  pelo Tesouro), a transferência ao Fundeb de estados e municípios (0C33, o fundo inteiro) e
  as ações constitucionais que não são nenhuma das acima (ex.: a compensação do ICMS de 2023).
- Linha sem UF válida entra com `uf = "ND"` (não regionalizada), para o total fechar com o Portal.
- **WAF**: o Portal responde 405 (página "Human Verification") depois de algumas dezenas de
  pedidos seguidos ao mesmo IP, e 403/405 também para mês não publicado. Um download por vez,
  `PAUSA` segundos entre meses e, no primeiro bloqueio, a carga PARA e registra erro: nada de
  repetir, trocar de IP ou disfarçar o cliente. Mês fora da lista da página nem é pedido.

Coleta mínima: o bruto é o recorte do mês (CSV gz com a soma por UF x município x bloco).
"""

import argparse
import csv
import gzip
import io
import re
import time
import unicodedata
import zipfile
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import FonteIngestao, TransferenciaUniao
from ingestion import comum
from ingestion.tesouro.transferencias import (
    ARQUIVO_TABELA,
    CKAN,
    PACOTE_SIAFI,
    UFS,
    Chave,
    decodificar,
    ler_tabela_siafi,
    sincronizar,
)

FONTE = "portal_transferencias"
FONTE_TABELA = "portal"
URL = "https://portaldatransparencia.gov.br/download-de-dados/transferencias/{ano}{mes:02d}"
PAGINA = "https://portaldatransparencia.gov.br/download-de-dados/transferencias"
ANO_INICIAL = 2019
PAUSA = 20  # segundos entre downloads (o WAF pede verificação humana após ~15 seguidos)
MESES_REVISADOS = 3  # meses recentes que são baixados de novo (o Portal os corrige)
BLOCOS = ("FUNDEB_UNIAO", "ROYALTIES", "LEGAIS_VOLUNTARIAS")
SEM_ACAO = "SEM_ACAO"  # só no recorte: constitucional sem ação (não vai para o banco)
ACOES_FUNDEB = frozenset({"0E36", "00SB"})
ACOES_ROYALTIES = frozenset({"0A53", "0547", "0546", "0223"})
CABECALHO_RECORTE = ["ano", "mes", "uf", "cod_siafi", "municipio", "bloco", "valor"]


class Bloqueio(Exception):
    """O Portal recusou o download (403/405 do WAF): a carga para, sem contornar."""


def _chave_coluna(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


def meses_publicados(pagina: str) -> set[tuple[int, int]]:
    """Os (ano, mês) de Transferências na página de downloads do Portal."""
    return {
        (int(a), int(m))
        for a, m in re.findall(
            r'"ano"\s*:\s*"(\d{4})"\s*,\s*"mes"\s*:\s*"(\d{2})"[^}]*"origem"\s*:\s*"Transferencias"',
            pagina,
        )
    }


def bloco_da_linha(tipo: str, acao: str, nome_acao: str) -> str | None:
    """Em qual bloco entra a linha (None = fica de fora). `tipo` é o TIPO TRANSFERÊNCIA."""
    tipo = _chave_coluna(tipo)
    acao = acao.strip()
    nome = _chave_coluna(nome_acao)
    if acao in ACOES_FUNDEB or nome.startswith("complementacao da uniao ao fundo de manutencao"):
        return "FUNDEB_UNIAO"
    if acao in ACOES_ROYALTIES:
        return "ROYALTIES"
    if tipo.startswith("legais"):
        return "LEGAIS_VOLUNTARIAS"
    if tipo.startswith("constitucionais") and acao in ("-1", ""):
        return SEM_ACAO
    return None


def recortar_mes(arquivo: Path | bytes) -> bytes:
    """Zip do mês -> CSV gz com a soma por (ano, mês, UF, SIAFI, município, bloco)."""
    origem = io.BytesIO(arquivo) if isinstance(arquivo, bytes) else arquivo
    somas: dict[tuple[str, str, str, str, str, str], Decimal] = defaultdict(Decimal)
    with zipfile.ZipFile(origem) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nome) as bruto:
            texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
            leitor = csv.DictReader(texto, delimiter=";")
            leitor.fieldnames = [_chave_coluna(c) for c in leitor.fieldnames or []]
            for linha in leitor:
                bloco = bloco_da_linha(
                    linha.get("tipo transferencia") or "",
                    linha.get("acao") or "",
                    linha.get("nome acao") or "",
                )
                if bloco is None:
                    continue
                periodo = (linha.get("ano / mes") or "").strip()
                if not re.fullmatch(r"\d{6}", periodo):
                    continue
                uf = (linha.get("uf") or "").strip().upper()
                uf = uf if uf in UFS else "ND"
                cod = (linha.get("codigo municipio siafi") or "").strip() if uf != "ND" else ""
                cidade = (linha.get("nome municipio") or "").strip() if cod else ""
                valor = Decimal((linha.get("valor transferido") or "0").strip().replace(",", "."))
                chave = (periodo[:4], periodo[4:], uf, cod, cidade, bloco)
                somas[chave] += valor
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\n")
    escritor.writerow(CABECALHO_RECORTE)
    for chave in sorted(somas):
        if somas[chave] != 0:
            escritor.writerow([*chave[:-1], chave[-1], f"{somas[chave]:.2f}"])
    return gzip.compress(saida.getvalue().encode("utf-8"), mtime=0)


def ler_recorte(payload: bytes) -> list[dict[str, str]]:
    return list(
        csv.DictReader(io.StringIO(gzip.decompress(payload).decode("utf-8")), delimiter=";")
    )


def linhas_do_recorte(
    linhas: list[dict[str, str]], tabela: dict[str, tuple[str, str]]
) -> tuple[dict[Chave, Decimal], set[tuple[int, int]], list[str]]:
    """Recorte -> {(ano, mês, UF, IBGE, bloco): valor}, os meses cobertos e os alertas."""
    avisos: list[str] = []
    soma: dict[Chave, Decimal] = {}
    meses: set[tuple[int, int]] = set()
    nao_casados: dict[tuple[str, str, str], Decimal] = {}
    sem_acao: dict[int, Decimal] = {}
    for r in linhas:
        ano, mes, valor = int(r["ano"]), int(r["mes"]), Decimal(r["valor"])
        meses.add((ano, mes))
        if r["bloco"] == SEM_ACAO:
            sem_acao[ano] = sem_acao.get(ano, Decimal(0)) + valor
            continue
        ibge = None
        if r["cod_siafi"]:
            achado = tabela.get(r["cod_siafi"])
            ibge = achado[1] if achado and achado[0] == r["uf"] else None
            if ibge is None:
                par = (r["cod_siafi"], r["uf"], r["municipio"])
                nao_casados[par] = nao_casados.get(par, Decimal(0)) + valor
        chave = (ano, mes, r["uf"], ibge, r["bloco"])
        soma[chave] = soma.get(chave, Decimal(0)) + valor
    if nao_casados:
        total = sum(nao_casados.values())
        nomes = "; ".join(f"{c}/{u} {n}" for (c, u, n) in sorted(nao_casados))
        avisos.append(
            f"{len(nao_casados)} município(s) do Portal fora da tabela SIAFI x IBGE"
            f" (R$ {total:,.2f}"
            f" ficam só na UF): {nomes}"
        )
    for ano, valor in sorted(sem_acao.items()):
        avisos.append(
            f"{ano}: R$ {valor:,.2f} de repasses constitucionais sem ação identificada no Portal"
            " (não entram em nenhum bloco)"
        )
    return {k: v.quantize(Decimal("0.01")) for k, v in soma.items() if v != 0}, meses, avisos


_TABELA: dict[str, tuple[str, str]] = {}  # lida uma vez por execução


def tabela_siafi(session: Session) -> dict[str, tuple[str, str]]:
    """A tabela SIAFI x IBGE do último recorte do Tesouro carregado (a mesma da outra fonte)."""
    if not _TABELA:
        _TABELA.update(_ler_tabela_siafi(session))
    return _TABELA


def _ler_tabela_siafi(session: Session) -> dict[str, tuple[str, str]]:
    ultimo = session.scalar(
        select(FonteIngestao)
        .where(FonteIngestao.fonte == "tesouro_transferencias", FonteIngestao.status == "ok")
        .order_by(FonteIngestao.iniciado_em.desc(), FonteIngestao.id.desc())
        .limit(1)
    )
    if ultimo is not None and Path(ultimo.arquivo_raw).suffix == ".zip":
        try:
            with zipfile.ZipFile(ultimo.arquivo_raw) as z:
                return ler_tabela_siafi(decodificar(z.read(ARQUIVO_TABELA)))
        except (OSError, KeyError, zipfile.BadZipFile):
            pass
    with comum.criar_cliente() as client:  # sem recorte do Tesouro à mão: baixa a tabela
        client.headers["Accept"] = "*/*"
        pacote = comum.get_json(client, CKAN, {"id": PACOTE_SIAFI})
        url = next(
            r["url"]
            for r in pacote["result"]["resources"]
            if r["url"].lower().endswith("tabmun.csv")
        )
        return ler_tabela_siafi(decodificar(comum.get_bytes(client, url)))


def carregar(session: Session, payload: bytes, ingestao: FonteIngestao) -> int:
    linhas, meses, avisos = linhas_do_recorte(ler_recorte(payload), tabela_siafi(session))
    if not meses or not linhas:
        raise ValueError("Recorte do Portal sem repasses; abortando.")
    t = TransferenciaUniao
    total = 0
    for ano, mes in sorted(meses):
        do_mes = {k: v for k, v in linhas.items() if k[0] == ano and k[1] == mes}
        novas, corrigidas, apagadas = sincronizar(
            session, FONTE_TABELA, [t.ano == ano, t.mes == mes, t.bloco.in_(BLOCOS)], do_mes,
            ingestao.id,
        )  # fmt: skip
        print(
            f"  Portal {ano}-{mes:02d}: {len(do_mes)} linhas ({novas} novas, {corrigidas} "
            f"corrigidas, {apagadas} apagadas)",
            flush=True,
        )
        total += len(do_mes)
    ingestao.alertas = avisos or None
    ingestao.total_fonte = total
    return total


def _registrar_erro(url: str, motivo: str) -> None:
    with SessionLocal() as session:
        session.add(
            FonteIngestao(
                fonte=FONTE, url=url, arquivo_raw="", status="erro",
                alertas=[motivo], concluido_em=datetime.now(UTC),
            )
        )  # fmt: skip
        session.commit()


def baixar(client: httpx.Client, url: str) -> bytes:
    """Baixa o zip do mês (em disco) e devolve só o recorte. 403/405 ou resposta que não é zip
    (a página de verificação do WAF) viram `Bloqueio`."""
    try:
        caminho = comum.baixar_para_arquivo(client, url)
    except httpx.HTTPStatusError as erro:
        if erro.response.status_code in (403, 405):
            raise Bloqueio(f"HTTP {erro.response.status_code} em {url}") from erro
        raise
    try:
        if not zipfile.is_zipfile(caminho):
            raise Bloqueio(f"Resposta que não é zip (verificação do WAF?) em {url}")
        return recortar_mes(caminho)
    finally:
        caminho.unlink(missing_ok=True)


def executar_mes(ano: int, mes: int, de_raw: Path | None = None) -> int:
    url = URL.format(ano=ano, mes=mes)

    def baixar_mes(client: httpx.Client) -> bytes:
        return baixar(client, url)

    try:
        return comum.executar_ingestao(
            FONTE,
            url,
            baixar_mes,
            carregar,
            de_raw=de_raw,
            prefixo_raw=f"{ano}{mes:02d}_",
            extensao_raw=".csv.gz",
            incremental=comum.Incremental(chave=f"{FONTE}:{ano}{mes:02d}"),
        )
    except Bloqueio as erro:
        _registrar_erro(url, str(erro))
        raise


def meses_ja_carregados() -> set[tuple[int, int]]:
    """(ano, mês) com carga ok (ou sem mudança) registrada."""
    with SessionLocal() as session:
        urls = session.scalars(
            select(FonteIngestao.url).where(
                FonteIngestao.fonte == FONTE, FonteIngestao.status.in_(comum.STATUS_SUCESSO)
            )
        )
        achados = (re.search(r"/transferencias/(\d{4})(\d{2})$", u) for u in urls)
        return {(int(m.group(1)), int(m.group(2))) for m in achados if m}


def executar(
    anos: list[int] | int | None = None,
    meses: list[int] | None = None,
    de_raw: Path | None = None,
    refazer: bool = False,
    pausa: float = PAUSA,
) -> int:
    """Carrega os meses publicados. `anos` (+ `meses` opcional): esses meses. Sem `anos`: os
    `MESES_REVISADOS` últimos publicados. Mês antigo já carregado é pulado (`refazer` força).
    Para no primeiro bloqueio e relança."""
    if isinstance(anos, int):  # o acervo chama executar(ano)
        anos = [anos]
    if de_raw is not None:
        achado = re.search(r"(\d{4})(\d{2})_", Path(de_raw).name)
        if achado is None:
            raise SystemExit("Com --de-raw, use um arquivo AAAAMM_*.")
        return executar_mes(int(achado.group(1)), int(achado.group(2)), de_raw)

    publicados = None
    with comum.criar_cliente() as client:
        try:
            resposta = client.get(PAGINA, headers={"Accept": "text/html"})
            if resposta.status_code == 200:
                publicados = meses_publicados(resposta.text) or None
        except httpx.HTTPError:
            pass
    if publicados is None:
        print("  Lista de meses do Portal indisponível; tenta os pedidos e para no bloqueio.")

    if anos:
        pedidos = sorted(
            (a, m) for a in anos for m in (meses or range(1, 13)) if (a, m) >= (ANO_INICIAL, 1)
        )
    else:
        base = sorted(publicados or {(date.today().year, date.today().month)})
        pedidos = base[-MESES_REVISADOS:]
    if publicados is not None:
        fora = [p for p in pedidos if p not in publicados]
        if fora:
            print(f"  Ainda não publicados no Portal: {len(fora)} mês(es), pulados.")
        pedidos = [p for p in pedidos if p in publicados]
    carregados = set() if refazer else meses_ja_carregados()
    recentes = set(sorted(publicados or pedidos)[-MESES_REVISADOS:])
    pedidos = [p for p in pedidos if p not in carregados or p in recentes]

    total = 0
    for i, (ano, mes) in enumerate(pedidos):
        if i:
            time.sleep(pausa)  # um download por vez, com pausa (WAF)
        try:
            total += executar_mes(ano, mes)
        except Bloqueio as erro:
            print(f"  BLOQUEIO do Portal em {ano}-{mes:02d}: {erro}. Carga interrompida.")
            raise
        except httpx.HTTPError as erro:  # falha de rede: para, o resto fica para a próxima
            print(f"  Falha em {ano}-{mes:02d}: {erro}. Carga interrompida.")
            raise
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", help="Anos (todos os meses publicados)")
    parser.add_argument("--mes", type=int, nargs="*", help="Meses (1 a 12) dentro de --ano")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa o recorte de um mês (AAAAMM_*)")
    parser.add_argument("--refazer", action="store_true", help="Baixa de novo meses já carregados")
    parser.add_argument("--pausa", type=float, default=PAUSA, help="Segundos entre downloads")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(args.ano, args.mes, args.de_raw, args.refazer, args.pausa)} linhas")
