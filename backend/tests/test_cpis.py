import json
from datetime import date, datetime
from pathlib import Path

import pytest
import respx
from sqlalchemy import select

from app.models import (
    Candidatura,
    Cpi,
    CpiIndiciamentoSugestao,
    CpiParticipacao,
    Evento,
    FonteIngestao,
    Parlamentar,
    Pessoa,
    PessoaVinculo,
)
from ingestion import comum
from ingestion.congresso import cpi_indiciamentos, cpis

FIXTURES = Path(__file__).parent / "fixtures" / "cpi"


def _html(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


def _json(nome: str):
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


# --- cargos e Câmara ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("PRESIDENTE", "Presidente"),
        ("1º VICE-PRESIDENTE", "Vice-presidente"),
        ("3º Vice-Presidente", "Vice-presidente"),
        ("RELATOR", "Relator"),
        ("RELATORA", "Relatora"),
        ("Titular", "Titular"),
        ("Suplente", "Suplente"),
    ],
)
def test_cargo_normalizado(bruto, esperado):
    assert cpis.cargo_normalizado(bruto) == esperado


def test_cpi_da_camara_com_cargos_e_relatorio():
    dados = _json("cpi_camara.json")
    relatorio = cpis.relatorio_camara(
        dados["tramitacoes"], "CPIBRUMA", date(2019, 3, 14), date(2020, 1, 4)
    )
    # Entre a "apresentação do relatório do relator" e o "relatório final", fica o final.
    assert relatorio["url"].endswith("codteor=1826809") and "final" in relatorio["rotulo"].lower()
    (cpi,) = cpis.linhas_camara([dados["orgao"]], dados["membros"], {"538350": relatorio})
    assert (cpi["casa"], cpi["id_externo"], cpi["tipo"], cpi["sigla"]) == (
        "camara", "538350", "CPI", "CPIBRUMA"
    )  # fmt: skip
    assert cpi["nome"] == "CPI - Rompimento da Barragem de Brumadinho"
    assert cpi["objeto"].startswith("Comissão Parlamentar de Inquérito destinada a investigar")
    assert cpi["data_instalacao"] == date(2019, 4, 25) and cpi["data_fim"] == date(2019, 11, 5)
    assert cpi["situacao"] == "Parecer aprovado"
    assert cpi["fonte_url"] == "https://dadosabertos.camara.leg.br/api/v2/orgaos/538350"
    cargos = {(p["nome"], p["cargo"]) for p in cpi["participacoes"]}
    assert ("Rogério Correia", "Relator") in cargos
    assert any(c == "Presidente" for _, c in cargos)
    assert any(c == "Vice-presidente" for _, c in cargos)
    assert any(c == "Suplente" for _, c in cargos)
    assert all(p["casa_parlamentar"] == "camara" and p["id_parlamentar"].isdigit()
               for p in cpi["participacoes"])  # fmt: skip


def test_relatorio_so_dentro_da_vida_da_cpi_e_sem_diligencia():
    tram = _json("cpi_camara.json")["tramitacoes"]
    assert cpis.relatorio_camara(tram, "CPIBRUMA", date(2020, 1, 1), date(2020, 6, 1)) is None
    assert cpis.relatorio_camara(tram, "OUTRASIGLA", date(2019, 1, 1), date(2020, 6, 1)) is None
    diligencia = [
        {"siglaOrgao": "X", "dataHora": "2023-06-23T10:00", "url": "http://u",
         "despacho": "Apresentação da REL n. 1/2023 (Relatório), pela CPI: Relatório da diligência"
         " do relator", "descricaoTramitacao": "Apresentação de Proposição"}
    ]  # fmt: skip
    assert cpis.relatorio_camara(diligencia, "X", date(2023, 1, 1), date(2023, 12, 1)) is None


