"""Viagens a serviço das pessoas da base (Portal da Transparência), somadas por ano.

O Portal publica um ZIP por ano (`viagens/AAAA`, 150 MB com `Viagem`, `Pagamento`, `Passagem`
e `Trecho`; 814 mil viagens em 2025). Só o `Viagem.csv` interessa: uma linha por viagem, com
o CPF do viajante mascarado (`***.123.456-**`; estrangeiros vêm como `ID123456789` e nunca
ligam), situação, período e os valores. Liga pelos 6 dígitos do meio do CPF + nome igual.

Cargo de natureza especial (ministros, secretários-executivos...): o cadastro SIAPE não os traz,
mas a coluna `Função` das viagens vem como `CNE-0001` para eles, com o órgão superior. Disso sai
um cargo federal (`servidor_federal`, origem "viagens") com o órgão e o período observado
(primeira e última viagem com a função): é o que o registro de viagens mostra, não a data de
posse nem de saída.

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
from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import (
    Evento,
    FonteIngestao,
    Pessoa,
    PessoaVinculo,
    ServidorFederal,
    ViagemFederalAno,
)
from ingestion import comum
from ingestion.transparencia.servidores import indice_pessoas

FONTE = "cgu_viagens"
URL = "https://portaldatransparencia.gov.br/download-de-dados/viagens/{ano}"
URL_CONSULTA = "https://portaldatransparencia.gov.br/viagens/consulta"
SITUACAO_REALIZADA = "realizada"
FONTE_CNE = "cgu_viagens_cne"
ORIGEM_CNE = "viagens"
SUFIXO_ORGAO = " - Unidades com vínculo direto"


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


def somar(
    linhas,
    indice: dict[tuple[str, str], set[int]],
    cargos: dict[tuple[int, str], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Soma por (pessoa, ano do início da viagem) as viagens realizadas de pessoas da base.
    Se `cargos` vier, acumula nele os cargos de natureza especial (função `CNE-...`) por
    (pessoa, órgão superior), com a primeira e a última viagem."""
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
        pessoa_id = next(iter(candidatos))
        funcao = (linha.get("funcao") or "").strip().upper()
        orgao = (linha.get("nome do orgao superior") or "").strip().removesuffix(SUFIXO_ORGAO)
        if cargos is not None and funcao.startswith("CNE") and orgao:
            cargo = cargos.setdefault(
                (pessoa_id, orgao[:120]), {"primeira": inicio, "ultima": inicio}
            )
            cargo["primeira"] = min(cargo["primeira"], inicio)
            cargo["ultima"] = max(cargo["ultima"], inicio)
        soma = somas[(pessoa_id, inicio.year)]
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


def periodo(primeira: date, ultima: date) -> str:
    if primeira == ultima:
        return f"em {primeira:%d/%m/%Y}"
    return f"de {primeira:%d/%m/%Y} a {ultima:%d/%m/%Y}"


def gravar_cargos(session: Session, cargos: dict[tuple[int, str], dict[str, Any]]) -> None:
    """Acumula os cargos de natureza especial (a primeira e a última viagem valem entre os
    anos já carregados)."""
    for (pessoa_id, orgao), c in cargos.items():
        r = {
            "pessoa_id": pessoa_id, "id_externo": f"viagens:CNE:{pessoa_id}:{orgao[:50]}",
            "origem": ORIGEM_CNE, "sigla": "CNE", "funcao": "Cargo de natureza especial",
            "orgao": orgao, "orgao_superior": orgao,
        }  # fmt: skip
        stmt = pg_insert(ServidorFederal).values(
            **r, primeiro_mes=c["primeira"], ultimo_mes=c["ultima"]
        )
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=["id_externo"],
                set_={
                    "primeiro_mes": func.least(ServidorFederal.primeiro_mes, c["primeira"]),
                    "ultimo_mes": func.greatest(ServidorFederal.ultimo_mes, c["ultima"]),
                },
            )
        )


def publicar_cargos(session: Session, ingestao_id: int | None) -> int:
    """Refaz vínculos e eventos dos cargos de natureza especial (todo o histórico)."""
    session.execute(delete(PessoaVinculo).where(PessoaVinculo.fonte == FONTE_CNE))
    total = 0
    cargos = select(ServidorFederal).where(ServidorFederal.origem == ORIGEM_CNE)
    for s in session.scalars(cargos.order_by(ServidorFederal.id)):
        vinculo_id = session.scalar(
            insert(PessoaVinculo)
            .values(pessoa_id=s.pessoa_id, fonte=FONTE_CNE, id_externo=s.id_externo,
                    regra="cpf_parcial_nome")
            .returning(PessoaVinculo.id)
        )  # fmt: skip
        session.execute(
            insert(Evento).values(
                pessoa_id=s.pessoa_id,
                vinculo_id=vinculo_id,
                data=s.primeiro_mes,
                tipo="cargo_federal",
                descricao=(
                    f"Exerceu cargo de natureza especial em {s.orgao} (registro de viagens a "
                    f"serviço, {periodo(s.primeiro_mes, s.ultimo_mes)})."
                ),
                orgao=s.orgao,
                situacao="período em que consta nas viagens",
                fonte=FONTE_CNE,
                id_externo=s.id_externo,
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
        cargos: dict[tuple[int, str], dict[str, Any]] = {}
        somas = somar(linhas, indice_pessoas(pessoas), cargos)
        if linhas.total == 0:
            raise RuntimeError(f"Viagens de {ano} vazias: nada alterado.")
        comum.conferir_carga(ingestao, total_fonte=linhas.total)
        total = gravar(session, somas, ano, ingestao.id)
        gravar_cargos(session, cargos)
        session.flush()
        publicar_cargos(session, ingestao.id)
        print(
            f"  {ano}: {linhas.total} viagens no arquivo; {sum(s['viagens'] for s in somas)} "
            f"realizadas de {len({s['pessoa_id'] for s in somas})} pessoas da base; "
            f"{len(cargos)} cargos de natureza especial"
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
