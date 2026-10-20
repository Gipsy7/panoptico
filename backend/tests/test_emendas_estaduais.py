"""Emendas estaduais de Santa Catarina (SC Transferências, CGE/SC).

Fixtures em tests/fixtures/emendas_estaduais_sc/ (recortes reais de 19/10/2026):
- emendas.csv: as 15 propostas de emenda com beneficiário em Gaspar (4205902), mais uma de
  Blumenau cujo objeto cita Gaspar, uma de bancada, uma de autor com apelido entre
  parênteses e uma com valor atualizado diferente do original (UTF-8 com BOM, como vem do
  botão "Baixar CSV" de /pesquisa-detalhada/emendas);
- financeiro.csv: as linhas do razão financeiro (dados_financeiros_AAAA.zip) dessas
  transferências (latin-1).
"""

import io
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models import (
    Candidatura,
    EmendaEstadual,
    FonteIngestao,
    MandatoLocal,
    Municipio,
    Pessoa,
    PessoaVinculo,
)
from ingestion import comum
from ingestion.emendas_estaduais import sc

FIXTURES = Path(__file__).parent / "fixtures" / "emendas_estaduais_sc"
GASPAR = "4205902"
MUNICIPIOS = {
    GASPAR: "Gaspar",
    "4202404": "Blumenau",
    "4214201": "Quilombo",
    "4205407": "Florianópolis",
    "4204301": "Concórdia",
}


def _pacote() -> bytes:
    financeiro = io.BytesIO()
    with zipfile.ZipFile(financeiro, "w") as z:
        z.writestr(
            "dados-abertos/dados_financeiros_2025.csv", (FIXTURES / "financeiro.csv").read_bytes()
        )
    return sc.empacotar((FIXTURES / "emendas.csv").read_bytes(), {2025: financeiro.getvalue()})


def _ingestao(session, status="em_andamento") -> FonteIngestao:
    ingestao = FonteIngestao(
        fonte=sc.FONTE, url=sc.URL, arquivo_raw="x.zip", status=status,
        concluido_em=datetime.now(UTC) if status == "ok" else None,
    )  # fmt: skip
    session.add(ingestao)
    session.flush()
    return ingestao


def _pessoa(session, nome: str, fonte: str, id_externo: str, regra: str = "cpf") -> Pessoa:
    pessoa = Pessoa(nome=nome, chave_nome=comum.chave_nome(nome))
    session.add(pessoa)
    session.flush()
    session.add(PessoaVinculo(pessoa_id=pessoa.id, fonte=fonte, id_externo=id_externo, regra=regra))
    return pessoa


def _candidatura(session, sq: str, nome: str, urna: str) -> Candidatura:
    c = Candidatura(
        ano_eleicao=2022, sq_candidato=sq, cargo="DEPUTADO ESTADUAL", uf="SC",
        unidade="SANTA CATARINA", nome=nome, nome_urna=urna, situacao_turno="ELEITO POR QP",
    )  # fmt: skip
    session.add(c)
    session.flush()
    return c


def _mandato(session, id_externo: str, nome: str, candidatura_id=None) -> MandatoLocal:
    m = MandatoLocal(
        casa="assembleia", uf="SC", id_externo=id_externo, nome=nome, titular=True,
        em_exercicio=True, sapl_url="https://www.alesc.sc.gov.br/deputados",
        candidatura_id=candidatura_id, proposicoes_por_tipo={},
    )  # fmt: skip
    session.add(m)
    session.flush()
    return m


@pytest.fixture
def base(session, monkeypatch):
    """Municípios, deputados e pessoas para ligar os autores."""
    monkeypatch.setattr(sc, "MINIMO", 10)
    for ibge, nome in MUNICIPIOS.items():
        if session.get(Municipio, ibge) is None:
            session.add(Municipio(ibge=ibge, nome=nome, uf="SC", nome_chave=comum.chave_nome(nome)))
    # Jerry Comper: eleito em 2022 e no cargo (ALESC), mesma pessoa pelos dois registros.
    jerry = _candidatura(session, "240001", "Jerry Edson Comper", "Jerry Comper")
    pessoa = _pessoa(session, "Jerry Edson Comper", "candidatura", "2022:240001")
    m_jerry = _mandato(session, "jerry-comper", "Jerry Comper", jerry.id)
    session.add(
        PessoaVinculo(
            pessoa_id=pessoa.id, fonte="mandato_local",
            id_externo="assembleia:SC::jerry-comper", regra="nome_exato_casa",
        )
    )  # fmt: skip
    # Romildo Titon: no cargo (suplente que assumiu), sem pessoa ligada.
    m_romildo = _mandato(session, "romildo-titon", "Romildo Titon")
    # Uma deputada sem emenda: entra na média com zero.
    m_outra = _mandato(session, "outra", "Deputada Sem Emenda")
    # Homônimos: duas pessoas com o mesmo nome de urna não ligam ninguém.
    for sq in ("240002", "240003"):
        _candidatura(session, sq, f"Ana Campagnolo {sq}", "Ana Campagnolo")
        _pessoa(session, f"Ana Campagnolo {sq}", "candidatura", f"2022:{sq}")
    session.flush()
    return {"jerry": m_jerry, "romildo": m_romildo, "outra": m_outra, "pessoa_jerry": pessoa}


