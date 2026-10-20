from ingestion.assembleias import cldf


def test_autoria_em_texto_e_distribuicao():
    assert cldf.autores_de("Deputado Martins Machado, Deputado Martins Machado") == [
        "Martins Machado"
    ]
    assert cldf.nome_sem_titulo("Deputado João Cardoso ") == "João Cardoso"
    # Recortes reais da API do PLE (09/10/2026).
    props = [
        {"id": 159379, "tipoProposicao": "Requerimento", "siglaNumeroAno": "REQ 3090/2026",
         "dataLeitura": "2026-10-08", "autoria": "Deputado Martins Machado", "ementa": "Requer…"},
        {"id": 1, "tipoProposicao": "Projeto de Lei", "siglaNumeroAno": "PL 12/2026",
         "dataLeitura": "2026-02-03", "ementa": "Institui  o  Dia X.",
         "autoria": "Deputada Paula Belmonte, Deputado Martins Machado"},
        {"id": 2, "tipoProposicao": "Projeto de Lei", "siglaNumeroAno": "PL 13/2026",
         "dataLeitura": "2026-02-04", "ementa": "Y", "autoria": "Poder Executivo"},
    ]  # fmt: skip
    por = cldf.distribuir(props, {"Martins Machado", "Paula Belmonte"})
    assert por["Martins Machado"]["contagem"] == {"Requerimento": 1, "Projeto de Lei": 1}
    projeto = por["Paula Belmonte"]["projetos"][0]
    assert (projeto["numero"], projeto["ano"], projeto["primeiro_autor"]) == (12, 2026, True)
    assert projeto["ementa"] == "Institui o Dia X."
    assert por["Martins Machado"]["projetos"][0]["primeiro_autor"] is False


def test_verbas_colunas_datas_e_categorias():
    from datetime import date

    # 2026: colunas em maiúsculas e data como número do Excel; 2025: outras colunas e
    # data em mês/dia/ano (recortes reais, CPFs trocados).
    de_2026 = [{"CPF_PARLAMENTAR": "111.111.111-11", "NOME_PARLAMENTAR": "Deputado Hermeto",
                "DATA_COMPROVANTE": "46024", "VALOR_DESPESA": "5600",
                "CLASSIFICACAO": "Locação de veículo"}]  # fmt: skip
    de_2025 = [
        {"CPF do(a) Deputado(a)": "222.222.222-22", "Nome do(a) Deputado(a)": "Max Maciel",
         "Data do Recibo/NF": "1/16/2025", "Valor": "219.95",
         "Classificação": "Locação de Veículos"},
        {"CPF do(a) Deputado(a)": "222.222.222-22", "Nome do(a) Deputado(a)": "Max Maciel",
         "Data do Recibo/NF": "1/22/2025", "Valor": "10.05",
         "Classificação": "VIII - Locação de veículo"},
    ]  # fmt: skip
    linhas = cldf.padronizar(de_2026) + cldf.padronizar(de_2025)
    assert [lin["data"] for lin in linhas] == [
        date(2026, 1, 2),
        date(2025, 1, 16),
        date(2025, 1, 22),
    ]
    assert cldf.ordem_das_datas(["3/4/2025", "25/04/2025"]) == "dm"
    gastos = cldf.somar_gastos(linhas, {2025, 2026})
    assert gastos["22222222222"] == [
        {"ano": 2025, "mes": 1, "categoria": "Locação de veículo", "valor": cldf.Decimal("230.00")}
    ]


CSV_2026 = (
    "﻿ID_REGISTRO;NOME_PARLAMENTAR;CPF_PARLAMENTAR;NOME_PRESTADOR;CNPJ_PRESTADOR;"
    "CPF_PRESTADOR;NR_COMPROVANTE;DATA_COMPROVANTE;VALOR_DESPESA;CLASSIFICACAO;OBSERVACOES\n"
    "1;Jane Kléber;111.111.111-11;ELDORADO FROTAS LTDA;41.685.059/0001-48;;2533574;"
    "02/01/2026 00:00;R$ 5.600,00;Locação de veículo;\n"
    "2;Jane Kléber;111.111.111-11;SUPREMA LTDA;24.894.397/0001-70;;797;"
    "25/01/2026 00:00;R$ 649,50;VIII - Locação de Veículos;\n"
).encode()


