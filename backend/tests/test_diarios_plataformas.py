"""Conectores de plataformas compartilhadas de diário oficial (SIGPub e DOM/SC via CIGA).

Amostras reais, recortadas: `sigpub_amm_mg_amostra.txt` (texto da edição nº 4384 do Diário
Oficial dos Municípios Mineiros, de 20/10/2026, que o PyMuPDF extrai do PDF) e
`domsc_ciga_amostra.json` (publicações do lote de 07/10/2026 dos dados abertos do CIGA).
"""

import csv
import json
import re
from datetime import date
from pathlib import Path

import httpx
import respx

from app.models import DiarioAto, Pessoa
from ingestion import comum
from ingestion.diarios import domsc, sigpub
from ingestion.diarios import plataformas as pl

FIXTURES = Path(__file__).parent / "fixtures"
INDICE = {
    "MG": {"PIRAPORA": "3151206", "RIO POMBA": "3155801", "SAO JOAO": "3162500"},
    "SC": {"POMERODE": "4213203", "CAPIVARI DE BAIXO": "4203097"},
}


def _sigpub_texto() -> str:
    return (FIXTURES / "sigpub_amm_mg_amostra.txt").read_text(encoding="utf-8")


def test_sigpub_separa_materias_pelo_codigo_identificador():
    materias = sigpub.separar_materias(_sigpub_texto())
    assert [m["codigo"] for m in materias] == ["F63B1469", "4B608BEC", "27C670D5"]
    assert materias[1]["cabecalho"].startswith("PREFEITURA MUNICIPAL DE RIO POMBA")


def test_resolve_municipio_so_de_orgao_municipal():
    materias = sigpub.separar_materias(_sigpub_texto())
    # Sem "ESTADO DE.../órgão" no começo: o município vem do início do texto.
    assert pl.resolver_municipio(materias[0]["cabecalho"], ("MG",), INDICE) is None
    assert pl.resolver_municipio(materias[0]["texto"][:800], ("MG",), INDICE) == (
        "3151206",
        "MG",
    )
    assert pl.resolver_municipio(materias[1]["cabecalho"], ("MG",), INDICE) == ("3155801", "MG")
    # Associação de municípios não é município.
    assert pl.resolver_municipio(materias[2]["cabecalho"], ("MG",), INDICE) is None
    # O nome do município de outra UF não casa.
    assert pl.resolver_municipio("PREFEITURA MUNICIPAL DE POMERODE", ("MG",), INDICE) is None


def test_sigpub_sugere_nomeacao_do_nomeado_e_ignora_quem_assina():
    alvos = {
        "3151206": [
            (1, "Vera Rodrigues dos Santos"),  # nomeada na portaria
            (2, "Alexandro Costa Cesar"),  # prefeito que assina: não é alvo do ato
        ],
        "3155801": [(3, "Athila Viana de Oliveira")],  # só consta como agente de contratação
    }
    vistos: dict = {}
    achados = sigpub.processar_edicao(
        {
            "slug": "amm-mg",
            "data": "2026-10-20",
            "url": "https://x/e.pdf",
            "texto": _sigpub_texto(),
        },
        INDICE,
        alvos,
        vistos,
    )
    assert [(a["pessoa_id"], a["tipo_ato"]) for a in achados] == [(1, "nomeacao")]
    assert achados[0]["municipio_ibge"] == "3151206"
    assert achados[0]["url"] == "https://x/e.pdf#F63B1469"
    assert len(achados[0]["trecho"]) <= 500
    # Cobertura: Pirapora e Rio Pomba aparecem; a associação não.
    assert set(vistos) == {("MG", "3151206"), ("MG", "3155801")}


def test_sigpub_calendario_usa_token_e_junta_edicao_repetida():
    corpo = {
        "edicao": [{"numero_edicao": "4384", "link_diario": "publicado_1_2026-10-19_ab"}],
        "url_arquivos": "https://www-storage.voxtecnologia.com.br/?m=sigpub.publicacao&f=182&i=",
    }
    with respx.mock:
        rota = respx.post("https://www.diariomunicipal.com.br/amm-mg/materia/calendario").mock(
            return_value=httpx.Response(200, json=corpo)
        )
        respx.post("https://www.diariomunicipal.com.br/amm-mg/materia/calendario/extra").mock(
            return_value=httpx.Response(200, json=corpo)  # o "extra" repete a regular
        )
        with httpx.Client() as client:
            sigpub.PAUSA = 0
            edicoes = sigpub.edicoes_do_dia(client, "amm-mg", "TOKEN", date(2026, 10, 20))
    assert len(edicoes) == 1 and edicoes[0]["extra"] is False
    assert edicoes[0]["url"].endswith("publicado_1_2026-10-19_ab.pdf")
    enviado = rota.calls[0].request.content.decode()
    assert "calendar%5B_token%5D=TOKEN" in enviado and "calendar%5Bday%5D=20" in enviado


def test_sigpub_sem_edicao_no_dia():
    with respx.mock:
        respx.post(re.compile(r".*/materia/calendario.*")).mock(
            return_value=httpx.Response(200, json={"error": "Ocorreu um erro inesperado!"})
        )
        with httpx.Client() as client:
            sigpub.PAUSA = 0
            assert sigpub.edicoes_do_dia(client, "aam", "T", date(2026, 10, 18)) == []


