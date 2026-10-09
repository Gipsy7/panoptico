from datetime import date

import httpx
import respx

from app.models import Candidatura, DiarioAto, Pessoa, PessoaVinculo
from ingestion import comum
from ingestion.diarios import atos

# Trechos reais do Querido Diário (Porto Alegre, 2025), como a API devolve: o texto do PDF
# sai com as palavras fora de ordem ("aDESIGNA" colado depois do nome).
DESIGNACAO = (
    "Portaria 719, de  (Processos  e 19/08/2025  24.0.000041687-4  21.0.000118155-3).\n \n\n"
    " MARIA ELISABETE MARQUES BONES para exercer a função honorífica de Prefeito da Praça da"
    "DESIGNA\nSaibreira, a contar de  em conformidade com o art. 2º,  do Decreto  de 17 de "
    "junho de 2021, 16/08/2025,  §1º,  21.073,\natravés"
)
CONTRATO = (
    "PREFEITO  EXTRATO DE CONTRATO PROCESSO 24.0.000132711-5  PACCONTRATO:  Nº 0639.707-70/2024."
    " Município de Porto Alegre, representado pelo Prefeito Sr. SEBASTIÃO DE ARAÚJO MELO, "
    "CNPJCONTRATANTE:  nº 92.963.560/0001-60.  Caixa Econômica Federal, CNPJCONTRATADA"
)
RESPOSTA = {
    "total_gazettes": 2,
    "gazettes": [
        {
            "territory_id": "4314902",
            "date": "2025-08-21",
            "url": "https://data.queridodiario.ok.org.br/4314902/2025-08-21/08c5.pdf",
            "excerpts": [CONTRATO, DESIGNACAO],
        },
        {
            "territory_id": "4314902",
            "date": "2025-01-21",
            "url": "https://data.queridodiario.ok.org.br/4314902/2025-01-21/407e.pdf",
            "excerpts": [CONTRATO],
        },
    ],
}


def test_achar_ato_exige_nome_completo_e_palavra_de_ato():
    tipo, trecho = atos.achar_ato("Maria Elisabete Marques Bones", DESIGNACAO)
    assert tipo == "designacao"
    assert "MARIA ELISABETE MARQUES BONES" in trecho and len(trecho) <= 500
    assert "\n" not in trecho
    # Assinatura/contrato com o nome, mas sem ato de pessoal: não é achado.
    assert atos.achar_ato("Sebastião de Araújo Melo", CONTRATO) is None
    # Só parte do nome: não é achado.
    assert atos.achar_ato("Maria Elisabete Bones", DESIGNACAO) is None
    # Nome com menos de 3 palavras não é buscado (risco de homônimo).
    assert atos.padrao_nome("Lucilene Vale") is None


def test_achar_ato_ignora_acentos_e_distingue_exoneracao():
    texto = "O PREFEITO EXONERA, a pedido, JOSÉ ROBERTO TAVARES do cargo de Secretário."
    assert atos.achar_ato("José Roberto Tavares", texto)[0] == "exoneracao"
    assert atos.achar_ato("JOSE ROBERTO TAVARES", texto.replace("JOSÉ", "JOSE"))[0] == "exoneracao"


def test_sugestoes_uma_por_diario_com_url_do_diario():
    lista = atos.sugestoes("Maria Elisabete Marques Bones", "4314902", RESPOSTA)
    assert lista == [
        {
            "municipio_ibge": "4314902",
            "data": date(2025, 8, 21),
            "tipo_ato": "designacao",
            "trecho": lista[0]["trecho"],
            "url": "https://data.queridodiario.ok.org.br/4314902/2025-08-21/08c5.pdf",
        }
    ]
    assert atos.sugestoes("Sebastião de Araújo Melo", "4314902", RESPOSTA) == []


@respx.mock
def test_buscar_usa_frase_territorio_e_data(monkeypatch):
    monkeypatch.setattr(atos, "PAUSA", 0)
    rota = respx.get(atos.URL_DIARIOS).mock(return_value=httpx.Response(200, json=RESPOSTA))
    with comum.criar_cliente() as client:
        assert atos.buscar(client, "Maria Elisabete Marques Bones", "4314902") == RESPOSTA
    params = rota.calls[0].request.url.params
    assert params["querystring"] == '"Maria Elisabete Marques Bones"'
    assert params["territory_ids"] == "4314902"
    assert params["published_since"] == "2025-01-01"
    assert "User-Agent" in rota.calls[0].request.headers