def test_so_cpis_desde_2019_e_tipo_cpi():
    orgaos = [
        {"uri": ".../orgaos/1", "codTipoOrgao": 4, "dataInicio": "2018-07-03T00:00:00"},
        {"uri": ".../orgaos/2", "codTipoOrgao": 4, "dataInicio": "2019-03-14T00:00:00"},
        {"uri": ".../orgaos/3", "codTipoOrgao": 3, "dataInicio": "2020-03-14T00:00:00"},
        {"uri": ".../orgaos/4", "codTipoOrgao": 20, "dataInicio": "2023-03-14T00:00:00"},
    ]
    assert [o["uri"] for o in cpis.orgaos_cpi_camara(orgaos)] == [".../orgaos/2"]


# --- Senado e Congresso -------------------------------------------------------------------


def test_composicao_da_cpi_da_pandemia():
    membros = cpis.membros_do_html(_html("senado_composicao_cpipandemia.html"))
    por_cargo = {m["cargo"]: m for m in membros if m["cargo"] not in ("Titular", "Suplente")}
    assert por_cargo["Presidente"]["nome"] == "Omar Aziz"
    presidente = por_cargo["Presidente"]
    assert (presidente["casa_parlamentar"], presidente["id_parlamentar"]) == ("senado", "5525")
    assert (presidente["partido"], presidente["uf"]) == ("PSD", "AM")
    assert por_cargo["Relator"]["nome"] == "Renan Calheiros"
    assert por_cargo["Relator"]["id_parlamentar"] == "70"
    assert por_cargo["Vice-presidente"]["nome"] == "Randolfe Rodrigues"
    vagas = [m["cargo"] for m in membros]
    assert "Titular" in vagas and "Suplente" in vagas
    assert any(m["nome"] == "Eduardo Braga" and m["cargo"] == "Titular" for m in membros)


def test_cpmi_traz_o_id_do_deputado_na_camara():
    membros = cpis.membros_do_html(_html("senado_composicao_cpmi8jan.html"))
    presidente = next(m for m in membros if m["cargo"] == "Presidente")
    assert (presidente["nome"], presidente["casa_parlamentar"], presidente["id_parlamentar"]) == (
        "Arthur Oliveira Maia", "camara", "160600"
    )  # fmt: skip
    relatora = next(m for m in membros if m["cargo"] == "Relatora")
    assert (relatora["nome"], relatora["casa_parlamentar"]) == ("Eliziane Gama", "senado")
    assert {m["casa_parlamentar"] for m in membros} == {"camara", "senado"}


def test_pagina_da_comissao_situacao_datas_e_relatorio():
    d = cpis.dados_da_pagina(_html("senado_comissao_cpipandemia.html"))
    assert d["situacao"] == "Encerrada"
    assert d["finalidade"].startswith("Apurar, no prazo de 90 dias")
    assert (date(2021, 4, 27), "Instalação") in d["eventos"]
    url, rotulo = d["relatorio"]
    assert url.endswith("documento/download/72c805d3-888b-4228-8682-260175471243")
    assert rotulo == "Relatório Final aprovado"
    # O "&amp;" do HTML vira "&" no link.
    d2 = cpis.dados_da_pagina(_html("senado_comissao_cpmi8jan.html"))
    assert "&ts=" in d2["relatorio"][0] and "&amp;" not in d2["relatorio"][0]
    assert cpis.dados_da_pagina(_html("senado_comissao_cpmifake.html"))["relatorio"] is None


def _colegiado(nome: str, comissao: str, composicao: str, casa="SF", codigo="2441", sigla="X"):
    return {"codigo": codigo, "sigla": sigla, "nome": nome, "casa": casa,
            "comissao_html": _html(comissao), "composicao_html": _html(composicao)}  # fmt: skip


def test_linha_do_senado_e_do_congresso():
    pandemia = cpis.linha_senado(
        _colegiado("CPI da Pandemia", "senado_comissao_cpipandemia.html",
                   "senado_composicao_cpipandemia.html", sigla="CPIPANDEMIA")
    )  # fmt: skip
    assert (pandemia["casa"], pandemia["tipo"], pandemia["id_externo"]) == ("senado", "CPI", "2441")
    assert pandemia["data_instalacao"] == date(2021, 4, 27)
    assert pandemia["data_fim"] == date(2021, 11, 5)  # último "prazo final"
    assert pandemia["fonte_url"] == "https://legis.senado.leg.br/comissoes/comissao?codcol=2441"
    cpmi = cpis.linha_senado(
        _colegiado("CPMI dos Atos de 8 de Janeiro", "senado_comissao_cpmi8jan.html",
                   "senado_composicao_cpmi8jan.html", casa="CN", codigo="2606")
    )  # fmt: skip
    assert (cpmi["casa"], cpmi["tipo"]) == ("congresso", "CPMI")
    assert cpmi["data_instalacao"] == date(2023, 5, 25)


