"""Emendas estaduais das outras UFs (adaptadores de ingestion/emendas_estaduais/).

Fixtures em tests/fixtures/emendas_estaduais_ufs/, recortes reais de 21/10/2026:
- mg_indicacoes.csv: 7 indicações de Belo Horizonte do arquivo da SEGOV/MG (uma de bloco, uma
  de caixa escolar sem código IBGE, uma reprovada e uma com CNPJ que perdeu o zero à esquerda);
- es_emendas-estaduais-2024.csv: 5 linhas do CSV da SEFAZ/ES (uma emenda com dois
  instrumentos, código IBGE de 6 dígitos);
- pe_tabela_completa_{gtv,direta,pix}.csv: registros das três tabelas da SEPLAG/PE com as
  armadilhas (empenho repetido por chamamento, campo com `;` entre aspas, objeto com quebra
  de linha solta);
- ba_emendasparlamentares.zip: 5 linhas da visão de despesas da SEFAZ/BA;
- ac_emendas.csv (planilha da SEPLAN/AC, contas bancárias apagadas no recorte), al_emendas.json,
  se_emendas.json e ma_emendas.csv.

Recortes reais de 27/10/2026:
- df_emendas.json: 3 linhas de 2025 da API do Portal da Transparência do DF (uma de sete
  autores juntos, com pago acima do empenhado);
- pb_execucao.json: 3 linhas de 2025 da API de dados abertos da PB (duas da mesma emenda);
- go_emendas_2023.csv: 5 linhas do arquivo de 2023 de GO (latin-1; duas da mesma emenda, CNPJ
  com 10 e 13 dígitos, valor com vírgula) e o rodapé; a linha "Total" foi refeita com a soma
  dessas 5 linhas, como a planilha faz.
"""

import io
import json
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models import (
    Candidatura,
    EmendaEstadual,
    FonteIngestao,
    MandatoLocal,
    Municipio,
    Pessoa,
    PessoaVinculo,
)
from ingestion import comum
from ingestion.emendas_estaduais import ac, al, ba, base, df, es, go, ma, mg, pb, pe, se

F = Path(__file__).parent / "fixtures" / "emendas_estaduais_ufs"
BH = "3106200"


def _ler(nome: str) -> bytes:
    return (F / nome).read_bytes()


def _pacote_mg() -> bytes:
    return base.empacotar({mg.ARQUIVO: _ler("mg_indicacoes.csv")})


def _pacote_pe() -> bytes:
    return base.empacotar(
        {f"tabela_completa_{m}.csv": _ler(f"pe_tabela_completa_{m}.csv") for m in pe.SIGLA}
    )


def _ingestao(session, fonte: str, status: str = "em_andamento") -> FonteIngestao:
    ingestao = FonteIngestao(
        fonte=fonte, url="https://exemplo", arquivo_raw="x.zip", status=status,
        concluido_em=datetime.now(UTC) if status == "ok" else None,
    )  # fmt: skip
    session.add(ingestao)
    session.flush()
    return ingestao


# --------------------------------------------------------------------------- leitura comum


def test_valor_e_nomes_do_autor():
    assert base.valor("1.234,56") == Decimal("1234.56")
    assert base.valor(" 200.000 ") == Decimal("200000")
    assert base.valor("194000,0000") == Decimal("194000.0000")
    assert base.valor("100000.0") == Decimal("100000.0")
    assert base.valor(" -   ") is None and base.valor("") is None
    assert base.nomes_do_autor("Dep. Mazinho dos Anjos") == ["MAZINHO DOS ANJOS"]
    assert base.nomes_do_autor("DEPUTADO ANTONIO ALBUQUERQUE") == ["ANTONIO ALBUQUERQUE"]
    assert base.nomes_do_autor("MARCOS JOSÉ ABREU ( MARQUITO)") == [
        "MARCOS JOSE ABREU",
        "MARQUITO",
    ]
    assert base.coletivo("BLOCO AVANCA MINAS") and base.coletivo("BANCADA DO OESTE")
    assert not base.coletivo("Professor Cleiton")
    assert base.cnpj("123.456.789-09") is None  # CPF nunca vira documento


