# ruff: noqa: E501  (linhas no formato real dos arquivos da Receita)
"""Cadastro de empresas por CNPJ: validador (numérico e alfanumérico), leitura do formato da
Receita (amostra no formato real dos arquivos de 2026-10), LGPD (CPF na razão social de MEI)
e o nome completado nas rotas."""

import io
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.cnpj import cnpj_valido, digitos_verificadores, normalizar_cnpj
from app.models import DespesaFornecedor, Empresa, Municipio, PncpAnual
from app.services import destino_emendas, empresas, fornecedores
from ingestion.receita import empresas as carga

# Linhas no formato real (aspas, ";", latin-1, sem cabeçalho). O CPF do MEI é de teste (inventado);
# a prefeitura é uma amostra do tipo (natureza 1244) com o nome como a Receita grava.
EMPRESAS = (
    '"36627969";"JOSE DE TESTE 11144477735";"2135";"50";"2000,00";"01";""\n'
    '"36627981";"R WELLINGTON DE SENA LTDA";"2062";"49";"120000,00";"01";""\n'
    '"36627971";"36.627.971 JONATHAS AUGUSTO DOS SANTOS CAMILO";"2135";"50";"3000,00";"01";""\n'
    '"82892282";"MUNICIPIO DE ILHOTA";"1244";"50";"0,00";"00";"1"\n'
    '"11222333";"CAF\xc9 DO ZE 12345678901 ME";"2062";"49";"1000,00";"01";""\n'
).encode("latin-1")
ESTABELECIMENTOS = (
    '"36627969";"0001";"90";"1";"";"02";"20200101";"00";"";"";"20200101";"4712100";"";"RUA";"A";"1";"";"B";"41830595";"BA";"3849";"";"";"";"";"";"";"";"";""\n'
    '"36627981";"0001";"17";"1";"WELLINGTON SENA";"02";"20200101";"00";"";"";"20200101";"4712100";"";"RUA";"A";"1";"";"B";"41830595";"SP";"7107";"";"";"";"";"";"";"";"";""\n'
    '"82892282";"0001";"20";"1";"PREFEITURA";"02";"19970101";"00";"";"";"19970101";"8411600";"";"RUA";"A";"1";"";"B";"88370000";"SC";"8111";"";"";"";"";"";"";"";"";""\n'
    '"11222333";"0001";"81";"1";"CAFE 12345678901";"02";"20200101";"00";"";"";"20200101";"5611201";"";"RUA";"A";"1";"";"B";"88370000";"SC";"9999";"";"";"";"";"";"";"";"";""\n'
).encode("latin-1")
MUNICIPIOS = '"3849";"SALVADOR"\n"7107";"SAO PAULO"\n"8111";"ILHOTA"\n"9999";"LUGAR QUE NAO EXISTE"\n'.encode(
    "latin-1"
)


def _linhas():
    return carga.normalizar(EMPRESAS, ESTABELECIMENTOS, MUNICIPIOS)


# -- CNPJ --------------------------------------------------------------------------------------


def test_validador_numerico_como_sempre():
    assert cnpj_valido("11.222.333/0001-81")
    assert cnpj_valido("11222333000181")
    assert not cnpj_valido("11.222.333/0001-82")
    assert not cnpj_valido("00000000000000")
    assert not cnpj_valido("123")
    assert not cnpj_valido(None)


def test_validador_alfanumerico():
    # exemplo da IN RFB 2229/2024: 12.ABC.345/01DE-35
    assert digitos_verificadores("12ABC34501DE") == "35"
    assert cnpj_valido("12.ABC.345/01DE-35")
    assert cnpj_valido("12abc34501de35")  # minúsculas viram maiúsculas
    assert not cnpj_valido("12.ABC.345/01DE-36")
    assert normalizar_cnpj("12.abc.345/01de-35") == "12ABC34501DE35"
    assert normalizar_cnpj("12ABC34501DEAB") is None  # dígitos verificadores são números


# -- leitura e LGPD ----------------------------------------------------------------------------


def test_normalizar_junta_empresa_e_estabelecimento():
    por_cnpj = {x["cnpj"]: x for x in _linhas()}
    assert set(por_cnpj) == {"36627969000190", "36627981000117",
                             "82892282000120", "11222333000181"}  # fmt: skip
    ltda = por_cnpj["36627981000117"]
    assert ltda["razao_social"] == "R WELLINGTON DE SENA LTDA"
    assert ltda["nome_fantasia"] == "WELLINGTON SENA"
    assert ltda["natureza_juridica"] == "2062" and ltda["situacao"] == "02"
    assert ltda["uf"] == "SP" and ltda["municipio_receita"] == "SAO PAULO"
    assert ltda["nome_omitido"] is False


