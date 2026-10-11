"""Cartão de pagamento do governo federal (CPGF) das pessoas da base (Portal da Transparência).

O Portal publica um ZIP por mês (`cpgf/AAAAMM`, ~300 KB, um CSV com cada transação: órgão,
unidade gestora, portador, favorecido, tipo, data e valor). O portador vem com CPF mascarado
(`***.123.456-**`): liga pelos 6 dígitos do meio + nome igual (a mesma regra forte de
`servidores.py`). Portador sem CPF parcial (só o nome, ou "-2"/"Sem informação") NÃO liga:
nome sozinho não é ligação forte.

Coleta mínima: só as transações de portadores da base, somadas por pessoa x órgão x mês do
extrato (quantidade, total e parte sacada em dinheiro). Favorecido e transação individual não
ficam: estão no Portal. Evento por pessoa x órgão x ano na linha do tempo. Rode depois de
ingestion.pessoas.
"""

import argparse
import csv
import io
import re
import time
import zipfile
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.models import CpgfPortadorMes, Evento, FonteIngestao, Pessoa, PessoaVinculo
from ingestion import comum
from ingestion.transparencia.servidores import indice_pessoas
from ingestion.transparencia.viagens import _chave_coluna, _valor, brl

FONTE = "cgu_cpgf"
URL = "https://portaldatransparencia.gov.br/download-de-dados/cpgf/{ano}{mes:02d}"
PAGINA = "https://portaldatransparencia.gov.br/download-de-dados/cpgf"
URL_CONSULTA = "https://portaldatransparencia.gov.br/cartoes/consulta"
SUFIXO_ORGAO = " - Unidades com vínculo direto"
PAUSA = 5  # segundos entre meses: o Portal pede verificação humana (405) após ~15 pedidos


def meses_publicados(pagina: str) -> set[tuple[int, int]]:
    """Os (ano, mês) de CPGF na página de downloads do Portal (o último costuma ficar uns
    dois meses atrás; pedir um mês não publicado devolve 405, igual ao bloqueio anti-robô)."""
    return {
        (int(a), int(m))
        for a, m in re.findall(
            r'"ano"\s*:\s*"(\d{4})",\s*"mes"\s*:\s*"(\d{2})"[^}]*"origem"\s*:\s*"CPGF"', pagina
        )
    }


def ler_cpgf(arquivo: Path | bytes):
    """Linhas do CSV do mês, com os nomes de coluna sem acento e em minúsculas."""
    origem = io.BytesIO(arquivo) if isinstance(arquivo, bytes) else arquivo
    with zipfile.ZipFile(origem) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nome) as bruto:
            texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
            leitor = csv.DictReader(texto, delimiter=";")
            leitor.fieldnames = [_chave_coluna(c) for c in leitor.fieldnames or []]
            yield from leitor


def somar(linhas, indice: dict[tuple[str, str], set[int]]) -> list[dict[str, Any]]:
    """Soma por (pessoa, órgão, ano e mês do extrato) as transações de portadores da base."""
    somas: dict[tuple[int, str, int, int], dict[str, Any]] = defaultdict(
        lambda: {"transacoes": 0, "total": Decimal(0), "saques": Decimal(0)}
    )
    for linha in linhas:
        meio = re.sub(r"\D", "", linha.get("cpf portador") or "")
        if len(meio) != 6:  # sem CPF parcial (só nome, "-2"...): não liga
            continue
        candidatos = indice.get((meio, comum.chave_nome(linha.get("nome portador"))), set())
        try:
            ano, mes = int(linha["ano extrato"]), int(linha["mes extrato"])
        except (KeyError, TypeError, ValueError):
            continue
        orgao = (linha.get("nome orgao") or "").strip().removesuffix(SUFIXO_ORGAO)
        if len(candidatos) != 1 or not orgao:
            continue
        valor = _valor(linha.get("valor transacao"))
        soma = somas[(next(iter(candidatos)), orgao[:160], ano, mes)]
        soma["transacoes"] += 1
        soma["total"] += valor
        if "SAQUE" in (linha.get("transacao") or "").upper():
            soma["saques"] += valor
    return [
        {"pessoa_id": p, "orgao": o, "ano": a, "mes": m, **v}
        for (p, o, a, m), v in sorted(somas.items())
    ]


def descricao(orgao: str, ano: int, transacoes: int, total: Decimal, saques: Decimal) -> str:
    n = f"{transacoes} {'transação' if transacoes == 1 else 'transações'}"
    texto = (
        f"Portador(a) de cartão de pagamento do governo federal em {orgao}: "
        f"{n} em {ano}, {brl(total)} no total"
    )
    if saques:
        texto += f" ({brl(saques)} em saques em dinheiro)"
    return texto + " (Portal da Transparência, CPGF)."


