from datetime import UTC, date, datetime
from decimal import Decimal

from app.models import (
    FonteIngestao,
    PartidoContaSoma,
    PartidoCotaMensal,
    PartidoDespesaVinculada,
    PartidoFefcFp,
)


def _soma(ano, tipo, partido, natureza, valor, categoria="Pessoal", fonte="Fundo Partidário", **kw):
    return PartidoContaSoma(
        ano=ano, tipo=tipo, partido=partido, esfera=kw.get("esfera", "Nacional"), uf="",
        fonte_recurso=fonte, natureza=natureza, categoria=categoria,
        valor=Decimal(valor), lancamentos=1,
    )  # fmt: skip


def _popular(session):
    session.add_all(
        [
            _soma(2024, "receita", "PL", "cota_tse", "1000.50"),
            _soma(
                2024, "receita", "PL", "transferencia_partidaria", "300", fonte="Outros recursos"
            ),
            _soma(2024, "receita", "PL", "outra", "50", fonte="Outros recursos"),
            _soma(2024, "despesa", "PL", "gasto", "400", "Pessoal"),
            _soma(2024, "despesa", "PL", "gasto", "100", "Aluguéis", esfera="Estadual"),
            _soma(2024, "despesa", "PL", "transferencia_diretorio", "250", "Repasse"),
            _soma(2024, "despesa", "PL", "transferencia_candidato", "700", "Repasse"),
            _soma(2024, "receita", "PT", "cota_tse", "10"),
            _soma(2023, "receita", "PL", "cota_tse", "5"),
            PartidoCotaMensal(
                ano=2024,
                mes=date(2024, 1, 1),
                partido="PL",
                fundo="Fundo Partidário",
                valor=Decimal("600.25"),
            ),
            PartidoCotaMensal(
                ano=2024,
                mes=date(2024, 2, 1),
                partido="PL",
                fundo="Fundo Partidário",
                valor=Decimal("400.25"),
            ),
            PartidoCotaMensal(
                ano=2024,
                mes=date(2024, 2, 1),
                partido="PL",
                fundo="FEFC",
                valor=Decimal("900"),
            ),
            PartidoFefcFp(
                ano=2024,
                fundo="FEFC",
                partido="PL",
                esfera="Nacional",
                genero="Feminino",
                cor_raca="",
                candidatos=3,
                valor_recebido=Decimal("300"),
                valor_minimo_cota=Decimal("0"),
                valor_partido=Decimal("900"),
            ),
            PartidoFefcFp(
                ano=2024,
                fundo="FEFC",
                partido="PL",
                esfera="Nacional",
                genero="Masculino",
                cor_raca="",
                candidatos=6,
                valor_recebido=Decimal("600"),
                valor_minimo_cota=Decimal("0"),
                valor_partido=Decimal("900"),
            ),
            PartidoFefcFp(
                ano=2024,
                fundo="FEFC",
                partido="PL",
                esfera="Nacional",
                genero="Feminino",
                cor_raca="Parda",
                candidatos=2,
                valor_recebido=Decimal("200"),
                valor_minimo_cota=Decimal("0"),
                valor_partido=Decimal("900"),
            ),
        ]
    )
    ingestao = FonteIngestao(
        fonte="tse_contas_partidarias",
        url="x",
        arquivo_raw="x",
        status="ok",
        concluido_em=datetime(2026, 10, 1, tzinfo=UTC),
    )
    session.add(ingestao)
    session.flush()


def test_lista_de_partidos_separa_gasto_de_transferencias(client, session):
    _popular(session)
    corpo = client.get("/partidos").json()
    assert corpo["ano"] == 2024  # o mais recente com dados
    assert corpo["anos_disponiveis"] == [2024, 2023]
    pl = next(p for p in corpo["partidos"] if p["sigla"] == "PL")
    assert pl["cota_fundo_partidario"] == 1000.50
    assert pl["cota_fefc"] == 900
    assert pl["receita_total"] == 1350.50
    assert pl["gasto"] == 500  # só natureza gasto: sem os R$ 250 + R$ 700 de repasses
    assert pl["repasse_candidatos"] == 700
    pt = next(p for p in corpo["partidos"] if p["sigla"] == "PT")
    assert pt["gasto"] == 0 and pt["cota_fefc"] == 0
    assert corpo["fonte_url"].startswith("https://")
    assert corpo["atualizado_em"] is not None


def test_lista_por_ano_e_ano_sem_dados(client, session):
    _popular(session)
    assert [p["sigla"] for p in client.get("/partidos?ano=2023").json()["partidos"]] == ["PL"]
    assert client.get("/partidos?ano=1999").status_code == 404


def test_lista_vazia_e_404(client):
    assert client.get("/partidos").status_code == 404


def test_detalhe_do_partido(client, session):
    _popular(session)
    corpo = client.get("/partidos/pl?ano=2024").json()  # caixa não importa
    assert corpo["sigla"] == "PL"
    assert [(m["mes"], m["fundo_partidario"], m["fefc"]) for m in corpo["cotas_mensais"]] == [
        ("2024-01-01", 600.25, 0),
        ("2024-02-01", 400.25, 900),
    ]
    assert corpo["gasto"] == 500
    assert corpo["despesas_por_categoria"] == [
        {"nome": "Pessoal", "valor": 400},
        {"nome": "Aluguéis", "valor": 100},
    ]
    fontes = {f["nome"]: f["valor"] for f in corpo["receitas_por_fonte"]}
    assert fontes == {"Fundo Partidário": 1000.50, "Outros recursos": 50}  # sem a transferência
    assert corpo["transferencias"] == {
        "recebidas_de_outros_diretorios": 300,
        "enviadas_a_outros_diretorios": 250,
        "repassadas_a_candidatos": 700,
        "outras_enviadas": 0,
    }
    fefc = corpo["fefc_fp"]
    assert fefc["fefc_total_partido"] == 900  # um valor por partido, não 3 x 900
    assert [g["nome"] for g in fefc["fefc_por_genero"]] == ["Masculino", "Feminino"]
    assert fefc["fefc_por_cor_raca"] == [{"nome": "Parda", "candidatos": 2, "valor": 200}]
    assert corpo["fonte_nome"] and corpo["fonte_url"]


def test_detalhe_sem_ano_usa_o_mais_recente_do_partido(client, session):
    _popular(session)
    assert client.get("/partidos/PL").json()["ano"] == 2024
    assert client.get("/partidos/PL?ano=2023").json()["fefc_fp"] is None
    assert client.get("/partidos/PT?ano=2023").status_code == 404
    assert client.get("/partidos/XYZ").status_code == 404


def test_detalhe_nao_expoe_despesa_vinculada(client, session):
    _popular(session)
    session.add(
        PartidoDespesaVinculada(
            ano=2024, partido="PL", esfera="Nacional", uf="", motivo="pessoa",
            categoria="Pessoal", fonte_recurso="Fundo Partidário", natureza="gasto",
            valor=Decimal("1"),
        )
    )  # fmt: skip
    session.flush()
    corpo = client.get("/partidos/PL?ano=2024").json()
    assert not any("vinculad" in chave for chave in corpo)