def test_comissao_anterior_a_2019_ou_sem_data_fica_de_fora():
    antiga = _html("senado_comissao_cpmifake.html").replace("/2019", "/2018")
    col = _colegiado("CPMI Fake News", "senado_comissao_cpmifake.html",
                     "senado_composicao_cpmi8jan.html", casa="CN")  # fmt: skip
    assert cpis.linha_senado(col)["data_instalacao"] == date(2019, 9, 4)
    col["comissao_html"] = antiga
    assert cpis.linha_senado(col) is None
    col["comissao_html"] = "<dl><dt>Situação atual</dt><dd>Aguardando Instalac?o</dd></dl>"
    assert cpis.linha_senado(col) is None
    col["data_inicio"] = "2024-03-13"  # a lista de CPIs em atividade dá a data de criação
    linha = cpis.linha_senado(col)
    assert linha["data_criacao"] == date(2024, 3, 13) and linha["data_instalacao"] is None
    assert linha["situacao"] == "Aguardando Instalação"


def _comissao_do_senador(codigo, sigla, nome, casa, inicio, fim=None):
    return {
        "IdentificacaoComissao": {
            "CodigoComissao": codigo,
            "SiglaComissao": sigla,
            "NomeComissao": nome,
            "SiglaCasaComissao": casa,
        },
        "DescricaoParticipacao": "Titular",
        "DataInicio": inicio,
        **({"DataFim": fim} if fim else {}),
    }


def test_comissoes_do_senador_so_cpi_desde_2019():
    lista = [
        _comissao_do_senador("1928", "CPIDFDQ", "CPI do Futebol - 2015", "SF", "2015-07-07",
                             "2016-12-09"),
        _comissao_do_senador("2441", "CPIPANDEMIA", "CPI da Pandemia", "SF", "2021-04-15",
                             "2021-11-03"),
        _comissao_do_senador("2606", "CPMI - 8 de Janeiro",
                             "Comissão Parlamentar Mista de Inquérito dos Atos de 8 de Janeiro",
                             "CN", "2023-05-18", "2023-10-18"),
        _comissao_do_senador("2050", "GPMARROCOS", "Grupo Parlamentar Brasil - Marrocos", "CN",
                             "2023-01-01"),
    ]  # fmt: skip
    achadas = cpis.comissoes_de_inquerito(lista)
    assert set(achadas) == {"2441", "2606"}
    assert achadas["2606"]["casa"] == "CN"


def test_colegiados_da_lista_aninhada():
    resposta = {"ListaBasicaComissoes": {"colegiado": {"colegiados": [{"colegiado": [
        {"CodigoColegiado": "2658", "SiglaColegiado": "CPIVD", "DataInicio": "2024-03-13"},
        {"CodigoColegiado": "2805", "SiglaColegiado": "CPIPED"},
    ]}]}}}  # fmt: skip
    assert [c["CodigoColegiado"] for c in cpis.colegiados_da_lista(resposta)] == ["2658", "2805"]
    assert cpis.colegiados_da_lista({"ListaBasicaComissoes": {"Metadados": {}}}) == []


def test_papel_pelo_maior_cargo():
    assert cpis.papel(["Titular", "Presidente"]) == "Presidente"
    assert cpis.papel(["Suplente", "Titular"]) == "Membro titular"
    assert cpis.papel(["Suplente"]) == "Membro suplente"
    assert cpis.papel(["Relator", "Vice-presidente", "Titular"]) == "Relator e vice-presidente"


# --- carga no banco -----------------------------------------------------------------------


def _ingestao(session):
    ingestao = FonteIngestao(fonte="cpis", url="https://exemplo", arquivo_raw="x.json")
    session.add(ingestao)
    session.flush()
    return ingestao


