import io
import zipfile
from datetime import date

from sqlalchemy import select

from app.models import Parlamentar
from app.services import presenca
from ingestion import votacoes_comum as vc
from ingestion.camara import votacoes as camara
from ingestion.senado import votacoes as senado
from tests.test_api import _ingestao, _popular


def test_classificar():
    assert presenca.classificar("Sim") == "votou"
    assert presenca.classificar("Votou") == "votou"  # votação secreta
    assert presenca.classificar("Presidente (art. 51 RISF)") == "votou"
    assert presenca.classificar("P-NRV") == "presente_sem_voto"
    assert presenca.classificar("MIS") == "justificada"
    assert presenca.classificar("NCom") == "nao_compareceu"
    assert presenca.classificar("NA") == "fora"


def test_resumir_camara_conta_ausencia_pelo_total():
    r = presenca._resumir("camara", 10, {"Sim": 6, "Não": 1, "": 1})
    assert (r["votou"], r["presente_sem_voto"], r["nao_compareceu"]) == (7, 1, 2)
    assert r["percentual"] == 70.0


def test_resumir_senado_usa_os_registros():
    r = presenca._resumir("senado", 99, {"Sim": 5, "MIS": 3, "NCom": 1, "NA": 1})
    assert r["total_votacoes"] == 9
    assert (r["votou"], r["justificada"], r["nao_compareceu"]) == (5, 3, 1)
    assert r["justificativas"] == [{"motivo": "Missão oficial", "quantidade": 3}]


def test_normalizar_camara_so_plenario_nominal():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(
            "votacoes.csv",
            '﻿"id";"data";"siglaOrgao";"descricao"\n'
            '"1-1";"2026-02-03";"PLEN";"Aprovado o projeto."\n'
            '"1-2";"2026-02-03";"PLEN";"Simbólica."\n'
            '"2-1";"2026-02-03";"CCJC";"Comissão."\n',
        )
        z.writestr(
            "votos.csv",
            '﻿"idVotacao";"deputado_id";"voto"\n"1-1";"204379";"Sim"\n"2-1";"204379";"Não"\n',
        )
    votacoes, votos = camara.normalizar(buffer.getvalue())
    assert [v["id_externo"] for v in votacoes] == ["1-1"]
    assert [v["id_externo_votacao"] for v in votos] == ["1-1"]


def test_normalizar_senado():
    payload = [
        {
            "codigoSessaoVotacao": 7104, "dataSessao": "2026-09-01", "descricaoVotacao": "PDL",
            "identificacao": "PDL 995/2026", "votacaoSecreta": "S",
            "informeLegislativo": {"siglaColegiado": "PLEN"},
            "votos": [{"codigoParlamentar": 5672, "siglaVotoParlamentar": "Votou"}],
        },
        {"codigoSessaoVotacao": 1, "dataSessao": "2026-09-01", "votos": []},
    ]  # fmt: skip
    votacoes, votos = senado.normalizar(payload)
    assert votacoes[0]["secreta"] is True
    assert votos == [{"id_externo_votacao": "7104", "codigo_senador": "5672", "voto": "Votou"}]


def test_presenca_endpoint_respeita_inicio_do_exercicio(client, session):
    _popular(session)
    deps = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).all()
    deps[1].em_exercicio_desde = date(2026, 6, 1)  # assumiu no meio do ano
    votacoes = [
        {"id_externo": str(i), "data": date(2026, m, 1), "descricao": "x", "proposicao": None,
         "secreta": False}
        for i, m in enumerate([2, 3, 7, 8])
    ]  # fmt: skip
    votos = [
        {"id_externo_votacao": "0", "parlamentar_id": deps[0].id, "voto": "Sim"},
        {"id_externo_votacao": "1", "parlamentar_id": deps[0].id, "voto": "Não"},
        {"id_externo_votacao": "2", "parlamentar_id": deps[0].id, "voto": "Sim"},
        {
            "id_externo_votacao": "1",
            "parlamentar_id": deps[1].id,
            "voto": "Sim",
        },  # antes de assumir
        {"id_externo_votacao": "2", "parlamentar_id": deps[1].id, "voto": "Sim"},
    ]
    vc.recarregar_votacoes(session, "camara", 2026, votacoes, votos, _ingestao(session))
    session.flush()

    a = client.get(f"/parlamentares/{deps[0].id}/presenca").json()
    assert (a["total_votacoes"], a["votou"], a["percentual"]) == (4, 3, 75.0)
    b = client.get(f"/parlamentares/{deps[1].id}/presenca").json()
    assert b["periodo_inicio"] == "2026-06-01"
    assert (b["total_votacoes"], b["votou"], b["percentual"]) == (2, 1, 50.0)
    # média dos 3 deputados em exercício: (75 + 50 + 0) / 3
    assert a["media_casa_percentual"] == 41.7
    assert client.get(f"/parlamentares/{deps[0].id}/presenca?ano=1999").status_code == 404
