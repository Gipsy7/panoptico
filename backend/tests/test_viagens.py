import csv
import io
import zipfile
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models import Evento, Pessoa, ViagemFederalAno
from ingestion.transparencia import servidores, viagens

COLUNAS = ["Identificador do processo de viagem", "Número da Proposta (PCDP)", "Situação",
           "CPF viajante", "Nome", "Cargo", "Função", "Descrição Função",
           "Período - Data de início", "Período - Data de fim", "Destinos", "Motivo",
           "Valor diárias", "Valor passagens", "Valor devolução",
           "Valor outros gastos"]  # fmt: skip
# Formato real do Viagem.csv de 2025 (nomes e CPFs inventados).
LINHAS = [
    ["1", "000001/25", "Realizada", "***.123.456-**", "MARIA APARECIDA DE TESTE", "", "CNE-0001",
     "Cargo de Natureza Especial", "10/03/2025", "12/03/2025", "Recife/PE", "Reunião",
     "1.250,50", "2.000,00", "100,00", "0,00"],
    ["2", "000002/25", "Realizada", "***.123.456-**", "MARIA APARECIDA DE TESTE", "", "CNE-0001",
     "Cargo de Natureza Especial", "05/11/2025", "06/11/2025", "Brasília/DF", "Reunião",
     "800,00", "1.500,25", "0,00", "30,00"],
    ["3", "000003/25", "Não realizada", "***.123.456-**", "MARIA APARECIDA DE TESTE", "", "",
     "", "01/12/2025", "02/12/2025", "Natal/RN", "Cancelada", "999,00", "999,00", "0,00", "0,00"],
    ["4", "000004/25", "Realizada", "***.777.666-**", "MARIA APARECIDA DE TESTE", "", "", "",
     "01/12/2025", "02/12/2025", "Natal/RN", "Outra pessoa", "50,00", "0,00", "0,00", "0,00"],
    ["5", "000005/25", "Realizada", "ID123456789", "MARIA APARECIDA DE TESTE", "", "", "",
     "01/12/2025", "02/12/2025", "Natal/RN", "Estrangeiro", "50,00", "0,00", "0,00", "0,00"],
]  # fmt: skip


def _zip() -> bytes:
    texto = io.StringIO()
    escritor = csv.writer(texto, delimiter=";")
    escritor.writerow(COLUNAS)
    escritor.writerows(LINHAS)
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("2025_Viagem.csv", texto.getvalue().encode("latin-1"))
        z.writestr("2025_Trecho.csv", b"x;y\n")
    return saida.getvalue()


def _maria(session):
    maria = Pessoa(nome="Maria Aparecida de Teste", chave_nome="MARIA APARECIDA DE TESTE",
                   cpf="00012345600")  # fmt: skip
    session.add(maria)
    session.flush()
    pessoas = session.execute(select(Pessoa.id, Pessoa.cpf, Pessoa.chave_nome)).all()
    return maria, servidores.indice_pessoas(pessoas)


def test_somar_so_realizadas_da_pessoa_ligada(session):
    maria, indice = _maria(session)
    somas = viagens.somar(viagens.ler_viagens(_zip()), indice)
    assert somas == [
        {
            "pessoa_id": maria.id, "ano": 2025, "viagens": 2,
            "diarias": Decimal("2050.50"), "passagens": Decimal("3500.25"),
            "outros": Decimal("30.00"), "devolucao": Decimal("100.00"),
            "ultima_viagem": date(2025, 11, 5),
        }
    ]  # fmt: skip


def test_gravar_troca_o_ano_e_publica_o_evento(session):
    maria, indice = _maria(session)
    somas = viagens.somar(viagens.ler_viagens(_zip()), indice)
    for _ in range(2):  # idempotente
        assert viagens.gravar(session, somas, 2025, None) == 1
    assert len(list(session.scalars(select(ViagemFederalAno)))) == 1
    (ev,) = session.scalars(select(Evento).where(Evento.fonte == viagens.FONTE))
    assert ev.tipo == "viagem_federal" and ev.data == date(2025, 11, 5)
    assert ev.descricao == (
        "2 viagens a serviço em 2025: R$ 2.050,50 em diárias, R$ 3.500,25 em passagens e "
        "R$ 30,00 em outros gastos, com R$ 100,00 devolvidos (Portal da Transparência, "
        "viagens a serviço)."
    )
    assert viagens.gravar(session, [], 2025, None) == 0  # ano sem viagens da base: some
