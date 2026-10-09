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
