"""Gastos do gabinete de assembleias em carga própria (ingestion/assembleias/gastos_*.py), com
recortes reais dos portais (29/10/2026; fornecedor e beneficiário omitidos nos recortes)."""

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx
from sqlalchemy import select

from app.models import FonteIngestao, GastoLocal, MandatoLocal
from app.services import camaras
from ingestion.assembleias import (
    apelidos,
    gastos,
    gastos_alba,
    gastos_aleam,
    gastos_alepe,
    gastos_alero,
    gastos_ales,
    gastos_alpb,
)

FIX = Path(__file__).parent / "fixtures" / "gastos_assembleias"


def _texto(nome: str) -> str:
    return (FIX / nome).read_text(encoding="utf-8")


def _bytes(nome: str) -> bytes:
    return (FIX / nome).read_bytes()


# --- leitores ---------------------------------------------------------------------------------


def test_valor_br_com_virgula_ponto_e_traco():
    assert gastos.valor_br("R$ 4.669,65") == Decimal("4669.65")
    assert gastos.valor_br("13816,6") == Decimal("13816.60")
    assert gastos.valor_br("21880") == Decimal("21880.00")
    assert gastos.valor_br("-") is None
    assert gastos.valor_br("") is None


def test_alba_listagem_uma_linha_por_nota_e_ultima_pagina():
    pagina = _texto("alba_listagem.html")
    notas = gastos_alba.notas(pagina)
    assert notas == [
        {"nome": "Olivia Santana", "ano": 2025, "mes": 11,
         "categoria": "Locação de veículo terrestre", "valor": Decimal("4500.00")},
        {"nome": "Olivia Santana", "ano": 2025, "mes": 11,
         "categoria": "Locação de veículo terrestre", "valor": Decimal("2700.00")},
        {"nome": "Olivia Santana", "ano": 2025, "mes": 11,
         "categoria": "Locação de veículo terrestre", "valor": Decimal("4500.00")},
    ]  # fmt: skip
    assert gastos_alba.ultima_pagina(pagina) == 219  # 220 páginas de 20 em 2025


def test_alba_baixa_todas_as_paginas_do_ano():
    pagina = re.sub(r"page=\d+", "page=1", _texto("alba_listagem.html"))
    with respx.mock:
        rota = respx.get(gastos_alba.URL).mock(return_value=httpx.Response(200, text=pagina))
        with httpx.Client() as client:
            arquivos = gastos_alba.baixar_ano(client, 2025)
    assert sorted(arquivos) == ["2025_0000.html", "2025_0001.html"]
    assert rota.call_count == 2
    assert len(gastos_alba.ler(arquivos)) == 6


def test_alepe_soma_notas_por_rubrica_e_confere_com_o_total_do_documento():
    arquivos = {
        "deputados.json": _bytes("alepe_deputados.json"),
        "rubricas_2025.json": _bytes("alepe_rubricas_2025.json"),
        "docs_4508_2025_03.json": _bytes("alepe_docs_4508_2025_03.json"),
        "notas_6744.json": _bytes("alepe_notas_6744.json"),
        "docs_4433_2025_02.json": _bytes("alepe_docs_4433_2025_02.json"),
        "notas_6660.json": _bytes("alepe_notas_6660.json"),
    }
    linhas = gastos_alepe.ler(arquivos)
    abimael = [x for x in linhas if x["nome"] == "Abimael Santos"]
    assert sum(x["valor"] for x in abimael) == Decimal("59724")  # "total" do documento 6744
    assert {x["categoria"] for x in abimael} == {
        "Assessoria jurídica", "Consultorias e trabalhos técnicos",
        "Divulgação da atividade parlamentar",
    }  # fmt: skip
    assert all(set(x) == {"nome", "ano", "mes", "categoria", "valor"} for x in linhas)
    adalto = [x for x in linhas if x["nome"] == "Adalto Santos"]
    assert (adalto[0]["ano"], adalto[0]["mes"]) == (2025, 2)
    assert sum(x["valor"] for x in adalto) == Decimal("60000")


def test_alepe_aborta_se_as_notas_nao_batem_com_o_total():
    arquivos = {
        "deputados.json": _bytes("alepe_deputados.json"),
        "rubricas_2025.json": _bytes("alepe_rubricas_2025.json"),
        "docs_4508_2025_03.json": _bytes("alepe_docs_4508_2025_03.json"),
        "notas_6744.json": _bytes("alepe_notas_6744.json").replace(b'"12000"', b'"11000"'),
    }
    with pytest.raises(ValueError, match="6744"):
        gastos_alepe.ler(arquivos)


