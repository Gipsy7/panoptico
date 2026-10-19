"""Convênios das emendas: situação, valores, vigência e prestação de contas.

O arquivo de convênios do Portal da Transparência (CGU, ~67 MB, atualizado em dias úteis)
traz todos os convênios federais desde os anos 90. Ficam só os que a base de emendas
aponta (`emenda_convenio`, preenchida pela carga de emendas; desde 18/10/2026 de todos os
anos do arquivo de emendas, ~72 mil). O CSV é lido em fluxo; o bruto guardado é o recorte e
os entes do SICONFI (mapa CNPJ -> município, ingestion.transferegov.municipio). A situação
do convênio mistura execução e prestação de contas ("Em execução", "Prestação de contas em
análise", "Aprovada"...).
"""

import argparse
import csv
import gzip
import io
import json
import re
import zipfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, func, insert, literal_column, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import EmendaConvenio, EmendaTransferencia, FonteIngestao
from ingestion import comum
from ingestion.transferegov import municipio

FONTE = "transferegov_convenios"
URL_PAGINA = "https://portaldatransparencia.gov.br/download-de-dados/convenios"
URL = URL_PAGINA + "/{dia:%Y%m%d}"
SEM_INFORMACAO = {"", "sem informação", "sem informacao"}
CAMPOS = {
    "numero": "NÚMERO CONVÊNIO",
    "uf": "UF",
    "situacao": "SITUAÇÃO CONVÊNIO",
    "objeto": "OBJETO DO CONVÊNIO",
    "orgao": "NOME ÓRGÃO CONCEDENTE",
    "cnpj": "CÓDIGO CONVENENTE",
    "convenente": "NOME CONVENENTE",
    "valor": "VALOR CONVÊNIO",
    "liberado": "VALOR LIBERADO",
    "contrapartida": "VALOR CONTRAPARTIDA",
    "inicio": "DATA INÍCIO VIGÊNCIA",
    "fim": "DATA FINAL VIGÊNCIA",
    "municipio": "NOME MUNICÍPIO",
    "tipo_convenente": "TIPO CONVENENTE",
}
# Convenentes cujo "NOME MUNICÍPIO" é a cidade que recebe. Governo estadual, agente
# intermediário (Caixa) e pessoa física ficam sem município pelo nome.
CONVENENTES_MUNICIPAIS = {
    "Administração Pública Municipal",
    "Administração Pública",
    "Entidades Sem Fins Lucrativos",
}


def _valor(texto: str | None) -> Decimal | None:
    texto = (texto or "").strip()
    return Decimal(texto.replace(".", "").replace(",", ".")) if texto else None


def _data(texto: str | None) -> date | None:
    try:
        dia, mes, ano = (texto or "").strip().split("/")
        return date(int(ano), int(mes), int(dia))
    except ValueError:
        return None


def frase(texto: str | None) -> str | None:
    """ "PRESTAÇÃO DE CONTAS EM ANÁLISE" -> "Prestação de contas em análise"."""
    texto = " ".join((texto or "").split())
    if texto.lower() in SEM_INFORMACAO:
        return None
    return texto[:1].upper() + texto[1:].lower()


def dia_publicado(client: httpx.Client, hoje: date) -> date:
    """O último dia com arquivo publicado: lê a lista da página; sem ela, volta até 15 dias
    (o servidor da CGU responde 403, não 404, para arquivo inexistente)."""
    try:
        pagina = comum.get_bytes(client, URL_PAGINA).decode("utf-8", "replace")
        dias = [
            date(int(a), int(m), int(d))
            for a, m, d in re.findall(
                r'"ano"\s*:\s*"(\d{4})"\s*,\s*"mes"\s*:\s*"(\d+)"\s*,\s*"dia"\s*:\s*"(\d+)"', pagina
            )
        ]
        if dias:
            return max(dias)
    except httpx.HTTPError:
        pass
    for atraso in range(16):
        dia = hoje - timedelta(days=atraso)
        if client.head(URL.format(dia=dia), timeout=30).status_code == 200:
            return dia
    raise RuntimeError("Nenhum arquivo de convênios publicado nos últimos 15 dias.")


def recortar(arquivo_zip: Path | bytes, numeros: set[str]) -> list[dict[str, str]]:
    """Lê o CSV de convênios em fluxo e guarda os campos úteis dos números pedidos."""
    origem = io.BytesIO(arquivo_zip) if isinstance(arquivo_zip, bytes) else arquivo_zip
    achados: dict[str, dict[str, str]] = {}
    with zipfile.ZipFile(origem) as z:
        nome = next(n for n in z.namelist() if n.endswith("_Convenios.csv"))
        with z.open(nome) as f:
            for linha in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
                numero = linha[CAMPOS["numero"]].strip()
                if numero in numeros:
                    achados[numero] = {k: (linha.get(c) or "").strip() for k, c in CAMPOS.items()}
    return [achados[n] for n in sorted(achados)]


