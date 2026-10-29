# ruff: noqa: E501  (recortes de linhas reais do SICONFI, mais legíveis numa linha só)
from decimal import Decimal

from app.models import ContasMunicipio, Municipio
from ingestion.siconfi import contas

# Blumenau (4202404), DCA 2024, Anexo I-C: contas reais de transferências do estado.
_B = "Receitas Brutas Realizadas"
_F = "Deduções - FUNDEB"
RECEITAS_BLUMENAU = [
    {"cod_conta": "RO1.7.2.0.00.0.0", "coluna": _B, "valor": 577040532.63},
    {"cod_conta": "RO1.7.2.0.00.0.0", "coluna": _F, "valor": 96061366.36},
    {"cod_conta": "RO1.7.2.1.00.0.0", "coluna": _B, "valor": 480600017.97},
    {"cod_conta": "RO1.7.2.1.50.0.0", "coluna": _B, "valor": 379411143.31},
    {"cod_conta": "RO1.7.2.1.50.0.0", "coluna": _F, "valor": 75882227.61},
    {"cod_conta": "RO1.7.2.1.51.0.0", "coluna": _B, "valor": 96414300.51},
    {"cod_conta": "RO1.7.2.1.52.0.0", "coluna": _B, "valor": 4481398.67},
    {"cod_conta": "RO1.7.2.1.53.0.0", "coluna": _B, "valor": 293175.48},
    {"cod_conta": "RO1.7.2.3.00.0.0", "coluna": _B, "valor": 80659582.76},
    {"cod_conta": "RO1.7.2.4.00.0.0", "coluna": _B, "valor": 5543177.21},
    {"cod_conta": "RO1.7.2.9.00.0.0", "coluna": _B, "valor": 10237754.69},
    {"cod_conta": "RO2.4.2.0.00.0.0", "coluna": _B, "valor": 47991012.83},
    {"cod_conta": "RO2.4.2.2.00.0.0", "coluna": _B, "valor": 15138044.16},
    {"cod_conta": "RO2.4.2.9.00.0.0", "coluna": _B, "valor": 32852968.67},
    {"cod_conta": "RO1.7.1.0.00.0.0", "coluna": _B, "valor": 464144237.07},  # União: fora
]  # fmt: skip


def test_repasses_do_estado_por_tipo_somam_o_total():
    r = contas.repasses_estado(RECEITAS_BLUMENAU)
    assert r["total"] == 625031545.46  # 1.7.2 + 2.4.2
    assert (r["icms"], r["ipva"], r["ipi"], r["cide"]) == (
        379411143.31,
        96414300.51,
        4481398.67,
        293175.48,
    )
    assert r["royalties"] == 0
    assert r["sus"] == 80659582.76
    assert r["convenios"] == round(5543177.21 + 15138044.16, 2)
    assert r["outras"] == round(10237754.69 + 32852968.67, 2)  # o resto: 1.7.2.9 + 2.4.2.9
    partes = sum(v for k, v in r.items() if k not in ("total", "fundeb"))
    assert round(partes, 2) == r["total"]
    assert r["fundeb"] == 96061366.36


def test_repasses_do_estado_sem_conta_e_nulo_e_fundeb_negativo_vira_modulo():
    assert contas.repasses_estado([]) is None
    assert (
        contas.repasses_estado(
            [x for x in RECEITAS_BLUMENAU if x["cod_conta"].startswith("RO1.7.1")]
        )
        is None
    )
    negativo = [{**x, "valor": -x["valor"]} if x["coluna"] == _F else x for x in RECEITAS_BLUMENAU]
    assert contas.repasses_estado(negativo)["fundeb"] == 96061366.36
    # Só a conta de capital: vale ela.
    capital = [x for x in RECEITAS_BLUMENAU if x["cod_conta"].startswith("RO2.4.2")]
    assert contas.repasses_estado(capital)["total"] == 47991012.83
    # recortar() leva o recorte junto.
    assert (
        contas.recortar("4202404", RECEITAS_BLUMENAU, [])["transf_estado"]["icms"] == 379411143.31
    )


