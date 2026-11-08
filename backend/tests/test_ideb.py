"""IDEB do INEP: planilhas montadas no formato real da divulgação de 2025 (08/11/2026)."""

import io
import json
import zipfile
from decimal import Decimal

import pytest

from app.models import Municipio
from ingestion.inep import ideb
from tests.test_api import _ingestao


def _xlsx(folhas: list[list[list[str]]]) -> bytes:
    """xlsx mínimo com texto inline, uma planilha por lista de linhas."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n, linhas in enumerate(folhas, start=1):
            xml = []
            for i, linha in enumerate(linhas, start=1):
                cels = "".join(
                    f'<c r="{chr(65 + j)}{i}" t="inlineStr"><is><t>{v}</t></is></c>'
                    for j, v in enumerate(linha)
                    if v != ""
                )
                xml.append(f'<row r="{i}">{cels}</row>')
            z.writestr(
                f"xl/worksheets/sheet{n}.xml",
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f"<sheetData>{''.join(xml)}</sheetData></worksheet>",
            )
    return buf.getvalue()


CAB_MUNICIPIO = ["SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "REDE", "VL_APROVACAO_2023",
                 "VL_OBSERVADO_2023", "VL_OBSERVADO_2025", "VL_PROJECAO_2021"]  # fmt: skip
MUNICIPIOS = [
    ["", "Ministério da Educação"],
    ["Ensino Fundamental Regular - Anos Iniciais"],
    ["Sigla da UF", "Código do Município"],
    CAB_MUNICIPIO,
    ["SC", "4202404", "Blumenau", "Estadual", "95", "5.7", "6.2999999999999998", "6.1"],
    ["SC", "4202404", "Blumenau", "Municipal", "97", "6.5999999999999996", "6.7", "6.5"],
    ["SC", "4202404", "Blumenau", "Pública", "96", "6.3", "6.6", "6.3"],
    ["SC", "4200051", "Abdon Batista", "Municipal", "90", "-", "-", "5"],  # sem nota: fora
    [],
    ["(1) Nota de rodapé que não é dado."],
]
CAB_UF = ["", "", "VL_OBSERVADO_2023", "VL_OBSERVADO_2025"]
UFS = [["Sul", "Total", "6.5", "6.6"], ["Santa Catarina", "Pública (4)", "6.4", "6.5"],
       ["R. G. do Sul", "Pública (4)", "6", "6.1"]]  # fmt: skip
BRASIL = [["Brasil", "Pública", "6", "6.1"], ["Brasil", "Privada (1)", "7.1", "7.1"]]


def _recorte() -> dict:
    rec = {"edicao": 2025, "municipios": {}, "ufs": {}, "brasil": {}}
    linhas = ideb.planilhas(_xlsx([MUNICIPIOS]))[0]
    rec["municipios"]["iniciais"] = [[r[1], r[3], r[4]] for r in ideb.notas(linhas, 3)]
    for chave, dados in (("ufs", UFS), ("brasil", BRASIL)):
        folhas = ideb.planilhas(_xlsx([[["x"], CAB_UF, *dados]] * 3))
        for etapa, f in zip(ideb.ORDEM_ETAPAS, folhas, strict=True):
            rec[chave][etapa] = [[r[0], r[1], r[2]] for r in ideb.notas(f, 1)]
    return rec


def test_notas_lidas_da_planilha():
    linhas = _recorte()
    blumenau = linhas["municipios"]["iniciais"]
    assert blumenau[1] == ["4202404", "municipal", {"2023": "6.6", "2025": "6.7"}]
    assert [r[1] for r in blumenau] == ["estadual", "municipal", "publica"]  # sem "-"
    assert {r[0] for r in linhas["ufs"]["iniciais"]} == {"Sul", "Santa Catarina", "R. G. do Sul"}


def test_normalizar_tira_regioes_e_traduz_abreviacoes():
    linhas = ideb.normalizar(_recorte())
    ufs = {(r["codigo"], r["etapa"]) for r in linhas if r["abrangencia"] == "uf"}
    assert ("SC", "medio") in ufs and ("RS", "iniciais") in ufs
    assert not any(r["codigo"] == "Sul" for r in linhas)
    br = [r for r in linhas if r["abrangencia"] == "brasil" and r["rede"] == "privada"]
    assert {r["valor"] for r in br} == {Decimal("7.1")}


def test_carga_aborta_com_poucos_municipios(session):
    with pytest.raises(ValueError):
        ideb.carregar(session, json.dumps(_recorte()).encode(), _ingestao(session, ideb.FONTE))


def test_rota_do_ideb_da_cidade(client, session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    from sqlalchemy import insert

    from app.models import IdebResultado

    ing = _ingestao(session, ideb.FONTE)
    session.execute(
        insert(IdebResultado),
        [{**r, "ingestao_id": ing.id} for r in ideb.normalizar(_recorte())],
    )
    corpo = client.get("/municipios/4202404/ideb").json()
    iniciais = corpo["etapas"][0]
    assert iniciais["etapa"] == "iniciais"
    publica = next(r for r in iniciais["redes"] if r["rede"] == "publica")
    assert publica["serie"][-1] == {"ano": 2025, "valor": 6.6}
    assert publica["uf"][-1] == {"ano": 2025, "valor": 6.5}
    assert publica["brasil"][-1] == {"ano": 2025, "valor": 6.1}
    assert [r["rede"] for r in iniciais["redes"]] == ["municipal", "estadual", "publica"]
    assert client.get("/municipios/9999999/ideb").status_code == 404
