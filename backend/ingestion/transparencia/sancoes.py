"""Sanções da CGU a pessoas físicas (CEIS, CNEP e CEAF), só das pessoas que já temos,
gravadas como eventos da linha do tempo.

- CEIS: inidôneos e impedidos de contratar com o poder público. A maior parte das
  pessoas físicas são condenações por improbidade repassadas pelo CNJ. CPF completo.
- CNEP: punições da Lei Anticorrupção (quase só empresas). CPF completo.
- CEAF: servidores federais expulsos (demissão, cassação de aposentadoria, destituição).
  CPF mascarado (***.123.456-**): liga pelos 6 dígitos do meio + nome igual.

Empresas sancionadas ficam de fora por enquanto (coleta mínima): entram quando houver
o cruzamento com fornecedores e sócios. Rode depois de ingestion.pessoas.
"""

import argparse
import csv
import io
import re
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import Evento, FonteIngestao, Pessoa, PessoaVinculo
from ingestion import comum
from ingestion.normalizar import numero_cnj

FONTE = "cgu_sancoes"
URL = "https://portaldatransparencia.gov.br/download-de-dados/{cadastro}/{dia:%Y%m%d}"
URL_PAGINA = "https://portaldatransparencia.gov.br/download-de-dados/{cadastro}"
CADASTROS = ("ceis", "cnep", "ceaf")
NOME_CADASTRO = {
    "CEIS": "Cadastro de Empresas e Pessoas Inidôneas e Suspensas (CEIS)",
    "CNEP": "Cadastro Nacional de Empresas Punidas (CNEP)",
    "CEAF": "Cadastro de Expulsões da Administração Federal (CEAF)",
}
SEM_INFORMACAO = {"", "sem informação", "sem informacao"}


def _texto(valor: str | None) -> str | None:
    valor = (valor or "").strip()
    return None if valor.lower() in SEM_INFORMACAO else valor


def _data(valor: str | None) -> date | None:
    try:
        dia, mes, ano = (valor or "").strip().split("/")
        return date(int(ano), int(mes), int(dia))
    except ValueError:
        return None


def fundamentos(texto: str | None) -> str | None:
    """'LEI 8429 - ART. 12 - INDEPENDENTEMENTE DAS...;;LEI 12846 - ART. 5º, III - ...' ->
    'LEI 8429 - ART. 12; LEI 12846 - ART. 5º, III': só a norma e o artigo de cada item."""
    itens = [i.strip() for i in re.split(r";+", texto or "") if i.strip()]
    curtos = []
    for item in itens:
        curto = " - ".join(item.split(" - ")[:2])
        if curto not in curtos:
            curtos.append(curto)
    return "; ".join(curtos) or None


def normalizar(cadastro: str, linhas: Any) -> list[dict[str, Any]]:
    """Só pessoas físicas. CPF completo (CEIS, CNEP) ou os 6 dígitos do meio (CEAF)."""
    registros = []
    for linha in linhas:
        if (linha.get("TIPO DE PESSOA") or "").strip() != "F":
            continue
        bruto = (linha.get("CPF OU CNPJ DO SANCIONADO") or "").strip()
        digitos = re.sub(r"\D", "", bruto)
        cpf = digitos if len(digitos) == 11 else None
        meio = digitos if "*" in bruto and len(digitos) == 6 else None
        if not cpf and not meio:
            continue
        processo = linha.get("NÚMERO DO PROCESSO")
        registros.append(
            {
                "cadastro": cadastro,
                "codigo": (linha.get("CÓDIGO DA SANÇÃO") or "").strip(),
                "cpf": cpf,
                "cpf_meio": meio or (cpf[3:9] if cpf else None),
                "nome": (linha.get("NOME DO SANCIONADO") or "").strip(),
                "categoria": _texto(linha.get("CATEGORIA DA SANÇÃO")) or "Sanção",
                "orgao": _texto(linha.get("ÓRGÃO SANCIONADOR")),
                "processo": numero_cnj(processo) or (_texto(processo) or "")[:40] or None,
                "inicio": _data(linha.get("DATA INÍCIO SANÇÃO")),
                "fim": _data(linha.get("DATA FINAL SANÇÃO")),
                "fundamentos": fundamentos(linha.get("FUNDAMENTAÇÃO LEGAL")),
            }
        )
    return registros


def ler_zip(payload: bytes, cadastro: str) -> list[dict[str, str]]:
    """O bruto é um zip com o zip de cada cadastro (como veio do Portal)."""
    with zipfile.ZipFile(io.BytesIO(payload)) as externo:
        interno = zipfile.ZipFile(io.BytesIO(externo.read(f"{cadastro}.zip")))
    with interno, interno.open(interno.namelist()[0]) as arquivo:
        texto = io.TextIOWrapper(arquivo, encoding="latin-1", newline="")
        return list(csv.DictReader(texto, delimiter=";"))