def test_ales_produtos_conferidos_com_o_total_e_zeros_fora():
    tabela = _texto("ales_tabela_319_2025_01a12.html")
    assert gastos_ales.produtos(tabela) == [
        ("Diárias solicitadas pelo Gabinete", Decimal("33028.89")),
        ("Passagens aéreas solicitadas pelo Gabinete", Decimal("24214.47")),
        ("Divulgação da atividade parlamentar", Decimal("3762.01")),
    ]  # Total: R$ 61.005,37
    gabinetes = gastos_ales.gabinetes(_texto("ales_gabinetes.html"))
    assert len(gabinetes) == 30 and gabinetes[1] == ("346", "Alcântaro Filho")


def test_ales_devolucao_de_diaria_desconta_e_total_que_nao_bate_aborta():
    tabela = _texto("ales_tabela_319_2025_01a12.html")
    com_devolucao = re.sub(
        r"(Devolução de diária</td>.*?)R\$ 0,00", r"\1R$ 1.000,00", tabela, count=1, flags=re.S
    ).replace("R$ 61.005,37", "R$ 60.005,37")
    assert ("Devolução de diária", Decimal("-1000.00")) in gastos_ales.produtos(com_devolucao)
    with pytest.raises(ValueError, match="total"):
        gastos_ales.produtos(tabela.replace("R$ 61.005,37", "R$ 61.005,38"))
    assert gastos_ales.produtos("<p>Nenhum: resultado foi encontrado!</p>") == []


def test_aleam_valor_liquido_por_verba_conferido_com_a_despesa_reembolsavel():
    pagina = _texto("aleam_3_2025_03.html")
    assert ("3", "Abdala Fraxe") in gastos_aleam.deputados(pagina)
    notas = gastos_aleam.notas(pagina)
    assert sum(v for _, v in notas) == Decimal("50489.94")  # "Despesa Reembolsável"
    assert notas[0] == ("Consultoria e Assessoria Juridica", Decimal("10000.00"))
    with pytest.raises(ValueError, match="reembolsável"):
        gastos_aleam.notas(pagina.replace("R$ 50.489,94", "R$ 50.489,95"))
    # sem o quadro de resumo (a página às vezes não o traz), lê as notas sem conferir
    sem_resumo = pagina.replace("Despesa Reembolsável", "Outra coisa")
    assert len(gastos_aleam.notas(sem_resumo)) == 4


def test_alero_classes_conferidas_com_o_total_pago_do_lote():
    assert gastos_alero.deputados(_texto("alero_busca.html"))[0] == ("41", "CLÁUDIA DE JESUS")
    pagina = _texto("alero_41_2025_03.html")
    notas = gastos_alero.notas(pagina)
    assert len(notas) == 39
    assert sum(v for _, v in notas) == Decimal("69943.18")  # "Total pago" do lote
    assert notas[0] == ("Consultorias", Decimal("10000.00"))
    with pytest.raises(ValueError, match="total pago"):  # notas somam mais que o pago
        gastos_alero.notas(pagina.replace("R$ 69.943,18", "R$ 69.943,17"))
    # notas que somam menos que o total pago: a diferença entra numa linha própria
    a_mais = gastos_alero.notas(pagina.replace("R$ 69.943,18", "R$ 70.943,18"))
    assert a_mais[-1] == (gastos_alero.SEM_DETALHE, Decimal("1000.00"))


def test_alero_verbas_de_saude_sem_classe_e_nota_zerada_antes_do_titulo():
    pagina = (
        '<table id="tabela"><tbody>'
        "<tr><td>Prestador: (omitido)| Classe: DIVULGAÇÃO | Data: 27/03/2025 | Valor: R$ 0,00</td>"
        "</tr><tr><td><h4>Deputado Eyder Brasil - Mes: 2/2025 - Lote: Principal - Verbas de "
        "Saúde - Total pago: R$ 1.400,00</h4></td></tr>"
        "<tr><td>Data: 08/03/2025 | Valor: R$ 1.000,00</td></tr>"
        "<tr><td>Data: 25/02/2025 | Valor: R$ 400,00</td></tr>"
        "</tbody></table>"
    )  # estrutura real de ?ano=2025&mes=2&gabinete=17 e ?ano=2025&mes=2&gabinete=46
    assert gastos_alero.notas(pagina) == [
        ("Verbas de saúde", Decimal("1000.00")),
        ("Verbas de saúde", Decimal("400.00")),
    ]


