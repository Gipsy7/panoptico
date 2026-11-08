"""Resultado completo das eleições (ingestion/tse/resultados.py): soma das zonas, recorte por
município nas eleições gerais e comparecimento."""

import pytest

from app.models import Municipio, ResultadoCandidato, ResultadoTotais
from ingestion.tse import resultados


def linha_voto(**k):
    base = {
        "ANO_ELEICAO": "2022",
        "NR_TURNO": "1",
        "SG_UF": "SC",
        "SG_UE": "SC",
        "CD_MUNICIPIO": "81051",
        "NM_MUNICIPIO": "BLUMENAU",
        "DS_CARGO": "Deputado Federal",
        "SQ_CANDIDATO": "1",
        "NR_CANDIDATO": "1010",
        "NM_URNA_CANDIDATO": "FULANA",
        "SG_PARTIDO": "PX",
        "QT_VOTOS_NOMINAIS": "0",
        "QT_VOTOS_NOMINAIS_VALIDOS": "0",
        "DS_SIT_TOT_TURNO": "NÃO ELEITO",
    }
    return base | k


def test_soma_zonas_na_disputa_e_no_municipio():
    linhas = [
        linha_voto(SQ_CANDIDATO="1", QT_VOTOS_NOMINAIS_VALIDOS="10", DS_SIT_TOT_TURNO="ELEITO"),
        linha_voto(SQ_CANDIDATO="1", QT_VOTOS_NOMINAIS_VALIDOS="5", DS_SIT_TOT_TURNO="ELEITO"),
        linha_voto(
            SQ_CANDIDATO="1",
            CD_MUNICIPIO="80000",
            NM_MUNICIPIO="OUTRA",
            QT_VOTOS_NOMINAIS_VALIDOS="7",
            DS_SIT_TOT_TURNO="ELEITO",
        ),
        linha_voto(SQ_CANDIDATO="2", QT_VOTOS_NOMINAIS_VALIDOS="3"),
    ]
    ap = resultados.apurar([linhas], 2022)
    assert ap.disputa[(1, "DEPUTADO FEDERAL", "SC", "")] == {"1": 22, "2": 3}
    assert ap.recorte[(1, "DEPUTADO FEDERAL", "SC", "81051")] == {"1": 15, "2": 3}
    # Dos 18 votos dados em Blumenau, 15 foram para quem se elegeu.
    assert ap.em_eleitos[(1, "DEPUTADO FEDERAL", "SC", "81051")] == 15


def test_deputado_guarda_so_os_10_mais_votados_do_municipio():
    linhas = [
        linha_voto(SQ_CANDIDATO=str(i), QT_VOTOS_NOMINAIS_VALIDOS=str(100 - i)) for i in range(15)
    ]
    ap = resultados.apurar([linhas], 2022)
    recorte = ap.recorte[(1, "DEPUTADO FEDERAL", "SC", "81051")]
    assert len(recorte) == resultados.MAIS_VOTADOS
    assert set(recorte) == {str(i) for i in range(10)}
    # Na disputa inteira ficam todos.
    assert len(ap.disputa[(1, "DEPUTADO FEDERAL", "SC", "")]) == 15


def test_presidente_disputa_nacional_soma_todas_as_ufs():
    linhas = [
        linha_voto(DS_CARGO="Presidente", SG_UF="SC", SG_UE="SC", QT_VOTOS_NOMINAIS_VALIDOS="4"),
        linha_voto(
            DS_CARGO="Presidente",
            SG_UF="ZZ",
            SG_UE="ZZ",
            CD_MUNICIPIO="99999",
            NM_MUNICIPIO="LISBOA",
            QT_VOTOS_NOMINAIS_VALIDOS="2",
        ),
    ]
    ap = resultados.apurar([linhas], 2022)
    assert ap.disputa[(1, "PRESIDENTE", "BR", "")] == {"1": 6}
    ibge = {("SC", "81051"): "4202404"}
    saida = resultados.linhas_candidatos(ap, 2022, ibge)
    disputa = [r for r in saida if r["abrangencia"] == "disputa"]
    municipio = [r for r in saida if r["abrangencia"] == "municipio"]
    assert [(r["uf"], r["votos"]) for r in disputa] == [("BR", 6)]
    # O exterior não tem município: entra na disputa, não no recorte.
    assert [(r["municipio_ibge"], r["votos"]) for r in municipio] == [("4202404", 4)]


def test_eleicao_municipal_disputa_e_o_municipio():
    linhas = [
        linha_voto(
            ANO_ELEICAO="2024",
            SG_UE="81051",
            DS_CARGO="Prefeito",
            QT_VOTOS_NOMINAIS_VALIDOS="9",
            DS_SIT_TOT_TURNO="ELEITO",
        )
    ]
    ap = resultados.apurar([linhas], 2024)
    assert ap.disputa[(1, "PREFEITO", "SC", "81051")] == {"1": 9}
    assert ap.recorte == {}
    saida = resultados.linhas_candidatos(ap, 2024, {("SC", "81051"): "4202404"})
    assert saida[0]["municipio_ibge"] == "4202404"
    assert saida[0]["situacao"] == "ELEITO"