def normalizar(recorte: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Número do convênio -> colunas de `emenda_transferencia`."""
    saida = {}
    for r in recorte:
        cnpj = re.sub(r"\D", "", r["cnpj"])
        saida[r["numero"]] = {
            "situacao": frase(r["situacao"]),
            "beneficiario": r["convenente"] or None,
            "beneficiario_cnpj": cnpj if len(cnpj) == 14 else None,
            "uf": r["uf"] if len(r["uf"]) == 2 else None,
            "orgao_concedente": r["orgao"] or None,
            "objeto": " ".join(r["objeto"].split()) or None,
            "valor_total": _valor(r["valor"]),
            "valor_repassado": _valor(r["liberado"]),
            "valor_contrapartida": _valor(r["contrapartida"]),
            "inicio_vigencia": _data(r["inicio"]),
            "fim_vigencia": _data(r["fim"]),
        }
    return saida


def numeros_ligados(session: Session) -> set[str]:
    return set(session.scalars(select(EmendaConvenio.numero_convenio).distinct()))


def contexto(session: Session) -> str:
    """Muda quando a lista de convênios das emendas muda (recarrega com o arquivo igual)."""
    numero = EmendaConvenio.numero_convenio
    resumo = session.scalar(
        select(func.md5(func.string_agg(numero, aggregate_order_by(literal_column("','"), numero))))
    )
    return f"convenios:{resumo}:{municipio.contexto(session)}"


def municipios(recorte: list[dict[str, str]], mapa: municipio.Mapa) -> tuple[dict, dict]:
    """Número do convênio -> IBGE do convenente; e a contagem por forma de resolução."""
    saida: dict[str, str | None] = {}
    contagem: dict[str, int] = {}
    for r in recorte:
        nome_municipio = (
            r.get("municipio") if r.get("tipo_convenente") in CONVENENTES_MUNICIPAIS else None
        )
        ibge, como = mapa.resolver(r["cnpj"], r["uf"], r["convenente"], nome_municipio)
        saida[r["numero"]] = ibge
        contagem[como] = contagem.get(como, 0) + 1
    return saida, contagem


def carregar(session: Session, payload: bytes, ingestao: FonteIngestao) -> int:
    bruto = json.loads(gzip.decompress(payload) if payload[:2] == b"\x1f\x8b" else payload)
    # Brutos anteriores a 18/10/2026 são só a lista de convênios, sem os entes.
    recorte = bruto["convenios"] if isinstance(bruto, dict) else bruto
    entes = bruto.get("entes", []) if isinstance(bruto, dict) else []
    if not recorte:
        raise ValueError("Nenhum convênio das emendas no arquivo; abortando.")
    dados = normalizar(recorte)
    ibge, contagem = municipios(recorte, municipio.montar(session, entes))
    print(f"  convênios por forma de achar o município: {contagem}")
    ligacoes = session.execute(
        select(EmendaConvenio.emenda_codigo, EmendaConvenio.numero_convenio)
    ).all()
    linhas = [
        {
            "tipo": "convenio",
            "emenda_codigo": codigo,
            "ano_emenda": int(codigo[:4]),
            "identificador": numero,
            "ingestao_id": ingestao.id,
            "municipio_ibge": ibge[numero],
            **dados[numero],
        }
        for codigo, numero in ligacoes
        if numero in dados
    ]
    sem = len({n for _, n in ligacoes}) - len({r["identificador"] for r in linhas})
    print(f"  {len(linhas)} ligações emenda-convênio; {sem} convênios fora do arquivo")
    session.execute(delete(EmendaTransferencia).where(EmendaTransferencia.tipo == "convenio"))
    for inicio in range(0, len(linhas), 5000):
        session.execute(insert(EmendaTransferencia), linhas[inicio : inicio + 5000])
    return len(linhas)


def executar(de_raw: Path | None = None) -> int:
    url = URL_PAGINA
    if de_raw is None:
        with comum.criar_cliente() as client:
            url = URL.format(dia=dia_publicado(client, date.today()))

    def baixar(client: httpx.Client) -> bytes:
        with SessionLocal() as session:
            numeros = numeros_ligados(session)
        if not numeros:
            raise ValueError("Sem convênios ligados a emendas; rode transparencia.emendas antes.")
        arquivo = comum.baixar_para_arquivo(client, url)
        try:
            recorte = recortar(arquivo, numeros)
        finally:
            arquivo.unlink(missing_ok=True)
        bruto = {"convenios": recorte, "entes": municipio.baixar_entes(client)}
        return json.dumps(bruto, ensure_ascii=False).encode()

    return comum.executar_ingestao(
        FONTE,
        url,
        baixar,
        carregar,
        de_raw=de_raw,
        extensao_raw=".json.gz",
        incremental=comum.Incremental(chave=FONTE, sonda=url, contexto=contexto),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} ligações emenda-convênio")
