"""Cargos de confiança no governo federal das pessoas da base (Portal da Transparência).

O Portal publica, por mês, o cadastro de todos os servidores do SIAPE (`AAAAMM_Servidores_
SIAPE`, ZIP de ~80 MB com `Cadastro`, `Remuneracao`, `Afastamentos` e `Observacoes`, ~780 mil
linhas de cadastro). O CPF vem mascarado (`***.123.456-**`): liga pelos 6 dígitos do meio +
nome igual (regra forte `cpf_parcial_nome`, a mesma das sanções do CEAF).

Coleta mínima: o cadastro é lido em fluxo e só ficam as linhas de pessoas da base com cargo
de confiança (cargo comissionado, função comissionada e de direção; não a função gratificada
de servidor de carreira). Cada registro guarda o mês em que apareceu pela primeira e pela
última vez, então carregar um mês novo acumula o histórico de entradas e saídas. A
remuneração fica de fora (169 MB a mais por mês, e o valor do cargo não responde a nada que
o site mostre hoje). Rode depois de ingestion.pessoas.
"""

import argparse
import csv
import io
import re
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Evento, FonteIngestao, Pessoa, PessoaVinculo, ServidorFederal
from ingestion import comum

FONTE = "cgu_servidores"
PAGINA = "https://portaldatransparencia.gov.br/download-de-dados/servidores"
URL = PAGINA + "/{ano}{mes:02d}_Servidores_SIAPE"
URL_SERVIDOR = "https://portaldatransparencia.gov.br/servidores/{id}"
# Siglas de cargo/função de confiança no SIAPE (campo SIGLA_FUNCAO). Ficam de fora as
# funções gratificadas (FG, GF, FGR...) e as coordenações de curso (FUC).
SIGLAS = {
    "FEX", "CCX", "CD", "CGE", "CCT", "CCD", "CCH", "CTE", "CA", "PCC", "EC", "PFC",
    "DAS", "FCE", "FCPE", "CCE", "NE", "FAA",
}  # fmt: skip
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]  # fmt: skip
ACENTOS = {"FUNCAO": "Função", "FUNCOES": "Funções", "DIRECAO": "Direção",
           "GERENCIA": "Gerência", "TECNICO": "Técnico", "TEMPORARIO": "Temporário",
           "CONFIANCA": "Confiança", "COMISSAO": "Comissão", "ASSESSORIA": "Assessoria",
           "IFES": "IFES"}  # fmt: skip
PREPOSICOES = {"DE", "DO", "DA", "DOS", "DAS", "E", "EM"}
SEM_INFORMACAO = {"", "-1", "-2", "sem informação", "sem informa��o"}


def _data(valor: str | None) -> date | None:
    try:
        dia, mes, ano = (valor or "").strip().split("/")
        return date(int(ano), int(mes), int(dia))
    except ValueError:
        return None


def _texto(valor: str | None) -> str | None:
    valor = (valor or "").strip()
    return None if valor.lower() in SEM_INFORMACAO else valor


def titulo(texto: str | None) -> str | None:
    """'FUNCAO COMISSIONADA EXECUTIVA' -> 'Função comissionada executiva'. O texto do
    Portal vem em maiúsculas e sem acento."""
    if not texto:
        return None
    palavras = [
        ACENTOS.get(p, p.lower() if p in PREPOSICOES or len(p) > 3 else p) for p in texto.split()
    ]
    palavras[0] = palavras[0][:1].upper() + palavras[0][1:]
    return " ".join(palavras)


def ultimo_mes_publicado(pagina: str) -> tuple[int, int]:
    """O mês mais recente de `Servidores_SIAPE` na página de downloads do Portal."""
    meses = re.findall(
        r'"ano"\s*:\s*"(\d{4})",\s*"mes"\s*:\s*"(\d{2})"[^}]*"origem"\s*:\s*"Servidores_SIAPE"',
        pagina,
    )
    if not meses:
        raise RuntimeError("Página de servidores do Portal sem arquivos Servidores_SIAPE.")
    return max((int(a), int(m)) for a, m in meses)


def ler_cadastro(arquivo: Path | bytes):
    """Linhas do Cadastro em fluxo (o CSV tem ~450 MB descompactado)."""
    origem = io.BytesIO(arquivo) if isinstance(arquivo, bytes) else arquivo
    with zipfile.ZipFile(origem) as z:
        nome = next(n for n in z.namelist() if n.endswith("_Cadastro.csv"))
        with z.open(nome) as bruto:
            texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
            yield from csv.DictReader(texto, delimiter=";")


