"""Emendas impositivas da ALESC (Santa Catarina), pelo SC Transferências da CGE/SC.

Fonte: a "Pesquisa detalhada > Emendas" do SC Transferências
(consultas.sctransferencias.cge.sc.gov.br) tem um botão "Baixar CSV" que chama
`sctransf-api.prod.okd4.ciasc.sc.gov.br/csv/emendas`: sem filtro, devolve todas as emendas
com proposta no sistema (2022 em diante), uma linha por **proposta** de transferência
(convênio, termo de fomento ou de colaboração), com deputado ou bancada autora, beneficiário
(nome e CNPJ), município do beneficiário, órgão concedente, valor da emenda na Lei
Orçamentária e valor repassado. A página "Dados abertos" do mesmo sistema publica, por ano, o
razão financeiro das transferências (`dados_financeiros_AAAA.zip`: empenhos, liquidações e
pagamentos, com anulações e estornos em valor negativo); dele sai o valor empenhado de cada
transferência. Tudo público, sem login nem captcha; uma requisição por vez, com pausa.

Armadilhas (vistas na amostra de 19/10/2026):
- o número da emenda se repete: uma emenda pode ter várias propostas (refeita, cancelada,
  dividida). A chave é a proposta; o valor previsto só se soma uma vez por emenda;
- o município é o do beneficiário, por nome em maiúsculas e sem acento ("BRACO DO NORTE");
- o CSV de emendas vem em UTF-8 com BOM; o razão financeiro, em latin-1; ambos com `;` e
  vírgula decimal;
- "Valor Repassado" vazio quando ainda não há transferência; a soma dos pagamentos do razão
  difere do repassado em ~7% das transferências (devoluções e estornos), por isso o pago é o
  repassado que o próprio sistema mostra;
- autores coletivos ("BANCADA DO OESTE") e nome com apelido entre parênteses
  ("MARCOS JOSÉ ABREU ( MARQUITO)").

Recorte: só as emendas executadas por transferência voluntária no SC Transferências
(entidades sem fins lucrativos, APAEs, consórcios). Repasses fundo a fundo da saúde e
transferências especiais a prefeituras não passam por esse sistema e ficam de fora.
"""

import argparse
import csv
import difflib
import io
import re
import time
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.models import (
    Candidatura,
    EmendaEstadual,
    FonteIngestao,
    MandatoLocal,
    Municipio,
    PessoaVinculo,
)
from app.models.pessoa import REGRAS_FORTES
from ingestion import comum

FONTE = "sctransferencias_emendas"
UF = "SC"
URL = "https://sctransf-api.prod.okd4.ciasc.sc.gov.br/csv/emendas"
URL_FINANCEIRO = (
    "https://arquivos.transparencia.sc.gov.br/sctransferencias/dados-abertos/"
    "dados_financeiros_{ano}.zip"
)
PAGINA = "https://consultas.sctransferencias.cge.sc.gov.br/pesquisa-detalhada/emendas"
PRIMEIRO_ANO = 2022  # primeiro ano com emendas no sistema
PAUSA = 1.0
MINIMO = 500  # menos linhas que isso é falha da fonte (eram 2.490 em 19/10/2026)
LOTE = 2000
ARQUIVO_EMENDAS = "emendas.csv"

CNPJ = re.compile(r"^(?P<nome>.*?)\s*\((?P<doc>\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\)\s*$")
CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
APELIDO = re.compile(r"\(\s*([^)]*?)\s*\)")


def _valor(texto: str | None) -> Decimal | None:
    texto = (texto or "").strip()
    if not texto:
        return None
    return Decimal(texto.replace(".", "").replace(",", ".") if "," in texto else texto)


def _texto(texto: str | None) -> str | None:
    texto = " ".join((texto or "").split())
    return texto or None


def favorecido(texto: str) -> tuple[str | None, str | None]:
    """'NOME (82.804.642/0001-08)' -> (nome, cnpj só com dígitos). Pessoa física (CPF): sem
    nome nem documento (coleta mínima)."""
    achado = CNPJ.match(texto or "")
    if achado:
        return _texto(achado["nome"]), re.sub(r"\D", "", achado["doc"])
    if CPF.search(texto or ""):
        return None, None
    return _texto(texto), None


def nomes_do_autor(autor: str) -> list[str]:
    """Chaves de nome do autor, na ordem de tentativa: o nome sem o apelido entre
    parênteses e, se houver, o apelido ('MARCOS JOSÉ ABREU ( MARQUITO)')."""
    apelido = APELIDO.search(autor or "")
    base = APELIDO.sub(" ", autor or "")
    chaves = [comum.chave_nome(base)]
    if apelido:
        chaves.append(comum.chave_nome(apelido.group(1)))
    return [c for c in chaves if c]