# --- gravação ---------------------------------------------------------------------------------


def _mandato(session, uf, id_externo, nome, completo=None):
    m = MandatoLocal(
        casa="assembleia", uf=uf, id_externo=id_externo, nome=nome, nome_completo=completo,
        sapl_url="https://x",
    )  # fmt: skip
    session.add(m)
    session.flush()
    return m


def _lanc(nome, mes, categoria, valor, ano=2025):
    return {"nome": nome, "ano": ano, "mes": mes, "categoria": categoria, "valor": Decimal(valor)}


def test_gravar_soma_liga_nome_exato_e_poe_o_resto_na_fila(session):
    olivia = _mandato(session, "BA", "10", "Olivia Santana")
    rosemberg = _mandato(session, "BA", "11", "Rosemberg Pinto", "Rosemberg Evangelista Pinto")
    total, avisos = gastos.gravar(
        session, uf="BA", escopo="alba_gastos", sigla="ALBA",
        lancamentos=[
            _lanc("Olivia Santana", 11, "Locação de veículo terrestre", "4500"),
            _lanc("OLIVIA SANTANA", 11, "Locação de veículo terrestre", "2700"),
            _lanc("Rosemberg Evangelista Pinto", 3, "Assessorias", "1000"),  # nome civil
            _lanc("Olivia Santanna", 11, "Assessorias", "999"),  # grafia diferente: fila
        ],
    )  # fmt: skip
    assert total == 2
    linhas = session.scalars(select(GastoLocal).order_by(GastoLocal.valor)).all()
    assert [(g.mandato_id, g.mes, g.valor) for g in linhas] == [
        (rosemberg.id, 3, Decimal("1000.00")),
        (olivia.id, 11, Decimal("7200.00")),
    ]
    assert len(avisos) == 1 and "OLIVIA SANTANNA" in avisos[0] and "999.00" in avisos[0]
    fila = apelidos.pendentes()
    assert [f["nome_fonte"] for f in fila] == ["OLIVIA SANTANNA"]


def test_gravar_reaplica_decisao_humana_e_substitui_a_carga_anterior(session):
    jose = _mandato(session, "ES", "26", "Engenheiro José Esmeraldo")
    apelidos.gravar_decisao(
        {"escopo": "ales_gastos", "nome_fonte": "JOSE ESMERALDO"}, "aceito", "teste",
        id_externo="26", nome_deputado="Engenheiro José Esmeraldo",
    )  # fmt: skip
    for valor in ("100", "250"):
        gastos.gravar(
            session, uf="ES", escopo="ales_gastos", sigla="ALES",
            lancamentos=[_lanc("JOSE ESMERALDO", 1, "Diárias", valor)],
        )  # fmt: skip
    linhas = session.scalars(select(GastoLocal).where(GastoLocal.mandato_id == jose.id)).all()
    assert [g.valor for g in linhas] == [Decimal("250.00")]


def test_gravar_aborta_sem_lancamentos_sem_casa_ou_sem_ninguem_ligado(session):
    with pytest.raises(ValueError, match="nenhum lançamento"):
        gastos.gravar(session, uf="RO", escopo="alero_gastos", sigla="ALERO", lancamentos=[])
    with pytest.raises(ValueError, match="não tem deputados"):
        gastos.gravar(
            session, uf="RO", escopo="alero_gastos", sigla="ALERO",
            lancamentos=[_lanc("Fulano", 1, "X", "1")],
        )  # fmt: skip
    _mandato(session, "RO", "41", "Cláudia de Jesus")
    with pytest.raises(ValueError, match="nenhum gasto ligado"):
        gastos.gravar(
            session, uf="RO", escopo="alero_gastos", sigla="ALERO",
            lancamentos=[_lanc("Fulano de Tal", 1, "X", "1")],
        )  # fmt: skip