def normalizar(linhas, indice: dict[tuple[str, str], set[int]]) -> list[dict[str, Any]]:
    """Cargos de confiança de pessoas da base. `indice`: (6 dígitos do meio do CPF, chave do
    nome) -> ids das pessoas; só liga se houver uma única pessoa para a chave."""
    registros = []
    for linha in linhas:
        sigla = (linha.get("SIGLA_FUNCAO") or "").strip()
        if sigla not in SIGLAS:
            continue
        meio = re.sub(r"\D", "", linha.get("CPF") or "")
        if len(meio) != 6:
            continue
        candidatos = indice.get((meio, comum.chave_nome(linha.get("NOME"))), set())
        if len(candidatos) != 1:
            continue
        nivel = (linha.get("NIVEL_FUNCAO") or "").strip().lstrip("0") or None
        ingresso = _data(linha.get("DATA_INGRESSO_CARGOFUNCAO"))
        id_portal = int(linha["Id_SERVIDOR_PORTAL"])
        org = (linha.get("COD_ORG_EXERCICIO") or "").strip()
        registros.append(
            {
                "pessoa_id": next(iter(candidatos)),
                "id_externo": f"{id_portal}:{sigla}{nivel or ''}:{org}:"
                f"{ingresso.isoformat() if ingresso else ''}",
                "id_portal": id_portal,
                "sigla": sigla,
                "nivel": nivel,
                "funcao": (titulo(linha.get("FUNCAO")) or sigla)[:120],
                "atividade": (titulo(_texto(linha.get("ATIVIDADE"))) or "")[:120] or None,
                "orgao": nome_orgao(linha),
                "orgao_superior": (_texto(linha.get("ORGSUP_EXERCICIO")) or "")[:120] or None,
                "uf": ((_texto(linha.get("UF_EXERCICIO")) or "")[:2]) or None,
                "situacao_vinculo": (_texto(linha.get("SITUACAO_VINCULO")) or "")[:60] or None,
                "data_ingresso": ingresso,
                "data_nomeacao": _data(linha.get("DATA_NOMEACAO_CARGOFUNCAO")),
            }
        )
    return registros


def nome_orgao(linha: dict[str, str]) -> str | None:
    """O órgão de exercício; se vier em maiúsculas abreviadas ("MIN DESENV ASSIS SOCI..."),
    o órgão superior, que vem por extenso."""
    orgao = _texto(linha.get("ORG_EXERCICIO"))
    superior = _texto(linha.get("ORGSUP_EXERCICIO"))
    if orgao and orgao.isupper() and superior and not superior.isupper():
        orgao = superior
    return (orgao or "")[:120] or None


def indice_pessoas(pessoas: list[tuple[int, str | None, str]]) -> dict[tuple[str, str], set[int]]:
    indice: dict[tuple[str, str], set[int]] = {}
    for id_, cpf, chave_nome in pessoas:
        if cpf and chave_nome:
            indice.setdefault((cpf[3:9], chave_nome), set()).add(id_)
    return indice


def mes_por_extenso(mes: date) -> str:
    return f"{MESES[mes.month - 1]}/{mes.year}"


def gravar(session: Session, registros: list[dict[str, Any]], mes: date) -> int:
    """Acumula os registros do mês (primeiro e último mês em que apareceram). Registro que só
    existia neste mês e sumiu numa releitura é apagado (o Portal corrige o cadastro)."""
    chaves = {r["id_externo"] for r in registros}
    sumiram = [
        k
        for k in session.scalars(
            select(ServidorFederal.id_externo).where(
                ServidorFederal.primeiro_mes == mes, ServidorFederal.ultimo_mes == mes
            )
        )
        if k not in chaves
    ]
    for i in range(0, len(sumiram), 5000):
        session.execute(
            delete(ServidorFederal).where(ServidorFederal.id_externo.in_(sumiram[i : i + 5000]))
        )
    for r in registros:
        stmt = pg_insert(ServidorFederal).values(**r, primeiro_mes=mes, ultimo_mes=mes)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=["id_externo"],
                set_={
                    **{k: v for k, v in r.items() if k != "id_externo"},
                    "primeiro_mes": func.least(ServidorFederal.primeiro_mes, mes),
                    "ultimo_mes": func.greatest(ServidorFederal.ultimo_mes, mes),
                },
            )
        )
    return len(registros)