def ler_emendas(conteudo: bytes) -> list[dict[str, Any]]:
    """CSV de emendas do SC Transferências -> uma linha por proposta."""
    texto = conteudo.decode("utf-8-sig")
    linhas = []
    for x in csv.DictReader(io.StringIO(texto, newline=""), delimiter=";"):
        autor = _texto(x["Deputado"]) or ""
        nome, cnpj = favorecido(x["Beneficiário"])
        natureza = _texto(x["Natureza Jurídica Proponente"])
        if nome is None and cnpj is None:
            natureza = "Pessoa física"
        linhas.append(
            {
                "uf": UF,
                "ano": int(x["Ano"]),
                "codigo": x["Nº Emenda"].strip(),
                "proposta": x["Nº Proposta"].strip(),
                "transferencia": _texto(x["Nº Transferência"]),
                "tipo": "bancada"
                if comum.chave_nome(autor).startswith("BANCADA")
                else "individual",
                "autor_nome": autor,
                "autor_chave": comum.chave_nome(autor),
                "municipio_nome": _texto(x["Município"]) or "",
                "favorecido_nome": nome,
                "favorecido_cnpj": cnpj,
                "favorecido_natureza": natureza,
                "orgao": _texto(re.sub(r"\s*\(\d+\)\s*$", "", x["Concedente"] or "")),
                "instrumento": _texto(x["Instrumento"]),
                "objeto": _texto(x["Objeto Emenda"]),
                "situacao_proposta": _texto(x["Situação Proposta"]),
                "situacao_transferencia": _texto(x["Situação Transferência"]),
                # O valor atualizado (remanejamentos) é o que vale; difere em ~11 de 2.490.
                "valor_previsto": _valor(x["Valor Atualizado"]) or _valor(x["Valor Emenda"]) or 0,
                "valor_pago": _valor(x["Valor Repassado"]) or Decimal(0),
            }
        )
    return linhas


def empenhado_por_transferencia(financeiros: list[bytes]) -> dict[str, Decimal]:
    """Soma do valor empenhado (já líquido de anulações) por transferência, em todos os anos
    do razão financeiro. Lido em fluxo (cada CSV tem ~15 mil linhas)."""
    soma: dict[str, Decimal] = {}
    for conteudo in financeiros:
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            for nome in z.namelist():
                if not nome.lower().endswith(".csv"):
                    continue
                with z.open(nome) as arquivo:
                    texto = io.TextIOWrapper(arquivo, encoding="latin-1", newline="")
                    for x in csv.DictReader(texto, delimiter=";"):
                        valor = _valor(x.get("vlempenho"))
                        tr = (x.get("nutransferencia") or "").strip()
                        if tr and valor:
                            soma[tr] = soma.get(tr, Decimal(0)) + valor
    return soma


def empacotar(emendas: bytes, financeiros: dict[int, bytes]) -> bytes:
    """O CSV de emendas e os razões financeiros num zip só (bruto da carga). Datas fixas nas
    entradas, para o mesmo conteúdo dar o mesmo sha256 (carga incremental)."""
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo(ARQUIVO_EMENDAS, (2000, 1, 1, 0, 0, 0)), emendas)
        for ano, conteudo in sorted(financeiros.items()):
            info = zipfile.ZipInfo(f"dados_financeiros_{ano}.zip", (2000, 1, 1, 0, 0, 0))
            z.writestr(info, conteudo)
    return saida.getvalue()


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    """Bruto (zip com emendas.csv e os dados_financeiros_AAAA.zip) -> linhas da tabela."""
    with zipfile.ZipFile(io.BytesIO(pacote)) as z:
        linhas = ler_emendas(z.read(ARQUIVO_EMENDAS))
        financeiros = [z.read(n) for n in z.namelist() if n.startswith("dados_financeiros_")]
    empenhado = empenhado_por_transferencia(financeiros)
    for linha in linhas:
        tr = linha["transferencia"]
        linha["valor_empenhado"] = empenhado.get(tr) if tr else None
    return linhas


def resolver_municipios(
    linhas: list[dict[str, Any]], municipios: list[tuple[str, str]]
) -> dict[str, str | None]:
    """Nome do município (como veio) -> código IBGE, dentro de SC: nome igual sem acento e,
    se não houver, a grafia mais próxima (corte 0,88, como nas emendas federais)."""
    por_chave = dict((chave, ibge) for ibge, chave in municipios)
    saida: dict[str, str | None] = {}
    for nome in {linha["municipio_nome"] for linha in linhas}:
        chave = comum.chave_nome(nome)
        ibge = por_chave.get(chave)
        if ibge is None:
            proximo = difflib.get_close_matches(chave, list(por_chave), n=1, cutoff=0.88)
            ibge = por_chave[proximo[0]] if proximo else None
        saida[nome] = ibge
    return saida


