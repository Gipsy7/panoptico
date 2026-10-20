"""Revisão pelo navegador (ingestion/revisar_web.py): cada decisão vai para o CSV da fila
certa e "desfazer" tira só a última linha gravada nesta sessão. Sem servidor HTTP: as
funções são chamadas direto, com os CSVs apontados para tmp_path e filas fixas."""

import csv
from contextlib import nullcontext

import pytest

from app.models import Candidatura, Foto, MandatoLocal
from ingestion import revisar, revisar_web
from ingestion.congresso import cpi_revisao
from ingestion.diarios import revisao as diarios_revisao
from ingestion.dou import revisao as dou_revisao

VINCULOS = [
    {"fonte": "mandato_local", "id_externo": "assembleia:SP::1", "ligado_a": "candidatura:2022:9"},
    {"fonte": "mandato_local", "id_externo": "assembleia:SP::2", "ligado_a": "candidatura:2022:8"},
]
ATOS = [{"url": "https://diario/1", "pessoa_chave": "p1"}, {"url": "https://diario/2",
         "pessoa_chave": "p2"}]  # fmt: skip
DOU = [{"id_materia": "m1", "pessoa_chave": "p1"}]
CPI = [{"chave": "cpi:1"}, {"chave": "cpi:2"}]


@pytest.fixture
def csvs(tmp_path, monkeypatch):
    caminhos = {
        "vinculo": tmp_path / "vinculos_revisados.csv",
        "diario": tmp_path / "atos_revisados.csv",
        "dou": tmp_path / "dou_revisados.csv",
        "cpi": tmp_path / "indiciamentos_revisados.csv",
    }
    # As funções de gravar leem o caminho do próprio módulo; TIPOS guarda o seu.
    monkeypatch.setattr(revisar, "REVISOES", caminhos["vinculo"])
    monkeypatch.setattr(diarios_revisao, "ATOS_REVISADOS", caminhos["diario"])
    monkeypatch.setattr(dou_revisao, "DOU_REVISADOS", caminhos["dou"])
    monkeypatch.setattr(cpi_revisao, "INDICIAMENTOS_REVISADOS", caminhos["cpi"])
    filas = {"vinculo": VINCULOS, "diario": ATOS, "dou": DOU, "cpi": CPI}
    monkeypatch.setattr(
        revisar_web,
        "TIPOS",
        {
            tipo: (rotulo, lambda _s, fila=filas[tipo]: [dict(i) for i in fila], caminhos[tipo])
            for tipo, (rotulo, _, _) in revisar_web.TIPOS.items()
        },
    )
    # Os sinais do vínculo vêm do banco; aqui só interessa a gravação.
    monkeypatch.setattr(revisar_web, "SessionLocal", lambda: nullcontext(None))
    monkeypatch.setattr(revisar_web, "_sinais_do_vinculo", lambda _s, _i: {"foto_casa": ""})
    revisar_web._filas.clear()
    revisar_web._feitas.clear()
    yield caminhos
    revisar_web._filas.clear()
    revisar_web._feitas.clear()


def _linhas(caminho):
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_registro_gravado_inteiro_e_sem_cabecalho(tmp_path):
    arq = tmp_path / "x.csv"
    arq.write_bytes(b"cab\r\nprimeira\r\n")
    inicio = arq.stat().st_size
    arq.write_bytes(arq.read_bytes() + b'a,"x\ny"\r\n')
    assert revisar_web._registro_gravado(arq, inicio) == b'a,"x\ny"\r\n'
    # Arquivo criado agora: o cabeçalho não faz parte do registro.
    assert revisar_web._registro_gravado(arq, None) == b'primeira\r\na,"x\ny"\r\n'


@pytest.mark.parametrize(
    ("tipo", "chave", "valor"),
    [
        ("vinculo", "id_externo", "assembleia:SP::2"),
        ("diario", "url", "https://diario/2"),
        ("dou", "id_materia", "m1"),
        ("cpi", "chave", "cpi:2"),
    ],
)
def test_decidir_grava_no_csv_da_fila_e_tira_o_item(csvs, tipo, chave, valor):
    indice = len(revisar_web._fila(tipo)) - 1
    revisar_web.decidir(tipo, indice, "recusado", "Rev", observacao="obs")
    linhas = _linhas(csvs[tipo])
    assert len(linhas) == 1
    assert (linhas[0][chave], linhas[0]["decisao"], linhas[0]["revisado_por"]) == (
        valor,
        "recusado",
        "Rev",
    )
    assert linhas[0]["observacao"] == "obs"
    # Só o CSV da fila decidida foi criado.
    assert [t for t, c in csvs.items() if c.exists()] == [tipo]
    assert valor not in [i.get(chave) for i in revisar_web._fila(tipo)]
    assert revisar_web._feitas[-1][0] == tipo


def test_vinculo_ganha_os_sinais_ao_montar_a_fila(csvs):
    assert all(i["foto_casa"] == "" for i in revisar_web._fila("vinculo"))


