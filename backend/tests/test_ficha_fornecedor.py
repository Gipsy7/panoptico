from datetime import UTC, date, datetime
from decimal import Decimal

from app.models import (
    Despesa,
    DespesaFornecedor,
    EmendaPagamento,
    EmendaTransferencia,
    Empresa,
    FonteIngestao,
    Municipio,
    Parlamentar,
    PncpAnual,
    SancaoEmpresa,
)
from app.services import ficha_fornecedor

# CNPJs com dígitos verificadores válidos (fictícios).
CNPJ = "11222333000181"
OUTRO = "11444777000161"
AGORA = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def _parlamentar(session, n, nome, casa="camara", uf="SC"):
    p = Parlamentar(
        casa=casa,
        id_externo=str(n),
        nome_parlamentar=nome,
        partido="ABC",
        uf=uf,
        fonte_url="https://exemplo.test",
        atualizado_em=AGORA,
    )
    session.add(p)
    session.flush()
    return p


def _despesa(session, p, ano, valor, doc, fornecedor="GRAFICA EXEMPLO LTDA"):
    session.add(
        Despesa(
            parlamentar_id=p.id,
            casa=p.casa,
            ano=ano,
            mes=3,
            categoria="Divulgação",
            fornecedor=fornecedor,
            cnpj_cpf=doc,
            valor=Decimal(valor),
        )
    )


def _base(session):
    ana = _parlamentar(session, 1, "Ana")
    beto = _parlamentar(session, 2, "Beto", casa="senado")
    _despesa(session, ana, 2026, "1000.00", "11.222.333/0001-81")
    _despesa(session, ana, 2026, "500.00", CNPJ)
    _despesa(session, beto, 2026, "300.00", "11.222.333/0001-81")
    _despesa(session, beto, 2025, "70.00", CNPJ)
    # Outra empresa e uma pessoa física: nunca entram nesta ficha.
    _despesa(session, ana, 2026, "999.00", OUTRO, fornecedor="OUTRA LTDA")
    _despesa(session, ana, 2026, "888.00", "123.456.789-01", fornecedor="FULANO DE TAL")
    session.add(
        FonteIngestao(
            fonte="camara_despesas",
            url="x",
            arquivo_raw="x",
            status="ok",
            concluido_em=AGORA,
        )
    )
    session.flush()
    return ana, beto


def test_gabinetes_somam_por_ano_e_listam_quem_pagou(session):
    ana, beto = _base(session)
    f = ficha_fornecedor.ficha(session, CNPJ)
    assert f is not None
    assert f["cnpj"] == CNPJ and f["nome"] == "GRAFICA EXEMPLO LTDA"
    g = f["gabinetes"]
    assert g["por_ano"] == [
        {"ano": 2026, "valor": 1800.0, "gabinetes": 2, "lancamentos": 3},
        {"ano": 2025, "valor": 70.0, "gabinetes": 1, "lancamentos": 1},
    ]
    assert g["ano_da_lista"] == 2026
    assert [(m["parlamentar_id"], m["valor"]) for m in g["maiores"]] == [
        (ana.id, 1500.0),
        (beto.id, 300.0),
    ]
    assert g["atualizado_em"] == AGORA
    assert "_nome" not in g


def test_aceita_cnpj_formatado_e_recusa_cpf_e_cnpj_invalido(session):
    _base(session)
    assert (
        ficha_fornecedor.ficha(session, "11.222.333/0001-81")["gabinetes"]["por_ano"][0]["valor"]
        == 1800.0
    )
    # CPF (11 dígitos) e CNPJ com dígito verificador errado nunca devolvem ficha.
    assert ficha_fornecedor.ficha(session, "12345678901") is None
    assert ficha_fornecedor.ficha(session, "123.456.789-01") is None
    assert ficha_fornecedor.ficha(session, "11222333000180") is None
    assert ficha_fornecedor.ficha(session, "") is None


def test_cnpj_valido_sem_registro_devolve_nada(session):
    _base(session)
    assert ficha_fornecedor.ficha(session, "19131243000197") is None


