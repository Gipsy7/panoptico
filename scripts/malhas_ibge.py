"""Gera as malhas do mapa (UF e municípios) em frontend/public/mapa/.

Como rodar (local, precisa de rede e de Node para o `npx mapshaper`):

    python scripts/malhas_ibge.py [--manter-brutos]

Baixa do IBGE (servicodados.ibge.gov.br) a malha dos estados, a de municípios de cada estado e
os nomes; simplifica com mapshaper (UF 6%, municípios 12%, detalhado 45%, sempre keep-shapes);
projeta num único sistema de coordenadas (viewBox do Brasil 0 0 874 894) e grava:

    ufs.json         {sigla: {cod, nome, regiao, d, bbox, l}}
    mun/<UF>.json    {ibge: {n, d, b, l}}   só geometria e nome, sem dados
    det/<UF>.json    {ibge: d}           desenho detalhado, carregado ao abrir uma cidade

`l` = [x, y, r] é o ponto de rótulo: o ponto interior mais distante da borda (polylabel) no
maior polígono, e r é essa distância (raio do maior círculo que cabe ali), para o site decidir
se o nome cabe no desenho.

Os brutos ficam numa pasta temporária (fora do git) e são apagados ao fim.
"""

import argparse
import gzip
import heapq
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


def _dist_seg(px: float, py: float, a: tuple, b: tuple) -> float:
    x, y = a
    dx, dy = b[0] - x, b[1] - y
    if dx or dy:
        t = ((px - x) * dx + (py - y) * dy) / (dx * dx + dy * dy)
        if t > 1:
            x, y = b
        elif t > 0:
            x, y = x + dx * t, y + dy * t
    return math.hypot(px - x, py - y)


def _dist_poligono(px: float, py: float, aneis: list) -> float:
    """Distância com sinal do ponto à borda (positiva dentro, negativa fora)."""
    dentro, menor = False, math.inf
    for r in aneis:
        j = len(r) - 1
        for i in range(len(r)):
            a, b = r[i], r[j]
            cruza = (a[1] > py) != (b[1] > py)
            if cruza and px < (b[0] - a[0]) * (py - a[1]) / (b[1] - a[1]) + a[0]:
                dentro = not dentro
            menor = min(menor, _dist_seg(px, py, a, b))
            j = i
    return menor if dentro else -menor


def polylabel(aneis: list, precisao_rel: float = 0.01) -> tuple[float, float, float]:
    """Ponto interior mais distante da borda (polylabel, da Mapbox), em coordenadas do mapa."""
    xs = [p[0] for p in aneis[0]]
    ys = [p[1] for p in aneis[0]]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    w, h = x1 - x0, y1 - y0
    tam = min(w, h)
    if tam == 0:
        return x0, y0, 0.0
    prec = max(w, h) * precisao_rel
    fila: list = []

    def celula(cx: float, cy: float, m: float) -> None:
        d = _dist_poligono(cx, cy, aneis)
        heapq.heappush(fila, (-(d + m * math.sqrt(2)), cx, cy, m, d))

    m = tam / 2
    x = x0
    while x < x1:
        y = y0
        while y < y1:
            celula(x + m, y + m, m)
            y += tam
        x += tam
    # centroide da área como primeira aposta
    area = cx = cy = 0.0
    r = aneis[0]
    j = len(r) - 1
    for i in range(len(r)):
        a, b = r[i], r[j]
        f = a[0] * b[1] - b[0] * a[1]
        cx += (a[0] + b[0]) * f
        cy += (a[1] + b[1]) * f
        area += f * 3
        j = i
    melhor = ((x0 + w / 2, y0 + h / 2) if area == 0 else (cx / area, cy / area))
    melhor_d = _dist_poligono(*melhor, aneis)
    d_caixa = _dist_poligono(x0 + w / 2, y0 + h / 2, aneis)
    if d_caixa > melhor_d:
        melhor, melhor_d = (x0 + w / 2, y0 + h / 2), d_caixa
    while fila:
        neg_max, cx, cy, m, d = heapq.heappop(fila)
        if d > melhor_d:
            melhor, melhor_d = (cx, cy), d
        if -neg_max - melhor_d <= prec:
            continue
        m /= 2
        for sx in (-1, 1):
            for sy in (-1, 1):
                celula(cx + sx * m, cy + sy * m, m)
    return melhor[0], melhor[1], max(0.0, melhor_d)


def ponto_rotulo(geom: dict, dec: int) -> list:
    """[x, y, r] do rótulo no maior polígono (por área do anel externo)."""
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]

    def projetar(poly: list) -> list:
        return [[xy(c[0], c[1]) for c in r] for r in poly]

    def area(anel_xy: list) -> float:
        pares = zip(anel_xy, anel_xy[1:] + anel_xy[:1], strict=True)
        return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in pares)) / 2

    maior = max((projetar(p) for p in polys), key=lambda p: area(p[0]))
    x, y, r = polylabel(maior)
    return [round(x, dec), round(y, dec), round(r, dec)]


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
            ufs[e["sigla"]] = {
                "cod": cod, "nome": e["nome"], "regiao": e["regiao"]["nome"], "d": d, "bbox": bbox,
                "l": ponto_rotulo(f["geometry"], 1),
            }
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
                rot = ponto_rotulo(f["geometry"], 2)
                mun[c] = {"n": nomes.get(c, c), "d": d, "b": bbox, "l": rot}
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