def test_cpi_aceito_grava_a_pessoa_escolhida(csvs):
    revisar_web.decidir("cpi", 0, "aceito", "Rev", pessoa_chave="pessoa:42")
    assert _linhas(csvs["cpi"])[0]["pessoa_chave"] == "pessoa:42"


def test_desfazer_tira_so_a_ultima_linha_desta_sessao(csvs):
    caminho = csvs["diario"]
    caminho.write_text(
        "url,pessoa_chave,decisao,revisado_por,revisado_em,observacao\r\n"
        "https://antes,p0,aceito,Outro,2026-01-01,\r\n",
        encoding="utf-8",
        newline="",
    )
    revisar_web.decidir("diario", 0, "aceito", "Rev")
    revisar_web.decidir("diario", 0, "recusado", "Rev")
    assert revisar_web._fila("diario") == []
    assert [r["url"] for r in _linhas(caminho)] == [
        "https://antes",
        "https://diario/1",
        "https://diario/2",
    ]

    assert revisar_web.desfazer() == "diario"
    assert [r["url"] for r in _linhas(caminho)] == ["https://antes", "https://diario/1"]
    # O item volta ao começo da fila.
    assert revisar_web._fila("diario")[0]["url"] == "https://diario/2"

    assert revisar_web.desfazer() == "diario"
    assert [r["url"] for r in _linhas(caminho)] == ["https://antes"]
    # Nada mais desta sessão: a linha de antes fica.
    assert revisar_web.desfazer() is None
    assert [r["url"] for r in _linhas(caminho)] == ["https://antes"]
    assert [i["url"] for i in revisar_web._fila("diario")] == [
        "https://diario/1",
        "https://diario/2",
    ]


def test_desfazer_entre_filas_respeita_a_ordem(csvs):
    revisar_web.decidir("dou", 0, "aceito", "Rev")
    revisar_web.decidir("vinculo", 0, "aceito", "Rev")
    assert revisar_web.desfazer() == "vinculo"
    assert _linhas(csvs["vinculo"]) == []  # sobra só o cabeçalho
    assert len(_linhas(csvs["dou"])) == 1
    assert revisar_web.desfazer() == "dou"
    assert _linhas(csvs["dou"]) == []


def test_desfazer_recusa_se_o_csv_mudou_fora_da_pagina(csvs):
    revisar_web.decidir("dou", 0, "aceito", "Rev")
    with csvs["dou"].open("a", encoding="utf-8", newline="") as f:
        f.write("m9,p9,aceito,Outro,2026-01-01,\r\n")
    with pytest.raises(RuntimeError, match="mudou fora"):
        revisar_web.desfazer()
    assert len(_linhas(csvs["dou"])) == 2  # nada foi apagado
    assert revisar_web._feitas  # e a decisão continua na pilha para desfazer à mão


def test_desfazer_com_observacao_de_varias_linhas(csvs):
    # A observação vem de um <textarea>: o registro ocupa mais de uma linha do arquivo.
    caminho = csvs["dou"]
    caminho.write_text(
        "id_materia,pessoa_chave,decisao,revisado_por,revisado_em,observacao\r\n"
        "m0,p0,aceito,Outro,2026-01-01,\r\n",
        encoding="utf-8",
        newline="",
    )
    antes = caminho.read_bytes()
    revisar_web.decidir("dou", 0, "aceito", "Rev", observacao="linha 1\nlinha 2")
    assert _linhas(caminho)[-1]["observacao"] == "linha 1\nlinha 2"
    revisar_web.desfazer()
    assert caminho.read_bytes() == antes


def test_sinais_do_vinculo_vem_do_banco(session):
    c = Candidatura(
        ano_eleicao=2022, sq_candidato="9", cargo="DEPUTADO ESTADUAL", uf="SP",
        unidade="São Paulo", nome="Ana", nome_urna="Ana", partido="PSB",
    )  # fmt: skip
    session.add(c)
    session.flush()
    session.add(Foto(candidatura_id=c.id, webp=b"RIFF"))
    session.add(MandatoLocal(
        casa="assembleia", uf="SP", municipio_ibge=None, id_externo="1", nome="Ana",
        foto_url="https://al/foto.jpg", sapl_url="https://al",
    ))  # fmt: skip
    session.flush()
    item = {"id_externo": "assembleia:SP::1", "ligado_a": "candidatura:2022:9"}
    assert revisar_web._sinais_do_vinculo(session, item) == {
        "foto_casa": "https://al/foto.jpg",
        "foto_tse": f"/api/foto/{c.id}",
        "partido_tse": "PSB",
        "ano_tse": "2022",
    }
    # Sem mandato nem candidatura na base, os sinais ficam vazios em vez de quebrar.
    vazio = {"id_externo": "assembleia:SP::7", "ligado_a": "candidatura:2018:1"}
    assert revisar_web._sinais_do_vinculo(session, vazio) == {
        "foto_casa": "",
        "foto_tse": "",
        "partido_tse": "",
        "ano_tse": "2018",
    }
