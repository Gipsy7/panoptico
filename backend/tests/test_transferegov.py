import gzip
import io
import json
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import respx
from sqlalchemy import insert, select

from app.models import Emenda, EmendaConvenio, EmendaTransferencia, FonteIngestao, Parlamentar
from ingestion.transferegov import convenios, especiais, municipio
from ingestion.transparencia import emendas
from tests.test_api import _ingestao, _popular

# Linhas reais do arquivo de convênios do Portal da Transparência (2026-10-02).
CAB = (
    "NÚMERO CONVÊNIO;UF;CÓDIGO SIAFI MUNICÍPIO;NOME MUNICÍPIO;SITUAÇÃO CONVÊNIO;"
    "NÚMERO ORIGINAL;NÚMERO PROCESSO DO CONVÊNIO;OBJETO DO CONVÊNIO;CÓDIGO ÓRGÃO SUPERIOR;"
    "NOME ÓRGÃO SUPERIOR;CÓDIGO ÓRGÃO CONCEDENTE;NOME ÓRGÃO CONCEDENTE;CÓDIGO UG CONCEDENTE;"
    "NOME UG CONCEDENTE;CÓDIGO CONVENENTE;TIPO CONVENENTE;NOME CONVENENTE;"
    "TIPO ENTE CONVENENTE;TIPO INSTRUMENTO;VALOR CONVÊNIO;VALOR LIBERADO;DATA PUBLICAÇÃO;"
    "DATA INÍCIO VIGÊNCIA;DATA FINAL VIGÊNCIA;VALOR CONTRAPARTIDA;DATA ÚLTIMA LIBERAÇÃO;"
    "VALOR ÚLTIMA LIBERAÇÃO"
)
L_955158 = (
    "955158;PR;7885;SAO JOSE DOS PINHAIS;PRESTAÇÃO DE CONTAS APROVADA;70953/2023;709532023;"
    "Requalificacao da Estrada de acesso ao Caminho das Colonias Roteiro turistico do Municipio "
    "de Sao Jose dos Pinhais/PR.;54000;Ministério do Turismo;54000;"
    "Ministério do Turismo - Unidades com vínculo direto;540007;CAIXA - SNINFRA;76105543000135;"
    "Administração Pública Municipal;MUNICIPIO DE SAO JOSE DOS PINHAIS;Municipal;"
    "Não se aplica;1441714,00;1441714,00;05/01/2024;31/12/2023;31/12/2026;555282,52;"
    "07/11/2025;1441714,00"
)
L_943340 = (
    "943340;RS;1120;ALMIRANTE TAMANDARE DO SUL;EM EXECUÇÃO;10052/2023;100522023;"
    "Pavimentacao de ruas no perimetro urbano do municipio de Almirante Tamandare do Sul RS.;"
    "56000;Ministério das Cidades;56000;Ministério das Cidades - Unidades com vínculo direto;"
    "175004;CAIXA ECONOMICA FEDERAL - PROGRAMAS SOCIAIS;04215782000137;"
    "Administração Pública Municipal;MUNICIPIO DE ALMIRANTE TAMANDARE DO SUL;Municipal;"
    "Não se aplica;238856,00;100000,00;23/08/2023;21/08/2023;31/07/2026;12218,73;01/04/2024;"
    "100000,00"
)
L_OUTRO = L_955158.replace("955158;PR", "104141;SP", 1)


