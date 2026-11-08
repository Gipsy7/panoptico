"""Homicídios por município de residência no SIM (Sistema de Informações sobre Mortalidade) do
DATASUS, o mesmo dado que o Atlas da Violência (Ipea) usa.

Homicídio = causa básica (CID-10) de X85 a Y09 (agressões) ou Y35 e Y36 (intervenção legal e
operações de guerra), o recorte do Atlas. Só os anos fechados (`CID10/DORES`, um DBC por UF de
residência e ano). Os DBC são DBF comprimidos (largura fixa): descomprimimos com `pyreaddbc` e lemos
só duas colunas, `CODMUNRES` (6 dígitos, sem o dígito verificador) e `CAUSABAS`. Nada além das
contagens é guardado: nenhum dado de pessoa sai do arquivo.
"""

import argparse
import re
import shutil
import struct
import tempfile
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, HomicidioSim, Municipio
from app.services.pib import CODIGO_UF
from ingestion import comum

FONTE = "datasus_homicidios"
URL = "ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DORES/"
ANO_INICIAL = 2014
ARQUIVO = re.compile(r"^DO([A-Z]{2})(\d{4})\.dbc$", re.IGNORECASE)


def e_homicidio(causa: str) -> bool:
    g = causa[:3].upper()
    return "X85" <= g <= "Y09" or g in ("Y35", "Y36")


def ler_dbf(caminho: Path) -> tuple[Counter, int]:
    """Conta homicídios por município (6 dígitos) num DBF do SIM e o total do arquivo."""
    por_mun: Counter = Counter()
    total = 0
    with caminho.open("rb") as f:
        n, tam_cab, tam_reg = struct.unpack("<IHH", f.read(32)[4:12])
        campos: dict[str, tuple[int, int]] = {}
        pos = 1  # o 1º byte do registro é a marca de apagado
        while True:
            d = f.read(32)
            if not d or d[0] == 0x0D:
                break
            campos[d[:11].split(b"\0")[0].decode("latin-1")] = (pos, d[16])
            pos += d[16]
        (pm, tm), (pc, tc) = campos["CODMUNRES"], campos["CAUSABAS"]
        f.seek(tam_cab)
        for _ in range(n):
            r = f.read(tam_reg)
            if len(r) < tam_reg:
                break
            if r[0:1] == b"*":  # registro apagado
                continue
            if e_homicidio(r[pc : pc + tc].decode("latin-1").strip()):
                total += 1
                por_mun[r[pm : pm + tm].decode("latin-1").strip()] += 1
    return por_mun, total


def _abrir(url: str, tentativas: int = 5):
    for t in range(tentativas):
        try:
            return urllib.request.urlopen(url, timeout=120)  # noqa: S310 (FTP público do DATASUS)
        except OSError:
            if t == tentativas - 1:
                raise
            time.sleep(10 * (t + 1))
    raise RuntimeError("inalcançável")


def listar() -> list[tuple[str, int, str]]:
    with _abrir(URL) as r:
        texto = r.read().decode("latin-1")
    arquivos = []
    for linha in texto.splitlines():
        nome = linha.split()[-1] if linha.split() else ""
        m = ARQUIVO.match(nome)
        if m and m.group(1).upper() != "BR" and int(m.group(2)) >= ANO_INICIAL:
            arquivos.append((m.group(1).upper(), int(m.group(2)), nome))
    return sorted(arquivos, key=lambda a: (a[1], a[0]))


def baixar(client: httpx.Client) -> dict[str, Any]:
    import pyreaddbc  # só na carga: a API não precisa dele

    recorte: dict[str, Any] = {"anos": {}}
    pasta = Path(tempfile.mkdtemp(prefix="sim_"))
    try:
        for uf, ano, nome in listar():
            dbc, dbf = pasta / nome, pasta / (nome[:-4] + ".dbf")
            with _abrir(URL + nome) as r, dbc.open("wb") as saida:
                shutil.copyfileobj(r, saida, 1 << 20)
            pyreaddbc.dbc2dbf(str(dbc), str(dbf))
            dbc.unlink()
            por_mun, total = ler_dbf(dbf)
            dbf.unlink()
            do_ano = recorte["anos"].setdefault(str(ano), {"uf": {}, "municipios": {}})
            do_ano["uf"][uf] = total
            for cod, n in por_mun.items():
                do_ano["municipios"][cod] = do_ano["municipios"].get(cod, 0) + n
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    return recorte


def normalizar(recorte: dict[str, Any], mapa6: dict[str, str]) -> list[dict[str, Any]]:
    """Contagens -> linhas (código de 7 dígitos, 2 da UF ou 1 do Brasil). Municípios só com o
    código "ignorado" (ex.: 420000) entram no estado, não numa cidade."""
    linhas = []
    for ano_txt, do_ano in recorte["anos"].items():
        ano = int(ano_txt)
        if len(do_ano["uf"]) < 27:
            continue  # ano incompleto (algum estado ainda sem arquivo): fora
        for uf, n in do_ano["uf"].items():
            if uf in CODIGO_UF:
                linhas.append({"codigo": CODIGO_UF[uf], "ano": ano, "homicidios": n})
        linhas.append({"codigo": "1", "ano": ano, "homicidios": sum(do_ano["uf"].values())})
        com_ocorrencia = {}
        for cod6, n in do_ano["municipios"].items():
            ibge = mapa6.get(cod6[:6])
            if ibge:
                com_ocorrencia[ibge] = com_ocorrencia.get(ibge, 0) + n
        # Cidade sem nenhum homicídio no ano entra com zero (o arquivo só traz quem morreu).
        for ibge in mapa6.values():
            linhas.append({"codigo": ibge, "ano": ano, "homicidios": com_ocorrencia.get(ibge, 0)})
    return linhas


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    mapa6 = {ibge[:6]: ibge for ibge in session.scalars(select(Municipio.ibge))}
    linhas = normalizar(payload, mapa6)
    if len({r["ano"] for r in linhas}) < 1 or len(linhas) < 5000:
        raise ValueError("SIM sem nenhum ano completo; abortando.")
    session.execute(delete(HomicidioSim))
    lista = [{**r, "ingestao_id": ingestao.id} for r in linhas]
    for inicio in range(0, len(lista), 5000):
        session.execute(insert(HomicidioSim), lista[inicio : inicio + 5000])
    return len(lista)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} linhas (lugar × ano)")
