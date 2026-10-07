import io
import zipfile
from decimal import Decimal

from sqlalchemy import func, select

from app.models import Despesa, Parlamentar
from ingestion import comum
from ingestion.camara import despesas as despesas_camara
from ingestion.senado import despesas as despesas_senado
from tests.test_api import _ingestao, _popular

CABECALHO = (
    "txNomeParlamentar;cpf;ideCadastro;nuCarteiraParlamentar;nuLegislatura;sgUF;sgPartido;"
    "codLegislatura;numSubCota;txtDescricao;numEspecificacaoSubCota;txtDescricaoEspecificacao;"
    "txtFornecedor;txtCNPJCPF;txtNumero;indTipoDocumento;datEmissao;vlrDocumento;vlrGlosa;"
    "vlrLiquido;numMes;numAno;numParcela;txtPassageiro;txtTrecho;numLote;numRessarcimento;"
    "datPagamentoRestituicao;vlrRestituicao;nuDeputadoId;ideDocumento;urlDocumento"
)


def _linha(ide: str, descricao: str, valor: str, mes: int, doc: str) -> str:
    campos = [""] * 32
    campos[2], campos[9], campos[12], campos[19], campos[20] = (
        ide,
        descricao,
        "FORN",
        valor,
        str(mes),
    )
    campos[16], campos[30] = "2026-01-08T00:00:00", doc
    campos[31] = f"https://www.camara.leg.br/doc/{doc}.pdf"
    return ";".join(campos)


def _zip_ceap(*linhas: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("Ano-2026.csv", "﻿" + "\n".join([CABECALHO, *linhas]))
    return buffer.getvalue()


def test_limpar_categoria():
    assert comum.limpar_categoria("COMBUSTÍVEIS E LUBRIFICANTES.") == "Combustíveis e lubrificantes"
    assert comum.limpar_categoria("HOSPEDAGEM ,EXCETO DO PARLAMENTAR") == (
        "Hospedagem, exceto do parlamentar"
    )
    assert comum.limpar_categoria("Divulgação da atividade parlamentar") == (
        "Divulgação da atividade parlamentar"
    )
    assert comum.limpar_categoria(None) == "Não informado"


def test_normalizar_ceap_camara_ignora_liderancas():
    conteudo = _zip_ceap(
        _linha("204379", "TELEFONIA", "100.50", 1, "1"),
        _linha("", "TELEFONIA", "999", 1, "2"),  # liderança, sem ideCadastro
        _linha("204379", "TELEFONIA", "-20", 2, "3"),  # restituição
    )
    registros = despesas_camara.normalizar(conteudo)
    assert [r["valor"] for r in registros] == [Decimal("100.50"), Decimal("-20")]
    assert registros[0]["categoria"] == "Telefonia"
    assert registros[0]["id_externo_parlamentar"] == "204379"


def test_normalizar_ceaps_senado():
    registros = despesas_senado.normalizar(
        [
            {
                "id": 1, "ano": 2026, "mes": 2, "codSenador": 5672, "tipoDespesa": None,
                "cpfCnpj": "765.***.***-15", "fornecedor": " X ", "data": "2026-02-05",
                "valorReembolsado": 3189.66,
            }
        ]
    )  # fmt: skip
    assert registros[0]["valor"] == Decimal("3189.66")
    assert registros[0]["categoria"] == "Não informado"
    assert registros[0]["fornecedor"] == "X"


def _despesas(session, parlamentar, valores, ano=2026):
    linhas = [
        {"parlamentar_id": parlamentar.id, "mes": i + 1, "categoria": cat, "valor": Decimal(v),
         "fornecedor": "F", "url_documento": None}
        for i, (cat, v) in enumerate(valores)
    ]  # fmt: skip
    return linhas


def test_recarregar_despesas_substitui_o_ano(session):
    _popular(session)
    p = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).first()
    comum.recarregar_despesas(
        session,
        "camara",
        2026,
        _despesas(session, p, [("A", "10"), ("B", "5")]),
        _ingestao(session),
    )
    comum.recarregar_despesas(
        session, "camara", 2026, _despesas(session, p, [("A", "7")]), _ingestao(session)
    )
    total = session.scalar(select(func.sum(Despesa.valor)).where(Despesa.casa == "camara"))
    assert total == Decimal("7")


def test_gastos_endpoint(client, session):
    _popular(session)
    deps = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).all()
    linhas = _despesas(session, deps[0], [("Telefonia", "100"), ("Combustíveis", "300")])
    linhas += _despesas(session, deps[1], [("Telefonia", "200")])
    comum.recarregar_despesas(session, "camara", 2026, linhas, _ingestao(session))
    session.flush()

    corpo = client.get(f"/parlamentares/{deps[0].id}/gastos").json()
    assert corpo["ano"] == 2026
    assert corpo["total"] == 400
    # 3 deputados em exercício na fixture: (400 + 200 + 0) / 3
    assert corpo["media_casa"] == 200
    assert [c["categoria"] for c in corpo["por_categoria"]] == ["Combustíveis", "Telefonia"]
    assert corpo["maiores_despesas"][0]["valor"] == 300
    assert corpo["ultimo_mes"] == 2

    assert client.get(f"/parlamentares/{deps[0].id}/gastos?ano=1999").status_code == 404
    senador = session.scalars(select(Parlamentar).where(Parlamentar.casa == "senado")).first()
    assert client.get(f"/parlamentares/{senador.id}/gastos").status_code == 404


def test_nome_proprio():
    assert comum.nome_proprio("ADILSON BARROSO OLIVEIRA") == "Adilson Barroso Oliveira"
    assert comum.nome_proprio("MARIA DAS DORES E SILVA") == "Maria das Dores e Silva"
    assert comum.nome_proprio("Já Formatado") == "Já Formatado"
    assert comum.nome_proprio(None) is None
