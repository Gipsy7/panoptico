import copy
import json
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select

from app.models import Candidatura
from app.services import segundo_turno
from ingestion.tse import candidaturas, votos
from ingestion.tse import resultado_2_turno as r2t
from tests.test_api import _ingestao

FIXTURES = Path(__file__).parent / "fixtures"


def _json(nome: str) -> dict:
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


def _payload(parcial: bool = False) -> dict:
    ac = _json("resultado_2t_governador_ac.json")
    if parcial:  # apuração em curso: 63% das seções, sem resultado
        ac["and"] = "p"
        ac["s"]["pstn"] = "63"
        for c in r2t.candidatos(ac):
            c["e"] = "2"
    return {
        "ano": 2026,
        "arquivos": {
            "PRESIDENTE:br": _json("resultado_2t_presidente_br.json"),
            "GOVERNADOR:ac": ac,
        },
    }


def _cand(session, ingestao, sq, cargo, uf, numero, nome, **campos):
    c = Candidatura(
        ano_eleicao=2026,
        sq_candidato=sq,
        cargo=cargo,
        uf=uf,
        unidade="Brasil" if uf == "BR" else uf,
        nome=nome,
        nome_urna=nome,
        partido="PX",
        numero=numero,
        situacao_turno="2º TURNO",
        data_eleicao=date(2026, 10, 25),
        ingestao_id=ingestao.id,
        **campos,
    )
    session.add(c)
    session.flush()
    return c


def _banco(session):
    ing = _ingestao(session)
    return {
        "lula": _cand(
            session, ing, "280002542548", "PRESIDENTE", "BR", "13", "Lula", votos=55_000_000
        ),
        "flavio": _cand(
            session, ing, "280002551544", "PRESIDENTE", "BR", "22", "Flavio", votos=50_000_000
        ),
        "alckmin": _cand(session, ing, "280002542549", "VICE-PRESIDENTE", "BR", "13", "Alckmin"),
        "mailza": _cand(session, ing, "10002544107", "GOVERNADOR", "AC", "11", "Mailza", votos=1),
        "alan": _cand(session, ing, "10002532492", "GOVERNADOR", "AC", "10", "Alan Rick", votos=1),
    }


def test_disputas_do_ciclo_so_2_turno_de_presidente_e_governador():
    config = {
        "pl": [
            {
                "c": "ele2026",
                "e": [
                    {
                        "cd": "6257",
                        "t": "1",
                        "abr": [{"cd": "br", "cp": [{"cd": "1", "ds": "Presidente"}]}],
                    },
                    {
                        "cd": "6258",
                        "t": "2",
                        "abr": [{"cd": "br", "cp": [{"cd": "1", "ds": "Presidente"}]}],
                    },
                    {
                        "cd": "6260",
                        "t": "2",
                        "abr": [{"cd": "ac", "cp": [{"cd": "3", "ds": "Governador"}]}],
                    },
                    {
                        "cd": "6284",
                        "t": "1",
                        "abr": [{"cd": "sp", "cp": [{"cd": "11", "ds": "Prefeito"}]}],
                    },
                ],
            },
            {
                "c": "ele2024",
                "e": [
                    {
                        "cd": "620",
                        "t": "2",
                        "abr": [{"cd": "am", "cp": [{"cd": "11", "ds": "Prefeito"}]}],
                    }
                ],
            },
        ]
    }
    assert r2t.disputas_do_ciclo(config, 2026) == [
        {"eleicao": 6258, "cargo_codigo": 1, "cargo": "PRESIDENTE", "uf": "br"},
        {"eleicao": 6260, "cargo_codigo": 3, "cargo": "GOVERNADOR", "uf": "ac"},
    ]
    assert r2t.URL_DISPUTA.format(ano=2026, eleicao=6258, uf="br", cargo=1).endswith(
        "/oficial/ele2026/6258/dados/br/br-c0001-e006258-u.json"
    )