def test_razao_social_de_mei_com_cpf_nao_e_guardada():
    mei = {x["cnpj"]: x for x in _linhas()}["36627969000190"]
    assert mei["razao_social"] is None and mei["nome_omitido"] is True
    texto = repr(_linhas())
    assert "11144477735" not in texto  # CPF nunca sai da leitura


def test_cpf_em_natureza_que_nao_e_individual_so_corta_o_numero():
    cafe = {x["cnpj"]: x for x in _linhas()}["11222333000181"]
    assert cafe["razao_social"] == "CAFÉ DO ZE ME" and cafe["nome_omitido"] is False
    assert cafe["nome_fantasia"] == "CAFE"  # nome fantasia também passa por sem_cpf


def test_filtro_de_linhas_por_cnpj_e_por_raiz():
    saida = io.BytesIO()
    n = carga.filtrar_estabelecimentos(
        io.BytesIO(ESTABELECIMENTOS), {"82892282000120", "11222333000199"}, saida
    )
    assert n == 1 and saida.getvalue().startswith(b'"82892282";"0001"')
    saida = io.BytesIO()
    assert carga.filtrar_empresas(io.BytesIO(EMPRESAS), {"36627981", "82892282"}, saida) == 2


def test_ler_recorte_e_gravar_sao_idempotentes(session):
    session.add(Municipio(ibge="3550308", nome="São Paulo", uf="SP", nome_chave="SAO PAULO"))
    session.add(Municipio(ibge="4208203", nome="Ilhota", uf="SC", nome_chave="ILHOTA"))
    session.flush()
    pacote = io.BytesIO()
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("Empresas.csv", EMPRESAS)
        z.writestr("Estabelecimentos.csv", ESTABELECIMENTOS)
        z.writestr("Municipios.csv", MUNICIPIOS)
        z.writestr("referencia.txt", "2026-10\n5\n")
    linhas, referencia, interesse = carga.ler_recorte(pacote.getvalue())
    assert (referencia, interesse, len(linhas)) == ("2026-10", 5, 4)
    sem_ibge = carga.ligar_ibge(session, linhas)
    assert sem_ibge == 2  # Salvador (sem cadastro de município no teste) e o nome inventado
    assert carga.gravar(session, linhas, referencia) == 4
    assert carga.gravar(session, linhas, referencia) == 4  # de novo: sem duplicar
    session.flush()
    assert session.query(Empresa).count() == 4
    prefeitura = session.get(Empresa, "82892282000120")
    assert prefeitura.municipio_ibge == "4208203" and prefeitura.referencia == "2026-10"
    assert session.get(Empresa, "36627969000190").razao_social is None


def test_brasilapi_normaliza_com_as_mesmas_regras():
    linha = carga.normalizar_brasilapi(
        {"cnpj": "82892282000120", "razao_social": "MUNICIPIO DE ILHOTA", "nome_fantasia": "",
         "codigo_natureza_juridica": 1244, "codigo_municipio_ibge": 4208203, "uf": "SC",
         "situacao_cadastral": 2}
    )  # fmt: skip
    assert linha["natureza_juridica"] == "1244" and linha["municipio_ibge"] == "4208203"
    assert linha["situacao"] == "02" and linha["nome_fantasia"] is None
    mei = carga.normalizar_brasilapi(
        {"cnpj": "36627969000190", "razao_social": "JOSE DE TESTE 11144477735",
         "codigo_natureza_juridica": 2135}
    )  # fmt: skip
    assert mei["razao_social"] is None and mei["nome_omitido"] is True


# -- uso nas rotas -----------------------------------------------------------------------------


def _cadastro(session):
    agora = datetime.now(UTC)
    session.add_all(
        [
            Empresa(cnpj="11222333000181", razao_social="PADARIA DO ZE LTDA", natureza_juridica="2062",
                    referencia="2026-10", atualizado_em=agora),
            Empresa(cnpj="36627969000190", razao_social=None, nome_omitido=True,
                    natureza_juridica="2135", referencia="2026-10", atualizado_em=agora),
            Empresa(cnpj="82892282000120", razao_social="MUNICIPIO DE ILHOTA",
                    natureza_juridica="1244", municipio_ibge="4208203", uf="SC",
                    referencia="2026-10", atualizado_em=agora),
            Empresa(cnpj="55555555000155", razao_social="CASA FRANCISCO LTDA",
                    natureza_juridica="2062", municipio_ibge="4208203", uf="SC",
                    referencia="2026-10", atualizado_em=agora),
        ]
    )  # fmt: skip
    session.flush()


