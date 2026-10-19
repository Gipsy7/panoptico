"""Explicador de votação: orientação de partidos/blocos na ingestão e a rota /votacoes."""

import io
import json
import zipfile
from datetime import date

from sqlalchemy import select

from app.models import Orientacao, Parlamentar
from ingestion import votacoes_comum as vc
from ingestion.camara import votacoes as camara
from ingestion.senado import votacoes as senado
from tests.test_api import _ingestao, _popular

# Recorte real de /api/v2/blocos?idLegislatura=57 (com /blocos/{id}/partidos), out/2026.
BLOCOS = [
    {"id": "590", "nome": "AVANTE, SOLIDARIEDADE, PRD", "federacao": False, "partidos": []},
    {"id": "584", "nome": "Federação Brasil da Esperança - Fe Brasil", "federacao": True,
     "partidos": ["PT", "PCdoB", "PV"]},
    {"id": "585", "nome": "Federação PSDB CIDADANIA", "federacao": True,
     "partidos": ["PSDB", "CIDADANIA"]},
    {"id": "589", "nome": "UNIÃO, PP, PSD, REPUBLICANOS, MDB, Federação PSDB CIDADANIA, PODE",
     "federacao": False,
     "partidos": ["PSDB", "CIDADANIA", "UNIÃO", "PP", "REPUBLICANOS", "PSD", "MDB", "PODE"]},
]  # fmt: skip


def test_decompor_blocos_e_federacoes_truncados():
    assert camara.decompor("Fdr PT-PCdoB-PV", BLOCOS) == ["PT", "PCdoB", "PV"]
    # O CSV corta o nome: "CIDADAN".
    assert camara.decompor("Fdr PSDB-CIDADAN", BLOCOS) == ["PSDB", "CIDADANIA"]
    assert camara.decompor("Bl UniPpPsd...", BLOCOS)[2:5] == ["UNIÃO", "PP", "REPUBLICANOS"]
    # Bloco desfeito vem com a lista vazia: vale o nome oficial.
    assert camara.decompor("Bl AvanSolidPrd...", BLOCOS) == ["AVANTE", "SOLIDARIEDADE", "PRD"]
    # Bloco de 2025 com o PL que não está na lista atual: fica só com o nome.
    assert camara.decompor("Bl PlUniPpPsd...", BLOCOS) is None
    assert camara.decompor("Bl UniPpPsd...", []) is None
    assert camara.decompor("PL", BLOCOS) is None


def _csv(*linhas: str) -> str:
    return "﻿" + "\n".join(linhas)


def _zip_camara(blocos: list | None = BLOCOS) -> bytes:
    uri = "https://dadosabertos.camara.leg.br/api/v2/partidos/"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(
            "votacoes.csv",
            _csv(
                '"id";"data";"siglaOrgao";"descricao";"aprovacao";"votosSim";"votosNao"',
                '"1-1";"2026-09-03";"PLEN";"Aprovada a subemenda.";"1";"3";"1"',
                '"2-1";"2026-09-02";"PLEN";"Aprovado o PDL. Sim: 2";"1";"2";"0"',
            ),
        )
        z.writestr(
            "votos.csv",
            _csv(
                '"idVotacao";"deputado_id";"voto";"deputado_siglaPartido";"deputado_uriPartido"',
                f'"1-1";"1";"Sim";"PT";"{uri}36844"',
                f'"1-1";"2";"Não";"SOLIDARIEDADE";"{uri}37904"',
                f'"1-1";"3";"Sim";"PP";"{uri}5"',
                # Votação secreta: o arquivo lista quem votou, com o voto em branco.
                f'"2-1";"1";"";"PT";"{uri}36844"',
                f'"2-1";"3";"";"PP";"{uri}5"',
            ),
        )
        z.writestr(
            "orientacoes.csv",
            _csv(
                '"idVotacao";"siglaBancada";"uriBancada";"orientacao"',
                '"1-1";"Governo";"";"Sim"',
                '"1-1";"Maioria";"";""',
                f'"1-1";"Solidaried";"{uri}37904";"Não"',  # sigla cortada; id resolve
                '"1-1";"Fdr PT-PCdoB-PV";"";"Sim"',
                '"1-1";"Bl UniPpPsd...";"";"Sim"',
                f'"1-1";"PDT";"{uri}36786";""',  # não orientou: fica de fora
            ),
        )
        if blocos is not None:
            z.writestr("blocos.json", json.dumps(blocos, ensure_ascii=False))
    return buffer.getvalue()


def test_normalizar_camara_partidos_blocos_resultado_e_secreta():
    votacoes, _, orientacoes = camara.normalizar(_zip_camara())
    por_id = {v["id_externo"]: v for v in votacoes}
    assert por_id["1-1"]["resultado"] == "aprovada"
    assert (por_id["1-1"]["placar_sim"], por_id["1-1"]["placar_nao"]) == (3, 1)
    assert por_id["1-1"]["secreta"] is False
    assert por_id["2-1"]["secreta"] is True
    o = {x["bancada"]: x for x in orientacoes}
    assert set(o) == {"Governo", "Maioria", "SOLIDARIEDADE", "Fdr PT-PCdoB-PV", "Bl UniPpPsd..."}
    assert o["Maioria"]["orientacao"] == ""  # liderança em branco continua como antes
    assert (o["SOLIDARIEDADE"]["tipo"], o["SOLIDARIEDADE"]["orientacao"]) == ("partido", "Não")
    assert o["Fdr PT-PCdoB-PV"]["partidos"] == "PT,PCdoB,PV"
    assert o["Bl UniPpPsd..."]["tipo"] == "bloco"
    assert "PP" in o["Bl UniPpPsd..."]["partidos"].split(",")


