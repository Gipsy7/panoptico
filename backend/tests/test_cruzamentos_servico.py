"""Serviço de cruzamentos por pessoa (app/services/cruzamentos.py), chamado direto, sem a API.

As rotas já têm teste em test_cruzamentos.py; aqui ficam os ramos que a rota não exercita:
pessoa inexistente, pessoa sem nenhum dado, a média da Casa com quem não tem registro
entrando com zero e os vínculos não publicáveis ficando de fora.
"""

from datetime import UTC, date, datetime
from xml.etree import ElementTree as ET

import pytest

from app.models import (
    Candidatura,
    CpgfPortadorMes,
    Evento,
    FonteIngestao,
    Parlamentar,
    ServidorFederal,
    ViagemFederalAno,
)
from app.services import cruzamentos
from tests.test_cruzamentos import _evento, _pessoa, _vinculo

NS = {"a": cruzamentos.ATOM}
INEXISTENTE = 999_999


def _carga(session, fonte, quando, status="ok"):
    session.add(
        FonteIngestao(
            fonte=fonte, url="https://exemplo", arquivo_raw="x", status=status, concluido_em=quando
        )
    )
    session.flush()


def _parlamentar(session, casa, id_externo, em_exercicio=True):
    p = Parlamentar(
        casa=casa, id_externo=id_externo, nome_parlamentar=f"P{id_externo}", uf="AC",
        fonte_url="https://x", atualizado_em=datetime(2026, 1, 1, tzinfo=UTC),
        em_exercicio=em_exercicio,
    )  # fmt: skip
    session.add(p)
    session.flush()
    return p


def _viagem(session, pessoa, ano, viagens, diarias=0, passagens=0, outros=0):
    session.add(
        ViagemFederalAno(
            pessoa_id=pessoa.id, ano=ano, viagens=viagens, diarias=diarias, passagens=passagens,
            outros=outros, devolucao=0,
        )
    )  # fmt: skip
    session.flush()


# ---- pessoa inexistente --------------------------------------------------------------


@pytest.mark.parametrize("funcao", ["sancoes", "servico_federal", "carreira"])
def test_pessoa_inexistente_devolve_none(session, funcao):
    assert getattr(cruzamentos, funcao)(session, INEXISTENTE) is None


def test_feed_de_pessoa_inexistente_devolve_none(session):
    assert cruzamentos.feed_atom(session, INEXISTENTE, "https://f", "https://p") is None


# ---- sanções -------------------------------------------------------------------------


def test_sancoes_sem_registro_lista_vazia_e_data_das_fontes_padrao(session):
    p = _pessoa(session)
    _carga(session, "cgu_ceis", datetime(2026, 5, 1, tzinfo=UTC))
    _carga(session, "cgu_cnep", datetime(2026, 6, 1, tzinfo=UTC), status="erro")
    r = cruzamentos.sancoes(session, p.id)
    assert r["itens"] == []
    # Sem item, a data é a da última carga ok entre CEIS, CNEP e CEAF (a com erro não conta).
    assert r["atualizado_em"] == datetime(2026, 5, 1, tzinfo=UTC)
    assert r["fonte_url"] == cruzamentos.URL_SANCOES


def test_sancoes_inclui_tcu_ordena_por_data_e_descreve_a_revisao_manual(session):
    p = _pessoa(session)
    revisado = _vinculo(session, p, "tcu_contas", "1", "nome_casa", revisado=True)
    forte = _vinculo(session, p, "cgu_ceis", "2", "cpf")
    _evento(session, p, revisado, tipo="tcu_contas_irregulares", data=date(2022, 1, 1))
    _evento(session, p, forte, tipo="sancao", data=date(2025, 1, 1))
    _evento(session, p, forte, tipo="tcu_inabilitacao", data=None)
    _evento(session, p, forte, tipo="cassacao", data=date(2026, 1, 1))  # fora de TIPOS_SANCAO
    itens = cruzamentos.sancoes(session, p.id)["itens"]
    # Mais nova primeiro, sem data no fim; "cassacao" não é sanção.
    assert [i["tipo"] for i in itens] == ["sancao", "tcu_contas_irregulares", "tcu_inabilitacao"]
    assert itens[0]["ligacao"] == "ligado pelo CPF"
    assert itens[1]["regra"] == "nome_casa"
    assert itens[1]["ligacao"] == "ligado por revisão manual"


