# ruff: noqa: E501  (recortes de linhas reais do TSE, mais legíveis numa linha só)
import csv
import io
import zipfile
from decimal import Decimal

from sqlalchemy import insert, select, update

from app.models import BemDeclarado, CampanhaResumo, Candidatura, Parlamentar
from ingestion.tse import bens, campanha, candidaturas, comum_tse
from tests.test_api import _ingestao, _popular

# Recortes de linhas reais dos arquivos do TSE (só as colunas usadas).
CAND = [
    {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SC", "SG_UE": "SC", "NM_UE": "SANTA CATARINA",
     "DS_CARGO": "GOVERNADOR", "SQ_CANDIDATO": "240001679805", "NR_CANDIDATO": "11",
     "NM_CANDIDATO": "ESPERIDIÃO AMIN HELOU FILHO", "NM_URNA_CANDIDATO": "ESPERIDIÃO AMIN",
     "NR_CPF_CANDIDATO": "11268786934", "DS_SITUACAO_CANDIDATURA": "APTO", "SG_PARTIDO": "PP",
     "DS_SIT_TOT_TURNO": "2º TURNO"},
    {"ANO_ELEICAO": "2022", "NR_TURNO": "2", "SG_UF": "SC", "SG_UE": "SC", "NM_UE": "SANTA CATARINA",
     "DS_CARGO": "GOVERNADOR", "SQ_CANDIDATO": "240001679805", "NR_CANDIDATO": "11",
     "NM_CANDIDATO": "ESPERIDIÃO AMIN HELOU FILHO", "NM_URNA_CANDIDATO": "ESPERIDIÃO AMIN",
     "NR_CPF_CANDIDATO": "11268786934", "DS_SITUACAO_CANDIDATURA": "APTO", "SG_PARTIDO": "PP",
     "DS_SIT_TOT_TURNO": "NÃO ELEITO"},
    {"ANO_ELEICAO": "2024", "NR_TURNO": "1", "SG_UF": "SC", "SG_UE": "80691", "NM_UE": "CAMPOS NOVOS",
     "DS_CARGO": "VEREADOR", "SQ_CANDIDATO": "240002", "NR_CANDIDATO": "11111",
     "NM_CANDIDATO": "FULANO", "NM_URNA_CANDIDATO": "FULANO", "NR_CPF_CANDIDATO": "-4",
     "DS_SITUACAO_CANDIDATURA": "APTO", "SG_PARTIDO": "PP", "DS_SIT_TOT_TURNO": "#NULO"},
]  # fmt: skip


