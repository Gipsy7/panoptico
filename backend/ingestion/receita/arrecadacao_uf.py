"""Arrecadação federal por estado e mês (Receita Federal, dados abertos).

Um CSV só (`arrecadacao-estado.csv`, ~2,4 MB, latin-1, separador `;`) com uma linha por
ano, mês e UF desde 2000 e uma coluna por tributo. Guardamos de 2019 em diante.

Armadilhas (conferidas no arquivo):
- O servidor devolve 401 se o pedido tiver "Accept: application/json"; peça como CSV.
- Mês vem por extenso e com acento ("Março"); decimal com vírgula e, às vezes, sinal negativo.
- Célula vazia = sem arrecadação naquele tributo (soma como zero).
- `total` é a soma de todas as colunas de tributo, inclusive a receita previdenciária e as
  administradas por outros órgãos; `previdencia` é a coluna RECEITA PREVIDENCIÁRIA. As
  colunas "- PRÓPRIA" e "- DEMAIS" da previdência vêm zeradas no arquivo, então não duplicam.
- A conta é por domicílio fiscal do contribuinte (onde a empresa ou a pessoa declara), não
  por onde a atividade acontece. Entre fev/2025 e jan/2026 a Receita passou a registrar no DF
  boa parte da arrecadação do país (receita previdenciária do DF de ~R$ 2,5 bi/mês para
  ~R$ 18 bi/mês; DF 2024: R$ 184 bi; 2025: R$ 583 bi). O número bate com a fonte e não é
  ajustado; o site precisa dizer isso.
"""

import argparse
import csv
import io
import unicodedata
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import ArrecadacaoUF, FonteIngestao
from ingestion import comum

FONTE = "receita_arrecadacao_uf"
URL = "https://www.gov.br/receitafederal/dados/arrecadacao-estado.csv"
ANO_INICIAL = 2019
MESES = {
    nome: i
    for i, nome in enumerate(
        "janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro"
        " dezembro".split(),
        1,
    )
}
COLUNA_PREVIDENCIA = "RECEITA PREVIDENCIARIA"


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c))


def numero(texto: str) -> Decimal:
    """'1.234,56' -> Decimal('1234.56'); vazio -> 0."""
    texto = texto.strip().replace("R$", "").strip()
    if not texto or texto == "-":
        return Decimal(0)
    return Decimal(texto.replace(".", "").replace(",", "."))


def normalizar(payload: bytes, ano_inicial: int = ANO_INICIAL) -> list[dict[str, Any]]:
    """CSV bruto -> uma linha por UF, ano e mês (a partir de `ano_inicial`)."""
    leitor = csv.reader(io.StringIO(payload.decode("latin-1")), delimiter=";")
    cabecalho = [_sem_acento(c).strip().upper() for c in next(leitor)]
    if cabecalho[:3] != ["ANO", "MES", "UF"] or COLUNA_PREVIDENCIA not in cabecalho:
        raise ValueError(f"Cabeçalho inesperado no CSV da Receita: {cabecalho[:4]}")
    i_prev = cabecalho.index(COLUNA_PREVIDENCIA)
    linhas = []
    for r in leitor:
        if len(r) < len(cabecalho) or not r[0].strip().isdigit():
            continue
        ano = int(r[0])
        if ano < ano_inicial:
            continue
        mes = MESES[_sem_acento(r[1]).strip().lower()]
        linhas.append(
            {
                "uf": r[2].strip(),
                "ano": ano,
                "mes": mes,
                "total": sum((numero(x) for x in r[3 : len(cabecalho)]), Decimal(0)),
                "previdencia": numero(r[i_prev]),
            }
        )
    return linhas


def carregar(session: Session, payload: bytes, ingestao: FonteIngestao) -> int:
    linhas = normalizar(payload)
    anos = sorted({linha["ano"] for linha in linhas})
    if len(linhas) < 27 * 12 or len({linha["uf"] for linha in linhas}) != 27:
        raise ValueError(f"Só {len(linhas)} linhas de arrecadação; abortando.")
    session.execute(delete(ArrecadacaoUF).where(ArrecadacaoUF.ano.in_(anos)))
    for inicio in range(0, len(linhas), 2000):
        session.execute(
            insert(ArrecadacaoUF),
            [{**linha, "ingestao_id": ingestao.id} for linha in linhas[inicio : inicio + 2000]],
        )
    return len(linhas)


def baixar(client: httpx.Client) -> bytes:
    # O gov.br (Plone) responde 401 a "Accept: application/json", o padrão do cliente comum:
    # é negociação de conteúdo, não bloqueio. O arquivo é CSV e se pede como CSV.
    client.headers["Accept"] = "text/csv, */*"
    return comum.get_bytes(client, URL)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(
        FONTE,
        URL,
        baixar,
        carregar,
        de_raw=de_raw,
        extensao_raw=".csv.gz",
        incremental=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} linhas")