def gravar(
    session: Session, somas: list[dict[str, Any]], ano: int, mes: int, ingestao_id: int | None
) -> int:
    """Troca as somas do mês e refaz os eventos por pessoa x órgão x ano."""
    session.execute(
        delete(CpgfPortadorMes).where(CpgfPortadorMes.ano == ano, CpgfPortadorMes.mes == mes)
    )
    if somas:
        session.execute(insert(CpgfPortadorMes), somas)
    session.flush()
    session.execute(delete(PessoaVinculo).where(PessoaVinculo.fonte == FONTE))  # eventos em cascata
    consulta = (
        select(
            CpgfPortadorMes.pessoa_id,
            CpgfPortadorMes.orgao,
            CpgfPortadorMes.ano,
            func.max(CpgfPortadorMes.mes),
            func.sum(CpgfPortadorMes.transacoes),
            func.sum(CpgfPortadorMes.total),
            func.sum(CpgfPortadorMes.saques),
        )
        .group_by(CpgfPortadorMes.pessoa_id, CpgfPortadorMes.orgao, CpgfPortadorMes.ano)
        .order_by(CpgfPortadorMes.pessoa_id, CpgfPortadorMes.ano, CpgfPortadorMes.orgao)
    )
    total = 0
    for pessoa_id, orgao, a, ultimo_mes, n, soma, saques in session.execute(consulta).all():
        id_externo = f"{a}:{pessoa_id}:{orgao[:60]}"
        vinculo_id = session.scalar(
            insert(PessoaVinculo)
            .values(pessoa_id=pessoa_id, fonte=FONTE, id_externo=id_externo,
                    regra="cpf_parcial_nome")
            .returning(PessoaVinculo.id)
        )  # fmt: skip
        session.execute(
            insert(Evento).values(
                pessoa_id=pessoa_id,
                vinculo_id=vinculo_id,
                data=date(a, ultimo_mes, 1),
                tipo="cartao_corporativo",
                descricao=descricao(orgao, a, int(n), soma, saques),
                orgao=orgao,
                fonte=FONTE,
                id_externo=id_externo,
                fonte_url=URL_CONSULTA,
                ingestao_id=ingestao_id,
            )
        )
        total += 1
    return total


def executar_mes(ano: int, mes: int, de_raw: Path | None = None) -> int:
    url = URL.format(ano=ano, mes=mes)

    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, url)

    def carregar(session: Session, payload: Path | bytes, ingestao: FonteIngestao) -> int:
        pessoas = session.execute(select(Pessoa.id, Pessoa.cpf, Pessoa.chave_nome)).all()
        linhas = comum.ContaLinhas(ler_cpgf(payload))
        somas = somar(linhas, indice_pessoas(pessoas))
        comum.conferir_carga(ingestao, total_fonte=linhas.total)
        total = gravar(session, somas, ano, mes, ingestao.id)
        print(
            f"  {ano}-{mes:02d}: {linhas.total} transações no arquivo; "
            f"{sum(s['transacoes'] for s in somas)} de {len({s['pessoa_id'] for s in somas})} "
            f"portadores da base"
        )
        return total

    return comum.executar_ingestao(
        FONTE, url, baixar, carregar, de_raw=de_raw, prefixo_raw=f"{ano}{mes:02d}_",
        incremental=comum.Incremental(chave=f"{FONTE}:{ano}{mes:02d}", sonda=url,
                                      contexto=comum.contexto_pessoas),
    )  # fmt: skip


def executar(
    ano: int | None = None,
    mes: int | None = None,
    de_raw: Path | None = None,
    a_partir_de: int = 1,
    ultimos: int = 3,
) -> int:
    """Um mês (`ano` e `mes`), um ano inteiro (`ano`) ou, sem nada, os `ultimos` meses
    publicados."""
    if mes is None and de_raw is not None:
        achado = re.search(r"(\d{4})(\d{2})_", Path(de_raw).name)
        if achado is None:
            raise SystemExit("Com --de-raw, use o nome AAAAMM_* ou informe --ano e --mes.")
        ano, mes = ano or int(achado.group(1)), int(achado.group(2))
    if ano is not None and mes is not None:
        return executar_mes(ano, mes, de_raw)
    with comum.criar_cliente() as client:
        resposta = client.get(PAGINA, headers={"Accept": "text/html"})
        resposta.raise_for_status()
    publicados = sorted(meses_publicados(resposta.text))
    if ano is None:
        escolhidos = publicados[-ultimos:]
    else:
        escolhidos = [(a, m) for a, m in publicados if a == ano and m >= a_partir_de]
    total = 0
    for a, m in escolhidos:
        total += executar_mes(a, m)  # se o Portal bloquear (405), o erro sobe: não insiste
        time.sleep(PAUSA)
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, help="Sem --ano: os 3 últimos meses publicados")
    parser.add_argument("--mes", type=int)
    parser.add_argument("--a-partir-de", type=int, default=1, help="Pula os meses anteriores")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um ZIP já baixado")
    args = parser.parse_args()
    total = executar(args.ano, args.mes, args.de_raw, args.a_partir_de)
    print(f"{FONTE}: {total} somas por pessoa, órgão e mês")
