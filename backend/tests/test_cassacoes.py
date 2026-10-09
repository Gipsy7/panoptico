import csv
import io
import zipfile
from datetime import date

from sqlalchemy import select

from app.models import Evento
from ingestion import pessoas as carga_pessoas
from ingestion.normalizar import numero_cnj
from ingestion.tse import cassacoes, comum_tse
from tests.test_pessoas import _cenario

CABECALHO = ["DT_GERACAO", "ANO_ELEICAO", "SG_UF", "SQ_CANDIDATO", "NR_PROCESSO", "DS_TP_MOTIVO",
             "DS_MOTIVO"]  # fmt: skip
# Linhas reais do motivo_cassacao_2024 (recortadas), mais uma com o número adulterado.
LINHAS = [
    ["08/10/2026", "2024", "PE", "170002019590", "06000934620246170112",
     "Fundamentos legais de cassação", "Abuso de poder econômico"],
    ["08/10/2026", "2024", "PE", "170002019590", "06000934620246170112",
     "Fundamentos legais de cassação", "Abuso de poder político"],
    ["08/10/2026", "2024", "SP", "250002015288", "06004729520246260189",
     "Fundamentos legais de julgamento", "Inelegibilidade infraconstitucional(LC 64/90)"],
    ["08/10/2026", "2024", "SP", "3", "06004729520246260180",
     "Fundamentos legais de julgamento", "Ausência de condição de elegibilidade"],
]  # fmt: skip


def _zip(linhas=LINHAS) -> bytes:
    texto = io.StringIO()
    escritor = csv.writer(texto, delimiter=";")
    escritor.writerow(CABECALHO)
    escritor.writerows(linhas)
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("motivo_cassacao_2024_PE.csv", texto.getvalue().encode("latin-1"))
        # O arquivo _BRASIL repete tudo: não pode contar duas vezes.
        z.writestr("motivo_cassacao_2024_BRASIL.csv", texto.getvalue().encode("latin-1"))
    return saida.getvalue()


def test_numero_cnj():
    assert numero_cnj("06000934620246170112") == "0600093-46.2024.6.17.0112"
    assert numero_cnj("0600093-46.2024.6.17.0112") == "0600093-46.2024.6.17.0112"
    assert numero_cnj("06000934620246170113") is None  # dígito verificador não confere
    assert numero_cnj("123") is None and numero_cnj(None) is None


def test_normalizar_junta_fundamentos_e_separa_tipos():
    registros = cassacoes.normalizar(comum_tse.linhas(_zip(), "motivo_cassacao_"))
    por_sq = {r["sq_candidato"]: r for r in registros}
    assert len(registros) == 3
    assert por_sq["170002019590"]["tipo"] == "cassacao"
    assert por_sq["170002019590"]["fundamentos"] == [
        "Abuso de poder econômico",
        "Abuso de poder político",
    ]
    assert por_sq["250002015288"]["tipo"] == "julgamento_candidatura"
    assert cassacoes.descricao(por_sq["250002015288"]) == (
        "O TSE registra julgamento sobre o registro da candidatura de 2024, com fundamento em: "
        "Inelegibilidade infraconstitucional(LC 64/90)."
    )
    assert por_sq["3"]["numero_processo"] is None  # número inválido não é publicado
    assert cassacoes.descricao(por_sq["170002019590"]) == (
        "O TSE registra a cassação do registro ou do diploma da candidatura de 2024. "
        "Fundamento: Abuso de poder econômico; Abuso de poder político."
    )


def test_so_pessoas_que_temos_e_na_linha_do_tempo(client, session):
    _cenario(session)  # inclui a candidatura 2024:3 (Rui Lima, vereador)
    carga_pessoas.processar(session)

    from app.models import PessoaVinculo as Vinculo
    from ingestion.pessoas import PessoaVinculo  # noqa: F401  (só para garantir o import)

    vinculo, pessoa = session.execute(
        select(Vinculo.id, Vinculo.pessoa_id).where(Vinculo.id_externo == "2024:3")
    ).one()
    registros = cassacoes.normalizar(comum_tse.linhas(_zip(), "motivo_cassacao_"))
    linhas = cassacoes.eventos(registros, {"2024:3": (vinculo, pessoa)}, ingestao_id=None)
    assert len(linhas) == 1 and linhas[0]["situacao"] == "segundo o TSE em 08/10/2026"
    session.add_all([Evento(**linha) for linha in linhas])
    session.flush()
    itens = client.get(f"/pessoas/{pessoa}/eventos").json()["itens"]
    assert [i["tipo"] for i in itens] == [
        "eleito",
        "julgamento_candidatura",
    ]  # sem data vai para o fim
    assert itens[1]["numero_processo"] is None
    assert itens[0]["data"] == str(date(2024, 10, 6))


def test_formato_antigo_de_2016_sem_tipo_nem_processo():
    texto = io.StringIO()
    escritor = csv.writer(texto, delimiter=";")
    escritor.writerow(["DT_GERACAO", "ANO_ELEICAO", "SQ_CANDIDATO", "DS_MOTIVO_CASSACAO"])
    escritor.writerow(["18/02/2021", "2016", "10000002023", "Ausência de requisito de registro "])
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("motivo_cassacao_2016_AC.csv", texto.getvalue().encode("latin-1"))
    registros = cassacoes.normalizar(comum_tse.linhas(saida.getvalue(), "motivo_cassacao_"))
    assert registros[0]["tipo"] == "julgamento_candidatura"
    assert registros[0]["numero_processo"] is None
    assert registros[0]["fundamentos"] == ["Ausência de requisito de registro"]