def test_resolver_municipios_por_codigo_de_6_digitos_e_nome():
    municipios = [("3205309", "VITORIA"), ("3201209", "CACHOEIRO DE ITAPEMIRIM")]
    linhas = [
        {"municipio_ibge": "320530", "municipio_nome": "Vitória"},
        {"municipio_ibge": None, "municipio_nome": "Cachoeiro de Itapemirim"},
        {"municipio_ibge": None, "municipio_nome": base.SEM_MUNICIPIO},
    ]
    saida = base.resolver_municipios("ES", linhas, municipios)
    assert saida[("320530", "Vitória")] == "3205309"
    assert saida[(None, "Cachoeiro de Itapemirim")] == "3201209"
    assert saida[(None, base.SEM_MUNICIPIO)] is None


# --------------------------------------------------------------------------- por UF


def test_normalizar_mg():
    linhas = {x["proposta"]: x for x in mg.normalizar(_pacote_mg())}
    assert len(linhas) == 7
    # Código IBGE e CNPJ exportados como decimal ("3106200,0"); CNPJ sem o zero à esquerda.
    assert linhas["113912"]["municipio_ibge"] == BH
    assert linhas["116445"]["favorecido_cnpj"] == "09593822000106"
    assert linhas["141312"]["tipo"] == "bancada"  # BLOCO AVANCA MINAS
    caixa = linhas["114752"]  # caixa escolar: sem código IBGE, só o nome
    assert (caixa["municipio_ibge"], caixa["municipio_nome"]) == (None, "BELO HORIZONTE")
    assert linhas["119501"]["situacao_proposta"].startswith(mg.SITUACOES_FORA)
    assert linhas["144331"]["valor_pago"] == Decimal("134048.0")


def test_normalizar_es_tira_linha_repetida():
    linhas = es.normalizar(base.empacotar({"emendas-estaduais-2024.csv": _ler(
        "es_emendas-estaduais-2024.csv")}))  # fmt: skip
    assert len(linhas) == 5
    coser = [x for x in linhas if x["codigo"] == "2024 / E0274"]
    assert len(coser) == 2 and {x["valor_previsto"] for x in coser} == {Decimal("30000.00")}
    assert coser[0]["municipio_ibge"] == "320120"  # 6 dígitos, sem verificador
    # Linha repetida com outro Id e outro nome de ação (armadilha de 2023 e 2025): fica uma.
    conteudo = _ler("es_emendas-estaduais-2024.csv").decode("utf-8-sig")
    cabecalho, primeira = conteudo.splitlines()[:2]
    repetida = primeira.replace(";299562", ";999999", 1)
    pacote = base.empacotar(
        {"emendas-estaduais-2024.csv": "\r\n".join([cabecalho, primeira, repetida]).encode()}
    )
    assert len(es.normalizar(pacote)) == 1


def test_normalizar_pe_armadilhas():
    linhas = pe.normalizar(_pacote_pe())
    por = {x["proposta"]: x for x in linhas}
    # Empenho repetido uma vez por chamamento: entra uma vez (pago 280 mil, não 560 mil).
    caruaru = [x for x in linhas if x["codigo"] == "1078"]
    assert len(caruaru) == 1 and caruaru[0]["valor_pago"] == Decimal("280000.0")
    # Objeto com `;` entre aspas não desloca as colunas.
    assert por["D30085:2026NE002206"]["valor_pago"] == Decimal("938102.66")
    # Objeto com quebra de linha solta não corta o registro.
    pesqueira = por["P30071:-"]
    assert pesqueira["municipio_nome"] == "PESQUEIRA"
    assert pesqueira["valor_previsto"] == Decimal("1000000.0")
    assert "intertravado" in pesqueira["objeto"]
    assert all(x["ano"] == 2026 for x in linhas)


def test_normalizar_ba_sem_municipio():
    linhas = ba.normalizar(_ler("ba_emendasparlamentares.zip"))
    assert len(linhas) == 5
    assert linhas[0]["autor_nome"] == "Bobô"  # vinha com espaços à esquerda
    assert all(x["municipio_nome"] == "" and x["favorecido_nome"] is None for x in linhas)
    ultima = linhas[-1]
    assert (ultima["valor_previsto"], ultima["valor_empenhado"], ultima["valor_pago"]) == (
        Decimal("226000.00"),
        Decimal("225988.55"),
        Decimal("211019.68"),
    )


