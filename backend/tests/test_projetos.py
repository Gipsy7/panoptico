from datetime import date

from sqlalchemy import select

from app.models import Parlamentar
from ingestion import proposicoes_comum as pc
from ingestion.camara import proposicoes as camara
from ingestion.senado import proposicoes as senado
from tests.test_api import _ingestao, _popular

CAB_PROP = (
    '"id";"siglaTipo";"numero";"ano";"ementa";"dataApresentacao";"ultimoStatus_descricaoSituacao"'
)
CAB_AUT = '"idProposicao";"idDeputadoAutor";"codTipoAutor";"ordemAssinatura"'


def _csv(cabecalho: str, *linhas: str) -> bytes:
    return ("﻿" + "\n".join([cabecalho, *linhas])).encode("utf-8")


def test_virou_lei():
    assert pc.virou_lei("Transformado em Norma Jurídica")
    assert pc.virou_lei("Transformada em norma jurídica com veto parcial")
    assert not pc.virou_lei("Transformado em nova proposição")
    assert not pc.virou_lei(None)


def test_normalizar_proposicoes_camara_filtra_tipo_e_data():
    conteudo = _csv(
        CAB_PROP,
        '"1";"PL";"10";"2023";"Cria  algo.";"2023-03-01T10:00:00";"Transformado em Norma Jurídica"',
        '"2";"REQ";"11";"2023";"Requer.";"2023-03-01T10:00:00";""',
        '"3";"PL";"12";"2023";"Antigo.";"2007-03-01T10:00:00";""',
    )
    registros = camara.normalizar_proposicoes(conteudo)
    assert [r["id_externo"] for r in registros] == ["1"]
    assert registros[0]["ementa"] == "Cria algo."
    assert registros[0]["virou_lei"] is True
    assert registros[0]["data_apresentacao"] == date(2023, 3, 1)


def test_normalizar_autores_camara_so_deputados():
    conteudo = _csv(
        CAB_AUT, '"1";"204379";"10000";"1"', '"1";"";"40000";"1"', '"1";"220714";"10000";"2"'
    )
    autores = camara.normalizar_autores(conteudo)
    assert [(a["id_deputado"], a["primeiro_autor"]) for a in autores] == [
        ("204379", True),
        ("220714", False),
    ]


def test_primeiro_autor_senado():
    autoria = "Senadora Mara Gabrilli (PSD/SP), Senador Romário (PL/RJ)"
    assert senado.primeiro_autor(autoria) == "Mara Gabrilli"
    assert senado.primeiro_autor("Senador Dr. Hiran (PP/RR)") == "Dr. Hiran"
    assert senado.primeiro_autor(None) == ""


def test_normalizar_senado_dedup_e_primeiro_autor():
    processo = {
        "identificacao": "PL 2036/2023", "casaIdentificadora": "SF", "codigoMateria": 157013,
        "dataApresentacao": "2023-04-19", "ementa": "Estabelece normas.",
        "situacaoAtual": "AGUARDANDO DESIGNAÇÃO DO RELATOR",
        "autoria": "Senador Alan Rick (UNIÃO/AC), Senador Romário (PL/RJ)",
    }  # fmt: skip
    requerimento = {**processo, "identificacao": "RQS 1/2023", "codigoMateria": 1}
    payload = {"5672": [processo, requerimento], "22": [processo]}
    registros, autorias = senado.normalizar(payload, {"5672": "Alan Rick", "22": "Romário"})
    assert [r["id_externo"] for r in registros] == ["157013"]
    assert registros[0]["situacao"] == "Aguardando designação do relator"
    assert {a["codigo_senador"]: a["primeiro_autor"] for a in autorias} == {
        "5672": True,
        "22": False,
    }


def test_projetos_endpoint(client, session):
    _popular(session)
    deps = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).all()
    ingestao = _ingestao(session)
    base = {"ementa": "E.", "situacao": None, "virou_lei": False, "url": "u", "ano": 2024}
    mapa = pc.upsert_proposicoes(
        session,
        "camara",
        [
            {**base, "id_externo": "a", "sigla_tipo": "PL", "numero": 1,
             "data_apresentacao": date(2024, 1, 1)},
            {**base, "id_externo": "b", "sigla_tipo": "PEC", "numero": 2,
             "data_apresentacao": date(2024, 2, 1), "virou_lei": True,
             "situacao": "Transformada em norma jurídica"},
            {**base, "id_externo": "c", "sigla_tipo": "PL", "numero": 3,
             "data_apresentacao": date(2024, 3, 1)},
        ],
        ingestao,
    )  # fmt: skip
    pc.substituir_autorias(
        session,
        list(mapa.values()),
        [
            {"proposicao_id": mapa["a"], "parlamentar_id": deps[0].id, "primeiro_autor": True},
            {"proposicao_id": mapa["b"], "parlamentar_id": deps[0].id, "primeiro_autor": True},
            {"proposicao_id": mapa["c"], "parlamentar_id": deps[0].id, "primeiro_autor": False},
            {"proposicao_id": mapa["c"], "parlamentar_id": deps[1].id, "primeiro_autor": True},
        ],
    )
    session.flush()

    corpo = client.get(f"/parlamentares/{deps[0].id}/projetos").json()
    assert (corpo["primeiro_autor"], corpo["coautor"], corpo["viraram_norma"]) == (2, 1, 1)
    # 3 deputados: 2 + 1 + 0 projetos como primeiro autor
    assert corpo["media_casa_primeiro_autor"] == 1.0
    assert [t["sigla"] for t in corpo["por_tipo"]] == ["PL", "PEC"]
    assert [r["numero"] for r in corpo["recentes"]] == [2, 1]
    assert [r["numero"] for r in corpo["viraram_norma_lista"]] == [2]