def test_somar_totais_por_municipio():
    base = {
        "NR_TURNO": "1",
        "SG_UF": "SC",
        "CD_MUNICIPIO": "81051",
        "NM_MUNICIPIO": "BLUMENAU",
        "DS_CARGO": "Prefeito",
        "QT_APTOS": "100",
        "QT_COMPARECIMENTO": "80",
        "QT_ABSTENCOES": "20",
        "QT_VOTOS_BRANCOS": "2",
        "QT_TOTAL_VOTOS_NULOS": "3",
        "QT_TOTAL_VOTOS_VALIDOS": "75",
        "QT_VOTOS_NOMINAIS_VALIDOS": "75",
    }
    totais, nomes = resultados.somar_totais([base, base | {"QT_APTOS": "50"}])
    t = totais[(1, "PREFEITO", "SC", "81051")]
    assert t["aptos"] == 150 and t["comparecimento"] == 160 and t["nulos"] == 6
    assert nomes[("SC", "81051")] == "BLUMENAU"


def test_eleicao_geral():
    assert resultados.eleicao_geral(2022) and resultados.eleicao_geral(2026)
    assert not resultados.eleicao_geral(2024)


def test_transito_de_outra_uf_soma_no_recorte_do_presidente():
    # O arquivo da BA traz votos de presidente dados em SC (trânsito), entre linhas da BA.
    sc = linha_voto(DS_CARGO="Presidente", QT_VOTOS_NOMINAIS_VALIDOS="10")
    ba = linha_voto(
        DS_CARGO="Presidente",
        SG_UF="BA",
        SG_UE="BA",
        CD_MUNICIPIO="38490",
        NM_MUNICIPIO="SALVADOR",
        QT_VOTOS_NOMINAIS_VALIDOS="1",
    )
    ap = resultados.apurar([[sc], [ba, sc | {"QT_VOTOS_NOMINAIS_VALIDOS": "3"}, ba]], 2022)
    assert ap.recorte[(1, "PRESIDENTE", "SC", "81051")] == {"1": 13}
    assert ap.disputa[(1, "PRESIDENTE", "BR", "")] == {"1": 15}


# --- API -------------------------------------------------------------------------------------


def _cand(ano, cargo, nome, votos, situacao, mun="4202404", uf="SC", abr="disputa", turno=1):
    return ResultadoCandidato(
        ano=ano,
        turno=turno,
        cargo=cargo,
        abrangencia=abr,
        uf=uf,
        municipio_ibge=mun,
        sq_candidato=f"{ano}{nome}",
        numero="1",
        nome_urna=nome,
        partido="PX",
        votos=votos,
        situacao=situacao,
    )


def _tot(ano, cargo, aptos, comp, validos, nominais, em_eleitos=None, mun="4202404", turno=1):
    return ResultadoTotais(
        ano=ano,
        turno=turno,
        cargo=cargo,
        uf="SC",
        municipio_ibge=mun,
        aptos=aptos,
        comparecimento=comp,
        abstencoes=aptos - comp,
        brancos=2,
        nulos=3,
        validos=validos,
        nominais=nominais,
        votos_em_eleitos=em_eleitos,
    )


@pytest.fixture
def blumenau(session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.add_all(
        [
            _tot(2024, "PREFEITO", 100, 80, 75, 75),
            _cand(2024, "PREFEITO", "EGIDIO", 50, "ELEITO"),
            _cand(2024, "PREFEITO", "ODAIR", 25, "NÃO ELEITO"),
            _cand(2020, "PREFEITO", "MARIO", 40, "ELEITO"),
            _tot(2026, "DEPUTADO FEDERAL", 120, 100, 90, 80, em_eleitos=44),
            _cand(2026, "DEPUTADO FEDERAL", "JULIA", 30, "ELEITO POR QP", abr="municipio"),
            _cand(2026, "DEPUTADO FEDERAL", "JOAO", 20, "SUPLENTE", abr="municipio"),
        ]
    )
    session.flush()


def test_api_resultado_prefeito(client, blumenau):
    r = client.get(
        "/eleicoes/resultado", params={"ano": 2024, "cargo": "prefeito", "municipio": "4202404"}
    )
    assert r.status_code == 200
    d = r.json()
    assert [(c["nome_urna"], c["pct"], c["eleito"]) for c in d["candidatos"]] == [
        ("EGIDIO", 66.67, True),
        ("ODAIR", 33.33, False),
    ]
    assert d["totais"]["pct_comparecimento"] == 80.0
    assert d["anteriores"] == [
        {"ano": 2020, "turno": 1, "eleitos": [{"nome_urna": "MARIO", "partido": "PX", "votos": 40}]}
    ]


def test_api_mais_votados_e_pct_para_eleitos(client, blumenau):
    d = client.get("/municipios/4202404/mais-votados").json()
    assert d["ano"] == 2026
    federal = d["cargos"][0]
    assert federal["pct_em_eleitos"] == 55.0
    assert [(i["posicao"], i["nome_urna"], i["eleito"]) for i in federal["itens"]] == [
        (1, "JULIA", True),
        (2, "JOAO", False),
    ]


def test_api_eleitores_e_antecessores(client, blumenau):
    e = client.get("/municipios/4202404/eleitores").json()
    assert (e["ano"], e["eleitores"], e["votaram"]) == (2026, 120, 100)
    a = client.get("/eleicoes/antecessores", params={"cargo": "PREFEITO", "municipio": "4202404"})
    assert [(m["ano"], m["inicio"], m["fim"]) for m in a.json()["mandatos"]] == [
        (2024, 2025, 2028),
        (2020, 2021, 2024),
    ]


def test_api_resultado_sem_dado_e_404(client, blumenau):
    r = client.get(
        "/eleicoes/resultado", params={"ano": 2010, "cargo": "PREFEITO", "municipio": "4202404"}
    )
    assert r.status_code == 404
