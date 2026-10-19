from datetime import date, datetime
from decimal import Decimal

from app.models import (
    FonteIngestao,
    Municipio,
    Pessoa,
    PncpAnual,
    PncpContrato,
    PncpDia,
    PncpEntePublico,
    SocioPessoa,
)
from app.services import contratos_pncp


def _contrato(numero, cnpj, valor, publicado, receita=False):
    return PncpContrato(
        numero_controle=numero, orgao_cnpj="83551549000100", orgao_nome="Prefeitura de Exemplo",
        uf="SC", municipio_ibge="4202008", municipio_nome="Exemplo", fornecedor_cnpj=cnpj,
        fornecedor_nome="EMPRESA DA ANA LTDA", tipo_contrato="Contrato", receita=receita,
        objeto="Merenda escolar", valor_global=Decimal(valor), publicado_em=publicado,
        vigencia_inicio=date(2026, 1, 1), vigencia_fim=date(2026, 12, 31),
    )  # fmt: skip


def test_link_pncp():
    assert (
        contratos_pncp.link_pncp("83551549000100-2-000223/2025")
        == "https://pncp.gov.br/app/contratos/83551549000100/2025/223"
    )
    assert contratos_pncp.link_pncp("quebrado") is None


def test_contratos_da_pessoa_so_das_empresas_dela_sem_alienacao(client, session):
    ana = Pessoa(nome="Ana Souza", chave_nome="ANA SOUZA")
    bia = Pessoa(nome="Bia Lima", chave_nome="BIA LIMA")
    cris = Pessoa(nome="Cris Dias", chave_nome="CRIS DIAS")
    session.add_all([ana, bia, cris])
    session.flush()
    session.add_all([
        SocioPessoa(pessoa_id=ana.id, cnpj="11111111000111", qualificacao="Sócio-Administrador"),
        SocioPessoa(pessoa_id=bia.id, cnpj="22222222000122"),
        _contrato("83551549000100-2-000001/2026", "11111111000111", "1000", date(2026, 3, 1)),
        _contrato("83551549000100-2-000002/2026", "11111111000111", "500", date(2026, 5, 1)),
        _contrato("83551549000100-2-000003/2026", "11111111000111", "999", date(2026, 6, 1), True),
        _contrato("83551549000100-2-000004/2026", "22222222000122", "70", date(2026, 6, 1)),
        PncpDia(dia=date(2025, 1, 1), total_api=1, lidos=1, receitas=0, empenhos=0,
                pessoas_fisicas=0, linhas_alvo=0, lido_em=date(2026, 10, 1)),
    ])  # fmt: skip
    session.flush()
    r = client.get(f"/pessoas/{ana.id}/contratos")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["total_contratos"] == 2 and corpo["valor_total"] == 1500.0
    assert [i["publicado_em"] for i in corpo["itens"]] == ["2026-05-01", "2026-03-01"]
    assert corpo["itens"][0]["url"] == "https://pncp.gov.br/app/contratos/83551549000100/2026/2"
    assert corpo["empresas"] == [
        {"cnpj": "11111111000111", "nome": "EMPRESA DA ANA LTDA", "nome_omitido": False,
         "qualificacao": "Sócio-Administrador", "contratos": 2}
    ]  # fmt: skip
    assert corpo["cobertura_desde"] == "2025-01-01"
    # pessoa sem empresa contratada: 200 com listas vazias; inexistente: 404
    vazio = client.get(f"/pessoas/{cris.id}/contratos").json()
    assert vazio["itens"] == [] and vazio["empresas"] == []
    assert client.get(f"/pessoas/{cris.id + 1000}/contratos").status_code == 404


def test_maiores_fornecedores_do_municipio(client, session):
    session.add(Municipio(ibge="4202008", nome="Exemplo", uf="SC", nome_chave="EXEMPLO"))
    session.add(Municipio(ibge="1111111", nome="Vazio", uf="AC", nome_chave="VAZIO"))
    for i in range(12):
        session.add(PncpAnual(ano=2026, municipio_ibge="4202008", fornecedor_cnpj=f"{i:014d}",
                              fornecedor_nome=f"F{i}", quantidade=i + 1,
                              valor_global=Decimal(i * 10)))  # fmt: skip
    session.add(PncpAnual(ano=2025, municipio_ibge="4202008", fornecedor_cnpj="9" * 14,
                          quantidade=1, valor_global=Decimal(10**6)))  # fmt: skip
    session.flush()
    r = client.get("/municipios/4202008/fornecedores-pncp")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["ano"] == 2026 and len(corpo["itens"]) == 10  # só o ano mais recente, top 10
    assert corpo["itens"][0]["fornecedor"] == "F11" and corpo["itens"][0]["valor"] == 110.0
    assert client.get("/municipios/9999999/fornecedores-pncp").status_code == 404
    assert client.get("/municipios/1111111/fornecedores-pncp").status_code == 404


def test_fornecedor_ente_publico_nome_saneado_e_atualizado_em(client, session):
    # o Postgres nem aceita surrogate; o que pode ter sido gravado é mojibake ou U+FFFD
    estragado = ("SOCIEDADE ÁGUA S.A.".encode().decode("latin-1")) + chr(0xFFFD)
    session.add(Municipio(ibge="4202008", nome="Exemplo", uf="SC", nome_chave="EXEMPLO"))
    session.add_all([
        PncpAnual(ano=2026, municipio_ibge="4202008", fornecedor_cnpj="1" * 14,
                  fornecedor_nome=estragado, quantidade=1, valor_global=Decimal(200)),
        PncpAnual(ano=2026, municipio_ibge="4202008", fornecedor_cnpj="2" * 14,
                  fornecedor_nome="FUNDO MUNICIPAL DE SAUDE", quantidade=1,
                  valor_global=Decimal(100)),
        PncpEntePublico(cnpj="2" * 14),
        FonteIngestao(fonte="pncp_contratos", url="x", arquivo_raw="x", status="ok",
                      concluido_em=datetime(2026, 10, 10, 12, 0)),
    ])  # fmt: skip
    session.flush()
    r = client.get("/municipios/4202008/fornecedores-pncp")
    r.content.decode("utf-8")  # a resposta é UTF-8 válido, sem surrogate
    corpo = r.json()
    assert [(i["fornecedor"], i["ente_publico"]) for i in corpo["itens"]] == [
        ("SOCIEDADE ÁGUA S.A.", False),
        ("FUNDO MUNICIPAL DE SAUDE", True),
    ]
    assert corpo["atualizado_em"].startswith("2026-10-10")