def test_executar_com_portal_fora_do_ar_rele_o_ultimo_bruto(monkeypatch, tmp_path):
    from ingestion import comum

    monkeypatch.setattr(comum, "RAW_DIR", tmp_path)
    (tmp_path / "alero_gastos").mkdir()
    bruto = tmp_path / "alero_gastos" / "2026-10-28_000000.zip"
    bruto.write_bytes(gastos.empacotar({"a.html": b"x"}))
    chamado = {}

    def executar_ingestao(fonte, url, baixar, carregar, de_raw=None, **_):
        chamado["de_raw"] = de_raw
        return 7

    def falha(_client):
        raise httpx.ConnectError("fora do ar")

    monkeypatch.setattr(comum, "executar_ingestao", executar_ingestao)
    total = gastos.executar(
        fonte="alero_gastos", uf="RO", sigla="ALERO", url="https://x", baixar=falha,
        ler=lambda a: [],
    )  # fmt: skip
    assert total == 7 and chamado["de_raw"] == bruto


def test_secao_de_gastos_usa_a_fonte_e_a_data_da_carga_propria(session):
    m = _mandato(session, "BA", "10", "Olivia Santana")
    session.add(GastoLocal(mandato_id=m.id, ano=2025, mes=11, categoria="X", valor=Decimal("5")))
    quando = datetime(2026, 10, 29, tzinfo=UTC)
    session.add(
        FonteIngestao(
            fonte="alba_gastos", url="https://x", arquivo_raw="x", registros=1, status="ok",
            concluido_em=quando,
        )
    )  # fmt: skip
    session.flush()
    resumo = camaras.gastos(session, m)
    assert resumo["atualizado_em"] == quando
    assert resumo["fonte_url"] == "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias"
    assert "ALBA" in resumo["fonte_nome"]


def test_casa_sem_fonte_propria_de_gastos_nao_ganha_campos_novos(session):
    m = _mandato(session, "GO", "1", "Fulano")
    session.add(GastoLocal(mandato_id=m.id, ano=2025, mes=1, categoria="X", valor=Decimal("5")))
    session.flush()
    resumo = camaras.gastos(session, m)
    assert "fonte_nome" not in resumo and "fonte_url" not in resumo
    assert date(2025, 1, 1).year == resumo["ano"]


def test_alpb_link_da_planilha_e_gabinetes_do_seletor():
    pagina = _texto("alpb_viap_12731_2025_03.html")
    assert gastos_alpb.link_da_planilha(pagina) == (
        "https://www.al.pb.leg.br/wp-content/uploads/2025/05/"
        "202503-ADRIANO-CEZAR-GALDINO-DE-ARAUJO.ods"
    )
    gabinetes = gastos_alpb.gabinetes(pagina)
    assert len(gabinetes) == 36 and gabinetes[0] == ("12731", "Adriano Galdino")
    assert gastos_alpb.link_da_planilha("<p>sem planilha</p>") is None


def test_alpb_planilha_ods_de_2025_e_xlsx_de_2026_conferidas_com_o_total():
    ods = gastos_alpb.despesas(_bytes("alpb_12731_2025_03.ods"))
    assert sum(v for _, v in ods) == Decimal("49512.48")  # "Total de Despesas =>"
    assert ods[0] == ("Locação ou Fretamento de Veículos Automotores", Decimal("9000.00"))
    xlsx = gastos_alpb.despesas(_bytes("alpb_592_2026_08.xlsx"))
    assert sum(v for _, v in xlsx) == Decimal("42418.43")  # "Total de Despesas:"
    assert ("Serviços de Contabilidade", Decimal("9000.00")) in xlsx
    linhas = gastos_alpb.ler(
        {
            "gabinetes_2025.html": _bytes("alpb_viap_12731_2025_03.html"),
            "12731_2025_03.planilha": _bytes("alpb_12731_2025_03.ods"),
        }
    )
    assert {x["nome"] for x in linhas} == {"Adriano Galdino"}  # nome do seletor, não o civil
    assert all(set(x) == {"nome", "ano", "mes", "categoria", "valor"} for x in linhas)


def test_secao_de_gastos_diz_o_que_o_valor_significa_quando_nao_e_reembolso(session):
    es = _mandato(session, "ES", "21", "Janete de Sá")
    ba = _mandato(session, "BA", "10", "Olivia Santana")
    for m in (es, ba):
        session.add(GastoLocal(mandato_id=m.id, ano=2025, mes=1, categoria="X", valor=Decimal("5")))
    session.flush()
    assert "solicitado (reservado)" in camaras.gastos(session, es)["sobre_valor"]
    assert "não é necessariamente o valor pago" in camaras.gastos(session, es)["sobre_valor"]
    assert "sobre_valor" not in camaras.gastos(session, ba)  # reembolso: texto padrão do site
