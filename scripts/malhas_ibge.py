"""Gera as malhas do mapa (UF e municípios) em frontend/public/mapa/.

Como rodar (local, precisa de rede e de Node para o `npx mapshaper`):

    python scripts/malhas_ibge.py [--manter-brutos]

Baixa do IBGE (servicodados.ibge.gov.br) a malha dos estados, a de municípios de cada estado e
os nomes; simplifica com mapshaper (UF 6%, municípios 12%, detalhado 45%, sempre keep-shapes);
projeta num único sistema de coordenadas (viewBox do Brasil 0 0 874 894) e grava:

    ufs.json         {sigla: {cod, nome, regiao, d, bbox}}
    mun/<UF>.json    {ibge: {n, d, b}}   só geometria e nome, sem dados
    det/<UF>.json    {ibge: d}           desenho detalhado, carregado ao abrir uma cidade

Os brutos ficam numa pasta temporária (fora do git) e são apagados ao fim.
"""

import argparse
import gzip
import json
import math
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "frontend" / "public" / "mapa"
IBGE = "https://servicodados.ibge.gov.br/api"
GEO = "formato=application/vnd.geo+json&qualidade=intermediaria"

LON0, LAT_MAX, LAT0, K = -74.1, 5.35, -14.0, 22.8
COS = math.cos(math.radians(LAT0))


def baixar(url: str, destino: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "panoptico-malhas"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dados = r.read()
    if dados[:2] == bytes([0x1f, 0x8b]):
        dados = gzip.decompress(dados)
    destino.write_bytes(dados)


def simplificar(origem: Path, destino: Path, pct: int) -> None:
    subprocess.run(
        ["npx", "--yes", "mapshaper", str(origem), "-simplify", f"{pct}%", "keep-shapes",
         "-o", str(destino), "format=geojson"],
        check=True, shell=True,
    )


def xy(lon: float, lat: float) -> tuple[float, float]:
    return ((lon - LON0) * K * COS, (LAT_MAX - lat) * K)


def anel(coords: list, dec: int) -> str:
    out, px, py = [], None, None
    for i, c in enumerate(coords):
        x, y = (round(v, dec) for v in xy(c[0], c[1]))
        if i == 0:
            out.append(f"M{x:g} {y:g}")
        else:
            dx, dy = round(x - px, dec), round(y - py, dec)
            if dx == 0 and dy == 0:
                continue
            out.append(f"l{dx:g} {dy:g}")
        px, py = x, y
    return "".join(out) + "z"


def caminho(geom: dict, dec: int = 2) -> tuple[str, list]:
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    d, xs, ys = [], [], []
    for poly in polys:
        for r in poly:
            d.append(anel(r, dec))
            for c in r:
                x, y = xy(c[0], c[1])
                xs.append(x)
                ys.append(y)
    return "".join(d), [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)]


def gravar(arq: Path, obj) -> None:
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def principal() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manter-brutos", action="store_true")
    args = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="malhas_ibge_"))
    try:
        baixar(f"{IBGE}/v1/localidades/estados?orderBy=id", tmp / "uf_meta.json")
        baixar(f"{IBGE}/v1/localidades/municipios", tmp / "municipios.json")
        metas = json.loads((tmp / "uf_meta.json").read_text(encoding="utf-8"))
        nomes = {str(m["id"]): m["nome"] for m in json.loads((tmp / "municipios.json").read_text(encoding="utf-8"))}

        baixar(f"{IBGE}/v3/malhas/paises/BR?intrarregiao=UF&{GEO}", tmp / "br_uf_bruto.json")
        simplificar(tmp / "br_uf_bruto.json", tmp / "br_uf.json", 6)
        por_cod = {str(e["id"]): e for e in metas}
        ufs = {}
        for f in json.loads((tmp / "br_uf.json").read_text(encoding="utf-8"))["features"]:
            cod = f["properties"]["codarea"]
            e = por_cod[cod]
            d, bbox = caminho(f["geometry"])
            ufs[e["sigla"]] = {"cod": cod, "nome": e["nome"], "regiao": e["regiao"]["nome"], "d": d, "bbox": bbox}
        gravar(SAIDA / "ufs.json", ufs)

        for cod, e in por_cod.items():
            bruto = tmp / f"mun_{cod}_bruto.json"
            baixar(f"{IBGE}/v3/malhas/estados/{cod}?intrarregiao=municipio&{GEO}", bruto)
            simplificar(bruto, tmp / f"mun_{cod}.json", 12)
            simplificar(bruto, tmp / f"det_{cod}.json", 45)
            mun, det = {}, {}
            for f in json.loads((tmp / f"mun_{cod}.json").read_text(encoding="utf-8"))["features"]:
                c = f["properties"]["codarea"]
                d, bbox = caminho(f["geometry"])
                mun[c] = {"n": nomes.get(c, c), "d": d, "b": bbox}
            for f in json.loads((tmp / f"det_{cod}.json").read_text(encoding="utf-8"))["features"]:
                det[f["properties"]["codarea"]] = caminho(f["geometry"], 3)[0]
            gravar(SAIDA / "mun" / f"{e['sigla']}.json", mun)
            gravar(SAIDA / "det" / f"{e['sigla']}.json", det)
            print(e["sigla"], len(mun))
    finally:
        if args.manter_brutos:
            print("Brutos em", tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    principal()