def test_totalizado_gera_resultado_por_candidato_e_vice():
    resultados, avisos = r2t.normalizar(_payload())
    assert avisos == []
    por_sq = {r["sq_candidato"]: r for r in resultados}
    lula = por_sq["280002542548"]
    assert (lula["situacao_turno"], lula["votos"], lula["cargo"], lula["uf"]) == (
        "ELEITO",
        64256232,
        "PRESIDENTE",
        "BR",
    )
    assert por_sq["280002551544"]["situacao_turno"] == "NÃO ELEITO"
    assert por_sq["280002551544"]["votos"] == 59826041
    alckmin = por_sq["280002542549"]  # vice herda a situação, sem votos próprios
    assert (alckmin["cargo"], alckmin["situacao_turno"], alckmin["votos"]) == (
        "VICE-PRESIDENTE",
        "ELEITO",
        None,
    )
    assert por_sq["10002544107"]["uf"] == "AC" and por_sq["10002544107"]["votos"] == 272635
    assert lula["data_eleicao"] == date(2026, 10, 25)
    # A data é a da totalização do próprio JSON (horário de Brasília).
    assert lula["totalizado_em"].utcoffset().total_seconds() == -3 * 3600
    assert (lula["totalizado_em"].hour, lula["totalizado_em"].minute) == (23, 26)


def test_nao_totalizado_nao_grava_e_avisa():
    resultados, avisos = r2t.normalizar(_payload(parcial=True))
    assert {r["cargo"] for r in resultados} == {"PRESIDENTE", "VICE-PRESIDENTE"}
    assert avisos == ["GOVERNADOR AC: ainda não totalizado (não gravado)"]
    # Seção apurada abaixo de 100% mesmo com andamento "f" também fica de fora.
    ac = _json("resultado_2t_governador_ac.json")
    ac["s"]["pstn"] = "99,9"
    assert not r2t.totalizada(ac)
    # Sem nenhum eleito, ou sem horário de totalização, não vale.
    ac = _json("resultado_2t_governador_ac.json")
    for c in r2t.candidatos(ac):
        c["e"] = "n"
    assert not r2t.totalizada(ac)
    ac = _json("resultado_2t_governador_ac.json")
    del ac["ht"]
    assert not r2t.totalizada(ac)
    nada, avisos = r2t.normalizar(
        {"arquivos": {"GOVERNADOR:ac": copy.deepcopy(_payload(True)["arquivos"]["GOVERNADOR:ac"])}}
    )
    assert nada == [] and len(avisos) == 1


def test_aplicar_atualiza_so_o_que_existe(session):
    c = _banco(session)
    resultados, _ = r2t.normalizar(_payload())
    atualizadas, avisos = r2t.aplicar(session, resultados, 2026)
    session.expire_all()
    assert (c["lula"].situacao_turno, c["lula"].votos) == ("ELEITO", 64256232)
    assert (c["flavio"].situacao_turno, c["flavio"].votos) == ("NÃO ELEITO", 59826041)
    assert c["alckmin"].situacao_turno == "ELEITO" and c["alckmin"].votos is None
    assert (c["mailza"].situacao_turno, c["mailza"].votos) == ("ELEITO", 272635)
    assert c["alan"].situacao_turno == "NÃO ELEITO"
    assert atualizadas == 5  # Lula, Flávio, Alckmin, Mailza, Alan (os outros vices não existem)
    assert all("não guardada" not in a for a in avisos)
    # Nenhuma candidatura nova.
    assert len(session.scalars(select(Candidatura)).all()) == 5
    # Idempotente.
    assert r2t.aplicar(session, resultados, 2026)[0] == 5


def test_aplicar_sem_sequencial_liga_por_numero_cargo_uf(session):
    ing = _ingestao(session)
    c = _cand(session, ing, "999", "PRESIDENTE", "BR", "13", "Lula")
    resultados, _ = r2t.normalizar(_payload())
    atualizadas, avisos = r2t.aplicar(session, resultados, 2026)
    session.expire_all()
    assert c.situacao_turno == "ELEITO" and c.votos == 64256232
    assert atualizadas == 1
    assert any("PRESIDENTE BR nº 22" in a for a in avisos)  # Flávio não guardado: avisa, não cria


