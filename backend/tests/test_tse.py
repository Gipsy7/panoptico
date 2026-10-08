# ruff: noqa: E501  (recortes de linhas reais do TSE, mais legíveis numa linha só)
import csv
import io
import zipfile
from decimal import Decimal

from sqlalchemy import insert, select, update

from app.models import BemDeclarado, CampanhaResumo, Candidatura, Municipio, Parlamentar
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


def test_eleito_local_so_eleitos_de_camaras_assembleias_e_executivo():
    base = {"cargo": "VEREADOR", "situacao_turno": "ELEITO POR QP"}
    assert candidaturas.eleito_local(base)
    assert not candidaturas.eleito_local({**base, "situacao_turno": "SUPLENTE"})
    assert candidaturas.eleito_local({**base, "cargo": "PREFEITO", "situacao_turno": "ELEITO"})
    # Senadores e deputados federais entram pelo CPF, não por esta regra.
    assert not candidaturas.eleito_local({**base, "cargo": "SENADOR", "situacao_turno": "ELEITO"})
    assert candidaturas.eleito_local({"cargo": "DEPUTADO DISTRITAL", "situacao_turno": "ELEITO"})


def test_vereadores_e_estaduais_pela_api(client, session):
    session.add_all(
        [
            Municipio(ibge="2405306", nome="Januário Cicco", uf="RN", nome_chave="JANUARIO CICCO"),
            Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"),
        ]
    )
    session.flush()
    registros = [
        {"ano_eleicao": 2024, "sq_candidato": "1", "cargo": "VEREADOR", "uf": "RN", "unidade": "Boa Saúde",
         "codigo_ue": "16970", "nome": "A", "nome_urna": "Ana", "partido": "PT", "numero": "13000",
         "situacao_turno": "ELEITO POR QP", "situacao_candidatura": "APTO", "cpf": None},
        {"ano_eleicao": 2024, "sq_candidato": "2", "cargo": "VEREADOR", "uf": "SC", "unidade": "Blumenau",
         "codigo_ue": "80470", "nome": "B", "nome_urna": "Bruno", "partido": "PL", "numero": "22000",
         "situacao_turno": "SUPLENTE", "situacao_candidatura": "APTO", "cpf": None},
        {"ano_eleicao": 2024, "sq_candidato": "3", "cargo": "VEREADOR", "uf": "SC", "unidade": "Blumenau",
         "codigo_ue": "80470", "nome": "C", "nome_urna": "Carla", "partido": "MDB", "numero": "15000",
         "situacao_turno": "ELEITO POR MÉDIA", "situacao_candidatura": "APTO", "cpf": None},
    ]  # fmt: skip
    assert candidaturas.carregar_registros(session, registros, 2024, _ingestao(session).id) == 2
    session.flush()

    # "Boa Saúde" é o nome antigo de Januário Cicco no TSE.
    assert [
        v["nome_urna"] for v in client.get("/municipios/2405306/vereadores").json()["itens"]
    ] == ["Ana"]
    blumenau = client.get("/municipios/4202404/vereadores").json()
    assert blumenau["ano_eleicao"] == 2024
    assert [(v["nome_urna"], v["situacao"]) for v in blumenau["itens"]] == [
        ("Carla", "Eleito pela média (sobra de vagas)")
    ]
    detalhe = client.get(f"/eleitos/{blumenau['itens'][0]['id']}").json()
    assert (detalhe["cargo"], detalhe["unidade"], detalhe["bens"]) == ("Vereador", "Blumenau", None)
    assert client.get("/estados/SC/deputados-estaduais").json()["itens"] == []
    assert client.get("/estados/XX/deputados-estaduais").status_code == 404