def test_normalizar_ac_al_se_ma():
    acre = ac.normalizar(base.empacotar({ac.ARQUIVO: _ler("ac_emendas.csv")}))
    assert len(acre) == 4  # a linha em branco do fim fica de fora
    assert {x["valor_previsto"] for x in acre} == {
        Decimal("1500000"), Decimal("50000"), Decimal("100000"), Decimal("300000.00")
    }  # fmt: skip
    pagina = 'csvUrl = "https://docs.google.com/spreadsheets/d/e/2PACX-x/pub?gid=1&amp;output=csv";'
    assert ac.url_da_pagina(pagina).endswith("pub?gid=1&output=csv")
    alagoas = al.normalizar(base.empacotar({al.ARQUIVO: _ler("al_emendas.json")}))
    assert alagoas[0]["codigo"] == "I0355" and alagoas[0]["valor_pago"] == Decimal("4000000.00")
    sergipe = se.normalizar(base.empacotar({se.ARQUIVO: _ler("se_emendas.json")}))
    assert [x["valor_pago"] for x in sergipe] == [Decimal(0), Decimal("15000"), 0, 0]
    assert sergipe[2]["favorecido_cnpj"] == "34850068000181"  # CNPJ no texto do executor
    assert all(x["valor_empenhado"] is None for x in sergipe)
    assert len({x["proposta"] for x in sergipe}) == 4
    maranhao = ma.normalizar(base.empacotar({ma.ARQUIVO: _ler("ma_emendas.csv")}))
    assert maranhao[-1]["valor_pago"] == Decimal("444464.7")
    assert maranhao[0]["municipio_nome"] == "SÃO LUÍS"


# --------------------------------------------------------------------------- carga e rotas


@pytest.fixture
def minas(session):
    """BH, um deputado eleito e no cargo (Professor Cleiton) e uma deputada sem emenda."""
    if session.get(Municipio, BH) is None:
        session.add(Municipio(ibge=BH, nome="Belo Horizonte", uf="MG", nome_chave="BELO HORIZONTE"))
    c = Candidatura(
        ano_eleicao=2022, sq_candidato="130001", cargo="DEPUTADO ESTADUAL", uf="MG",
        unidade="MINAS GERAIS", nome="Cleiton Gontijo de Azevedo", nome_urna="Professor Cleiton",
        situacao_turno="ELEITO POR QP",
    )  # fmt: skip
    session.add(c)
    session.flush()
    pessoa = Pessoa(nome=c.nome, chave_nome=comum.chave_nome(c.nome))
    session.add(pessoa)
    session.flush()
    session.add(
        PessoaVinculo(pessoa_id=pessoa.id, fonte="candidatura", id_externo="2022:130001",
                      regra="cpf")
    )  # fmt: skip
    mandatos = []
    for ide, nome in (("cleiton", "Professor Cleiton"), ("outra", "Deputada Sem Emenda")):
        m = MandatoLocal(
            casa="assembleia", uf="MG", id_externo=ide, nome=nome, titular=True,
            em_exercicio=True, sapl_url="https://www.almg.gov.br", proposicoes_por_tipo={},
        )  # fmt: skip
        session.add(m)
        mandatos.append(m)
    session.flush()
    session.add(
        PessoaVinculo(pessoa_id=pessoa.id, fonte="mandato_local",
                      id_externo="assembleia:MG::cleiton", regra="nome_exato_casa")
    )  # fmt: skip
    session.flush()
    return {"pessoa": pessoa, "cleiton": mandatos[0], "outra": mandatos[1]}


def test_carga_mg_idempotente_e_aborta(session, minas, monkeypatch):
    monkeypatch.setattr(mg, "MINIMO", 5)
    linhas = mg.normalizar(_pacote_mg())
    for _ in range(2):
        assert base.gravar(session, mg, linhas, _ingestao(session, mg.FONTE)) == 7
    total = session.scalar(select(func.count()).where(EmendaEstadual.uf == "MG"))
    assert total == 7
    gravadas = {x.proposta: x for x in session.scalars(select(EmendaEstadual)).all()}
    assert gravadas["113912"].pessoa_id == minas["pessoa"].id
    assert gravadas["141312"].pessoa_id is None  # bloco
    assert gravadas["114752"].municipio_ibge == BH  # pelo nome
    monkeypatch.setattr(mg, "MINIMO", 500)
    with pytest.raises(ValueError):
        base.gravar(session, mg, linhas, _ingestao(session, mg.FONTE))