def descricao(s: ServidorFederal) -> str:
    cargo = f"{s.funcao} ({s.sigla}{' ' + s.nivel if s.nivel else ''})"
    if s.atividade:
        cargo += f", {s.atividade}"
    onde = f" em {s.orgao}" if s.orgao else ""
    return (
        f"Nomeado(a) para {cargo}{onde} "
        f"(Portal da Transparência, cadastro de {mes_por_extenso(s.primeiro_mes)})."
    )


def publicar_eventos(session: Session, ingestao_id: int | None) -> int:
    """Refaz vínculos e eventos desta fonte a partir de `servidor_federal` (todo o histórico)."""
    session.execute(delete(PessoaVinculo).where(PessoaVinculo.fonte == FONTE))  # eventos em cascata
    recente = session.scalar(select(func.max(ServidorFederal.ultimo_mes)))
    if recente is None:
        return 0
    total = 0
    for s in session.scalars(select(ServidorFederal)):
        vinculo_id = session.scalar(
            insert(PessoaVinculo)
            .values(pessoa_id=s.pessoa_id, fonte=FONTE, id_externo=s.id_externo,
                    regra="cpf_parcial_nome")
            .returning(PessoaVinculo.id)
        )  # fmt: skip
        if s.ultimo_mes >= recente:
            situacao = f"consta no cadastro de {mes_por_extenso(s.ultimo_mes)}"
        else:
            situacao = f"último cadastro em que consta: {mes_por_extenso(s.ultimo_mes)}"
        session.execute(
            insert(Evento).values(
                pessoa_id=s.pessoa_id,
                vinculo_id=vinculo_id,
                data=s.data_ingresso or s.data_nomeacao,
                tipo="cargo_federal",
                descricao=descricao(s),
                orgao=s.orgao,
                situacao=situacao[:80],
                fonte=FONTE,
                id_externo=s.id_externo,
                fonte_url=URL_SERVIDOR.format(id=s.id_portal),
                ingestao_id=ingestao_id,
            )
        )
        total += 1
    return total


def descobrir_mes(client: httpx.Client) -> tuple[int, int]:
    resposta = client.get(PAGINA, headers={"Accept": "text/html"})
    resposta.raise_for_status()
    return ultimo_mes_publicado(resposta.text)


def executar(ano: int | None = None, mes: int | None = None, de_raw: Path | None = None) -> int:
    """Carrega o cadastro de um mês (padrão: o mais recente publicado)."""
    if de_raw is not None and (ano is None or mes is None):
        achado = re.search(r"(\d{4})(\d{2})_", Path(de_raw).name)
        if achado is None:
            raise SystemExit("Com --de-raw, informe --ano e --mes (ou use o nome AAAAMM_*).")
        ano, mes = int(achado.group(1)), int(achado.group(2))
    if ano is None or mes is None:
        with comum.criar_cliente() as client:
            ano, mes = descobrir_mes(client)
    url = URL.format(ano=ano, mes=mes)
    mes_data = date(ano, mes, 1)

    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, url)

    def carregar(session: Session, payload: Path | bytes, ingestao: FonteIngestao) -> int:
        pessoas = session.execute(select(Pessoa.id, Pessoa.cpf, Pessoa.chave_nome)).all()
        linhas = comum.ContaLinhas(ler_cadastro(payload))
        registros = normalizar(linhas, indice_pessoas(pessoas))
        if linhas.total == 0:
            raise RuntimeError("Cadastro de servidores vazio: nada alterado.")
        comum.conferir_carga(
            ingestao, registros, total_fonte=linhas.total, nao_nulos=("id_externo",),
            unica=("id_externo",),
        )  # fmt: skip
        gravar(session, registros, mes_data)
        eventos = publicar_eventos(session, ingestao.id)
        pessoas_com_cargo = len({r["pessoa_id"] for r in registros})
        print(
            f"  {linhas.total} servidores no cadastro; {len(registros)} cargos de confiança de "
            f"{pessoas_com_cargo} pessoas da base; {eventos} eventos no histórico"
        )
        return len(registros)

    return comum.executar_ingestao(
        FONTE, url, baixar, carregar, de_raw=de_raw, prefixo_raw=f"{ano}{mes:02d}_",
        incremental=comum.Incremental(
            chave=f"{FONTE}:{ano}{mes:02d}", sonda=url, contexto=comum.contexto_pessoas
        ),
    )  # fmt: skip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int)
    parser.add_argument("--mes", type=int)
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um ZIP já baixado")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(args.ano, args.mes, args.de_raw)} cargos ligados")