def test_site_mostra_o_resultado_depois_da_carga(session):
    _banco(session)
    antes = segundo_turno._disputa(session, 2026, "PRESIDENTE", None, "Brasil")
    assert antes["decidida"] is False
    resultados, _ = r2t.normalizar(_payload())
    r2t.aplicar(session, resultados, 2026)
    session.expire_all()
    disputa = segundo_turno._disputa(session, 2026, "PRESIDENTE", None, "Brasil")
    assert disputa["decidida"] is True
    por_nome = {c["nome_urna"]: c for c in disputa["candidatos"]}
    assert por_nome["Lula"]["eleito"] is True and por_nome["Lula"]["votos_2turno"] == 64256232
    assert por_nome["Lula"]["votos_1turno"] is None
    assert por_nome["Flavio"]["eleito"] is False


def test_dados_abertos_antigos_nao_desfazem_o_resultado(session):
    c = _banco(session)
    resultados, _ = r2t.normalizar(_payload())
    r2t.aplicar(session, resultados, 2026)
    ing = _ingestao(session)
    # Arquivo de antes da apuração: "2º TURNO" e data do 1º turno.
    antigos = [
        {
            "ano_eleicao": 2026,
            "sq_candidato": sq,
            "cargo": "PRESIDENTE",
            "uf": "BR",
            "unidade": "Brasil",
            "codigo_ue": "BR",
            "nome": nome,
            "nome_urna": nome,
            "partido": "PX",
            "numero": numero,
            "situacao_turno": "2º TURNO",
            "situacao_candidatura": "APTO",
            "cpf": None,
            "titulo": None,
            "data_nascimento": None,
            "data_eleicao": date(2026, 10, 4),
            "genero": None,
            "cor_raca": None,
            "grau_instrucao": None,
            "ocupacao": None,
            "estado_civil": None,
            "turno_final": 2,
        }
        for sq, nome, numero in (("280002542548", "Lula", "13"), ("280002551544", "Flavio", "22"))
    ]
    candidaturas.carregar_registros(session, antigos, 2026, ing.id)
    session.expire_all()
    assert (c["lula"].situacao_turno, c["lula"].data_eleicao) == ("ELEITO", date(2026, 10, 25))
    assert c["flavio"].situacao_turno == "NÃO ELEITO"
    # Quando o arquivo traz o resultado, sobrescreve sem conflito.
    for r in antigos:
        r["situacao_turno"] = "ELEITO" if r["numero"] == "13" else "NÃO ELEITO"
        r["data_eleicao"] = date(2026, 10, 25)
    candidaturas.carregar_registros(session, antigos, 2026, ing.id)
    session.expire_all()
    assert c["lula"].situacao_turno == "ELEITO" and c["flavio"].situacao_turno == "NÃO ELEITO"


def test_votos_do_1_turno_nao_trocam_os_do_2_turno(session):
    c = _banco(session)
    resultados, _ = r2t.normalizar(_payload())
    r2t.aplicar(session, resultados, 2026)
    session.flush()
    candidaturas_ = {x.sq_candidato: x.id for x in c.values()}
    # Arquivo de votação pré-apuração: 2º turno sem votos (ou ausente).
    disputas = {"280002542548": ["PRESIDENTE", "BR", 0, False]}
    protegidas = votos.resultado_ja_gravado(session, 2026, candidaturas_, disputas)
    assert protegidas == {"280002542548", "280002551544", "10002544107", "10002532492"}
    # Arquivo com votos de 2º turno: não protege (grava o valor oficial dos dados abertos).
    disputas = {"280002542548": ["PRESIDENTE", "BR", 64256232, False]}
    assert "280002542548" not in votos.resultado_ja_gravado(session, 2026, candidaturas_, disputas)


def test_totalizacao_e_datetime_com_fuso():
    momento = r2t.totalizacao({"dt": "25/10/2026", "ht": "23:26:38"})
    assert momento == datetime.fromisoformat("2026-10-25T23:26:38-03:00")
    assert r2t.totalizacao({"dt": "x"}) is None
