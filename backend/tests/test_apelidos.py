"""Nomes de gastos grafados diferente do deputado: só o idêntico liga sozinho, o aproximado
vai para a fila, a decisão humana gravada é reaplicada e a sugestão pendente não liga nada."""

from decimal import Decimal

from ingestion import revisar
from ingestion.assembleias import alece, apelidos, base

DEPUTADOS = [
    {"id_externo": "sergio-aguiar", "nome": "Sérgio Aguiar"},
    {"id_externo": "emilia-pessoa", "nome": "Emília Pessoa"},
    {"id_externo": "carmelo-neto", "nome": "Carmelo Neto"},
]
TOTAIS = {
    "SERGIO AGUIAR": (10, Decimal("1000.00")),  # idêntico (sem acento)
    "SEGIO AGUIAR": (2, Decimal("2927.47")),  # erro de digitação
    "EMILA PESSOA": (2, Decimal("0")),
    "NIZO COSTA": (52, Decimal("401784.06")),  # ex-deputado: nenhum parecido
}


def test_identico_liga_sozinho_e_aproximado_vai_para_a_fila():
    ligados, sobras = base.ligar_nomes("alece", TOTAIS, DEPUTADOS, [])
    assert ligados == {"SERGIO AGUIAR": "Sérgio Aguiar"}
    assert sorted(sobras) == ["EMILA PESSOA", "NIZO COSTA", "SEGIO AGUIAR"]
    fila = {f["nome_fonte"]: f for f in apelidos.pendentes()}
    assert set(fila) == set(sobras)
    assert fila["SEGIO AGUIAR"]["valor"] == Decimal("2927.47")
    assert fila["SEGIO AGUIAR"]["candidatos"][0]["id_externo"] == "sergio-aguiar"
    assert fila["NIZO COSTA"]["candidatos"] == []


def test_sugestao_pendente_nao_liga_nada():
    ligados, _ = base.ligar_nomes("alece", TOTAIS, DEPUTADOS, [])
    assert "SEGIO AGUIAR" not in ligados and "EMILA PESSOA" not in ligados
    linhas = [
        {"DEPUTADO": "DEP SEGIO AGUIAR", "PERIODO": "03/2026", "DESCRICAO": "COMBUSTIVEL",
         "VALOR": "100,00"},
    ]  # fmt: skip
    soma, _ = alece.somar_gastos(linhas)
    casa = {"vereadores": [{**d, "nome": d["nome"]} for d in DEPUTADOS]}
    ligados, _ = base.ligar_nomes("alece", alece.totais_por_nome(linhas), casa["vereadores"], [])
    assert ligados == {} and soma  # a soma existe, mas ninguém recebe


def test_decisao_gravada_reaplica_nas_cargas_seguintes():
    base.ligar_nomes("alece", TOTAIS, DEPUTADOS, [])
    fila = {f["nome_fonte"]: f for f in apelidos.pendentes()}
    apelidos.gravar_decisao(
        fila["SEGIO AGUIAR"], "aceito", "Mikael", "sergio-aguiar", "Sérgio Aguiar"
    )
    apelidos.gravar_decisao(fila["NIZO COSTA"], "recusado", "Mikael")
    # nova carga
    ligados, sobras = base.ligar_nomes("alece", TOTAIS, DEPUTADOS, [])
    assert ligados == {"SERGIO AGUIAR": "Sérgio Aguiar", "SEGIO AGUIAR": "Sérgio Aguiar"}
    assert sobras == ["EMILA PESSOA"]
    assert [f["nome_fonte"] for f in apelidos.pendentes()] == ["EMILA PESSOA"]


def test_decisao_de_outra_casa_ou_de_deputado_ausente_e_ignorada():
    item = {"escopo": "alrn", "nome_fonte": "SEGIO AGUIAR"}
    apelidos.gravar_decisao(item, "aceito", "Mikael", "sergio-aguiar", "Sérgio Aguiar")
    item = {"escopo": "alece", "nome_fonte": "EMILA PESSOA"}
    apelidos.gravar_decisao(item, "aceito", "Mikael", "ex-deputada", "Fulana")
    ligados, sobras = base.ligar_nomes("alece", TOTAIS, DEPUTADOS, [])
    assert "SEGIO AGUIAR" not in ligados and "EMILA PESSOA" not in ligados
    assert "SEGIO AGUIAR" in sobras and "EMILA PESSOA" in sobras


def test_revisar_apelido_grava_a_decisao(monkeypatch):
    base.ligar_nomes("alece", TOTAIS, DEPUTADOS, [])
    respostas = iter(["n", "1", "s"])  # maior valor primeiro: NIZO COSTA, depois SEGIO AGUIAR
    monkeypatch.setattr("builtins.input", lambda _="": next(respostas))
    revisar._revisar_apelidos(apelidos.pendentes(), "Mikael")
    decisoes = {d["nome_fonte"]: d for d in apelidos.decisoes("alece")}
    assert decisoes["NIZO COSTA"]["decisao"] == "recusado"
    assert decisoes["SEGIO AGUIAR"]["decisao"] == "aceito"
    assert decisoes["SEGIO AGUIAR"]["id_externo"] == "sergio-aguiar"
