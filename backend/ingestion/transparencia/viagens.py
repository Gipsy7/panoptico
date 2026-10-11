"""Viagens a serviço das pessoas da base (Portal da Transparência), somadas por ano.

O Portal publica um ZIP por ano (`viagens/AAAA`, 150 MB com `Viagem`, `Pagamento`, `Passagem`
e `Trecho`; 814 mil viagens em 2025). Só o `Viagem.csv` interessa: uma linha por viagem, com
o CPF do viajante mascarado (`***.123.456-**`; estrangeiros vêm como `ID123456789` e nunca
ligam), situação, período e os valores. Liga pelos 6 dígitos do meio do CPF + nome igual.

Coleta mínima: só as viagens realizadas de pessoas da base, somadas por ano (quantidade,
diárias, passagens, outros gastos e devoluções). Destino, motivo e trechos não ficam: estão
no Portal. Mesma regra de ligação dos cargos (`servidores.py`). Rode depois de
ingestion.pessoas.
"""

import argparse
import csv
import io
import re
import unicodedata
import zipfile
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import Evento, FonteIngestao, Pessoa, PessoaVinculo, ViagemFederalAno
from ingestion import comum
from ingestion.transparencia.servidores import indice_pessoas

FONTE = "cgu_viagens"
URL = "https://portaldatransparencia.gov.br/download-de-dados/viagens/{ano}"
URL_CONSULTA = "https://portaldatransparencia.gov.br/viagens/consulta"
SITUACAO_REALIZADA = "realizada"