def test_prefeituras_pncp_emendas_e_sancoes(session):
    session.add(Municipio(ibge="4205902", nome="Gaspar", uf="SC", nome_chave="GASPAR"))
    session.flush()
    session.add_all(
        [
            DespesaFornecedor(
                municipio_ibge="4205902",
                ano=2025,
                orgao="prefeitura",
                fornecedor="GRAFICA EXEMPLO LTDA",
                documento=CNPJ,
                valor_pago=Decimal("2500.00"),
                pagamentos=4,
                fonte="tce_sp",
            ),
            PncpAnual(
                ano=2026,
                municipio_ibge="4205902",
                fornecedor_cnpj=CNPJ,
                fornecedor_nome="GRAFICA EXEMPLO",
                quantidade=2,
                valor_global=Decimal("9000.00"),
            ),
            EmendaPagamento(
                emenda_codigo="202612340001",
                ano_emenda=2026,
                ano_mes=202605,
                autor_codigo="1234",
                autor_nome="ANA",
                favorecido="GRAFICA EXEMPLO LTDA",
                favorecido_codigo=CNPJ,
                natureza="Associação Privada",
                grupo="entidade",
                municipio_ibge="4205902",
                valor=Decimal("400.00"),
            ),
            EmendaTransferencia(
                tipo="convenio",
                emenda_codigo="202612340001",
                ano_emenda=2026,
                identificador="900001",
                beneficiario="GRAFICA EXEMPLO LTDA",
                beneficiario_cnpj=CNPJ,
                valor_repassado=Decimal("350.00"),
            ),
            SancaoEmpresa(
                cadastro="CEIS",
                codigo="1",
                cnpj=CNPJ,
                nome="GRAFICA EXEMPLO LTDA",
                categoria="Suspensão",
                abrangencia="No órgão sancionador",
                orgao="Prefeitura de Exemplo",
                inicio=date(2026, 7, 14),
                fim=date(2028, 7, 14),
            ),
        ]
    )
    session.flush()
    f = ficha_fornecedor.ficha(session, CNPJ)
    assert f is not None and f["nome"] == "GRAFICA EXEMPLO LTDA"
    assert f["gabinetes"]["por_ano"] == [] and f["gabinetes"]["maiores"] == []
    assert f["prefeituras"]["por_ano"] == [{"ano": 2025, "valor": 2500.0, "municipios": 1}]
    assert f["prefeituras"]["maiores"] == [
        {
            "ibge": "4205902",
            "municipio": "Gaspar",
            "uf": "SC",
            "orgao": "prefeitura",
            "valor": 2500.0,
        }
    ]
    assert f["pncp"]["por_ano"] == [{"ano": 2026, "valor": 9000.0, "contratos": 2, "municipios": 1}]
    assert f["emendas"]["pagas_por_ano"] == [{"ano": 2026, "valor": 400.0, "autores": 1}]
    assert f["emendas"]["convenios"] == {"quantidade": 1, "valor_repassado": 350.0}
    assert [
        (s["cadastro"], s["categoria"], s["inicio"], s["fim"]) for s in f["sancoes"]["itens"]
    ] == [("CEIS", "Suspensão", date(2026, 7, 14), date(2028, 7, 14))]
    for bloco in ("gabinetes", "prefeituras", "pncp", "emendas", "sancoes"):
        assert f[bloco]["recorte"] and f[bloco]["fonte_nome"]


def test_nome_do_cadastro_vale_primeiro_e_cpf_nunca_sai(session):
    ana = _parlamentar(session, 1, "Ana")
    # MEI: a fonte escreve o CPF junto do nome.
    _despesa(session, ana, 2026, "10.00", CNPJ, fornecedor="JOSE DA SILVA 12345678901")
    session.flush()
    f = ficha_fornecedor.ficha(session, CNPJ)
    assert f["nome"] == "JOSE DA SILVA" and "12345678901" not in str(f)

    session.add(
        Empresa(
            cnpj=CNPJ,
            razao_social="EXEMPLO COMERCIO LTDA",
            nome_fantasia="Exemplo",
            uf="SC",
            situacao="02",
            referencia="2026-10",
            atualizado_em=AGORA,
        )
    )
    session.flush()
    f = ficha_fornecedor.ficha(session, CNPJ)
    assert (f["nome"], f["nome_fantasia"], f["uf"], f["situacao"]) == (
        "EXEMPLO COMERCIO LTDA",
        "Exemplo",
        "SC",
        "ativa",
    )


def test_rota_responde_ficha_404_e_422(session, client):
    _base(session)
    r = client.get(f"/fornecedores/{CNPJ}")
    assert r.status_code == 200 and r.json()["gabinetes"]["por_ano"][0]["gabinetes"] == 2
    assert client.get("/fornecedores/11.222.333.0001-81").status_code == 200
    assert client.get("/fornecedores/19131243000197").status_code == 404
    assert client.get("/fornecedores/12345678901").status_code == 422
    assert client.get("/fornecedores/abc").status_code == 422