def test_regra_forte_automatica_nao_e_descrita_como_revisao_manual():
    texto = cruzamentos._texto_regra("nome_exato_casa")
    assert texto != "ligado por revisão manual" and "nome" in texto
    # Toda regra forte tem texto próprio: nenhuma cai no padrão da revisão manual.
    from app.models.pessoa import REGRAS_FORTES

    assert REGRAS_FORTES <= set(cruzamentos.REGRAS)


# ---- média da Casa -------------------------------------------------------------------


def test_media_da_casa_sem_parlamentar_em_exercicio(session):
    _parlamentar(session, "camara", "1", em_exercicio=False)
    assert cruzamentos._media_da_casa(session) == {
        "parlamentares": 0,
        "viagens": {},
        "viagens_valor": {},
        "cartao": {},
    }


def test_media_da_casa_quem_nao_tem_registro_entra_com_zero(session):
    ana = _pessoa(session, "Ana Souza", "11111111111")
    rui = _pessoa(session, "Rui Lima", "22222222222")
    ex = _pessoa(session, "Eva Dias", "33333333333")
    _parlamentar(session, "camara", "1")
    _parlamentar(session, "senado", "2")
    _parlamentar(session, "camara", "3")  # em exercício, sem pessoa ligada: entra com zero
    _parlamentar(session, "camara", "4", em_exercicio=False)
    _vinculo(session, ana, "parlamentar", "camara:1", "origem")
    # Rui só está ligado ao parlamentar por nome aproximado, sem revisão: conta no divisor
    # (é parlamentar em exercício), mas as viagens dele não entram na soma.
    _vinculo(session, rui, "parlamentar", "senado:2", "nome_casa")
    _vinculo(session, ex, "parlamentar", "camara:4", "origem")

    _viagem(session, ana, 2024, 6, diarias=100, passagens=150, outros=50)
    _vinculo(session, ana, "cgu_viagens", f"2024:{ana.id}", "cpf_parcial_nome")
    _viagem(session, ana, 2023, 9, diarias=900)  # vínculo da viagem não publicável
    _vinculo(session, ana, "cgu_viagens", f"2023:{ana.id}", "nome_casa")
    _viagem(session, rui, 2024, 100, diarias=10_000)
    _vinculo(session, rui, "cgu_viagens", f"2024:{rui.id}", "cpf_parcial_nome")
    _viagem(session, ex, 2024, 50, diarias=5_000)  # fora de exercício
    _vinculo(session, ex, "cgu_viagens", f"2024:{ex.id}", "cpf_parcial_nome")

    session.add(CpgfPortadorMes(
        pessoa_id=ana.id, orgao="Órgão A", ano=2025, mes=1, transacoes=1, total=90, saques=0,
    ))  # fmt: skip
    _vinculo(session, ana, "cgu_cpgf", f"2025:{ana.id}:Órgão A", "cpf_parcial_nome")
    session.add(
        CpgfPortadorMes(
            pessoa_id=ana.id,
            orgao="Órgão B",
            ano=2025,
            mes=1,
            transacoes=1,
            total=3000,
            saques=0,
        )
    )  # fmt: skip  (sem vínculo publicável para o Órgão B)
    session.flush()

    m = cruzamentos._media_da_casa(session)
    assert m["parlamentares"] == 3
    assert m["viagens"] == {2024: 2.0}  # (6 + 0 + 0) / 3
    assert m["viagens_valor"] == {2024: 100.0}  # (300 + 0 + 0) / 3
    assert m["cartao"] == {2025: 30.0}  # (90 + 0 + 0) / 3


# ---- serviço federal -----------------------------------------------------------------


def test_servico_federal_pessoa_sem_dado(session):
    p = _pessoa(session)
    _carga(session, "cgu_viagens", datetime(2026, 4, 1, tzinfo=UTC))
    _carga(session, "outra_fonte", datetime(2026, 9, 1, tzinfo=UTC))
    r = cruzamentos.servico_federal(session, p.id)
    assert (r["regra"], r["ligacao"]) == (None, None)
    assert r["cargos"] == [] and r["viagens_por_ano"] == []
    assert r["cartao_por_ano_e_orgao"] == [] and r["media_da_casa"] is None
    assert r["atualizado_em"] == datetime(2026, 4, 1, tzinfo=UTC)