def test_executivo_liga_vice_ao_titular(client, session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    base = {"ano_eleicao": 2024, "uf": "SC", "unidade": "Blumenau", "codigo_ue": "80470",
            "partido": "PL", "situacao_candidatura": "APTO", "cpf": None}  # fmt: skip
    registros = [
        {**base, "sq_candidato": "p1", "cargo": "PREFEITO", "nome": "P", "nome_urna": "Prefeito Eleito", "numero": "22", "situacao_turno": "ELEITO"},
        {**base, "sq_candidato": "v1", "cargo": "VICE-PREFEITO", "nome": "V", "nome_urna": "Vice Eleita", "numero": "22", "situacao_turno": "ELEITO"},
        {**base, "sq_candidato": "p2", "cargo": "PREFEITO", "nome": "Q", "nome_urna": "Outro", "numero": "13", "situacao_turno": "NÃO ELEITO"},
    ]  # fmt: skip
    assert candidaturas.carregar_registros(session, registros, 2024, _ingestao(session).id) == 2
    session.flush()

    corpo = client.get("/executivo?uf=SC&municipio=4202404").json()
    assert corpo["prefeito"]["titular"]["nome_urna"] == "Prefeito Eleito"
    assert corpo["prefeito"]["vice"]["nome_urna"] == "Vice Eleita"
    assert corpo["presidente"] is None and corpo["governador"] is None
    assert (
        client.get(f"/eleitos/{corpo['prefeito']['vice']['id']}").json()["cargo"] == "Vice-prefeito"
    )
    assert client.get("/executivo?uf=XX").status_code == 404


def test_lista_de_estaduais_mostra_so_a_eleicao_mais_recente(client, session):
    base = {"cargo": "DEPUTADO ESTADUAL", "uf": "RR", "unidade": "Roraima", "codigo_ue": "RR",
            "nome": "X", "partido": "PL", "numero": "22", "situacao_turno": "ELEITO POR QP",
            "situacao_candidatura": "APTO", "cpf": None}  # fmt: skip
    ingestao = _ingestao(session).id
    candidaturas.carregar_registros(
        session,
        [{**base, "ano_eleicao": 2018, "sq_candidato": "a", "nome_urna": "Antigo"}],
        2018,
        ingestao,
    )
    candidaturas.carregar_registros(
        session,
        [{**base, "ano_eleicao": 2022, "sq_candidato": "b", "nome_urna": "Atual"}],
        2022,
        ingestao,
    )
    session.flush()
    corpo = client.get("/estados/RR/deputados-estaduais").json()
    assert (corpo["ano_eleicao"], [i["nome_urna"] for i in corpo["itens"]]) == (2022, ["Atual"])


def test_votos_somam_zonas_do_ultimo_turno():
    from ingestion.tse import votos

    linhas = [
        {"SQ_CANDIDATO": "p", "NR_TURNO": "1", "QT_VOTOS_NOMINAIS_VALIDOS": "100"},
        {"SQ_CANDIDATO": "p", "NR_TURNO": "1", "QT_VOTOS_NOMINAIS_VALIDOS": "50"},
        {"SQ_CANDIDATO": "p", "NR_TURNO": "2", "QT_VOTOS_NOMINAIS_VALIDOS": "300"},
        {"SQ_CANDIDATO": "v", "NR_TURNO": "1", "QT_VOTOS_NOMINAIS_VALIDOS": "7"},
        {"SQ_CANDIDATO": "fora", "NR_TURNO": "1", "QT_VOTOS_NOMINAIS_VALIDOS": "9"},
    ]
    assert votos.somar(linhas, {"p", "v"}) == {"p": 300, "v": 7}


def test_redes_so_enderecos_web_sem_repetir():
    from ingestion.tse import redes

    linhas = [
        {"SQ_CANDIDATO": "1", "DS_URL": "https://instagram.com/fulano"},
        {"SQ_CANDIDATO": "1", "DS_URL": "HTTPS://INSTAGRAM.COM/FULANO"},
        {"SQ_CANDIDATO": "1", "DS_URL": "fulano@email.com"},
        {"SQ_CANDIDATO": "2", "DS_URL": "https://site.com"},
    ]
    assert redes.normalizar(linhas, {"1": 10}) == [
        {"candidatura_id": 10, "url": "https://instagram.com/fulano"}
    ]


def test_idade_e_titulo():
    from datetime import date

    from app.services import tse

    assert tse._idade(date(1981, 9, 18), hoje=date(2026, 9, 17)) == 44
    assert tse._idade(date(1981, 9, 18), hoje=date(2026, 9, 18)) == 45
    assert comum_tse.titulo("030193680906") == "030193680906"
    assert comum_tse.titulo("-4") is None
    assert comum_tse.data("21/02/1959") == date(1959, 2, 21)


def test_titulo_liga_candidatura_sem_cpf_ao_parlamentar(session):
    _popular(session)
    deputado = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).first()
    session.execute(
        update(Parlamentar).where(Parlamentar.id == deputado.id).values(cpf="11111111111")
    )
    ingestao = _ingestao(session).id
    base = {"uf": "SC", "unidade": "SC", "codigo_ue": "SC", "nome": "X", "nome_urna": "X",
            "partido": "PL", "numero": "2222", "situacao_candidatura": "APTO",
            "titulo": "000011112222"}  # fmt: skip
    candidaturas.carregar_registros(
        session,
        [
            {
                **base,
                "ano_eleicao": 2022,
                "sq_candidato": "f",
                "cargo": "DEPUTADO FEDERAL",
                "situacao_turno": "ELEITO POR QP",
                "cpf": "11111111111",
            }
        ],
        2022,
        ingestao,
    )
    candidaturas.carregar_registros(
        session,
        [
            {
                **base,
                "ano_eleicao": 2024,
                "sq_candidato": "m",
                "cargo": "PREFEITO",
                "situacao_turno": "NÃO ELEITO",
                "cpf": None,
                "codigo_ue": "1",
                "unidade": "Cidade",
            }
        ],
        2024,
        ingestao,
    )
    session.flush()
    ligadas = session.scalars(
        select(Candidatura.ano_eleicao).where(Candidatura.parlamentar_id == deputado.id)
    ).all()
    assert sorted(ligadas) == [2022, 2024]


def test_fotos_reduz_e_liga_pelo_nome_do_arquivo():
    from PIL import Image

    from ingestion.tse import fotos

    buffer = io.BytesIO()
    Image.new("RGB", (300, 400), "white").save(buffer, format="JPEG")
    pacote = io.BytesIO()
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("FSC240001597409_div.jpg", buffer.getvalue())
        z.writestr("FSC999_div.jpg", buffer.getvalue())  # candidatura que não guardamos
        z.writestr("leiame.pdf", b"x")
    with zipfile.ZipFile(io.BytesIO(pacote.getvalue())) as z:
        extraidas = fotos.extrair(z, {"240001597409": 7})
    assert [f["candidatura_id"] for f in extraidas] == [7]
    with Image.open(io.BytesIO(extraidas[0]["webp"])) as reduzida:
        assert (reduzida.format, reduzida.size) == ("WEBP", (240, 320))
    assert fotos.reduzir(b"nao e imagem") is None
