from datetime import date

from ingestion import comum
from ingestion.receita import socios

# Resposta real da API do Querido Diário (09/10/2026), com um sócio pessoa física.
RESPOSTA = {"total_partners": 2, "partners": [
    {"identificador_socio": "2 - PESSOA FÍSICA", "razao_social": "JOSE ROBERTO TAVARES",
     "cnpj_cpf_socio": "***606618**", "qualificacao_socio": "49 - Sócio-Administrador",
     "data_entrada_sociedade": "01/02/2010"},
    {"identificador_socio": "1 - PESSOA JURÍDICA", "razao_social": "FBK HOLDING LTDA",
     "cnpj_cpf_socio": "44305929000102", "qualificacao_socio": "22 - Sócio"},
]}  # fmt: skip


def test_socios_pessoa_fisica_e_ligacao_forte():
    lista = socios.socios_pessoa_fisica(RESPOSTA)
    assert lista == [
        {
            "meio": "606618",
            "nome": "JOSE ROBERTO TAVARES",
            "qualificacao": "Sócio-Administrador",
            "entrada": date(2010, 2, 1),
        }
    ]
    chave = ("606618", comum.chave_nome("José Roberto Tavares"))
    assert socios.ligar(lista, {chave: {7}}) == [(7, lista[0])]
    assert socios.ligar(lista, {chave: {7, 8}}) == []  # ambíguo: não liga