def _parlamentar(session, casa, id_externo, nome, uf):
    pessoa = Pessoa(nome=nome, chave_nome=comum.chave_nome(nome))
    session.add(pessoa)
    session.flush()
    session.add(
        Parlamentar(
            casa=casa, id_externo=id_externo, nome_parlamentar=nome, uf=uf,
            fonte_url="https://exemplo", atualizado_em=datetime(2026, 10, 9),
        )
    )  # fmt: skip
    session.add(
        PessoaVinculo(
            pessoa_id=pessoa.id, fonte="parlamentar", id_externo=f"{casa}:{id_externo}",
            regra="origem",
        )
    )  # fmt: skip
    return pessoa


def _cenario(session):
    omar = _parlamentar(session, "senado", "5525", "Omar Aziz", "AM")
    renan = _parlamentar(session, "senado", "70", "Renan Calheiros", "AL")
    # Ex-senador, fora do cadastro: só o eleito pelo nome de urna e UF o liga.
    heinze = Pessoa(nome="Luis Carlos Heinze", chave_nome="LUIS CARLOS HEINZE")
    session.add(heinze)
    session.flush()
    session.add(
        Candidatura(
            ano_eleicao=2018, sq_candidato="900", cargo="SENADOR", uf="RS", unidade="RS",
            nome="Luis Carlos Heinze", nome_urna="Luis Carlos Heinze", situacao_turno="ELEITO",
        )
    )  # fmt: skip
    session.add(
        PessoaVinculo(
            pessoa_id=heinze.id, fonte="candidatura", id_externo="2018:900", regra="origem"
        )
    )
    return omar, renan, heinze


def _pandemia():
    return cpis.linha_senado(
        _colegiado("CPI da Pandemia", "senado_comissao_cpipandemia.html",
                   "senado_composicao_cpipandemia.html", sigla="CPIPANDEMIA")
    )  # fmt: skip


def test_gravar_liga_por_id_e_por_nome_e_gera_um_evento_por_pessoa(session):
    omar, renan, heinze = _cenario(session)
    cpi = _pandemia()
    # Mesmo nome de um eleito de outra UF não liga; um suplente sem registro fica sem pessoa.
    cpi["participacoes"].append(
        {"casa_parlamentar": "senado", "id_parlamentar": "9999", "nome": "Luis Carlos Heinze",
         "partido": "PP", "uf": "SC", "cargo": "Titular", "data_inicio": None, "data_fim": None}
    )  # fmt: skip
    ingestao = _ingestao(session)
    assert cpis.gravar(session, [cpi], ingestao.id) == 3  # Omar, Renan e Heinze
    registro = session.scalars(select(Cpi)).one()
    assert registro.sigla == "CPIPANDEMIA" and registro.relatorio_url
    partic = {(p.nome, p.cargo): p for p in session.scalars(select(CpiParticipacao))}
    assert partic[("Omar Aziz", "Presidente")].pessoa_id == omar.id
    assert partic[("Omar Aziz", "Presidente")].regra == "origem"
    assert partic[("Renan Calheiros", "Relator")].pessoa_id == renan.id
    assert partic[("Luis Carlos Heinze", "Titular")].regra in ("nome_parlamentar", None)
    por_regra = [
        p for p in session.scalars(select(CpiParticipacao)) if p.nome == "Luis Carlos Heinze"
    ]
    assert {(p.id_parlamentar, p.pessoa_id) for p in por_regra} == {
        ("1186", heinze.id),
        ("9999", None),
    }
    eventos = {e.pessoa_id: e for e in session.scalars(select(Evento).where(Evento.tipo == "cpi"))}
    assert set(eventos) == {omar.id, renan.id, heinze.id}
    e = eventos[omar.id]
    assert e.descricao.startswith(
        "Presidente na CPI da Pandemia, comissão parlamentar de inquérito"
    )
    assert "instalada em 27/04/2021" in e.descricao and "Apurar, no prazo de 90 dias" in e.descricao
    assert e.data == date(2021, 4, 27) and e.orgao == "Senado Federal – CPI"
    assert e.numero_processo == "CPIPANDEMIA" and e.situacao == "Encerrada"
    assert e.fonte == "cpis" and e.fonte_url.endswith("codcol=2441")
    assert eventos[renan.id].descricao.startswith("Relator na CPI da Pandemia")
    assert eventos[heinze.id].descricao.startswith("Membro titular na CPI da Pandemia")
    # Todo evento aponta para um vínculo forte da própria pessoa.
    for e in eventos.values():
        v = session.get(PessoaVinculo, e.vinculo_id)
        assert v.pessoa_id == e.pessoa_id and v.regra in ("origem", "nome_parlamentar")