def _zip_convenios(*linhas: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("20261002_Convenios.csv", "\n".join([CAB, *linhas]).encode("latin-1"))
        z.writestr("20261002_Convenios_OrdensBancarias.csv", b"x;y\n1;2")
    return buffer.getvalue()


def test_normalizar_convenios_das_emendas_ignora_sem_informacao_e_anos_antigos():
    cab = (
        "Código da Emenda;Código Função;Nome Função;Código Subfunção;Nome Subfunção;"
        "Localidade do gasto;Tipo de Emenda;Data Publicação Convênio;Convenente;"
        "Objeto Convênio;Número Convênio;Valor Convênio"
    )
    linhas = [
        "202360110001;15;Urbanismo;451;x;PR;Emenda Individual;05/01/2024;M;obj;955158;1,00",
        "202360110001;15;Urbanismo;451;x;PR;Emenda Individual;05/01/2024;M;obj;955158;1,00",
        "Sem informação;15;Urbanismo;451;x;PR;Emenda Individual;05/01/2024;M;obj;111;1,00",
        "202260110001;15;Urbanismo;451;x;PR;Emenda Individual;05/01/2024;M;obj;222;1,00",
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(emendas.ARQUIVO_CONVENIOS, "\n".join([cab, *linhas]).encode("latin-1"))
    assert emendas.normalizar_convenios(buffer.getvalue(), 2023) == [
        {"emenda_codigo": "202360110001", "numero_convenio": "955158"}
    ]


def test_recortar_so_os_convenios_pedidos_e_normalizar():
    arquivo = _zip_convenios(L_955158, L_943340, L_OUTRO)
    recorte = convenios.recortar(arquivo, {"955158", "943340"})
    assert [r["numero"] for r in recorte] == ["943340", "955158"]
    dados = convenios.normalizar(recorte)
    c = dados["955158"]
    assert c["situacao"] == "Prestação de contas aprovada"
    assert c["beneficiario_cnpj"] == "76105543000135"
    assert c["valor_total"] == Decimal("1441714.00")
    assert c["valor_repassado"] == Decimal("1441714.00")
    assert c["valor_contrapartida"] == Decimal("555282.52")
    assert c["inicio_vigencia"] == date(2023, 12, 31)
    assert c["fim_vigencia"] == date(2026, 12, 31)
    assert c["uf"] == "PR"
    assert dados["943340"]["situacao"] == "Em execução"
    assert dados["943340"]["valor_repassado"] == Decimal("100000.00")


def test_frase_e_sem_informacao():
    assert convenios.frase("PRESTAÇÃO DE CONTAS EM ANÁLISE") == "Prestação de contas em análise"
    assert convenios.frase("Sem informação") is None
    assert convenios._data("") is None


def _ligar(session, codigos_numeros):
    ing = _ingestao(session, "transparencia_emendas")
    session.execute(
        insert(EmendaConvenio),
        [
            {"emenda_codigo": c, "numero_convenio": n, "ingestao_id": ing.id}
            for c, n in codigos_numeros
        ],
    )


def test_carregar_convenios_idempotente_e_aborta_vazio(session):
    _ligar(session, [("202360110001", "955158"), ("202320230006", "943340")])
    recorte = convenios.recortar(_zip_convenios(L_955158, L_943340), {"955158", "943340"})
    payload = json.dumps(recorte).encode()
    for _ in range(2):
        convenios.carregar(session, payload, _ingestao(session, convenios.FONTE))
    linhas = session.scalars(select(EmendaTransferencia).order_by("identificador")).all()
    assert [(t.tipo, t.emenda_codigo, t.ano_emenda) for t in linhas] == [
        ("convenio", "202320230006", 2023),
        ("convenio", "202360110001", 2023),
    ]
    # o gz do bruto também é aceito
    convenios.carregar(session, gzip.compress(payload), _ingestao(session, convenios.FONTE))
    try:
        convenios.carregar(session, b"[]", _ingestao(session, convenios.FONTE))
    except ValueError:
        pass
    else:
        raise AssertionError("deveria abortar com lista vazia")
    assert session.query(EmendaTransferencia).count() == 2


# Registros reais da API de transferências especiais (plano 09032023-038450).
PLANO = {
    "id_plano_acao": 38450,
    "codigo_plano_acao": "09032023-038450",
    "situacao_plano_acao": "CIENTE",
    "cnpj_beneficiario_plano_acao": "17900473000148",
    "nome_beneficiario_plano_acao": "MUNICIPIO DE GUARANESIA",
    "uf_beneficiario_plano_acao": "MG",
    "numero_emenda_parlamentar_plano_acao": "202341400005",
    "valor_custeio_plano_acao": 0.0,
    "valor_investimento_plano_acao": 2000000.0,
    "ano_emenda_parlamentar_plano_acao": "2023",
}
OUTRO_PLANO = {**PLANO, "id_plano_acao": 1, "codigo_plano_acao": "x-1",
               "numero_emenda_parlamentar_plano_acao": "202399990001"}  # fmt: skip


@respx.mock
def test_baixar_tudo_pagina_sem_filtrar_e_traz_os_entes():
    def tabela(nome, linhas):
        def resposta(request):
            offset = int(request.url.params["offset"])
            return httpx.Response(200, json=linhas[offset : offset + especiais.PAGINA])

        respx.get(f"{especiais.BASE}/{nome}").mock(side_effect=resposta)

    tabela("plano_acao_especial", [PLANO, OUTRO_PLANO])
    tabela(
        "executor_especial",
        [
            {"id_plano_acao": 38450, "id_executor": 1, "nome_executor": "M",
             "objeto_executor": "DIVERSAS OBRAS MUNICÍPIO"},
            {"id_plano_acao": 1, "id_executor": 2, "nome_executor": "M", "objeto_executor": "z"},
        ],
    )  # fmt: skip
    tabela(
        "empenho_especial",
        [{"id_empenho": 9, "id_plano_acao": 38450, "valor_empenho": 2000000.0}],
    )
    tabela(
        "relatorio_gestao_especial",
        [{"id_relatorio_gestao": 5, "situacao_relatorio_gestao": "EM_ELABORACAO",
          "id_plano_acao": 38450}],
    )  # fmt: skip
    respx.get(municipio.URL_ENTES).mock(
        return_value=httpx.Response(
            200,
            json={"items": [{"cod_ibge": 3128303, "uf": "MG", "esfera": "M",
                             "cnpj": "17900473000148"}], "hasMore": False},
        )
    )  # fmt: skip
    with httpx.Client() as client:
        recorte = especiais.baixar_tudo(client)
    # Todos os planos, não só os das emendas da base.
    assert [p["id_plano_acao"] for p in recorte["planos"]] == [38450, 1]
    assert len(recorte["executores"]) == 2
    assert recorte["entes"] == [
        {"cnpj": "17900473000148", "ibge": "3128303", "uf": "MG", "esfera": "M"}
    ]
    linhas = especiais.normalizar(recorte)
    assert len(linhas) == 2
    assert linhas[:1] == [
        {
            "tipo": "especial",
            "emenda_codigo": "202341400005",
            "ano_emenda": 2023,
            "identificador": "09032023-038450",
            "situacao": "Ciente",
            "relatorio_gestao": "Em elaboração",
            "beneficiario": "MUNICIPIO DE GUARANESIA",
            "beneficiario_cnpj": "17900473000148",
            "uf": "MG",
            "objeto": "DIVERSAS OBRAS MUNICÍPIO",
            "valor_total": Decimal("2000000.0"),
            "valor_repassado": Decimal("2000000.0"),
        }
    ]


@respx.mock
def test_paginas_segue_ate_a_ultima():
    cheia = [{"i": n} for n in range(especiais.PAGINA)]
    respx.get(f"{especiais.BASE}/t").mock(
        side_effect=[httpx.Response(200, json=cheia), httpx.Response(200, json=[{"i": -1}])]
    )
    with httpx.Client() as client:
        assert len(especiais.paginas(client, "t", {})) == especiais.PAGINA + 1


def test_carregar_especiais_e_endpoint(client, session):
    camara, _ = _popular(session)
    parlamentar = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).first()
    ing = _ingestao(session, "transparencia_emendas")
    session.execute(
        insert(Emenda),
        [
            {
                "codigo": "202341400005", "ano": 2023, "tipo": "Emenda Individual",
                "individual": True,
                "autor_codigo": "1", "autor_nome": "X", "parlamentar_id": parlamentar.id,
                "localidade": "MG", "valor_empenhado": 1, "valor_pago": 1, "ingestao_id": ing.id,
            },
            {
                "codigo": "202360110001", "ano": 2023, "tipo": "Emenda Individual",
                "individual": True,
                "autor_codigo": "1", "autor_nome": "X", "parlamentar_id": parlamentar.id,
                "localidade": "PR", "valor_empenhado": 1, "valor_pago": 1, "ingestao_id": ing.id,
            },
        ],
    )  # fmt: skip
    _ligar(session, [("202360110001", "955158")])
    recorte = {"planos": [PLANO], "executores": [], "empenhos": [], "relatorios": []}
    especiais.carregar(session, json.dumps(recorte).encode(), _ingestao(session, especiais.FONTE))
    convenios.carregar(
        session,
        json.dumps(convenios.recortar(_zip_convenios(L_955158), {"955158"})).encode(),
        _ingestao(session, convenios.FONTE),
    )
    for i in session.scalars(select(FonteIngestao)):
        i.status, i.concluido_em = "ok", datetime.now(UTC)
    session.commit()

    r = client.get(f"/parlamentares/{parlamentar.id}/emendas-destino")
    assert r.status_code == 200
    d = r.json()
    assert d["quantidade"] == 2
    assert d["valor_total"] == 3441714.0
    assert {s["tipo"]: s["situacao"] for s in d["por_situacao"]} == {
        "convenio": "Prestação de contas aprovada",
        "especial": "Ciente",
    }
    assert d["itens"][0]["identificador"] == "09032023-038450"  # maior valor primeiro
    assert d["itens"][0]["fonte_url"].endswith("codigo_plano_acao=eq.09032023-038450")
    assert d["atualizado_em"] is not None

    outro = session.scalars(select(Parlamentar).where(Parlamentar.id != parlamentar.id)).first()
    assert client.get(f"/parlamentares/{outro.id}/emendas-destino").status_code == 404
