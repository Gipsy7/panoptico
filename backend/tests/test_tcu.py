from datetime import date

from ingestion.tcu import condenacoes

# Registros reais das listas do TCU (09/10/2026), com o CPF trocado.
IRREGULARES = [
    {
        "totalPaginas": 1,
        "totalElementos": 2,
        "elementos": [
            {"numeroProcessoFormatado": "001.825/2015-1", "nome": "FULANO", "tipoRegistro": "CPF",
             "numeroRegistro": "400.879.050-00", "dataTransitoEmJulgado": "02/08/2023",
             "linkDeliberacoesProcesso": "https://contas.tcu.gov.br/pesquisaJurisprudencia/#/resultado/acordao-completo/00182520151.PROC",
             "numeroAcordaoFormatado": "4206/2023-2C"},
            {"numeroProcessoFormatado": "015.398/2002-5", "nome": "EMPRESA", "tipoRegistro": "CNPJ",
             "numeroRegistro": "01.785.999/0001-94", "dataTransitoEmJulgado": "10/12/2010",
             "numeroAcordaoFormatado": "1386/2010-PL"},
        ],
    }
]  # fmt: skip
INABILITADOS = [
    {"nome": "ABDALA", "cpf": "215.805.453-00", "processo": "026.615/2020-7",
     "deliberacao": "AC-000738/2022-PL", "data_transito_julgado": "2022-07-16T03:00:00Z",
     "data_final": "2027-07-16T03:00:00Z"},
]  # fmt: skip


def test_normalizar_e_textos():
    irregular = condenacoes.normalizar_irregulares(IRREGULARES)
    inabilitado = condenacoes.normalizar_inabilitados(INABILITADOS)
    assert len(irregular) == 1 and irregular[0]["cpf"] == "40087905000"  # empresa fica de fora
    assert condenacoes.acordao("AC-000738/2022-PL") == "Acórdão 738/2022 – Plenário"
    assert condenacoes.descricao(irregular[0]) == (
        "O TCU julgou irregulares contas sob responsabilidade desta pessoa (processo TC "
        "001.825/2015-1, Acórdão 4206/2023 – 2ª Câmara), com trânsito em julgado em 02/08/2023."
    )
    hoje = date(2026, 10, 9)
    assert condenacoes.situacao(inabilitado[0], hoje) == "inabilitação até 16/07/2027"
    assert condenacoes.situacao(irregular[0], hoje) == "na lista do TCU em 09/10/2026"
    assert irregular[0]["url"].startswith("https://contas.tcu.gov.br/pesquisaJurisprudencia")