def mapa_pessoas(session: Session) -> dict[str, set[int]]:
    """Chave de nome -> pessoas publicáveis com esse nome entre os deputados estaduais de SC:
    eleitos pelo TSE (nome civil e de urna) e os que a ALESC lista no cargo hoje."""
    publicavel = PessoaVinculo.regra.in_(REGRAS_FORTES) | PessoaVinculo.revisado.is_(True)
    por_nome: dict[str, set[int]] = {}
    eleitos = session.execute(
        select(Candidatura.nome, Candidatura.nome_urna, PessoaVinculo.pessoa_id)
        .join(
            PessoaVinculo,
            (PessoaVinculo.fonte == "candidatura")
            & (
                PessoaVinculo.id_externo
                == func.concat(Candidatura.ano_eleicao, ":", Candidatura.sq_candidato)
            ),
        )
        .where(
            Candidatura.cargo == "DEPUTADO ESTADUAL",
            Candidatura.uf == UF,
            Candidatura.situacao_turno.like("ELEITO%"),
            publicavel,
        )
    ).all()
    no_cargo = session.execute(
        select(MandatoLocal.nome, MandatoLocal.nome_completo, PessoaVinculo.pessoa_id)
        .join(
            PessoaVinculo,
            (PessoaVinculo.fonte == "mandato_local")
            & (
                PessoaVinculo.id_externo
                == func.concat(
                    MandatoLocal.casa, ":", MandatoLocal.uf, "::", MandatoLocal.id_externo
                )
            ),
        )
        .where(MandatoLocal.casa == "assembleia", MandatoLocal.uf == UF, publicavel)
    ).all()
    for nome, outro, pessoa_id in [*eleitos, *no_cargo]:
        for chave in {comum.chave_nome(nome), comum.chave_nome(outro)} - {""}:
            por_nome.setdefault(chave, set()).add(pessoa_id)
    return por_nome


def vincular_pessoa(autor: str, por_nome: dict[str, set[int]]) -> int | None:
    """Pessoa do autor por nome idêntico e único na Casa; bancadas e nomes ambíguos: None."""
    if comum.chave_nome(autor).startswith("BANCADA"):
        return None
    for chave in nomes_do_autor(autor):
        candidatos = por_nome.get(chave, set())
        if len(candidatos) == 1:
            return next(iter(candidatos))
    return None


def carregar(session: Session, pacote: bytes, ingestao: FonteIngestao) -> int:
    linhas = normalizar(pacote)
    if len(linhas) < MINIMO:
        raise ValueError(f"Só {len(linhas)} emendas no SC Transferências; abortando.")
    municipios = session.execute(
        select(Municipio.ibge, Municipio.nome_chave).where(Municipio.uf == UF)
    ).all()
    ibge = resolver_municipios(linhas, [tuple(m) for m in municipios])
    por_nome = mapa_pessoas(session)
    pessoas = {a: vincular_pessoa(a, por_nome) for a in {linha["autor_nome"] for linha in linhas}}
    for linha in linhas:
        linha["municipio_ibge"] = ibge.get(linha["municipio_nome"])
        linha["pessoa_id"] = pessoas[linha["autor_nome"]]
        linha["fonte"] = FONTE
        linha["ingestao_id"] = ingestao.id
    session.execute(delete(EmendaEstadual).where(EmendaEstadual.uf == UF))
    for i in range(0, len(linhas), LOTE):
        session.execute(insert(EmendaEstadual), linhas[i : i + LOTE])
    sem_municipio = sorted({x["municipio_nome"] for x in linhas if not x["municipio_ibge"]})
    individuais = {x["autor_nome"] for x in linhas if x["tipo"] == "individual"}
    ligados = {a for a in individuais if pessoas[a]}
    print(
        f"{FONTE}: {len(linhas)} propostas, {len({x['codigo'] for x in linhas})} emendas; "
        f"autores individuais ligados a pessoa: {len(ligados)} de {len(individuais)}; "
        f"municípios sem código IBGE: {sem_municipio or 'nenhum'}",
        flush=True,
    )
    return len(linhas)


def contexto(session: Session) -> str:
    """Religa os autores quando entram pessoas ou mudam os deputados no cargo."""
    total = session.scalar(
        select(func.count(MandatoLocal.id)).where(
            MandatoLocal.casa == "assembleia", MandatoLocal.uf == UF
        )
    )
    return f"{comum.contexto_pessoas(session)};alesc:{total}"


def baixar(client: httpx.Client, hoje: date | None = None) -> bytes:
    hoje = hoje or date.today()
    emendas = comum.get_bytes(client, URL)
    financeiros = {}
    for ano in range(PRIMEIRO_ANO, hoje.year + 1):
        time.sleep(PAUSA)
        financeiros[ano] = comum.get_bytes(client, URL_FINANCEIRO.format(ano=ano))
    return empacotar(emendas, financeiros)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(
        FONTE,
        URL,
        baixar,
        carregar,
        de_raw=de_raw,
        # O sistema muda pouco de um dia para o outro: com o mesmo conteúdo (e as mesmas
        # pessoas), não regrava nem acumula bruto.
        incremental=comum.Incremental(chave=FONTE, contexto=contexto),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} propostas de emendas estaduais")