def situacao(r: dict[str, Any], hoje: date) -> str:
    if r["fim"] is None:
        return "sem data final informada"
    if r["fim"] < hoje:
        return f"encerrada em {r['fim']:%d/%m/%Y}"
    return f"vigente até {r['fim']:%d/%m/%Y}"


def descricao(r: dict[str, Any]) -> str:
    partes = [r["categoria"]]
    if r["orgao"]:
        partes[0] += f", aplicada por {r['orgao']}"
    if r["fundamentos"]:
        partes.append(f"Fundamento: {r['fundamentos']}")
    partes.append(f"Registro nº {r['codigo']} no {NOME_CADASTRO[r['cadastro']]}, da CGU")
    return ". ".join(partes) + "."


def ligar(
    registros: list[dict[str, Any]], pessoas: list[tuple[int, str | None, str]]
) -> list[tuple[dict[str, Any], int, str]]:
    """(registro, pessoa, regra) só por chave forte: CPF completo igual, ou 6 dígitos do
    meio + nome igual. Sem CPF na pessoa, não liga (o nome sozinho não basta)."""
    por_cpf = {cpf: id_ for id_, cpf, _ in pessoas if cpf}
    por_meio_nome: dict[tuple[str, str], set[int]] = {}
    for id_, cpf, chave_nome in pessoas:
        if cpf:
            por_meio_nome.setdefault((cpf[3:9], chave_nome), set()).add(id_)
    ligados = []
    for r in registros:
        if r["cpf"] and r["cpf"] in por_cpf:
            ligados.append((r, por_cpf[r["cpf"]], "cpf"))
            continue
        candidatos = por_meio_nome.get((r["cpf_meio"], comum.chave_nome(r["nome"])), set())
        if not r["cpf"] and len(candidatos) == 1:
            ligados.append((r, next(iter(candidatos)), "cpf_parcial_nome"))
    return ligados


def gravar(session: Session, ligados: list, ingestao_id: int | None, hoje: date) -> int:
    """Substitui as sanções ligadas (vínculos e eventos desta fonte)."""
    session.execute(delete(PessoaVinculo).where(PessoaVinculo.fonte == FONTE))  # eventos em cascata
    for r, pessoa_id, regra in ligados:
        id_externo = f"{r['cadastro']}:{r['codigo']}"
        vinculo_id = session.scalar(
            insert(PessoaVinculo)
            .values(pessoa_id=pessoa_id, fonte=FONTE, id_externo=id_externo, regra=regra)
            .returning(PessoaVinculo.id)
        )
        session.execute(
            insert(Evento).values(
                pessoa_id=pessoa_id,
                vinculo_id=vinculo_id,
                data=r["inicio"],
                tipo="sancao",
                descricao=descricao(r),
                orgao=(r["orgao"] or "")[:120] or None,
                numero_processo=r["processo"],
                situacao=situacao(r, hoje),
                fonte=FONTE,
                id_externo=id_externo,
                fonte_url=URL_PAGINA.format(cadastro=r["cadastro"].lower()),
                ingestao_id=ingestao_id,
            )
        )
    return len(ligados)


def baixar_cadastros(client: httpx.Client, hoje: date) -> bytes:
    """Os três cadastros do dia (ou do último dia publicado, até 7 dias antes)."""
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        for cadastro in CADASTROS:
            for atraso in range(8):
                try:
                    conteudo = comum.get_bytes(
                        client, URL.format(cadastro=cadastro, dia=hoje - timedelta(days=atraso))
                    )
                    break
                except httpx.HTTPStatusError as erro:
                    if erro.response.status_code != 404 or atraso == 7:
                        raise
            z.writestr(f"{cadastro.upper()}.zip", conteudo)
    return saida.getvalue()


def executar(de_raw: Path | None = None) -> int:
    hoje = date.today()

    def carregar(session: Session, payload: bytes, ingestao: FonteIngestao) -> int:
        registros = [
            r for c in CADASTROS for r in normalizar(c.upper(), ler_zip(payload, c.upper()))
        ]
        if not registros:
            raise RuntimeError("Nenhuma sanção a pessoa física nos arquivos: nada alterado.")
        pessoas = session.execute(select(Pessoa.id, Pessoa.cpf, Pessoa.chave_nome)).all()
        ligados = ligar(registros, pessoas)
        total = gravar(session, ligados, ingestao.id, hoje)
        print(f"  {len(registros)} sanções a pessoas físicas; {total} de pessoas que temos")
        return total

    return comum.executar_ingestao(
        FONTE, URL_PAGINA.format(cadastro="ceis"), lambda c: baixar_cadastros(c, hoje), carregar,
        de_raw=de_raw,
    )  # fmt: skip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} sanções ligadas")