def test_gravar_e_idempotente_e_aborta_sem_cpis(session):
    omar, renan, heinze = _cenario(session)
    for _ in range(2):
        cpis.gravar(session, [_pandemia()], _ingestao(session).id)
    assert len(session.scalars(select(Cpi)).all()) == 1
    assert len(session.scalars(select(Evento).where(Evento.tipo == "cpi")).all()) == 3
    assert (
        len(session.scalars(select(PessoaVinculo).where(PessoaVinculo.fonte == "cpis")).all()) == 3
    )
    with pytest.raises(RuntimeError):
        cpis.gravar(session, [], None)
    assert len(session.scalars(select(Evento).where(Evento.tipo == "cpi")).all()) == 3


# --- sugestões de indiciamento --------------------------------------------------------------


def _paginas(nome: str) -> list[str]:
    """As páginas reais do recorte, depois de 10 páginas de abertura (sumário e afins)."""
    return [""] * 10 + [texto for _, texto in _json("cpi_relatorios_paginas.json")[nome]]


def test_lista_numerada_com_nome_dois_pontos_brumadinho():
    s = cpi_indiciamentos.sugestoes_do_texto(_paginas("brum"))
    nomes = [x["nome_citado"] for x in s]
    assert nomes[:3] == [
        "Vale S.A",
        "Tüv Süd Bureau de Projetos e Consultoria L tda",
        "Fabio Schvartsman",
    ]
    assert [x["pessoa_juridica"] for x in s[:3]] == [True, True, False]
    assert len(nomes) >= 4  # o recorte tem as páginas 614, 615, 624 e 625; a lista quebra no 5
    assert s[0]["trecho"].startswith("1) Vale S.A: art. 33")
    # Quem só deve ser investigado mais a fundo não é pedido de indiciamento.
    assert not any("Siani" in n or "Baras" in n for n in nomes)
    assert all(len(x["trecho"]) <= 600 for x in s)


def test_lista_numerada_com_travessao_covid():
    s = cpi_indiciamentos.sugestoes_do_texto(_paginas("covid"))
    nomes = [x["nome_citado"] for x in s]
    assert nomes[:3] == ["JAIR MESSIAS BOLSONARO", "EDUARDO PAZUELLO",
                         "MARCELO ANTÔNIO C. QUEIROGA LOPES"]  # fmt: skip
    assert "ONYX DORNELLES LORENZONI" in nomes and len(nomes) == 9
    assert s[0]["trecho"].startswith("1) JAIR MESSIAS BOLSONARO – Presidente da República")


def test_marcadores_com_nomes_em_maiusculas_bndes():
    s = cpi_indiciamentos.sugestoes_do_texto(_paginas("bndes"))
    nomes = [x["nome_citado"] for x in s]
    assert nomes[0] == "LUIS INÁCIO LULA DA SILVA"
    # Nome com "E" no meio não é cortado; o "E" de fim de lista separa dois nomes.
    assert "LUIZ EDUARDO MELIN DE CARVALHO E SILVA" in nomes
    assert {"JOSÉ PIO BORGES", "EMILIO HUMBERTO CARAZZAI SOBRINHO"} <= set(nomes)
    # A seção seguinte (12.2.2, rescisão de acordos de colaboração) não entra.
    assert "JOSÉ BATISTA SOBRINHO" not in nomes


