# ruff: noqa: E501  (recorte da página de vereadores da Câmara de Queimada Nova, no PI)
import json
from pathlib import Path

import respx
from sqlalchemy import select

from app.models import Candidatura, MandatoLocal, Municipio
from ingestion.camaras import aos, sapl
from tests.test_api import _ingestao

CARTOES = json.loads(
    (Path(__file__).parent / "fixtures" / "aos_vereadores.json").read_text(encoding="utf-8")
)["cartoes"]
BASE = "https://queimadanova.pi.leg.br/vereadores"


def test_cartoes_com_apelido_nome_civil_e_partido():
    vereadores = aos.vereadores(CARTOES, BASE)
    por_id = {v["id_externo"]: v for v in vereadores}
    carlos = por_id[sapl.id_curto("carlos-alberto-nunes-amorim")]
    assert (carlos["nome"], carlos["nome_completo"], carlos["partido"]) == (
        "Carlos Amorim",
        "Carlos Alberto Nunes Amorim",
        "PT",
    )
    assert (
        por_id[sapl.id_curto("josimar-rodrigues-teixeira")]["nome_completo"]
        == "Josimar Rodrigues Teixeira"
    )
    assert all(v["em_exercicio"] and v["titular"] for v in vereadores)


def test_cartao_repetido_conta_uma_vez():
    assert len(aos.vereadores(CARTOES + CARTOES, BASE)) == len(aos.vereadores(CARTOES, BASE))


@respx.mock
def test_coletar_e_gravar_liga_ao_eleito(session):
    pagina = respx.get(BASE).respond(text=CARTOES)
    camara = aos.coletar("https://queimadanova.pi.leg.br/")
    assert pagina.calls[0].request.headers["User-Agent"].startswith("Panoptico")
    session.add(
        Municipio(ibge="2208650", nome="Queimada Nova", uf="PI", nome_chave="QUEIMADA NOVA")
    )
    session.flush()
    session.add(Candidatura(ano_eleicao=2024, sq_candidato="1", cargo="VEREADOR", uf="PI", unidade="Queimada Nova",
                            municipio_ibge="2208650", nome="CARLOS ALBERTO NUNES AMORIM", nome_urna="CARLOS AMORIM",
                            situacao_turno="ELEITO POR QP", ingestao_id=_ingestao(session).id))  # fmt: skip
    session.flush()
    total = len(camara["vereadores"])
    assert sapl.gravar(session, "2208650", camara) == total
    mandatos = {m.nome: m for m in session.scalars(select(MandatoLocal))}
    assert mandatos["Carlos Amorim"].candidatura_id is not None
    assert mandatos["Carlos Amorim"].partido == "PT"