def test_servico_federal_cargos_publicaveis_e_cadastro_mais_recente(session):
    p = _pessoa(session)
    outra = _pessoa(session, "Rui Lima", "22222222222")
    for pes, ext, ultimo, origem in (
        (p, "atual", date(2024, 7, 1), "siape"),
        (p, "antigo", date(2024, 3, 1), "siape"),
        (p, "fraco", date(2024, 7, 1), "siape"),
        (p, "viagem", date(2024, 9, 1), "viagens"),
        (outra, "x", date(2024, 7, 1), "siape"),
    ):
        session.add(ServidorFederal(
            pessoa_id=pes.id, id_externo=ext, funcao=ext.capitalize(), sigla="CCX",
            origem=origem, primeiro_mes=date(2024, 1, 1), ultimo_mes=ultimo,
        ))  # fmt: skip
    _vinculo(session, p, "cgu_servidores", "atual", "cpf")
    _vinculo(session, p, "cgu_servidores", "antigo", "cpf")
    _vinculo(session, p, "cgu_servidores", "fraco", "nome_casa")  # não publicável
    _vinculo(session, p, "cgu_viagens_cne", "viagem", "cpf")
    session.flush()

    r = cruzamentos.servico_federal(session, p.id)
    cargos = {c["funcao"]: c for c in r["cargos"]}
    assert set(cargos) == {"Atual", "Antigo", "Viagem"}
    assert cargos["Atual"]["consta_no_cadastro_mais_recente"] is True
    assert cargos["Antigo"]["consta_no_cadastro_mais_recente"] is False
    # Cargo que só aparece nas viagens não é do cadastro de servidores.
    assert cargos["Viagem"]["origem"] == "viagens"
    assert cargos["Viagem"]["consta_no_cadastro_mais_recente"] is False
    assert cargos["Atual"]["origem"] == "cadastro de servidores"
    assert (r["regra"], r["ligacao"]) == ("cpf", "ligado pelo CPF")
    # Sem viagem nem cartão, não há média da Casa para mostrar.
    assert r["media_da_casa"] is None


def test_servico_federal_com_regras_diferentes_fica_com_a_mais_fraca(session):
    p = _pessoa(session)
    session.add(ServidorFederal(
        pessoa_id=p.id, id_externo="s", funcao="Assessor", sigla="CCX",
        primeiro_mes=date(2024, 1, 1), ultimo_mes=date(2024, 1, 1),
    ))  # fmt: skip
    _vinculo(session, p, "cgu_servidores", "s", "cpf")
    _viagem(session, p, 2024, 1)
    _vinculo(session, p, "cgu_viagens", f"2024:{p.id}", "cpf_parcial_nome")
    r = cruzamentos.servico_federal(session, p.id)
    assert r["regra"] == "cpf_parcial_nome"
    # Sem parlamentar em exercício, a média existe mas é zero por ano.
    assert r["viagens_por_ano"][0]["media_casa_viagens"] == 0
    assert r["media_da_casa"]["parlamentares_em_exercicio"] == 0


# ---- carreira ------------------------------------------------------------------------


def test_carreira_sem_candidatura_mantem_o_recorte(session):
    p = _pessoa(session)
    r = cruzamentos.carreira(session, p.id)
    assert r["itens"] == []
    assert r["recorte"]["anos_candidaturas"] == cruzamentos.ANOS_CANDIDATURAS
    assert r["recorte"]["texto"] == cruzamentos.RECORTE_CARREIRA


def test_carreira_so_candidatura_publicavel_e_municipio_so_quando_ha_ibge(session):
    p = _pessoa(session)
    for ano, sq, ibge, regra in ((2024, "1", "1200401", "titulo"), (2022, "2", None, "nome_casa")):
        session.add(Candidatura(
            ano_eleicao=ano, sq_candidato=sq, cargo="VEREADOR", uf="AC", unidade="Rio Branco",
            municipio_ibge=ibge, nome="Ana", nome_urna="Ana", situacao_turno="SUPLENTE",
        ))  # fmt: skip
        _vinculo(session, p, "candidatura", f"{ano}:{sq}", regra)
    session.flush()
    itens = cruzamentos.carreira(session, p.id)["itens"]
    assert len(itens) == 1  # a de 2022 tem vínculo por nome sem revisão
    i = itens[0]
    assert (i["ano"], i["cargo"], i["municipio"]) == (2024, "Vereador", "Rio Branco")
    assert i["eleito"] is False and i["bens_declarados"] is False and i["bens_total"] is None
    assert i["ligacao"] == "ligado pelo título de eleitor"


# ---- feed Atom -----------------------------------------------------------------------