@respx.mock
def test_municipios_cobertos_so_com_data_de_disponibilidade():
    respx.get(atos.URL_CIDADES).mock(
        return_value=httpx.Response(
            200,
            json={
                "cities": [
                    {"territory_id": "4314902", "availability_date": "2022-05-09", "level": "3"},
                    {"territory_id": "1718006", "availability_date": "", "level": "0"},
                ]
            },
        )
    )
    with comum.criar_cliente() as client:
        assert atos.municipios_cobertos(client) == {"4314902"}


def test_pessoas_alvo_so_eleitos_em_municipio_coberto(session):
    def pessoa(nome, ibge, cargo, sq, turno="ELEITO"):
        p = Pessoa(nome=nome, chave_nome=comum.chave_nome(nome))
        c = Candidatura(
            ano_eleicao=2024, sq_candidato=sq, cargo=cargo, uf="RS", unidade="X",
            municipio_ibge=ibge, nome=nome, nome_urna=nome, situacao_turno=turno,
        )  # fmt: skip
        session.add_all([p, c])
        session.flush()
        session.add(
            PessoaVinculo(
                pessoa_id=p.id, fonte="candidatura", id_externo=f"2024:{sq}", regra="origem"
            )
        )
        return p

    a = pessoa("Ana Maria Souza", "4314902", "VEREADOR", "1", "ELEITO POR QP")
    pessoa("Beto Lima Dias", "1718006", "PREFEITO", "2")  # município sem diário
    pessoa("Caio Reis Nunes", "4314902", "VEREADOR", "3", "SUPLENTE")  # não eleito
    pessoa("Davi Pontes Gil", "4314902", "DEPUTADO FEDERAL", "4")  # outro cargo
    session.flush()
    assert atos.pessoas_alvo(session, {"4314902"}) == [(a.id, "Ana Maria Souza", "4314902")]


def test_diario_ato_nasce_nao_revisado(session):
    p = Pessoa(nome="Ana Maria Souza", chave_nome="ANA MARIA SOUZA")
    session.add(p)
    session.flush()
    ato = DiarioAto(
        pessoa_id=p.id, municipio_ibge="4314902", data=date(2025, 8, 21),
        tipo_ato="designacao", trecho="x", url="https://exemplo/d.pdf",
    )  # fmt: skip
    session.add(ato)
    session.flush()
    assert ato.revisado is False


def test_nome_como_titulo_ou_assinatura_nao_e_alvo_do_ato():
    # Trechos reais (Curitiba, 2025-26): o vereador aparece como lotação de servidores
    # nomeados/exonerados, e secretários como signatários; o ato não é sobre ele.
    lotacao = (
        "Exonera e nomeia servidores em Cargo de Provimento em Comissão do Gabinete "
        "Parlamentar do Vereador Marcos Antonio Vieira (Ver. Marcos Vieira). Matrícula"
    )
    assinatura = (
        "Eduardo Pimentel Slaviero : Prefeito Municipal Marcelo Tscha Fachinello : "
        "Secretário do Governo Municipal PORTARIA Nº 69 Nomeia para Cargo em Comissão."
    )
    prefeito = "representado pelo Prefeito, SANDRO DA MABEL ANTÔNIO SCODRO, nomeado pelo Decreto"
    diaria = (
        "Designa servidores para exercer a função de Fiscal e Gestor de Contratos "
        "Autorização de diária – GIORGIA TAIS XAVIER PRATES DIÁRIO OFICIAL ELETRÔNICO"
    )
    assert atos.achar_ato("Giorgia Tais Xavier Prates", diaria) is None
    assert atos.achar_ato("Marcos Antonio Vieira", lotacao) is None
    assert atos.achar_ato("Marcelo Tscha Fachinello", assinatura) is None
    assert atos.achar_ato("Sandro da Mabel Antônio Scodro", prefeito) is None
    # O nome como objeto do ato continua valendo.
    assert atos.achar_ato("Marcos Antonio Vieira", "NOMEAR MARCOS ANTONIO VIEIRA, CC3")[0] == (
        "nomeacao"
    )
