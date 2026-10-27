"""Pauta do Plenário e tramitação das proposições (Câmara e Senado), com respostas reais
recortadas em tests/fixtures/pauta e tests/fixtures/tramitacao."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest
import respx
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.models import (
    FonteIngestao,
    Parlamentar,
    PautaItem,
    Proposicao,
    Tramitacao,
    Votacao,
)
from ingestion import comum
from ingestion import pauta_comum as pc
from ingestion.camara import pauta as pauta_camara
from ingestion.camara import tramitacoes as tram_camara
from ingestion.senado import pauta as pauta_senado
from ingestion.senado import tramitacoes as tram_senado

FIXTURES = Path(__file__).parent / "fixtures"
C = "https://dadosabertos.camara.leg.br/api/v2"
S = "https://legis.senado.leg.br/dadosabertos"


def fx(pasta: str, nome: str):
    return json.loads((FIXTURES / pasta / nome).read_text(encoding="utf-8"))


@pytest.fixture
def ambiente(session, tmp_path, monkeypatch):
    """As cargas usam a conexão do teste (commit vira savepoint) e o bruto vai para tmp."""
    fabrica = sessionmaker(bind=session.get_bind(), join_transaction_mode="create_savepoint")
    monkeypatch.setattr(comum, "SessionLocal", fabrica)
    monkeypatch.setattr(comum, "RAW_DIR", tmp_path)
    monkeypatch.setattr(comum, "forcar", False)
    monkeypatch.setattr(comum.time, "sleep", lambda _: None)
    return session


def _ingestao(session):
    ingestao = FonteIngestao(fonte="teste", url="https://exemplo", arquivo_raw="x.json")
    session.add(ingestao)
    session.flush()
    return ingestao


# --- pauta da Câmara ----------------------------------------------------------------------


def _payload_camara(hoje: str) -> dict:
    eventos = fx("pauta", "camara_eventos_2026-09-01_a_04.json")
    pauta = fx("pauta", "camara_pauta_evento_82965.json")
    return {
        "hoje": hoje,
        "sessoes": [
            {
                "id": e["id"],
                "dataHoraInicio": e["dataHoraInicio"],
                "descricaoTipo": e["descricaoTipo"],
                "situacao": e["situacao"],
                "pauta": pauta if e["id"] == 82965 else [],
            }
            for e in eventos
        ],
    }


def test_pauta_camara_deduplica_por_materia_e_usa_a_relacionada_na_mpv():
    itens = pauta_camara.normalizar(_payload_camara("2026-09-03"))
    # 17 linhas da API (uma por votação) viram 6 matérias.
    assert [(i["ordem"], i["proposicao"]) for i in itens] == [
        (1, "MPV 1357/2026"),
        (2, "MPV 1360/2026"),
        (3, "MPV 1369/2026"),
        (4, "PL 1893/2026"),
        (5, "PLP 73/2025"),
        (6, "PLP 74/2026"),
    ]
    por_rotulo = {i["proposicao"]: i for i in itens}
    # MPV e PLP 74: o id é o da matéria (relacionada), não o do parecer (PAR/PEP, ano 0).
    assert por_rotulo["MPV 1357/2026"]["proposicao_id_externo"] == "2624161"
    assert por_rotulo["PLP 74/2026"]["proposicao_id_externo"] == "2611313"
    assert por_rotulo["PLP 74/2026"]["ementa"].startswith("Dispõe sobre regras")
    assert "PARECER" not in por_rotulo["MPV 1357/2026"]["ementa"]
    # MPV sem parecer: a própria proposição.
    assert por_rotulo["MPV 1360/2026"]["proposicao_id_externo"] == "2625946"
    assert all(i["sessao"] == "82965" and i["data"] == date(2026, 9, 3) for i in itens)
    assert por_rotulo["PL 1893/2026"]["url"].endswith("idProposicao=2617268")


def test_pauta_camara_respeita_a_janela():
    # Hoje = 4/9: a sessão de 3/9 já passou.
    assert pauta_camara.normalizar(_payload_camara("2026-09-04")) == []
    # Hoje = 1/9 com janela de 14 dias: entra.
    assert len(pauta_camara.normalizar(_payload_camara("2026-09-01"))) == 6


def test_pauta_camara_cancelada_nao_entra():
    payload = _payload_camara("2026-09-03")
    payload["sessoes"][-1]["situacao"] = "Cancelada"
    assert pauta_camara.normalizar(payload) == []


def test_pauta_recarrega_a_janela_inteira(session):
    payload = _payload_camara("2026-09-03")
    pauta_camara.carregar(session, payload, _ingestao(session))
    pauta_camara.carregar(session, payload, _ingestao(session))  # idempotente
    assert session.scalar(select(func.count()).select_from(PautaItem)) == 6
    # O Senado não é tocado pela recarga da Câmara.
    pauta_senado.carregar(session, _payload_senado("2026-10-06"), _ingestao(session))
    antes = session.scalar(
        select(func.count()).select_from(PautaItem).where(PautaItem.casa == "senado")
    )
    payload["sessoes"][-1]["pauta"] = payload["sessoes"][-1]["pauta"][:1]
    pauta_camara.carregar(session, payload, _ingestao(session))
    assert (
        session.scalar(
            select(func.count()).select_from(PautaItem).where(PautaItem.casa == "camara")
        )
        == 1
    )
    assert (
        session.scalar(
            select(func.count()).select_from(PautaItem).where(PautaItem.casa == "senado")
        )
        == antes
    )


def test_pauta_camara_janela_vazia_nao_aborta(session):
    payload = _payload_camara("2026-09-04")
    assert pauta_camara.carregar(session, payload, _ingestao(session)) == 0


def test_pauta_camara_de_ponta_a_ponta_e_de_raw(ambiente, tmp_path):
    eventos = fx("pauta", "camara_eventos_2026-09-01_a_04.json")
    with respx.mock(assert_all_called=True) as rota:
        rota.get(f"{C}/eventos").mock(return_value=httpx.Response(200, json={"dados": eventos}))
        for e in eventos:
            pauta = fx("pauta", "camara_pauta_evento_82965.json") if e["id"] == 82965 else []
            rota.get(f"{C}/eventos/{e['id']}/pauta").mock(
                return_value=httpx.Response(200, json={"dados": pauta})
            )
        assert pauta_camara.executar(hoje=date(2026, 9, 3)) == 6
    brutos = list((tmp_path / "camara_pauta").glob("*.json"))
    assert len(brutos) == 1
    ambiente.execute(PautaItem.__table__.delete())
    # Sem rede: qualquer chamada falharia (nenhuma rota registrada).
    with respx.mock(assert_all_called=False):
        assert pauta_camara.executar(de_raw=brutos[0]) == 6
    ok = ambiente.scalars(select(FonteIngestao).where(FonteIngestao.fonte == "camara_pauta")).all()
    assert [i.status for i in ok] == ["ok", "ok"]


# --- pauta do Senado ----------------------------------------------------------------------


def _payload_senado(hoje: str) -> dict:
    return {
        "hoje": hoje,
        "meses": [{"consulta": hoje, "agenda": fx("pauta", "senado_agenda_mes_202610.json")}],
    }


def test_pauta_senado_materias_por_sessao():
    itens = pauta_senado.normalizar(_payload_senado("2026-10-06"))
    por_sessao: dict[str, list] = {}
    for i in itens:
        por_sessao.setdefault(i["sessao"], []).append(i)
    # Sessões sem pauta, canceladas e "não realizadas" não geram item; a de 21/10 fica fora
    # da janela (6/10 a 20/10).
    assert sorted(por_sessao) == ["590398", "591267", "591273"]
    assert [len(por_sessao[s]) for s in ("590398", "591267", "591273")] == [7, 2, 10]
    primeiro = por_sessao["590398"][0]
    assert primeiro["proposicao"] == "REQ 341/2026 - CDIR"
    assert primeiro["proposicao_id_externo"] == "175914"  # o CodigoMateria das votações
    assert primeiro["data"] == date(2026, 10, 6) and primeiro["ordem"] == 1
    assert primeiro["url"].endswith("/materia/175914")
    pec = next(i for i in por_sessao["591267"] if i["proposicao"] == "PEC 221/2019")
    assert pec["ementa"].startswith("Altera o art. 7º da Constituição Federal")


def test_pauta_senado_janela_e_virada_de_mes():
    itens = pauta_senado.normalizar(_payload_senado("2026-10-14"))
    assert {i["sessao"] for i in itens} == {"591267", "591273"}
    assert pauta_senado._datas_de_consulta(date(2026, 10, 25)) == [
        date(2026, 10, 25),
        date(2026, 11, 1),
    ]
    assert pauta_senado._datas_de_consulta(date(2026, 10, 6)) == [date(2026, 10, 6)]


def test_pauta_senado_uma_materia_vem_como_objeto():
    payload = _payload_senado("2026-10-07")
    sessao = next(
        s
        for s in payload["meses"][0]["agenda"]["AgendaPlenario"]["Sessoes"]["Sessao"]
        if s["CodigoSessao"] == "591267"
    )
    sessao["Materias"]["Materia"] = sessao["Materias"]["Materia"][0]  # lista -> objeto
    itens = pauta_senado.normalizar(payload)
    assert [i["sessao"] for i in itens].count("591267") == 1


# --- recorte -------------------------------------------------------------------------------


def _proposicao(id_externo: str, casa="camara", ano=2025) -> Proposicao:
    return Proposicao(
        casa=casa,
        id_externo=id_externo,
        sigla_tipo="PL",
        numero=1,
        ano=ano,
        ementa="x",
        data_apresentacao=date(ano, 3, 1),
        url="https://exemplo",
    )


def _votacao(id_externo: str, data: date, proposicao: str | None, casa="camara") -> Votacao:
    return Votacao(
        casa=casa,
        id_externo=id_externo,
        data=data,
        descricao="x",
        proposicao_id_externo=proposicao,
    )


def test_recorte_votadas_pauta_e_todas(session):
    session.add_all(
        [
            _votacao("v1", date(2026, 9, 3), "100"),
            _votacao("v2", date(2025, 5, 1), "101"),
            _votacao("v3", date(2024, 12, 31), "102"),  # antes do ano anterior
            _votacao("v4", date(2026, 9, 3), None),  # sem proposição
            _votacao("v5", date(2026, 9, 3), "103", casa="senado"),
            PautaItem(
                casa="camara", data=date(2026, 10, 22), sessao="1", proposicao_id_externo="104"
            ),
            _proposicao("105"),
            _proposicao("106", casa="senado"),
        ]
    )
    session.flush()
    hoje = date(2026, 10, 21)
    assert pc.ids_do_recorte(session, "camara", hoje) == ["100", "101", "104"]
    assert pc.ids_do_recorte(session, "camara", hoje, todas=True) == ["100", "101", "104", "105"]
    assert pc.ids_do_recorte(session, "senado", hoje) == ["103"]


# --- tramitação da Câmara ------------------------------------------------------------------


def _registro_camara() -> dict:
    return {
        "ficha": fx("tramitacao", "camara_ficha_2611313.json"),
        "relator": {"id": "204436", "nome": "Isnaldo Bulhões Jr."},
        "tramitacoes": fx("tramitacao", "camara_tramitacoes_2611313.json"),
    }


def test_tramitacao_camara_normaliza_na_ordem_e_com_o_texto_oficial():
    linhas = tram_camara.normalizar(_registro_camara())
    assert len(linhas) == 34
    assert [linha["ordem"] for linha in linhas] == list(range(1, 35))
    assert [linha["data"] for linha in linhas] == sorted(linha["data"] for linha in linhas)
    primeira, ultima = linhas[0], linhas[-1]
    assert primeira["data"] == datetime(2026, 3, 23, 17, 21)
    assert primeira["tipo"] == "Apresentação de Proposição"
    assert primeira["descricao"].startswith("Apresentação do PLP n. 74/2026")
    assert primeira["orgao"] == "MESA"
    # O despacho é o texto; o espaço duplo do original ("Ofício nº  1305/2026") some.
    assert ultima["descricao"] == (
        "Recebimento do Ofício nº 1305/2026 (SF) comunicando remessa à sanção do PLP 74/2026."
    )
    assert ultima["situacao"] == "Transformado em Norma Jurídica"
    # A marca é a do último status da ficha (que pode ser mais novo que a última linha).
    assert {linha["fonte_marca"] for linha in linhas} == {"2026-09-04T00:00#50"}


def test_tramitacao_camara_sem_despacho_usa_a_descricao_do_ato():
    registro = _registro_camara()
    registro["tramitacoes"] = [{**registro["tramitacoes"][0], "despacho": None}]
    (linha,) = tram_camara.normalizar(registro)
    assert linha["descricao"] == "Apresentação de Proposição"


def _rotas_camara(rota, *, ficha=None, tramitacoes=None):
    ficha = ficha or fx("tramitacao", "camara_ficha_2611313.json")
    rota.get(f"{C}/proposicoes/2611313").mock(
        return_value=httpx.Response(200, json={"dados": ficha})
    )
    tram = rota.get(f"{C}/proposicoes/2611313/tramitacoes").mock(
        return_value=httpx.Response(
            200, json={"dados": tramitacoes or fx("tramitacao", "camara_tramitacoes_2611313.json")}
        )
    )
    rota.get(f"{C}/deputados/204436").mock(
        return_value=httpx.Response(
            200, json={"dados": fx("tramitacao", "camara_deputado_204436.json")}
        )
    )
    return tram


def _preparar_camara(session):
    relator = Parlamentar(
        casa="camara",
        id_externo="204436",
        nome_parlamentar="Isnaldo Bulhões Jr.",
        uf="AL",
        fonte_url="https://exemplo",
        atualizado_em=datetime.now(UTC),
    )
    session.add_all(
        [
            relator,
            _proposicao("2611313", ano=2026),
            _votacao("2611313-34", date(2026, 9, 3), "2611313"),
        ]
    )
    session.flush()
    return relator


HOJE = date(2026, 10, 21)


def test_tramitacao_camara_incremental_so_rebusca_quando_a_marca_muda(ambiente):
    relator = _preparar_camara(ambiente)
    with respx.mock as rota:
        tram = _rotas_camara(rota)
        assert tram_camara.executar(hoje=HOJE) == 34
        assert tram.call_count == 1
    ambiente.expire_all()
    proposicao = ambiente.scalars(
        select(Proposicao).where(Proposicao.id_externo == "2611313")
    ).one()
    assert proposicao.relator == "Isnaldo Bulhões Jr."
    assert proposicao.relator_parlamentar_id == relator.id

    # Mesma marca: a ficha é consultada (é a sonda), a tramitação não.
    with respx.mock as rota:
        tram = _rotas_camara(rota)
        assert tram_camara.executar(hoje=HOJE) == 0
        assert tram.call_count == 0

    # Marca nova (outro status): apaga e reinsere as linhas da proposição.
    ficha = fx("tramitacao", "camara_ficha_2611313.json")
    ficha["statusProposicao"]["sequencia"] = 51
    menos = fx("tramitacao", "camara_tramitacoes_2611313.json")[:-1]
    with respx.mock as rota:
        tram = _rotas_camara(rota, ficha=ficha, tramitacoes=menos)
        assert tram_camara.executar(hoje=HOJE) == 33
        assert tram.call_count == 1
    ambiente.expire_all()
    assert ambiente.scalar(select(func.count()).select_from(Tramitacao)) == 33
    assert ambiente.scalar(select(func.max(Tramitacao.ordem))) == 33


def test_tramitacao_camara_de_raw_reprocessa_sem_rede(ambiente, tmp_path):
    _preparar_camara(ambiente)
    with respx.mock as rota:
        _rotas_camara(rota)
        tram_camara.executar(hoje=HOJE)
    bruto = next((tmp_path / "camara_tramitacoes").glob("*.json"))
    ambiente.execute(Tramitacao.__table__.delete())
    ambiente.execute(Proposicao.__table__.update().values(relator=None))
    with respx.mock(assert_all_called=False):
        assert tram_camara.executar(de_raw=bruto) == 34
    ambiente.expire_all()
    assert ambiente.scalar(select(Proposicao.relator).where(Proposicao.id_externo == "2611313"))


def test_tramitacao_camara_proposicao_sem_ficha_vira_alerta(ambiente):
    ambiente.add(_votacao("v1", date(2026, 9, 3), "999"))
    ambiente.flush()
    with respx.mock as rota:
        rota.get(f"{C}/proposicoes/999").mock(return_value=httpx.Response(404))
        assert tram_camara.executar(hoje=HOJE) == 0
    ingestao = ambiente.scalars(
        select(FonteIngestao).where(FonteIngestao.fonte == "camara_tramitacoes")
    ).one()
    assert ingestao.status == "ok" and ingestao.alertas and "sem ficha" in ingestao.alertas[0]


# --- tramitação do Senado ------------------------------------------------------------------


def _registro_senado() -> dict:
    return {
        "marca": "2026-08-26T16:50:01.119",
        "processo": fx("tramitacao", "senado_processo_8828166.json"),
        "relatoria": fx("tramitacao", "senado_relatoria_8828166.json"),
    }


def test_tramitacao_senado_normaliza_informes_com_a_situacao_do_dia():
    linhas = tram_senado.normalizar(_registro_senado())
    assert len(linhas) == 24
    assert [linha["ordem"] for linha in linhas] == list(range(1, 25))
    assert [linha["data"] for linha in linhas] == sorted(linha["data"] for linha in linhas)
    primeira = linhas[0]
    assert primeira["data"] == datetime(2025, 5, 8, 17, 40, 3)
    assert primeira["orgao"] == "PLEN"
    assert primeira["descricao"].startswith(
        "Autuada a Proposta de Emenda à Constituição nº 22/2025"
    )
    assert primeira["situacao"] == "AGUARDANDO DESPACHO"
    assert all(
        linha["descricao"] and linha["fonte_marca"] == "2026-08-26T16:50:01.119" for linha in linhas
    )


def test_relator_do_senado_e_a_designacao_mais_recente():
    nome, codigo = tram_senado.ultimo_relator(fx("tramitacao", "senado_relatoria_8828166.json"))
    assert (nome, codigo) == ("Esperidião Amin", "22")
    assert tram_senado.ultimo_relator([]) is None


def _rotas_senado(rota, *, atualizacao=None, sem_data=False):
    lista = fx("tramitacao", "senado_lista_168484.json")
    if atualizacao:
        lista[0]["dataUltimaAtualizacao"] = atualizacao
    if sem_data:  # a lista de alguns processos (ex.: PEC 81/2015) não traz a data
        del lista[0]["dataUltimaAtualizacao"]
    rota.get(f"{S}/processo", params={"codigoMateria": "168484"}).mock(
        return_value=httpx.Response(200, json=lista)
    )
    processo = rota.get(f"{S}/processo/8828166").mock(
        return_value=httpx.Response(200, json=fx("tramitacao", "senado_processo_8828166.json"))
    )
    rota.get(f"{S}/processo/relatoria", params={"idProcesso": "8828166"}).mock(
        return_value=httpx.Response(200, json=fx("tramitacao", "senado_relatoria_8828166.json"))
    )
    return processo


def _preparar_senado(session):
    senador = Parlamentar(
        casa="senado",
        id_externo="22",
        nome_parlamentar="Esperidião Amin",
        uf="SC",
        fonte_url="https://exemplo",
        atualizado_em=datetime.now(UTC),
    )
    session.add_all(
        [
            senador,
            _proposicao("168484", casa="senado", ano=2025),
            _votacao("sv1", date(2026, 2, 24), "168484", casa="senado"),
        ]
    )
    session.flush()
    return senador


def test_tramitacao_senado_liga_codigo_da_materia_ao_processo_e_e_incremental(ambiente):
    senador = _preparar_senado(ambiente)
    with respx.mock as rota:
        processo = _rotas_senado(rota)
        assert tram_senado.executar(hoje=HOJE) == 24
        assert processo.call_count == 1
    ambiente.expire_all()
    # A linha fica sob o codigoMateria (o mesmo id das votações), não sob o idProcesso.
    assert (
        ambiente.scalar(
            select(func.count())
            .select_from(Tramitacao)
            .where(Tramitacao.casa == "senado", Tramitacao.proposicao_id_externo == "168484")
        )
        == 24
    )
    proposicao = ambiente.scalars(select(Proposicao).where(Proposicao.id_externo == "168484")).one()
    assert proposicao.relator == "Esperidião Amin"
    assert proposicao.relator_parlamentar_id == senador.id

    with respx.mock as rota:  # dataUltimaAtualizacao igual: não baixa o processo
        processo = _rotas_senado(rota)
        assert tram_senado.executar(hoje=HOJE) == 0
        assert processo.call_count == 0

    with respx.mock as rota:  # atualizada: apaga e reinsere
        processo = _rotas_senado(rota, atualizacao="2026-09-30T10:00:00.000")
        assert tram_senado.executar(hoje=HOJE) == 24
        assert processo.call_count == 1
    ambiente.expire_all()
    assert ambiente.scalar(select(func.count()).select_from(Tramitacao)) == 24


def test_tramitacao_senado_sem_data_de_atualizacao_sempre_rebusca(ambiente):
    _preparar_senado(ambiente)
    for _ in range(2):  # None == None não pode contar como "sem mudança"
        with respx.mock as rota:
            processo = _rotas_senado(rota, sem_data=True)
            assert tram_senado.executar(hoje=HOJE) == 24
            assert processo.call_count == 1
    ambiente.expire_all()
    assert ambiente.scalar(select(func.count()).select_from(Tramitacao)) == 24