def _zip(arquivos: dict[str, list[dict[str, str]]]) -> bytes:
    """Monta um zip como os do TSE: CSV com ';', em latin-1."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for nome, linhas in arquivos.items():
            texto = io.StringIO()
            escritor = csv.DictWriter(texto, fieldnames=list(linhas[0]), delimiter=";")
            escritor.writeheader()
            escritor.writerows(linhas)
            z.writestr(nome, texto.getvalue().encode("latin-1"))
    return buffer.getvalue()


def test_normalizar_fica_com_o_ultimo_turno_e_descarta_cpf_mascarado():
    registros = candidaturas.normalizar(CAND)
    assert len(registros) == 2
    governador = next(r for r in registros if r["cargo"] == "GOVERNADOR")
    assert governador["situacao_turno"] == "NÃO ELEITO"
    assert governador["cpf"] == "11268786934"
    assert governador["nome_urna"] == "Esperidião Amin"
    assert governador["unidade"] == "Santa Catarina"
    vereador = next(r for r in registros if r["cargo"] == "VEREADOR")
    assert vereador["cpf"] is None and vereador["situacao_turno"] is None


def test_linhas_ignora_o_arquivo_brasil_que_repete_os_estados():
    payload = _zip(
        {"consulta_cand_2022_SC.csv": CAND[:1], "consulta_cand_2022_BRASIL.csv": CAND[:1]}
    )
    assert len(list(comum_tse.linhas(payload, "consulta_cand_"))) == 1


def test_cpf_de_senador_so_com_nome_unico():
    registros = [
        {"cargo": "SENADOR", "uf": "SC", "nome": "Fulano de Tal", "cpf": "1"},
        {"cargo": "1º SUPLENTE", "uf": "SP", "nome": "Homonimo Silva", "cpf": "2"},
        {"cargo": "SENADOR", "uf": "SP", "nome": "Homonimo Silva", "cpf": "3"},
        {"cargo": "GOVERNADOR", "uf": "RJ", "nome": "Outro Nome", "cpf": "4"},
    ]
    senadores = [(1, "SC", "FULANO DE TAL"), (2, "SP", "Homônimo Silva"), (3, "RJ", "Outro Nome")]
    assert candidaturas.cpfs_de_senadores(registros, senadores) == {1: "1"}


def test_origem_da_receita_separa_dinheiro_publico():
    assert (
        campanha.origem_da_receita("FUNDO ESPECIAL", "Recursos de partido político")
        == "Fundo eleitoral"
    )
    assert campanha.origem_da_receita("FUNDO PARTIDARIO", None) == "Fundo partidário"
    assert (
        campanha.origem_da_receita("OUTROS RECURSOS", "Recursos de pessoas físicas")
        == "Pessoas físicas"
    )
    assert (
        campanha.origem_da_receita("OUTROS RECURSOS", "Rendimentos de aplicações financeiras")
        == "Outras origens"
    )


def test_carga_bens_e_campanha_ligadas_pelo_cpf(client, session):
    _popular(session)
    deputado = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).first()
    session.execute(
        update(Parlamentar).where(Parlamentar.id == deputado.id).values(cpf="11268786934")
    )
    ingestao = _ingestao(session)
    assert (
        candidaturas.carregar_registros(session, candidaturas.normalizar(CAND), 2022, ingestao.id)
        == 1
    )
    mapa = dict(session.execute(select(Candidatura.sq_candidato, Candidatura.id)).all())

    linhas_bens = [
        {"SQ_CANDIDATO": "240001679805", "NR_ORDEM_BEM_CANDIDATO": "1", "DS_TIPO_BEM_CANDIDATO": "Casa",
         "DS_BEM_CANDIDATO": "Casa em Florianópolis", "VR_BEM_CANDIDATO": "750000,00"},
        {"SQ_CANDIDATO": "999", "NR_ORDEM_BEM_CANDIDATO": "1", "DS_TIPO_BEM_CANDIDATO": "Casa",
         "DS_BEM_CANDIDATO": "De outra pessoa", "VR_BEM_CANDIDATO": "1,00"},
    ]  # fmt: skip
    normalizados = bens.normalizar(linhas_bens, mapa)
    assert [b["valor"] for b in normalizados] == [Decimal("750000.00")]

    receitas = [
        {"SQ_CANDIDATO": "240001679805", "DS_FONTE_RECEITA": "FUNDO ESPECIAL", "DS_ORIGEM_RECEITA": "Recursos de partido político",
         "NR_CPF_CNPJ_DOADOR": "1", "VR_RECEITA": "1000,00"},
        {"SQ_CANDIDATO": "240001679805", "DS_FONTE_RECEITA": "OUTROS RECURSOS", "DS_ORIGEM_RECEITA": "Recursos de pessoas físicas",
         "NR_CPF_CNPJ_DOADOR": "2", "VR_RECEITA": "50,50"},
        {"SQ_CANDIDATO": "240001679805", "DS_FONTE_RECEITA": "OUTROS RECURSOS", "DS_ORIGEM_RECEITA": "Recursos de pessoas físicas",
         "NR_CPF_CNPJ_DOADOR": "2", "VR_RECEITA": "49,50"},
    ]  # fmt: skip
    despesas = [
        {"SQ_CANDIDATO": "240001679805", "DS_ORIGEM_DESPESA": "Despesas com pessoal", "VR_DESPESA_CONTRATADA": "800,00"},
    ]  # fmt: skip
    [resumo] = campanha.resumir(receitas, despesas, mapa)
    assert resumo["receitas_total"] == Decimal("1100.00")
    assert resumo["receitas_por_origem"] == {"Fundo eleitoral": 1000.0, "Pessoas físicas": 100.0}
    assert resumo["numero_doadores"] == 1
    assert resumo["despesas_por_tipo"] == {"Despesas com pessoal": 800.0}

    session.execute(insert(BemDeclarado), normalizados)
    session.execute(insert(CampanhaResumo), [resumo])
    session.flush()

    corpo = client.get(f"/parlamentares/{deputado.id}/candidatura").json()
    assert corpo["candidaturas"][0]["cargo"] == "Governador"
    assert corpo["bens"]["total"] == 750000.0 and corpo["bens"]["anterior"] is None
    # Governador não é o cargo do mandato de deputado: não há campanha "do mandato".
    assert corpo["campanha"] is None