def test_sem_secao_de_indiciamentos_nao_devolve_nada():
    assert cpi_indiciamentos.sugestoes_do_texto([""] * 10 + ["Texto qualquer sem a seção."]) == []
    # Sumário (linha com pontilhado) não conta como título.
    sumario = "10.4.3 Sugestão de indiciamentos ......... 614"
    assert cpi_indiciamentos.sugestoes_do_texto([""] * 10 + [sumario]) == []


def test_gravar_sugestoes_nao_vira_evento_e_preserva_revisadas(session):
    cpis.gravar(session, [_pandemia()], _ingestao(session).id)
    cpi = session.scalars(select(Cpi)).one()
    s = cpi_indiciamentos.sugestoes_do_texto(_paginas("covid"))
    resultado = [{"casa": "senado", "id_externo": "2441", "url": "https://pdf", "sugestoes": s}]
    eventos_antes = len(session.scalars(select(Evento)).all())
    assert cpi_indiciamentos.gravar(session, resultado) == 9
    linhas = session.scalars(select(CpiIndiciamentoSugestao)).all()
    assert len(linhas) == 9 and not any(x.revisado for x in linhas)
    assert all(x.cpi_id == cpi.id and x.url == "https://pdf" for x in linhas)
    # Nada publicável: nenhum evento novo e nenhum vínculo com pessoa.
    assert len(session.scalars(select(Evento)).all()) == eventos_antes
    assert not hasattr(CpiIndiciamentoSugestao, "pessoa_id")
    # Revisada uma, a recarga troca as outras e mantém a revisada.
    linhas[0].revisado = True
    session.flush()
    assert cpi_indiciamentos.gravar(session, resultado) == 9
    session.expire_all()
    todas = session.scalars(select(CpiIndiciamentoSugestao)).all()
    assert len(todas) == 9 and sum(x.revisado for x in todas) == 1


def test_so_relatorio_adotado_e_elegivel():
    def cpi(casa, situacao, rotulo, url="https://r"):
        return Cpi(casa=casa, id_externo="1", tipo="CPI", nome="x", situacao=situacao,
                   relatorio_rotulo=rotulo, relatorio_url=url)  # fmt: skip

    elegivel = cpi_indiciamentos.elegivel
    assert elegivel(cpi("camara", "Parecer aprovado", "Relatório final"))
    assert not elegivel(cpi("camara", "Extinta", "Relatório final"))
    assert not elegivel(cpi("camara", "Parecer aprovado", "x", url=None))
    assert elegivel(cpi("senado", "Encerrada", "Relatório Final aprovado"))
    assert not elegivel(cpi("senado", "Encerrada", "Relatório final apresentado pelo relator"))


def test_resposta_que_nao_e_pdf_fica_registrada_como_bloqueada(tmp_path):
    html = tmp_path / "x.pdf"
    html.write_text("<!DOCTYPE html><title>Verificação de segurança</title>", encoding="utf-8")
    r = cpi_indiciamentos.processar(None, {"url": "https://x"}, pdf=html)
    assert r["status"].startswith("bloqueado") and r["sugestoes"] == []


# --- rede (respx) -------------------------------------------------------------------------


@respx.mock
def test_baixar_camara_filtra_cpis_e_acha_o_relatorio(monkeypatch):
    monkeypatch.setattr(cpis, "PAUSA", 0)
    dados = _json("cpi_camara.json")
    outro = {**dados["orgao"], "uri": ".../orgaos/1", "codTipoOrgao": 3}
    respx.get(cpis.URL_CD_ORGAOS).respond(json={"dados": [dados["orgao"], outro]})
    membros = dados["membros"] + [{**dados["membros"][0], "uriOrgao": ".../orgaos/1"}]
    respx.get(cpis.URL_CD_MEMBROS.format(leg=56)).respond(json={"dados": membros})
    respx.get(cpis.URL_CD_MEMBROS.format(leg=57)).respond(404)  # arquivo ainda não existe
    respx.get(cpis.API_CD + "/proposicoes").respond(
        json={"dados": [{"id": 2190415}], "links": [{"rel": "self", "href": "x"}]}
    )
    respx.get(cpis.API_CD + "/proposicoes/2190415/tramitacoes").respond(
        json={"dados": dados["tramitacoes"]}
    )
    with comum.criar_cliente() as client:
        bruto = cpis.baixar_camara(client)
    assert [o["sigla"] for o in bruto["orgaos"]] == ["CPIBRUMA"]  # a comissão especial sai
    assert len(bruto["membros"]) == len(dados["membros"])  # e os membros dela também
    assert bruto["relatorios"]["538350"]["url"].endswith("codteor=1826809")