def test_favorecido_e_nomes_do_autor():
    assert sc.favorecido("CLUBE ATLETICO TUPI (82.741.984/0001-26)") == (
        "CLUBE ATLETICO TUPI",
        "82741984000126",
    )
    # Pessoa física: nem nome nem CPF (coleta mínima).
    assert sc.favorecido("FULANO DE TAL (123.456.789-09)") == (None, None)
    assert sc.nomes_do_autor("MARCOS JOSÉ ABREU ( MARQUITO)") == ["MARCOS JOSE ABREU", "MARQUITO"]
    assert sc.nomes_do_autor("JERRY EDSON COMPER") == ["JERRY EDSON COMPER"]


def test_normalizar_amostra_real():
    linhas = sc.normalizar(_pacote())
    assert len(linhas) == 16
    por_proposta = {x["proposta"]: x for x in linhas}
    # Valor atualizado (remanejado) vale sobre o original: 200 mil -> 800 mil.
    assert por_proposta["29581"]["valor_previsto"] == Decimal("800000.00")
    # Bancada é autor coletivo.
    assert por_proposta["34064"]["tipo"] == "bancada"
    assert por_proposta["34064"]["valor_pago"] == Decimal("2474058.30")
    # Empenhado vem do razão financeiro; sem transferência, nulo e pago zero.
    gaspar = por_proposta["31738"]
    assert (gaspar["transferencia"], gaspar["valor_empenhado"], gaspar["valor_pago"]) == (
        "2024TR002516",
        Decimal("150000.0"),
        Decimal("150000.00"),
    )
    assert por_proposta["33066"]["valor_empenhado"] is None
    assert por_proposta["33066"]["valor_pago"] == 0
    # A mesma emenda tem quatro propostas (três canceladas).
    assert sum(1 for x in linhas if x["codigo"] == "2025EP000485") == 4
    assert por_proposta["30723"]["orgao"] == "Fundação Catarinense de Esporte (FESPORTE)"


def test_carga_liga_autores_e_e_idempotente(session, base):
    for _ in range(2):  # recarga apaga e reinsere a UF
        assert sc.carregar(session, _pacote(), _ingestao(session)) == 16
    total = session.scalar(select(func.count()).select_from(EmendaEstadual))
    assert total == 16
    linhas = session.scalars(select(EmendaEstadual)).all()
    autores = {x.autor_nome: x.pessoa_id for x in linhas}
    assert autores["JERRY EDSON COMPER"] == base["pessoa_jerry"].id
    assert autores["ANA CAMPAGNOLO"] is None  # homônimos: não liga
    assert autores["BANCADA DO OESTE"] is None
    assert {x.municipio_ibge for x in linhas} == set(MUNICIPIOS)


def test_carga_aborta_com_lista_curta(session, base, monkeypatch):
    monkeypatch.setattr(sc, "MINIMO", 500)
    with pytest.raises(ValueError):
        sc.carregar(session, _pacote(), _ingestao(session))


def test_rota_municipio_gaspar(session, client, base):
    sc.carregar(session, _pacote(), _ingestao(session, "ok"))
    resposta = client.get(f"/municipios/{GASPAR}/emendas")
    assert resposta.status_code == 200
    corpo = resposta.json()
    est = corpo["estaduais"]
    # Pago: cinco emendas de 2023 e 2024 com transferência (R$ 1 milhão).
    assert est["total_pago"] == 1_000_000
    # Previsto: uma vez por emenda e sem as propostas canceladas.
    assert est["total_previsto"] == 1_685_000
    assert est["emendas"] == 9
    assert est["somado_ao_federal"] is False
    # Esfera estadual fora dos totais federais.
    assert corpo["total_geral"] == 0
    primeiro = est["por_autor"][0]
    assert (primeiro["autor_nome"], primeiro["pago"]) == ("Romildo Titon", 500_000)
    jerry = next(a for a in est["por_autor"] if a["autor_nome"] == "Jerry Edson Comper")
    assert jerry["mandato_id"] == base["jerry"].id and jerry["em_exercicio"] is True
    assert (jerry["pago"], jerry["previsto"]) == (150_000, 450_000)
    assert [a["ano"] for a in est["por_ano"]] == [2023, 2024, 2025, 2026]
    assert est["fonte_url"] == sc.PAGINA
    assert est["atualizado_em"] is not None


def test_rota_municipio_sem_fonte_estadual(session, client, base):
    # Sem carga ok da fonte, o bloco não aparece.
    sc.carregar(session, _pacote(), _ingestao(session))
    assert client.get(f"/municipios/{GASPAR}/emendas").json()["estaduais"] is None


def test_rota_deputado_estadual_com_media(session, client, base):
    sc.carregar(session, _pacote(), _ingestao(session, "ok"))
    corpo = client.get(f"/deputados-estaduais/{base['jerry'].id}/emendas").json()
    assert (corpo["total_pago"], corpo["total_previsto"], corpo["emendas"]) == (
        150_000,
        450_000,
        2,
    )
    # Média dos 3 em exercício: Jerry 150 mil, Romildo 500 mil (nome idêntico ao da Casa) e
    # uma deputada sem emenda (zero).
    assert corpo["deputados_na_media"] == 3
    assert corpo["media_casa_pago"] == pytest.approx(216_666.67)
    assert corpo["por_municipio"][0]["ibge"] == GASPAR
    romildo = client.get(f"/deputados-estaduais/{base['romildo'].id}/emendas").json()
    assert romildo["total_pago"] == 500_000
    assert client.get(f"/deputados-estaduais/{base['outra'].id}/emendas").json()["emendas"] == 0
    assert client.get("/deputados-estaduais/999999999/emendas").status_code == 404
