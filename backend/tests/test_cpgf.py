import csv
import io
import zipfile
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models import CpgfPortadorMes, Evento, Pessoa
from ingestion.transparencia import cpgf, servidores

COLUNAS = ["CÓDIGO ÓRGÃO SUPERIOR", "NOME ÓRGÃO SUPERIOR", "CÓDIGO ÓRGÃO", "NOME ÓRGÃO",
           "CÓDIGO UNIDADE GESTORA", "NOME UNIDADE GESTORA", "ANO EXTRATO", "MÊS EXTRATO",
           "CPF PORTADOR", "NOME PORTADOR", "CNPJ OU CPF FAVORECIDO", "NOME FAVORECIDO",
           "TRANSAÇÃO", "DATA TRANSAÇÃO", "VALOR TRANSAÇÃO"]  # fmt: skip


def _linha(cpf, nome, transacao, valor, mes="08"):
    org = "Ministério do Teste"
    return ["63000", org, "63000", org + " - Unidades com vínculo direto", "1", "UG", "2025",
            mes, cpf, nome, "123", "LOJA", transacao, "18/07/2025", valor]  # fmt: skip


# Formato real do CSV de agosto/2025 (nomes e CPFs inventados).
LINHAS = [
    _linha("***.123.456-**", "MARIA APARECIDA DE TESTE", "COMPRA A/V - R$ - APRES", "93,46"),
    _linha("***.123.456-**", "MARIA APARECIDA DE TESTE", "SAQUE CASH/ATM BB", "1000,00"),
    _linha("***.123.456-**", "MARIA APARECIDA DE TESTE", "COMPRA A/V - R$ - APRES", "-3,46"),
    _linha("***.777.666-**", "MARIA APARECIDA DE TESTE", "COMPRA A/V - R$ - APRES", "50,00"),
    _linha("-2", "MARIA APARECIDA DE TESTE", "COMPRA A/V - R$ - APRES", "70,00"),  # só o nome
    _linha("", "MARIA APARECIDA DE TESTE", "COMPRA A/V - R$ - APRES", "80,00"),
]


def _zip() -> bytes:
    texto = io.StringIO()
    escritor = csv.writer(texto, delimiter=";", quoting=csv.QUOTE_ALL)
    escritor.writerow(COLUNAS)
    escritor.writerows(LINHAS)
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("202508_CPGF.csv", texto.getvalue().encode("latin-1"))
    return saida.getvalue()


def _maria(session):
    maria = Pessoa(nome="Maria Aparecida de Teste", chave_nome="MARIA APARECIDA DE TESTE",
                   cpf="00012345600")  # fmt: skip
    session.add(maria)
    session.flush()
    pessoas = session.execute(select(Pessoa.id, Pessoa.cpf, Pessoa.chave_nome)).all()
    return maria, servidores.indice_pessoas(pessoas)


def test_somar_so_portador_com_cpf_parcial_e_nome_igual(session):
    maria, indice = _maria(session)
    assert cpgf.somar(cpgf.ler_cpgf(_zip()), indice) == [
        {"pessoa_id": maria.id, "orgao": "Ministério do Teste", "ano": 2025, "mes": 8,
         "transacoes": 3, "total": Decimal("1090.00"), "saques": Decimal("1000.00")}
    ]  # fmt: skip


def test_gravar_troca_o_mes_e_publica_evento_por_ano(session):
    maria, indice = _maria(session)
    somas = cpgf.somar(cpgf.ler_cpgf(_zip()), indice)
    for _ in range(2):  # idempotente
        assert cpgf.gravar(session, somas, 2025, 8, None) == 1
    setembro = [{**somas[0], "mes": 9, "transacoes": 1, "total": Decimal("10.00"),
                 "saques": Decimal(0)}]  # fmt: skip
    assert cpgf.gravar(session, setembro, 2025, 9, None) == 1  # soma os dois meses do ano
    assert len(list(session.scalars(select(CpgfPortadorMes)))) == 2
    (ev,) = session.scalars(select(Evento).where(Evento.fonte == cpgf.FONTE))
    assert ev.tipo == "cartao_corporativo" and ev.data == date(2025, 9, 1)
    assert ev.descricao == (
        "Portador(a) de cartão de pagamento do governo federal em Ministério do Teste: "
        "4 transações em 2025, R$ 1.100,00 no total (R$ 1.000,00 em saques em dinheiro) "
        "(Portal da Transparência, CPGF)."
    )
    assert cpgf.gravar(session, [], 2025, 8, None) == 1  # agosto sumiu: fica setembro


def test_meses_publicados_pela_pagina_do_portal():
    pagina = """
        arquivos.push({"ano" : "2026", "mes" : "07", "dia" : "", "origem" :  "CPGF"});
        arquivos.push({"ano" : "2026", "mes" : "08", "dia" : "", "origem" :  "CPGF"});
        arquivos.push({"ano" : "2026", "mes" : "09", "dia" : "", "origem" :  "Outra"});
    """
    assert cpgf.meses_publicados(pagina) == {(2026, 7), (2026, 8)}