@respx.mock
def test_baixar_senado_acha_cpis_encerradas_pelos_senadores_e_pelas_em_atividade(monkeypatch):
    monkeypatch.setattr(cpis, "PAUSA", 0)
    monkeypatch.setattr(cpis, "_legislatura_atual", lambda: 56)
    base = cpis.URL_SF
    senador = {"IdentificacaoParlamentar": {"CodigoParlamentar": 5525}}
    respx.get(base + "/senador/lista/legislatura/56").respond(
        json={"ListaParlamentarLegislatura": {"Parlamentares": {"Parlamentar": senador}}}
    )  # um senador só: a API devolve objeto, e não lista
    pandemia = _comissao_do_senador("2441", "CPIPANDEMIA", "CPI da Pandemia", "SF", "2021-04-15")
    respx.get(base + "/senador/5525/comissoes").respond(
        json={
            "MembroComissaoParlamentar": {
                "Parlamentar": {"MembroComissoes": {"Comissao": [pandemia]}}
            }
        }
    )
    respx.get(base + "/comissao/lista/CPI").respond(
        json={
            "ListaBasicaComissoes": {
                "colegiado": {
                    "colegiados": [
                        {
                            "colegiado": [
                                {
                                    "CodigoColegiado": "2658",
                                    "NomeColegiado": "CPI da Violência Doméstica",
                                    "SiglaColegiado": "CPIVD",
                                    "DataInicio": "2024-03-13",
                                    "SiglaCasa": "SF",
                                }
                            ]
                        }
                    ]
                }
            }
        }
    )
    paginas = {
        "2441": (
            _html("senado_comissao_cpipandemia.html"),
            _html("senado_composicao_cpipandemia.html"),
        ),
        "2658": ("<dl><dt>Situação atual</dt><dd>Aguardando Instalac?o</dd></dl>", "<div></div>"),
    }
    for codigo, (comissao, composicao) in paginas.items():
        respx.get(cpis.URL_SF_COMISSAO.format(codigo=codigo)).respond(text=comissao)
        respx.get(cpis.URL_SF_COMPOSICAO.format(codigo=codigo)).respond(text=composicao)
    with comum.criar_cliente() as client:
        colegiados = cpis.baixar_senado(client)
        assert client.headers["Accept"] == "application/json"  # voltou ao padrão depois do HTML
    assert {c["codigo"] for c in colegiados} == {"2441", "2658"}
    linhas = [c for c in map(cpis.linha_senado, colegiados) if c]
    assert {(c["sigla"], c["situacao"]) for c in linhas} == {
        ("CPIPANDEMIA", "Encerrada"),
        ("CPIVD", "Aguardando Instalação"),
    }


@respx.mock
def test_pdf_do_relatorio_baixado_e_lido(monkeypatch, tmp_path):
    """O download passa pela mesma rotina dos outros arquivos grandes (em fluxo, para um
    arquivo temporário) e a resposta HTML de verificação de segurança não é tratada como PDF."""
    respx.get("https://pdf.exemplo/bloqueado").respond(
        text="<!DOCTYPE html><title>Verificação de segurança — Senado Federal</title>"
    )
    with comum.criar_cliente() as client:
        r = cpi_indiciamentos.processar(client, {"url": "https://pdf.exemplo/bloqueado"})
    assert r["status"].startswith("bloqueado") and r["paginas"] == 0
    respx.get("https://pdf.exemplo/fora").respond(404)
    monkeypatch.setattr(comum.time, "sleep", lambda _: None)
    with comum.criar_cliente() as client:
        r = cpi_indiciamentos.processar(client, {"url": "https://pdf.exemplo/fora"})
    assert r["status"].startswith("erro de rede") and r["sugestoes"] == []
