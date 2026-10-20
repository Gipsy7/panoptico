"""Geometria do gerador de malhas do mapa (scripts/malhas_ibge.py): projeção, path SVG e
ponto de rótulo (polylabel). Sem rede nem mapshaper: só as funções puras."""

import importlib.util
import math
import re
from pathlib import Path

import pytest

_ARQ = Path(__file__).resolve().parents[2] / "scripts" / "malhas_ibge.py"
_spec = importlib.util.spec_from_file_location("malhas_ibge", _ARQ)
malhas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(malhas)

VIEWBOX = (874, 894)


def _quadrado(x0, y0, lado):
    return [[x0, y0], [x0 + lado, y0], [x0 + lado, y0 + lado], [x0, y0 + lado], [x0, y0]]


def test_xy_origem_e_ponto_conhecido():
    assert malhas.xy(malhas.LON0, malhas.LAT_MAX) == (0.0, 0.0)
    x, y = malhas.xy(-50.0, -14.0)
    assert x == pytest.approx(24.1 * 22.8 * math.cos(math.radians(-14.0)))
    assert y == pytest.approx(19.35 * 22.8)
    # Norte para cima: latitude menor fica mais abaixo; longitude maior, mais à direita.
    assert malhas.xy(-50, -20)[1] > y and malhas.xy(-40, -14)[0] > x


@pytest.mark.parametrize(
    "lon_lat",
    [
        (-34.79, -7.15),  # Ponta do Seixas (leste)
        (-53.37, -33.75),  # Chuí (sul)
        (-60.21, 5.27),  # Monte Caburaí (norte)
        (-73.99, -7.54),  # Serra do Divisor (oeste)
    ],
)
def test_extremos_do_brasil_cabem_no_viewbox(lon_lat):
    x, y = malhas.xy(*lon_lat)
    assert 0 <= x <= VIEWBOX[0] and 0 <= y <= VIEWBOX[1]


def test_anel_relativo_sem_pontos_repetidos():
    lon, lat = malhas.LON0, malhas.LAT_MAX
    passo = 1 / (malhas.K * malhas.COS)  # 1 unidade do mapa em x
    coords = [[lon, lat], [lon + passo, lat], [lon + passo, lat], [lon, lat]]
    d = malhas.anel(coords, 2)
    # Começa absoluto, segue relativo, o ponto repetido some e o anel fecha.
    assert d == "M0 0l1 0l-1 0z"


def test_caminho_polygon_e_multipolygon():
    q1 = _quadrado(-50, -10, 1)
    q2 = _quadrado(-45, -20, 2)
    d1, bbox1 = malhas.caminho({"type": "Polygon", "coordinates": [q1]})
    assert re.fullmatch(r"M[-\d. ]+(l[-\d. ]+)+z", d1)
    xs = [malhas.xy(*c)[0] for c in q1]
    ys = [malhas.xy(*c)[1] for c in q1]
    assert bbox1 == [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)]

    d2, bbox2 = malhas.caminho({"type": "MultiPolygon", "coordinates": [[q1], [q2]]})
    assert d2.count("M") == 2 and d2.count("z") == 2
    assert d2.startswith(d1)
    # A caixa do MultiPolygon cobre os dois polígonos.
    assert bbox2[0] == bbox1[0] and bbox2[1] == bbox1[1]
    assert bbox2[2] > bbox1[2] and bbox2[3] > bbox1[3]


def test_caminho_com_buraco_gera_dois_aneis():
    externo = _quadrado(-50, -10, 4)
    buraco = _quadrado(-49, -9, 1)
    d, _ = malhas.caminho({"type": "Polygon", "coordinates": [externo, buraco]})
    assert d.count("M") == 2


def test_polylabel_no_quadrado_da_o_centro_e_meio_lado():
    x, y, r = malhas.polylabel([_quadrado(0, 0, 10)])
    assert x == pytest.approx(5, abs=0.1) and y == pytest.approx(5, abs=0.1)
    assert r == pytest.approx(5, abs=0.1)


def test_polylabel_em_u_fica_dentro_e_fora_do_vao():
    # U de 30 x 30 com vão central de 10 de largura e 20 de altura (aberto em cima).
    u = [[0, 0], [30, 0], [30, 30], [20, 30], [20, 10], [10, 10], [10, 30], [0, 30], [0, 0]]
    x, y, r = malhas.polylabel([u])
    assert malhas._dist_poligono(x, y, [u]) > 0
    assert not (10 < x < 20 and y > 10)  # não cai no vão
    assert r == pytest.approx(malhas._dist_poligono(x, y, [u]), abs=1e-6)
    # O maior círculo fica na junção da base com uma perna, a igual distância das duas
    # paredes externas e do canto interno (10, 10): r = 10·√2 / (1 + √2) ≈ 5,86.
    assert r == pytest.approx(10 * math.sqrt(2) / (1 + math.sqrt(2)), abs=0.3)


def test_polylabel_desvia_do_buraco():
    externo = _quadrado(0, 0, 10)
    buraco = _quadrado(4, 4, 2)
    x, y, r = malhas.polylabel([externo, buraco])
    assert malhas._dist_poligono(x, y, [externo, buraco]) > 0
    assert not (4 <= x <= 6 and 4 <= y <= 6)


def test_polylabel_degenerado():
    assert malhas.polylabel([[[1, 1], [5, 1], [1, 1]]]) == (1, 1, 0.0)


def test_ponto_rotulo_no_maior_poligono():
    pequeno = _quadrado(-60, -10, 0.5)
    grande = _quadrado(-45, -20, 3)
    geo = {"type": "MultiPolygon", "coordinates": [[pequeno], [grande]]}
    x, y, r = malhas.ponto_rotulo(geo, 1)
    gx0, gy0 = malhas.xy(-45, -17)  # canto superior esquerdo do grande no mapa
    gx1, gy1 = malhas.xy(-42, -20)
    assert gx0 < x < gx1 and gy0 < y < gy1
    lado = gx1 - gx0
    assert r == pytest.approx(min(lado, gy1 - gy0) / 2, abs=0.2)
    assert all(v == round(v, 1) for v in (x, y, r))
    # Polygon simples dá o mesmo que o MultiPolygon com um polígono só.
    assert malhas.ponto_rotulo({"type": "Polygon", "coordinates": [grande]}, 1) == [x, y, r]