def _repasse(total, icms=0.0, convenios=0.0):
    return {"total": total, "icms": icms, "ipva": 0, "ipi": 0, "cide": 0, "royalties": 0,
            "sus": 0, "convenios": convenios, "outras": round(total - icms - convenios, 2),
            "fundeb": round(icms * 0.2, 2)}  # fmt: skip


def _conta(ibge, ano, populacao, transf_estado):
    return ContasMunicipio(municipio_ibge=ibge, ano=ano, populacao=populacao,
                           receita_total=Decimal("1"), despesa_paga=Decimal("1"),
                           despesa_por_area={}, transf_estado=transf_estado)  # fmt: skip


def _municipios(session):
    session.add_all(
        [
            Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"),
            Municipio(ibge="4205407", nome="Florianópolis", uf="SC", nome_chave="FLORIANOPOLIS"),
            Municipio(ibge="4200101", nome="Não enviou", uf="SC", nome_chave="NAO ENVIOU"),
            Municipio(ibge="3550308", nome="São Paulo", uf="SP", nome_chave="SAO PAULO"),
            Municipio(ibge="5300108", nome="Brasília", uf="DF", nome_chave="BRASILIA"),
        ]
    )
    session.flush()


def test_repasses_estaduais_da_cidade_com_media_do_estado(client, session):
    _municipios(session)
    session.add_all(
        [
            _conta("4202404", 2024, 100, _repasse(1000, icms=600, convenios=100)),
            _conta("4202404", 2023, 100, _repasse(800, icms=500)),
            _conta("4205407", 2024, 200, _repasse(1000, icms=1000)),
            _conta("3550308", 2024, 10, _repasse(99999, icms=99999)),  # outro estado: fora
            _conta("4200101", 2023, 50, _repasse(10, icms=10)),  # não enviou 2024
        ]
    )
    session.flush()
    corpo = client.get("/municipios/4202404/repasses-estaduais").json()
    assert corpo["disponivel"] and corpo["ano"] == 2024
    assert (corpo["total"], corpo["por_habitante"]) == (1000.0, 10.0)
    # Média simples de 10 (Blumenau) e 5 (Florianópolis); "Não enviou" fica de fora em 2024.
    assert (
        corpo["media_uf_por_habitante"],
        corpo["municipios_na_media"],
        corpo["municipios_uf"],
    ) == (7.5, 2, 3)
    tipos = {t["chave"]: t for t in corpo["tipos"]}
    assert set(tipos) == {"icms", "convenios", "outras"}  # tipos zerados não são listados
    assert tipos["icms"]["por_lei"] and not tipos["convenios"]["por_lei"]
    assert (tipos["icms"]["por_habitante"], tipos["icms"]["media_uf_por_habitante"]) == (6.0, 5.5)
    # Florianópolis não teve convênio: entra como zero na média.
    assert tipos["convenios"]["media_uf_por_habitante"] == 0.5
    assert (corpo["parte_por_lei"], corpo["percentual_por_lei"]) == (600.0, 60.0)
    assert corpo["fundeb"] == 120.0
    assert corpo["anterior"] == {"ano": 2023, "total": 800.0}
    assert corpo["anos_sem_contas"] == []


def test_repasses_estaduais_quem_nao_enviou_e_df(client, session):
    _municipios(session)
    session.add_all(
        [
            _conta("4202404", 2024, 100, _repasse(1000, icms=600)),
            _conta("4205407", 2024, 200, None),  # carga antiga, sem o recorte
        ]
    )
    session.flush()
    nao_enviou = client.get("/municipios/4200101/repasses-estaduais").json()
    assert not nao_enviou["disponivel"] and nao_enviou["anos_sem_contas"] == [2024]
    assert "não enviou" in nao_enviou["motivo"]
    df = client.get("/municipios/5300108/repasses-estaduais").json()
    assert not df["disponivel"] and "Distrito Federal" in df["motivo"]
    sem_carga = client.get("/municipios/3550308/repasses-estaduais").json()
    assert not sem_carga["disponivel"] and "ainda não foram carregados" in sem_carga["motivo"]
    assert client.get("/municipios/0000000/repasses-estaduais").status_code == 404