def _chave_coluna(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


def _valor(texto: str | None) -> Decimal:
    try:
        return Decimal((texto or "0").strip().replace(".", "").replace(",", "."))
    except InvalidOperation:
        return Decimal(0)


def _data(valor: str | None) -> date | None:
    try:
        dia, mes, ano = (valor or "").strip().split("/")
        return date(int(ano), int(mes), int(dia))
    except ValueError:
        return None


def ler_viagens(arquivo: Path | bytes):
    """Linhas de `Viagem.csv` em fluxo, com os nomes de coluna sem acento e em minúsculas
    (o Portal acentua e já mudou capitalização)."""
    origem = io.BytesIO(arquivo) if isinstance(arquivo, bytes) else arquivo
    with zipfile.ZipFile(origem) as z:
        nome = next(n for n in z.namelist() if n.endswith("_Viagem.csv"))
        with z.open(nome) as bruto:
            texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
            leitor = csv.DictReader(texto, delimiter=";")
            leitor.fieldnames = [_chave_coluna(c) for c in leitor.fieldnames or []]
            yield from leitor


def somar(linhas, indice: dict[tuple[str, str], set[int]]) -> list[dict[str, Any]]:
    """Soma por (pessoa, ano do início da viagem) as viagens realizadas de pessoas da base."""
    somas: dict[tuple[int, int], dict[str, Any]] = defaultdict(
        lambda: {"viagens": 0, "diarias": Decimal(0), "passagens": Decimal(0),
                 "outros": Decimal(0), "devolucao": Decimal(0), "ultima_viagem": None}
    )  # fmt: skip
    for linha in linhas:
        if _chave_coluna(linha.get("situacao") or "") != SITUACAO_REALIZADA:
            continue
        meio = re.sub(r"\D", "", linha.get("cpf viajante") or "")
        if len(meio) != 6:
            continue
        candidatos = indice.get((meio, comum.chave_nome(linha.get("nome"))), set())
        inicio = _data(linha.get("periodo - data de inicio"))
        if len(candidatos) != 1 or inicio is None:
            continue
        soma = somas[(next(iter(candidatos)), inicio.year)]
        soma["viagens"] += 1
        soma["diarias"] += _valor(linha.get("valor diarias"))
        soma["passagens"] += _valor(linha.get("valor passagens"))
        soma["outros"] += _valor(linha.get("valor outros gastos"))
        soma["devolucao"] += _valor(linha.get("valor devolucao"))
        if soma["ultima_viagem"] is None or inicio > soma["ultima_viagem"]:
            soma["ultima_viagem"] = inicio
    return [{"pessoa_id": p, "ano": a, **v} for (p, a), v in sorted(somas.items())]


def brl(valor: Decimal) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def descricao(s: dict[str, Any]) -> str:
    n = s["viagens"]
    partes = [f"{n} {'viagem' if n == 1 else 'viagens'} a serviço em {s['ano']}"]
    gastos = [
        f"{brl(s['diarias'])} em diárias",
        f"{brl(s['passagens'])} em passagens",
    ]
    if s["outros"]:
        gastos.append(f"{brl(s['outros'])} em outros gastos")
    texto = f"{partes[0]}: {', '.join(gastos[:-1])} e {gastos[-1]}"
    if s["devolucao"]:
        texto += f", com {brl(s['devolucao'])} devolvidos"
    return texto + " (Portal da Transparência, viagens a serviço)."


def gravar(session: Session, somas: list[dict[str, Any]], ano: int, ingestao_id: int | None) -> int:
    """Troca as somas do ano e refaz os eventos de viagens desta fonte."""
    session.execute(delete(ViagemFederalAno).where(ViagemFederalAno.ano == ano))
    if somas:
        session.execute(insert(ViagemFederalAno), somas)
    session.flush()
    session.execute(delete(PessoaVinculo).where(PessoaVinculo.fonte == FONTE))  # eventos em cascata
    total = 0
    for s in session.scalars(select(ViagemFederalAno).order_by(ViagemFederalAno.id)):
        id_externo = f"{s.ano}:{s.pessoa_id}"
        vinculo_id = session.scalar(
            insert(PessoaVinculo)
            .values(pessoa_id=s.pessoa_id, fonte=FONTE, id_externo=id_externo,
                    regra="cpf_parcial_nome")
            .returning(PessoaVinculo.id)
        )  # fmt: skip
        session.execute(
            insert(Evento).values(
                pessoa_id=s.pessoa_id,
                vinculo_id=vinculo_id,
                data=s.ultima_viagem,
                tipo="viagem_federal",
                descricao=descricao(
                    {
                        c: getattr(s, c)
                        for c in ("ano", "viagens", "diarias", "passagens", "outros", "devolucao")
                    }
                ),  # fmt: skip
                orgao="Portal da Transparência",
                fonte=FONTE,
                id_externo=id_externo,
                fonte_url=URL_CONSULTA,
                ingestao_id=ingestao_id,
            )
        )
        total += 1
    return total


def executar(ano: int, de_raw: Path | None = None) -> int:
    url = URL.format(ano=ano)

    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, url)

    def carregar(session: Session, payload: Path | bytes, ingestao: FonteIngestao) -> int:
        pessoas = session.execute(select(Pessoa.id, Pessoa.cpf, Pessoa.chave_nome)).all()
        linhas = comum.ContaLinhas(ler_viagens(payload))
        somas = somar(linhas, indice_pessoas(pessoas))
        if linhas.total == 0:
            raise RuntimeError(f"Viagens de {ano} vazias: nada alterado.")
        comum.conferir_carga(ingestao, total_fonte=linhas.total)
        total = gravar(session, somas, ano, ingestao.id)
        print(
            f"  {ano}: {linhas.total} viagens no arquivo; {sum(s['viagens'] for s in somas)} "
            f"realizadas de {len({s['pessoa_id'] for s in somas})} pessoas da base"
        )
        return total

    return comum.executar_ingestao(
        FONTE, url, baixar, carregar, de_raw=de_raw, prefixo_raw=f"{ano}_",
        incremental=comum.Incremental(chave=f"{FONTE}:{ano}", sonda=url,
                                      contexto=comum.contexto_pessoas),
    )  # fmt: skip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, required=True)
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um ZIP já baixado")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(args.ano, args.de_raw)} somas por pessoa e ano")
