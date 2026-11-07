"""Custo do mandato (app/services/custo_mandato.py, data/custo_mandato_congresso.csv)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models import Despesa, Parlamentar
from app.services import custo_mandato
from tests.test_api import _ingestao, _popular

UFS = sorted(
    "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
)
HOJE = date(2026, 11, 7)


def test_copia_empacotada_igual_a_versionada():
    """Se falhar: copie data/custo_mandato_congresso.csv para backend/app/dados/."""
    original = custo_mandato.CSV.parents[3] / "data" / "custo_mandato_congresso.csv"
    assert original.read_bytes() == custo_mandato.CSV.read_bytes()


def test_cada_valor_tem_fonte_e_sem_valor_tem_motivo():
    for linha in custo_mandato.tabela():
        if linha["valor_mensal"] is None:
            assert linha["observacao"], linha
            assert not linha["vigente_desde"]
        else:
            assert linha["valor_url"].startswith("https://"), linha
            assert linha["consultado_em"]


def test_cota_tem_as_27_ufs_nas_duas_casas():
    for cargo in ("deputado_federal", "senador"):
        ufs = [custo_mandato.vigente(cargo, "cota", uf, HOJE) for uf in UFS]
        assert all(linha and linha["valor_mensal"] for linha in ufs), cargo


def test_valores_conferidos_na_fonte():
    def valor(cargo, item, uf=None, em=HOJE):
        return custo_mandato.vigente(cargo, item, uf, em)["valor_mensal"]

    # Guia da Câmara (Ato da Mesa 244/2026): menor (DF) e maior (RR) limite, e SC.
    assert valor("deputado_federal", "cota", "DF") == Decimal("41612.55")
    assert valor("deputado_federal", "cota", "RR") == Decimal("58474.70")
    assert valor("deputado_federal", "cota", "SC") == Decimal("51951.42")
    # Antes de 20/02/2026 valia o Anexo do Ato 43/2009 na redação do Ato 270/2023.
    assert valor("deputado_federal", "cota", "SC", date(2026, 2, 19)) == Decimal("45671.58")
    assert valor("deputado_federal", "verba_gabinete") == Decimal("165806.07")
    assert valor("deputado_federal", "auxilio_moradia") == Decimal("4253.00")
    # Anexo do Ato do Presidente do Senado 8/2025.
    assert valor("senador", "cota", "AM") == Decimal("52798.82")
    assert valor("senador", "cota", "DF") == Decimal("36582.46")
    assert valor("senador", "auxilio_moradia") == Decimal("5500.00")
    assert valor("senador", "subsidio") == valor("deputado_federal", "subsidio")
    assert valor("senador", "verba_gabinete") is None  # não publicado


def test_cota_da_camara_2026_e_a_de_2023_corrigida_pelo_mesmo_indice():
    """O Ato 244/2026 corrige todas as UFs pelo mesmo IPCA: a razão é igual em todas."""
    razoes = {
        round(
            custo_mandato.vigente("deputado_federal", "cota", uf, HOJE)["valor_mensal"]
            / custo_mandato.vigente("deputado_federal", "cota", uf, date(2025, 6, 1))[
                "valor_mensal"
            ],
            4,
        )
        for uf in UFS
    }
    assert razoes == {Decimal("1.1375")}


def _gastos(session, casa, linhas):
    ing = _ingestao(session)
    for parlamentar_id, ano, mes, valor in linhas:
        session.add(
            Despesa(
                parlamentar_id=parlamentar_id,
                casa=casa,
                ano=ano,
                mes=mes,
                categoria="Passagens",
                valor=Decimal(valor),
                ingestao_id=ing.id,
            )
        )
    session.flush()


def test_resumo_do_deputado(session):
    _popular(session)
    deps = session.scalars(
        select(Parlamentar)
        .where(Parlamentar.casa == "camara", Parlamentar.em_exercicio.is_(True))
        .order_by(Parlamentar.id)
    ).all()
    alvo = deps[0]
    # 2026 até outubro: o alvo gastou 30.000 em jan e 20.000 em out; outro, 10.000; o resto, nada.
    _gastos(
        session,
        "camara",
        [
            (alvo.id, 2026, 1, "30000"),
            (alvo.id, 2026, 10, "20000"),
            (deps[1].id, 2026, 3, "10000"),
            (alvo.id, 2025, 5, "99999"),
        ],
    )
    r = custo_mandato.resumo(session, alvo, HOJE)

    itens = {i["item"]: i for i in r["itens"]}
    assert list(itens) == ["subsidio", "verba_gabinete", "cota", "auxilio_moradia"]
    cota = custo_mandato.vigente("deputado_federal", "cota", alvo.uf, HOJE)["valor_mensal"]
    assert itens["cota"]["valor"] == cota
    assert r["total_se_usar_tudo"] == Decimal("46366.19") + Decimal("165806.07") + cota + Decimal(
        "4253.00"
    )
    assert r["faltando"] == []
    assert (r["ano"], r["ultimo_mes"]) == (2026, 10)
    assert itens["cota"]["usou"] == Decimal("5000.00")  # 50.000 / 10 meses
    media = (Decimal("60000") / len(deps) / 10).quantize(Decimal("0.01"))
    assert itens["cota"]["media_casa"] == media
    assert itens["subsidio"]["usou_situacao"] == "fixo"
    assert itens["verba_gabinete"]["usou_situacao"] == "na_pagina_da_casa"
    assert itens["verba_gabinete"]["usou"] is None
    assert r["medidos"] == ["Salário", "Gastos do gabinete"]
    assert r["usou_total"] == Decimal("46366.19") + Decimal("5000.00")
    assert r["media_total"] == Decimal("46366.19") + media
    assert "CEAP" in itens["cota"]["oficial"] and alvo.uf in itens["cota"]["oficial"]


def test_resumo_do_senador_sem_verba_publicada_e_sem_gastos(session):
    _popular(session)
    sen = session.scalars(select(Parlamentar).where(Parlamentar.casa == "senado")).first()
    r = custo_mandato.resumo(session, sen, HOJE)
    itens = {i["item"]: i for i in r["itens"]}
    assert itens["verba_gabinete"]["valor"] is None
    assert itens["verba_gabinete"]["usou_situacao"] == "nao_publicado"
    assert r["faltando"] == ["Verba para pagar assessores"]
    assert r["total_se_usar_tudo"] == (
        Decimal("46366.19") + itens["cota"]["valor"] + Decimal("5500.00")
    )
    # Sem gastos carregados, só o salário é medido.
    assert r["ano"] is None and r["medidos"] == ["Salário"]
    assert itens["cota"]["usou"] is None
    assert itens["auxilio_moradia"]["usou_situacao"] == "nao_carregado"


def test_rota_do_perfil_traz_o_custo(client, session):
    _popular(session)
    p = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).first()
    corpo = client.get(f"/parlamentares/{p.id}").json()["remuneracao"]
    assert corpo["subsidio_mensal"] == 46366.19
    custo = corpo["custo"]
    assert [i["item"] for i in custo["itens"]] == list(custo_mandato.ORDEM)
    assert custo["itens"][1]["valor"] == 165806.07
    assert custo["itens"][1]["ato"] == "Ato da Mesa nº 243/2026"
