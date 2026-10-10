# ruff: noqa: E501  (recortes de respostas reais da API de dados abertos da CR2)
import json
from pathlib import Path

import respx
from sqlalchemy import select

from app.models import Candidatura, MandatoLocal, Municipio
from ingestion.camaras import cr2, sapl
from tests.test_api import _ingestao

REGISTROS = json.loads(
    (Path(__file__).parent / "fixtures" / "cr2_parlamentares.json").read_text(encoding="utf-8")
)
URL = "https://www.portalcr2.com.br/entidade/cm-benevides"


def test_entidade_do_endereco():
    assert cr2.entidade_de(URL) == "cm-benevides"
    assert cr2.entidade_de("https://www.benevides.pa.leg.br/") is None


def test_slug_no_inicio_ou_no_fim():
    assert cr2.eh_da_camara("cm-benevides-vitor", "cm-benevides")
    assert cr2.eh_da_camara("jose-pedro-solon-de-oliveira-cm-benevides", "cm-benevides")
    assert not cr2.eh_da_camara("cm-benevides2-fulano", "cm-benevides")


def test_partido_em_cada_formato():
    assert cr2.partido("MDB") == "MDB"
    assert cr2.partido("Movimento Democrático Brasileiro (MDB)") == "MDB"
    assert cr2.partido("PV (Partido Verde)") == "PV"
    assert cr2.partido(" Podemos (PODEMOS)") == "PODEMOS"
    assert cr2.partido("UNIÃO BRASIL") == "UNIÃO BRASIL"
    for vazio in ("*", "Sem partido", "Aguardando Informação", None, ""):
        assert cr2.partido(vazio) is None


def test_so_ativos_nao_apagados_e_sem_duplicar():
    benevides = {v["nome"]: v for v in cr2.vereadores(REGISTROS, "cm-benevides")}
    # Fabiano saiu (inativo); o primeiro "Bizinho" está apagado e o "-1" é o cadastro vigente.
    assert sorted(benevides) == ["Bizinho", "José Pedro Solon de Oliveira", "Vitor"]
    assert benevides["Vitor"]["partido"] == "UNIÃO BRASIL"
    assert benevides["Bizinho"]["partido"] == "PV"
    guama = cr2.vereadores(REGISTROS, "cm-sao-miguel-do-guama")
    assert len(guama) == 2  # o "*" apagado e quem saiu ficam de fora
    ita = cr2.vereadores(REGISTROS, "cm-itamarandiba")
    assert [v["partido"] for v in ita] == ["AVANTE", "AVANTE"]
    assert all(v["em_exercicio"] for v in ita)


@respx.mock
def test_coletar_pagina_e_grava_ligando_ao_eleito(monkeypatch, session):
    monkeypatch.setattr(cr2, "PAUSA", 0)
    rota = respx.get(cr2.API).mock(
        side_effect=[
            respx.MockResponse(json={"response": {"cursor": 0, "results": REGISTROS[:7], "count": 7, "remaining": 7}}),
            respx.MockResponse(json={"response": {"cursor": 7, "results": REGISTROS[7:], "count": 7, "remaining": 0}}),
        ]
    )  # fmt: skip
    camara = cr2.coletar(URL)
    primeira = rota.calls[0].request.url.params
    assert json.loads(primeira["constraints"])[0]["value"] == "benevides"
    assert rota.calls[1].request.url.params["cursor"] == "7"
    assert len(camara["vereadores"]) == 3
    assert camara["base"].endswith("/parlamentares/parlamentares-cm-benevides")

    session.add(Municipio(ibge="1501501", nome="Benevides", uf="PA", nome_chave="BENEVIDES"))
    session.flush()
    session.add(Candidatura(ano_eleicao=2024, sq_candidato="1", cargo="VEREADOR", uf="PA", unidade="Benevides",
                            municipio_ibge="1501501", nome="VITOR", nome_urna="VITOR",
                            situacao_turno="ELEITO POR QP", ingestao_id=_ingestao(session).id))  # fmt: skip
    session.flush()
    assert sapl.gravar(session, "1501501", camara) == 3
    mandatos = {m.nome: m for m in session.scalars(select(MandatoLocal))}
    assert mandatos["Vitor"].candidatura_id is not None
    assert sapl.gravar(session, "1501501", camara) == 3
    assert len(list(session.scalars(select(MandatoLocal)))) == 3