def test_normalizar_senado_partido_pelo_nome_de_uso():
    payload = {
        "votacoes": [
            {
                "codigoSessaoVotacao": 7047, "sequencialVotacao": 4360,
                "dataSessao": "2026-02-24", "votacaoSecreta": "N", "resultadoVotacao": "A",
                "totalVotosSim": None, "identificacao": "PEC 22/2025",
                "informeLegislativo": {"siglaColegiado": "PLEN"},
                "votos": [
                    {"codigoParlamentar": 1, "nomeParlamentar": "Esperidião Amin",
                     "siglaPartidoParlamentar": "PP", "siglaVotoParlamentar": "Sim"},
                    {"codigoParlamentar": 2, "nomeParlamentar": "Soraya Thronicke",
                     "siglaPartidoParlamentar": "PODE", "siglaVotoParlamentar": "Sim"},
                ],
            }
        ],
        "orientacoes": {
            "2026-02-24": {
                "votacoes": [
                    {
                        "sequencialVotacao": 4360,
                        "orientacoesLideranca": [
                            {"partido": "Progressistas", "voto": "SIM"},
                            {"partido": "Podemos", "voto": "LIVRE"},
                            {"partido": "B.Feminina", "voto": "SIM"},
                            {"partido": "Governo", "voto": "SIM"},
                        ],
                        "votosParlamentar": [
                            {"nomeParlamentar": "Esperidião Amin", "partido": "Progressistas"},
                            {"nomeParlamentar": "Soraya Thronicke", "partido": "Podemos"},
                        ],
                    }
                ]
            }
        },
    }  # fmt: skip
    votacoes, _, orientacoes = senado.normalizar(payload)
    assert votacoes[0]["resultado"] == "aprovada"
    assert {(o["bancada"], o["tipo"], o["orientacao"]) for o in orientacoes} == {
        ("PP", "partido", "Sim"),
        ("PODE", "partido", "Liberado"),
        ("B.Feminina", "outra", "Sim"),
        ("Governo", "lideranca", "Sim"),
    }


def _carregar(session, conteudo: bytes) -> list[Parlamentar]:
    _popular(session)
    deputados = session.scalars(
        select(Parlamentar).where(Parlamentar.casa == "camara").order_by(Parlamentar.id)
    ).all()
    votacoes, votos, orientacoes = camara.normalizar(conteudo)
    ids = {"1": deputados[0].id, "2": deputados[1].id, "3": deputados[2].id}
    votos = [v | {"parlamentar_id": ids[v["id_deputado"]]} for v in votos]
    vc.recarregar_votacoes(
        session, "camara", 2026, votacoes, votos, _ingestao(session), orientacoes
    )
    session.flush()
    return deputados


def test_recarga_grava_tipo_e_e_idempotente(session):
    _carregar(session, _zip_camara())
    tipos = {o.bancada: o.tipo for o in session.scalars(select(Orientacao))}
    assert tipos["Governo"] == "lideranca" and tipos["SOLIDARIEDADE"] == "partido"
    _carregar(session, _zip_camara())  # recarga do mesmo ano: apaga e reinsere
    assert len(session.scalars(select(Orientacao)).all()) == len(tipos)


def test_rota_da_votacao(client, session):
    deputados = _carregar(session, _zip_camara())
    resposta = client.get("/votacoes/camara/1-1")
    assert resposta.status_code == 200
    d = resposta.json()
    assert d["resultado"] == "aprovada"
    assert d["placar"] == {"sim": 2, "nao": 1, "abstencao": 0, "obstrucao": 0}
    assert d["placar_oficial"] == {"sim": 3, "nao": 1, "abstencao": None}
    assert d["liderancas"][0] == {"bancada": "Governo", "orientacao": "Sim"}
    assert {"bancada": "Maioria", "orientacao": None} in d["liderancas"]
    # Votou como o Governo orientou (Sim): 2 de 3.
    assert d["seguiram_governo"] == {"iguais": 2, "total": 3, "percentual": 66.7}
    partidos = {p["partido"]: p for p in d["partidos"]}
    # PT orientado pela federação; PP pelo bloco; SOLIDARIEDADE por conta própria.
    assert (partidos["PT"]["orientacao"], partidos["PT"]["orientacao_por"]) == (
        "Sim",
        "Fdr PT-PCdoB-PV",
    )
    assert partidos["PP"]["orientacao_por"] == "Bl UniPpPsd..."
    assert (partidos["SOLIDARIEDADE"]["orientacao_por"], partidos["SOLIDARIEDADE"]["seguiram"]) == (
        None,
        1,
    )
    assert d["seguiram_partido"]["total"] == 3
    nomes = {p["nome"] for p in d["parlamentares"]}
    assert deputados[0].nome_parlamentar in nomes
    assert d["fonte_url"].endswith("/votacoes/1-1")

    secreta = client.get("/votacoes/camara/2-1").json()
    assert secreta["secreta"] is True
    assert secreta["outros_registros"] == [{"rotulo": "Votou (voto secreto)", "quantidade": 2}]
    assert secreta["seguiram_partido"]["total"] == 0

    assert client.get("/votacoes/camara/nao-existe").status_code == 404
    assert client.get("/votacoes/stf/1-1").status_code == 422


def test_lista_de_votos_do_perfil_leva_o_id_da_votacao(client, session):
    deputados = _carregar(session, _zip_camara())
    itens = client.get(f"/parlamentares/{deputados[0].id}/votos?ano=2026").json()["itens"]
    assert [i["id_externo"] for i in itens] == ["1-1", "2-1"]
    assert date.fromisoformat(itens[0]["data"]) == date(2026, 9, 3)