def test_fornecedores_pncp_completa_o_nome_pelo_cadastro(client, session):
    session.add(Municipio(ibge="4202008", nome="Exemplo", uf="SC", nome_chave="EXEMPLO"))
    _cadastro(session)
    for cnpj, nome, valor in [
        ("11222333000181", None, 300),  # nome vazio na fonte: vem do cadastro
        ("36627969000190", None, 200),  # MEI com CPF: nome omitido
        ("77777777000177", None, 100),  # fora do cadastro: continua sem nome
        ("82892282000120", "NOME DA FONTE", 50),  # a fonte tem nome: vale a fonte
    ]:
        session.add(PncpAnual(ano=2026, municipio_ibge="4202008", fornecedor_cnpj=cnpj,
                              fornecedor_nome=nome, quantidade=1, valor_global=Decimal(valor)))  # fmt: skip
    session.flush()
    itens = client.get("/municipios/4202008/fornecedores-pncp").json()["itens"]
    por_cnpj = {i["fornecedor_cnpj"]: i for i in itens}
    assert por_cnpj["11222333000181"]["fornecedor"] == "PADARIA DO ZE LTDA"
    assert por_cnpj["11222333000181"]["nome_omitido"] is False
    assert por_cnpj["36627969000190"]["fornecedor"] is None
    assert por_cnpj["36627969000190"]["nome_omitido"] is True
    assert por_cnpj["77777777000177"]["fornecedor"] is None
    assert por_cnpj["77777777000177"]["nome_omitido"] is False
    assert por_cnpj["82892282000120"]["fornecedor"] == "NOME DA FONTE"


def test_fornecedores_do_tce_completam_nome_vazio(client, session):
    session.add(Municipio(ibge="4202008", nome="Exemplo", uf="SC", nome_chave="EXEMPLO"))
    _cadastro(session)
    session.add_all([
        DespesaFornecedor(municipio_ibge="4202008", ano=2025, orgao="prefeitura", fornecedor="",
                          documento="11222333000181", valor_pago=Decimal(10), pagamentos=1,
                          fonte="tce_sp"),
        DespesaFornecedor(municipio_ibge="4202008", ano=2025, orgao="prefeitura", fornecedor="",
                          documento="36627969000190", valor_pago=Decimal(5), pagamentos=1,
                          fonte="tce_sp"),
    ])  # fmt: skip
    session.flush()
    itens = fornecedores.resumo(session, "4202008")["orgaos"][0]["itens"]
    por_doc = {i["documento"]: i for i in itens}
    assert por_doc["11222333000181"]["fornecedor"] == "PADARIA DO ZE LTDA"
    assert por_doc["36627969000190"]["fornecedor"] == "Não identificado"
    assert por_doc["36627969000190"]["nome_omitido"] is True
    r = client.get("/municipios/4202008/fornecedores")
    assert r.status_code == 200 and r.json()["orgaos"][0]["itens"][0]["fornecedor"]


def test_destino_de_emendas_completa_o_beneficiario(session):
    _cadastro(session)
    cadastro = empresas.nomes(session, ["11222333000181", "36627969000190"])
    vazio = SimpleNamespace(beneficiario=None, beneficiario_cnpj="11222333000181")
    assert destino_emendas._beneficiario(vazio, cadastro) == {
        "beneficiario": "PADARIA DO ZE LTDA", "nome_omitido": False}  # fmt: skip
    mei = SimpleNamespace(beneficiario=None, beneficiario_cnpj="36627969000190")
    assert destino_emendas._beneficiario(mei, cadastro) == {
        "beneficiario": None, "nome_omitido": True}  # fmt: skip
    # nome da fonte com CPF perde o número mas continua valendo
    fonte = SimpleNamespace(beneficiario="ANA 11144477735", beneficiario_cnpj="11222333000181")
    assert destino_emendas._beneficiario(fonte, cadastro)["beneficiario"] == "ANA"


def test_cnpj_para_ibge_so_de_entes_municipais(session):
    _cadastro(session)
    mapa = empresas.cnpj_para_ibge(
        session, ["82892282000120", "55555555000155", "11222333000181", "82.892.282/0001-20"]
    )
    assert mapa == {"82892282000120": "4208203"}  # a empresa privada e a sem município ficam fora
    assert empresas.cnpj_para_ibge(session, ["55555555000155"], so_municipais=False) == {
        "55555555000155": "4208203"
    }
    assert empresas.ibge_do_cnpj(session, "82.892.282/0001-20") == "4208203"
    assert empresas.ibge_do_cnpj(session, "99999999000199") is None