def _ciga() -> dict:
    return json.loads((FIXTURES / "domsc_ciga_amostra.json").read_text(encoding="utf-8"))


def test_domsc_recorta_so_ato_de_prefeitura_e_camara():
    publicacoes = domsc.recortar(_ciga())
    # Ata de registro de preços (CISAMVE, consórcio) fica de fora; as 2 portarias entram.
    assert [p["municipio"] for p in publicacoes] == ["Pomerode", "Capivari de Baixo"]
    # Título de compras também sai, mesmo em categoria de ato.
    base = {"categoria": "Outras publicações", "municipio": "Pomerode"}
    homologacao = base | {
        "entidade": "Prefeitura Municipal de Pomerode",
        "titulo": "TERMO DE HOMOLOGAÇÃO",
    }
    assert domsc.recortar({"autopublicacoes": [homologacao]}) == []


def test_domsc_sugere_ato_e_ignora_prefeito_que_assina():
    alvos = {
        "4213203": [(10, "Maheli Sueli da Silva")],
        "4203097": [(11, "Claudir Antônio de Bitencourt")],  # prefeito que assina a portaria
    }
    vistos: dict = {}
    achados = domsc.processar(domsc.recortar(_ciga()), INDICE, alvos, vistos)
    assert [(a["pessoa_id"], a["tipo_ato"], a["municipio_ibge"]) for a in achados] == [
        (10, "nomeacao", "4213203")
    ]
    assert achados[0]["data"].year == 2026
    assert achados[0]["url"].startswith("https://diariomunicipal.sc.gov.br/")
    assert set(vistos) == {("SC", "4213203"), ("SC", "4203097")}


def test_domsc_lista_lotes_do_conjunto_mensal():
    html = (
        '<a href="https://dados.ciga.sc.gov.br/dataset/abc/resource/r1/download/'
        'cigadados_publicacoes_2026_10_19_0000_1159.zip">x</a>'
        '<a href="https://dados.ciga.sc.gov.br/dataset/abc/resource/r2/download/'
        'cigadados_publicacoes_2026_10_02_0000_1159.zip">y</a>'
    )
    domsc.PAUSA = 0
    with respx.mock:
        respx.get("https://dados.ciga.sc.gov.br/dataset/domsc-publicacoes-de-10-2026").mock(
            return_value=httpx.Response(200, text=html)
        )
        with comum.criar_cliente() as client:
            lotes = domsc.listar_lotes(client, date(2026, 10, 15), date(2026, 10, 21))
    assert [(d.isoformat(), n) for d, n, _ in lotes] == [
        ("2026-10-19", "cigadados_publicacoes_2026_10_19_0000_1159.zip")
    ]


def test_gravar_sugestoes_e_idempotente_e_nasce_nao_revisada(session):
    p = Pessoa(nome="Vera Rodrigues dos Santos", chave_nome="VERA RODRIGUES DOS SANTOS")
    session.add(p)
    session.flush()
    s = {
        "pessoa_id": p.id,
        "municipio_ibge": "3151206",
        "data": date(2026, 10, 20),
        "tipo_ato": "nomeacao",
        "trecho": "x",
        "url": "https://x/e.pdf#F63B1469",
    }
    assert pl.gravar_sugestoes(session, [s]) == 1
    assert pl.gravar_sugestoes(session, [s]) == 0
    ato = session.query(DiarioAto).one()
    assert ato.revisado is False


def test_registrar_cobertura_guarda_ultima_edicao(tmp_path, monkeypatch):
    monkeypatch.setattr(pl, "COBERTURA_CSV", tmp_path / "cobertura.csv")
    pl.registrar_cobertura("sigpub_atos", {("MG", "3151206"): ("PIRAPORA", date(2026, 10, 1), 2)})
    pl.registrar_cobertura("sigpub_atos", {("MG", "3151206"): ("PIRAPORA", date(2026, 10, 20), 3)})
    with (tmp_path / "cobertura.csv").open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    assert len(linhas) == 1
    assert linhas[0]["materias"] == "3" and linhas[0]["ultima_edicao"] == "2026-10-20"


def test_raw_da_edicao_ida_e_volta(tmp_path, monkeypatch):
    monkeypatch.setattr(comum, "RAW_DIR", tmp_path)
    caminho = pl.gravar_raw_edicao("sigpub_atos", "amm-mg", "2026-10-20_4384", {"texto": "ação"})
    assert pl.ler_raw_edicao(caminho) == {"texto": "ação"}


def test_sigpub_varredura_incremental_pela_marca(tmp_path, monkeypatch):
    monkeypatch.setattr(comum, "RAW_DIR", tmp_path)
    hoje = date(2026, 10, 21)
    assert sigpub._inicio("aam", hoje, 90) == date(2026, 7, 23)  # primeira carga: 90 dias
    sigpub._marcar_varredura("aam", date(2026, 10, 14))
    assert sigpub._inicio("aam", hoje, 90) == date(2026, 10, 11)  # marca - 3 dias de folga
    sigpub._marcar_varredura("aam", date(2026, 1, 1))
    assert sigpub._inicio("aam", hoje, 90) == date(2026, 7, 23)  # nunca antes da janela