def test_verbas_2026_csv_rotulado_como_xlsx():
    """O recurso de 2026 do catálogo diz XLSX mas é CSV (UTF-8 com BOM, ';', 'R$ 5.600,00',
    data com hora): quebrava com BadZipFile e derrubava a carga."""
    from datetime import date

    linhas = cldf.padronizar(cldf.ler_verbas(CSV_2026))
    assert [lin["data"] for lin in linhas] == [date(2026, 1, 2), date(2026, 1, 25)]
    gastos = cldf.somar_gastos(linhas, {2026})["11111111111"]
    assert gastos == [
        {"ano": 2026, "mes": 1, "categoria": "Locação de veículo", "valor": cldf.Decimal("6249.50")}
    ]


def test_verbas_2026_data_em_outra_ordem_e_valor_digitado_errado():
    from datetime import date

    # o mesmo arquivo traz "8/20/2026" (mês/dia) e "R$ 5,500,00" (vírgula no milhar)
    assert cldf._data("8/20/2026", "dm") == date(2026, 8, 20)
    assert cldf._data("02/01/2026 00:00", "dm") == date(2026, 1, 2)
    assert cldf._valor("R$ 5,500,00") == cldf.Decimal("5500.00")
    assert cldf._valor("R$ 5.600,00") == cldf.Decimal("5600.00")


def test_verbas_sem_data_viram_alerta_com_contagem_e_valor():
    # "3" (dia digitado) vira série 3 = 1900: sem data; Robério 2025 tem a categoria no valor
    linhas = cldf.padronizar(
        [
            {"NOME_PARLAMENTAR": "A", "DATA_COMPROVANTE": "3", "VALOR_DESPESA": "R$ 1.000,50"},
            {"NOME_PARLAMENTAR": "B", "DATA_COMPROVANTE": "", "VALOR_DESPESA": "V- Combustíveis"},
            {"NOME_PARLAMENTAR": "C", "DATA_COMPROVANTE": "02/01/2026", "VALOR_DESPESA": "9"},
        ]
    )
    (alerta,) = cldf.alertas_verbas(linhas, {2026})
    assert "2 de 3 linhas" in alerta and "1.000,50" in alerta and "1 com valor ilegível" in alerta


def test_verbas_html_de_erro_nao_e_planilha():
    import pytest

    with pytest.raises(ValueError):
        cldf.ler_verbas(b"<html>erro</html>")


def test_baixar_verbas_ano_ruim_vira_aviso_e_nenhum_ano_falha(monkeypatch, tmp_path):
    import pytest

    recursos = [
        {"name": "Verbas - 2026 (Até Agosto)", "format": "XLSX", "url": "u26"},
        {"name": "Verbas - 2025", "format": "XLSX", "url": "u25"},
    ]
    corpos = {"u26": CSV_2026, "u25": b"<html>403</html>"}
    monkeypatch.setattr(cldf.comum, "get_json", lambda c, u: {"result": {"resources": recursos}})
    monkeypatch.setattr(cldf.comum, "get_bytes", lambda c, u: corpos[u])
    monkeypatch.setattr(cldf.comum, "salvar_raw", lambda *a, **k: tmp_path)
    linhas = cldf.baixar_verbas(None, {2025, 2026})
    assert len(linhas) == 2  # 2025 ilegível só avisa; 2026 carrega
    corpos["u26"] = b"<html></html>"
    with pytest.raises(ValueError, match="nenhum ano"):
        cldf.baixar_verbas(None, {2025, 2026})