def _feed(session, pessoa_id):
    corpo = cruzamentos.feed_atom(session, pessoa_id, "https://site/feed", "https://site/p")
    assert corpo.startswith(b"<?xml")
    return ET.fromstring(corpo)


def test_feed_sem_eventos_e_atom_valido_sem_entradas(session):
    p = _pessoa(session, "Ana Souza")
    raiz = _feed(session, p.id)
    assert raiz.tag == f"{{{cruzamentos.ATOM}}}feed"
    assert raiz.find("a:title", NS).text == "Panóptico: fatos oficiais sobre Ana Souza"
    assert raiz.find("a:id", NS).text == "https://site/feed"
    hoje = date.today()
    assert (
        raiz.find("a:updated", NS).text
        == datetime(hoje.year, hoje.month, hoje.day, tzinfo=UTC).isoformat()
    )
    links = {lk.get("rel"): lk.get("href") for lk in raiz.findall("a:link", NS)}
    assert links == {"self": "https://site/feed", "alternate": "https://site/p"}
    assert raiz.findall("a:entry", NS) == []


def test_feed_entrada_sem_data_nem_link_e_vinculo_fraco_fora(session):
    p = _pessoa(session)
    forte = _vinculo(session, p, "cgu_ceis", "1")
    fraco = _vinculo(session, p, "cgu_ceaf", "2", "nome_casa")
    session.add(Evento(
        pessoa_id=p.id, vinculo_id=forte.id, tipo="processo_novo", fonte="cgu_ceis",
        id_externo="sem-data", descricao="Registro sem data.", fonte_url=None,
    ))  # fmt: skip
    _evento(session, p, forte, data=date(2024, 3, 1), orgao="CGU")
    _evento(session, p, fraco, data=date(2025, 1, 1), descricao="Não publicável.")
    raiz = _feed(session, p.id)
    entradas = raiz.findall("a:entry", NS)
    assert len(entradas) == 2
    com, sem = entradas
    assert com.find("a:title", NS).text == "Sanção registrada, CGU"
    assert com.find("a:summary", NS).text == "Registro de teste. Data: 01/03/2024. Fonte: CGU."
    assert com.find("a:updated", NS).text == "2024-03-01T00:00:00+00:00"
    # Tipo sem título próprio vira texto legível; sem link da fonte, aponta para o perfil.
    assert sem.find("a:title", NS).text == "Processo novo"
    assert sem.find("a:link", NS).get("href") == "https://site/p"
    assert sem.find("a:id", NS).text.endswith("#1-processo_novo-sem-data")
    assert sem.find("a:summary", NS).text == "Registro sem data. Sem data informada."
    # O feed é atualizado na data do evento mais novo publicável (o fraco, de 2025, não conta).
    assert raiz.find("a:updated", NS).text == "2024-03-01T00:00:00+00:00"
    assert all("Não publicável" not in e.find("a:summary", NS).text for e in entradas)


def test_feed_limita_a_cinquenta_entradas_mais_novas(session):
    p = _pessoa(session)
    v = _vinculo(session, p, "cgu_ceis", "1")
    for n in range(cruzamentos.LIMITE_FEED + 5):
        session.add(Evento(
            pessoa_id=p.id, vinculo_id=v.id, tipo="sancao", fonte="cgu_ceis",
            id_externo=str(n), descricao=f"n{n}", data=date(2000 + n, 1, 1),
        ))  # fmt: skip
    session.flush()
    entradas = _feed(session, p.id).findall("a:entry", NS)
    assert len(entradas) == cruzamentos.LIMITE_FEED
    assert entradas[0].find("a:summary", NS).text.startswith("n54 ")
    assert entradas[-1].find("a:summary", NS).text.startswith("n5 ")


def test_feed_inclui_eleicao_da_candidatura_ligada(session):
    p = _pessoa(session)
    session.add(Candidatura(
        ano_eleicao=2022, sq_candidato="9", cargo="DEPUTADO FEDERAL", uf="AC", unidade="Acre",
        nome="Ana", nome_urna="Ana", partido="PT", situacao_turno="ELEITO POR QP",
    ))  # fmt: skip
    _vinculo(session, p, "candidatura", "2022:9", "titulo")
    entradas = _feed(session, p.id).findall("a:entry", NS)
    assert len(entradas) == 1
    assert entradas[0].find("a:title", NS).text == "Eleição, TSE"
    assert "2022" in entradas[0].find("a:summary", NS).text
