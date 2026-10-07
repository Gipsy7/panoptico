import io
import zipfile
from decimal import Decimal

from sqlalchemy import insert, select

from app.models import EmendaPagamento, Municipio, Parlamentar
from ingestion import comum
from ingestion.transparencia import emendas
from tests.test_api import _popular

CAB_FAV = (
    "Código da Emenda;Código do Autor da Emenda;Nome do Autor da Emenda;Número da emenda;"
    "Tipo de Emenda;Ano/Mês;Código do Favorecido;Favorecido;Natureza Jurídica;"
    "Tipo Favorecido;UF Favorecido;Município Favorecido;Valor Recebido"
)


def _zip(**arquivos: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for nome, conteudo in arquivos.items():
            z.writestr(nome, conteudo.encode("latin-1"))
    return buffer.getvalue()


def test_chave_nome():
    assert comum.chave_nome("Dr. Flávio") == "DR FLAVIO"
    assert comum.chave_nome("Sant'Ana do Livramento") == "SANT ANA DO LIVRAMENTO"


def test_normalizar_pagamentos_filtra_natureza_tipo_e_ano():
    ind = "Emenda Individual - Transferências Especiais"
    linhas = [
        f"202512340001;1234;FULANO;0001;{ind};202603;1;PREFEITURA X;Município;PJ;SP;"
        "SÃO PAULO;1.000,50",
        f"202512340001;1234;FULANO;0001;{ind};202603;2;CAIXA;Sociedade de Economia Mista;PJ;"
        "DF;BRASÍLIA;999,00",
        "202571280004;7128;BANCADA;0004;Emenda de Bancada;202609;3;P;Município;PJ;TO;X;5,00",
        f"202012340001;1234;FULANO;0001;{ind};202103;1;P;Município;PJ;SP;SÃO PAULO;7,00",
        f"Sem informação;1234;FULANO;0001;{ind};202103;1;P;Município;PJ;SP;SÃO PAULO;7,00",
        f"202512340002;1234;FULANO;0002;{ind};202604;4;SANTA CASA;Associação Privada;PJ;SP;"
        "SÃO PAULO;10,00",
    ]
    conteudo = _zip(**{emendas.ARQUIVO_FAVORECIDOS: "\n".join([CAB_FAV, *linhas])})
    pagamentos = emendas.normalizar_pagamentos(conteudo, 2023)
    assert [(p["grupo"], p["valor"]) for p in pagamentos] == [
        ("prefeitura", Decimal("1000.50")),
        ("entidade", Decimal("10.00")),
    ]


def test_resolver_municipios_exato_aproximado_e_fora():
    municipios = [
        ("3550308", "SP", "SAO PAULO"),
        ("4317103", "RS", "SANT ANA DO LIVRAMENTO"),
    ]
    pagamentos = [
        {"uf": "SP", "municipio_nome": "SÃO PAULO", "valor": 1},
        {"uf": "RS", "municipio_nome": "SANTANA DO LIVRAMENTO", "valor": 2},
        {"uf": "SP", "municipio_nome": "EMBU", "valor": 3},
    ]
    resolvidos, fora = emendas.resolver_municipios(pagamentos, municipios)
    assert [r["municipio_ibge"] for r in resolvidos] == ["3550308", "4317103"]
    assert fora == 1
    assert "uf" not in resolvidos[0]


def test_vincular_autores_pelo_nome_mais_recente_e_sem_ambiguidade():
    registros = [
        {"individual": True, "autor_codigo": "1", "ano": 2023, "autor_nome": "NOME ANTIGO"},
        {"individual": True, "autor_codigo": "1", "ano": 2025, "autor_nome": "DR. FLÁVIO"},
        {"individual": True, "autor_codigo": "2", "ano": 2025, "autor_nome": "HOMONIMO"},
        {"individual": False, "autor_codigo": "3", "ano": 2025, "autor_nome": "BANCADA"},
    ]
    parlamentares = [(10, "Dr Flávio"), (20, "Homônimo"), (21, "Homonimo")]
    assert emendas.vincular_autores(registros, parlamentares) == {"1": 10}


def test_emendas_municipio_endpoint(client, session):
    _popular(session)
    session.execute(
        insert(Municipio),
        [{"ibge": "1600303", "nome": "Macapá", "uf": "AP", "nome_chave": "MACAPA"}],
    )
    deps = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).all()
    base = {
        "emenda_codigo": "x", "ano_mes": 202601, "autor_codigo": "1", "autor_nome": "A",
        "favorecido": "F", "favorecido_codigo": "1", "natureza": "Município",
        "municipio_ibge": "1600303",
    }  # fmt: skip
    session.execute(
        insert(EmendaPagamento),
        [
            {**base, "ano_emenda": 2025, "parlamentar_id": deps[0].id, "grupo": "prefeitura",
             "valor": Decimal("100")},
            {**base, "ano_emenda": 2026, "parlamentar_id": deps[0].id, "grupo": "entidade",
             "valor": Decimal("50")},
            {**base, "ano_emenda": 2026, "parlamentar_id": None, "grupo": "prefeitura",
             "autor_codigo": "9", "autor_nome": "EX DEPUTADO", "valor": Decimal("30")},
        ],
    )  # fmt: skip
    session.flush()

    corpo = client.get("/municipios/1600303/emendas").json()
    assert (corpo["total"], corpo["total_prefeitura"], corpo["total_entidades"]) == (180, 130, 50)
    assert [a["ano"] for a in corpo["por_ano"]] == [2025, 2026]
    assert corpo["parlamentares"][0]["total"] == 150
    assert corpo["parlamentares"][0]["do_estado"] == (deps[0].uf == "AP")
    assert corpo["outros_autores"] == [{"autor_nome": "EX DEPUTADO", "total": 30.0}]
    assert corpo["numero_autores"] == 2
    assert client.get("/municipios/0000000/emendas").status_code == 404