def test_rotas_mg(session, client, minas, monkeypatch):
    monkeypatch.setattr(mg, "MINIMO", 5)
    base.gravar(session, mg, mg.normalizar(_pacote_mg()), _ingestao(session, mg.FONTE, "ok"))
    est = client.get(f"/municipios/{BH}/emendas").json()["estaduais"]
    # Pago: 300 + 134,048 + 200 + 160 + 80 + 200 mil (a reprovada pagou zero).
    assert est["total_pago"] == pytest.approx(1_074_048)
    # Previsto sem a indicação reprovada (90 mil).
    assert est["total_previsto"] == pytest.approx(1_090_000)
    assert est["uf"] == "MG" and est["fonte_url"] == mg.PAGINA
    assert est["recorte"] == mg.RECORTE and est["empenhado_informado"] is True
    cleiton = client.get(f"/deputados-estaduais/{minas['cleiton'].id}/emendas").json()
    assert (cleiton["total_pago"], cleiton["emendas"]) == (300_000, 1)
    # Média dos 2 em exercício (o outro tem zero).
    assert cleiton["deputados_na_media"] == 2
    assert cleiton["media_casa_pago"] == pytest.approx(150_000)


def test_ba_sem_bloco_na_cidade_e_se_sem_empenhado(session, client, monkeypatch):
    ssa = "2927408"
    if session.get(Municipio, ssa) is None:
        session.add(Municipio(ibge=ssa, nome="Salvador", uf="BA", nome_chave="SALVADOR"))
    monkeypatch.setattr(ba, "MINIMO", 1)
    base.gravar(session, ba, ba.normalizar(_ler("ba_emendasparlamentares.zip")),
                _ingestao(session, ba.FONTE, "ok"))  # fmt: skip
    # A Bahia não informa o município: nada de bloco (zero) na página da cidade.
    assert client.get(f"/municipios/{ssa}/emendas").json()["estaduais"] is None
    aju = "2800308"
    if session.get(Municipio, aju) is None:
        session.add(Municipio(ibge=aju, nome="Aracaju", uf="SE", nome_chave="ARACAJU"))
    monkeypatch.setattr(se, "MINIMO", 1)
    linhas = se.normalizar(base.empacotar({se.ARQUIVO: _ler("se_emendas.json")}))
    base.gravar(session, se, linhas, _ingestao(session, se.FONTE, "ok"))
    est = client.get(f"/municipios/{aju}/emendas").json()["estaduais"]
    assert est["empenhado_informado"] is False
    assert (est["total_previsto"], est["total_pago"]) == (285_000, 15_000)


def test_chave_longa_ou_repetida_aborta(session, monkeypatch):
    monkeypatch.setattr(al, "MINIMO", 1)
    linhas = al.normalizar(base.empacotar({al.ARQUIVO: _ler("al_emendas.json")}))
    with pytest.raises(ValueError, match="repetida"):
        base.gravar(session, al, linhas + linhas[:1], _ingestao(session, al.FONTE))
    linhas[0]["proposta"] = "x" * 61
    with pytest.raises(ValueError, match="longo"):
        base.gravar(session, al, linhas, _ingestao(session, al.FONTE))


def test_registro_tem_todas_as_ufs_com_atributos():
    from ingestion.emendas_estaduais.registro import ADAPTADORES

    for uf, a in ADAPTADORES.items():
        assert a.UF == uf
        for nome in ("FONTE", "URL", "PAGINA", "FONTE_NOME", "CASA", "RECORTE", "TERMOS"):
            assert getattr(a, nome), (uf, nome)
        assert isinstance(a.MINIMO, int) and isinstance(a.SITUACOES_FORA, tuple)
    assert len(ADAPTADORES) == 12


# --------------------------------------------------------------------------- DF, GO e PB


def _zip_go(conteudo: bytes) -> bytes:
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("Emendas Parlamentares 2023.csv", conteudo)
    return saida.getvalue()


def test_normalizar_df():
    linhas = df.normalizar(base.empacotar({df.ARQUIVO: _ler("df_emendas.json")}))
    assert len(linhas) == 3 and len({x["proposta"] for x in linhas}) == 3
    dayse = linhas[0]
    assert dayse["autor_nome"] == "DAYSE AMARILIO" and dayse["tipo"] is None
    assert dayse["valor_previsto"] == Decimal("11700000.00")  # autorizado, não o aprovado
    assert dayse["valor_pago"] == Decimal("11254378.44")  # sem passar por float
    assert dayse["municipio_ibge"] == df.BRASILIA and dayse["favorecido_nome"] is None
    assert dayse["orgao"] == "SECRETARIA DE EST. DE JUSTIÇA E CIDADANIA DO DF"
    coletiva = linhas[2]
    assert coletiva["tipo"] == "bancada" and coletiva["autor_nome"].startswith("CHICO VIGILANTE -")
    # A chave não depende da ordem nem de campos de valor.
    assert df.chave(json.loads(_ler("df_emendas.json"))[0]) == dayse["proposta"]


def test_normalizar_go_confere_total_e_cnpj():
    linhas = go.normalizar(_zip_go(_ler("go_emendas_2023.csv")))
    assert len(linhas) == 5  # sem "Total", linha em branco e "Filtros aplicados"
    assert {x["ano"] for x in linhas} == {2023}
    assert len({x["codigo"] for x in linhas}) == 5  # a emenda 10 tem duas linhas
    assert sum(x["valor_pago"] for x in linhas) == Decimal("2191097.56")
    cnpjs = [x["favorecido_cnpj"] for x in linhas]
    assert "00001883000154" in cnpjs and "01112580000171" in cnpjs  # zeros devolvidos
    assert linhas[0]["municipio_nome"] == "BURITI ALEGRE"
    assert linhas[0]["autor_nome"] == "Helio De Sousa"
    # Soma que não bate com o "Total" do arquivo: aborta.
    adulterado = _ler("go_emendas_2023.csv").replace(b"2191097,56", b"2191097,00", 1)
    with pytest.raises(ValueError, match="soma"):
        go.normalizar(_zip_go(adulterado))


def test_documento_go_nao_guarda_cpf():
    assert go.documento("1112580000171") == ("01112580000171", False)
    assert go.documento("52998224725") == (None, True)  # CPF válido (exemplo público)
    assert go.documento("12345") == (None, False)  # verificador não confere


def test_normalizar_pb():
    linhas = pb.normalizar(base.empacotar({pb.ARQUIVO: _ler("pb_execucao.json")}))
    assert len(linhas) == 3 and len({x["proposta"] for x in linhas}) == 3
    codigos = sorted(x["codigo"] for x in linhas)
    assert codigos == ["0005/2025", "0019/2025", "0019/2025 (2)"]
    galego = [x for x in linhas if x["codigo"].startswith("0019")]
    assert sum(x["valor_previsto"] for x in galego) == Decimal("604500.0")
    assert base.nomes_do_autor(galego[0]["autor_nome"])[-1] == "GALEGO SOUZA"
    assert all(x["municipio_ibge"] is None and x["favorecido_nome"] is None for x in linhas)


def test_carga_df_pb_go(session, client, monkeypatch):
    if session.get(Municipio, df.BRASILIA) is None:
        session.add(Municipio(ibge=df.BRASILIA, nome="Brasília", uf="DF", nome_chave="BRASILIA"))
    buriti = "5204102"
    if session.get(Municipio, buriti) is None:
        session.add(Municipio(ibge=buriti, nome="Buriti Alegre", uf="GO",
                              nome_chave="BURITI ALEGRE"))  # fmt: skip
    for adaptador in (df, go, pb):
        monkeypatch.setattr(adaptador, "MINIMO", 1)
    pacote_df = base.empacotar({df.ARQUIVO: _ler("df_emendas.json")})
    for _ in range(2):  # idempotente
        assert base.gravar(session, df, df.normalizar(pacote_df),
                           _ingestao(session, df.FONTE, "ok")) == 3  # fmt: skip
    base.gravar(session, go, go.normalizar(_zip_go(_ler("go_emendas_2023.csv"))),
                _ingestao(session, go.FONTE, "ok"))  # fmt: skip
    base.gravar(session, pb, pb.normalizar(base.empacotar({pb.ARQUIVO: _ler("pb_execucao.json")})),
                _ingestao(session, pb.FONTE, "ok"))  # fmt: skip
    contagem = dict(
        session.execute(
            select(EmendaEstadual.uf, func.count())
            .where(EmendaEstadual.uf.in_(("DF", "GO", "PB")))
            .group_by(EmendaEstadual.uf)
        ).all()
    )
    assert contagem == {"DF": 3, "GO": 5, "PB": 3}
    est = client.get(f"/municipios/{df.BRASILIA}/emendas").json()["estaduais"]
    assert est["uf"] == "DF" and est["recorte"] == df.RECORTE
    assert est["total_pago"] == pytest.approx(11254378.44 + 10879000 + 5750571.32)
    est = client.get(f"/municipios/{buriti}/emendas").json()["estaduais"]
    assert est["total_previsto"] == pytest.approx(1_380_000)  # as duas linhas da emenda 10
