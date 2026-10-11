import json
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import (
    PncpAnual,
    PncpContrato,
    PncpDia,
    PncpJanela,
    PncpOrgao,
    PncpSoma,
    PncpSuspeito,
    SancaoEmpresa,
)
from ingestion.pncp import anual, contratos, pacote

HOJE = date(2026, 10, 10)  # corte da janela: 2026-09-30
CNPJ_A, CNPJ_B = "11111111000111", "22222222000122"
IBGE = "4202008"


def _dia(dia, **kw):
    return PncpDia(dia=dia, total_api=3, lidos=3, receitas=0, empenhos=0, pessoas_fisicas=1,
                   linhas_alvo=0, lido_em=datetime(2026, 10, 9, tzinfo=UTC), **kw)  # fmt: skip


def _soma(dia, orgao, ibge, pessoa, forn, q, v, tipo="Contrato"):
    return PncpSoma(dia=dia, orgao_cnpj=orgao, municipio_ibge=ibge, tipo_pessoa=pessoa,
                    fornecedor_cnpj=forn, tipo_contrato=tipo, quantidade=q,
                    valor_global=Decimal(v))  # fmt: skip


def _contrato(numero, cnpj, publicado, objeto="Merenda"):
    return PncpContrato(numero_controle=numero, orgao_cnpj="83551549000100", fornecedor_cnpj=cnpj,
                        fornecedor_nome="EMPRESA X 123.456.789-09", tipo_contrato="Contrato",
                        objeto=objeto, valor_global=Decimal("10.50"), publicado_em=publicado,
                        atualizado_em=datetime(2026, 1, 2, 3, 4))  # fmt: skip


@pytest.fixture
def acervo(session):
    session.add_all([
        PncpOrgao(cnpj="1" * 14, nome="Prefeitura", esfera="M"),
        PncpOrgao(cnpj="2" * 14, nome="Ministério", esfera="F"),
        SancaoEmpresa(cadastro="CEIS", codigo="1", cnpj=CNPJ_A, nome="EMPRESA A", categoria="x"),
        _dia(date(2024, 12, 31)), _dia(date(2025, 1, 1)), _dia(date(2026, 9, 29)),
        _dia(date(2026, 9, 30)), _dia(date(2026, 10, 9)),
        # compactados (antes de 30/09): município, só PJ, só esfera M
        _soma(date(2025, 1, 1), "1" * 14, IBGE, "PJ", CNPJ_A, 2, "100"),
        _soma(date(2026, 9, 29), "1" * 14, IBGE, "PJ", CNPJ_A, 1, "50"),
        _soma(date(2026, 9, 29), "1" * 14, IBGE, "PJ", CNPJ_B, 4, "70"),
        _soma(date(2026, 9, 29), "2" * 14, IBGE, "PJ", CNPJ_B, 9, "999"),  # federal: fora
        _soma(date(2026, 9, 29), "1" * 14, IBGE, "PF", "", 5, "888"),  # PF: fora
        _soma(date(2024, 12, 31), "1" * 14, IBGE, "PJ", CNPJ_B, 7, "777"),  # antes do recorte
        # janela
        _soma(date(2026, 9, 30), "1" * 14, IBGE, "PJ", CNPJ_A, 1, "5"),
        _soma(date(2026, 10, 9), "1" * 14, IBGE, "PJ", CNPJ_B, 2, "6"),
        _contrato("A-1", CNPJ_A, date(2025, 3, 1)),
        _contrato("A-0", CNPJ_A, date(2024, 3, 1)),  # antes do recorte
        _contrato("B-1", CNPJ_B, date(2025, 3, 1)),  # não é alvo
    ])  # fmt: skip
    session.flush()
    return session


def test_montar_reproduz_o_recorte_da_producao(acervo):
    t = pacote.montar(acervo, HOJE)
    assert [
        (x["ano"], x["fornecedor_cnpj"], x["quantidade"], x["valor_global"])
        for x in t["pncp_anual"]
    ] == [
        (2025, CNPJ_A, 2, Decimal("100.00")),
        (2026, CNPJ_A, 1, Decimal("50.00")),
        (2026, CNPJ_B, 4, Decimal("70.00")),
    ]
    assert t["pncp_anual"][0]["fornecedor_nome"] == "EMPRESA X"  # nome do PNCP vence, sem o CPF
    assert {(x["dia"], x["compactado"]) for x in t["pncp_dia"]} == {
        (date(2025, 1, 1), True),
        (date(2026, 9, 29), True),
        (date(2026, 9, 30), False),
        (date(2026, 10, 9), False),
    }
    assert [(x["dia"], x["fornecedor_cnpj"]) for x in t["pncp_janela"]] == [
        (date(2026, 9, 30), CNPJ_A),
        (date(2026, 10, 9), CNPJ_B),
    ]
    assert [c["numero_controle"] for c in t["pncp_contrato"]] == ["A-1"]


def test_so_os_maiores_por_municipio(acervo):
    for i in range(35):
        acervo.add(_soma(date(2026, 9, 29), "1" * 14, "4205407", "PJ", f"{i:014d}", 1, i + 1))
    acervo.flush()
    t = pacote.montar(acervo, HOJE)
    do_municipio = [x for x in t["pncp_anual"] if x["municipio_ibge"] == "4205407"]
    assert len(do_municipio) == anual.MAIORES_POR_MUNICIPIO
    assert min(x["valor_global"] for x in do_municipio) == Decimal("6.00")


def test_sem_cpf_no_pacote(acervo, tmp_path):
    destino = tmp_path / "p.zip"
    m = pacote.gerar(acervo, destino, HOJE)
    with zipfile.ZipFile(destino) as z:
        texto = b"".join(z.read(n) for n in z.namelist()).decode()
    assert not pacote.CPF.search(texto)
    assert "123.456.789-09" not in texto
    assert m["tabelas"]["pncp_contrato"]["linhas"] == 1
    # a varredura barra o que escapar
    assert pacote.varrer_cpf({"t": [{"nome": "FULANO 123.456.789-09"}]}) == ["t.nome"]
    assert pacote.varrer_cpf({"t": [{"cnpj": CNPJ_A, "n": "83551549000100-2-000223/2025"}]}) == []


def _estado(session):
    return {
        "anual": sorted(
            session.execute(
                select(
                    PncpAnual.ano, PncpAnual.municipio_ibge, PncpAnual.fornecedor_cnpj,
                    PncpAnual.quantidade, PncpAnual.valor_global,
                )
            ).all()
        ),
        "janela": sorted(
            session.execute(
                select(PncpJanela.dia, PncpJanela.fornecedor_cnpj, PncpJanela.valor_global)
            ).all()
        ),
        "dia": sorted(session.execute(select(PncpDia.dia, PncpDia.compactado)).all()),
        "contrato": session.scalar(select(func.count()).select_from(PncpContrato)),
    }  # fmt: skip


def _producao(session, tmp_path):
    """Gera o pacote do acervo e esvazia as tabelas (uma produção ainda sem a carga)."""
    destino = tmp_path / "p.zip"
    pacote.gerar(session, destino, HOJE)
    for modelo in (PncpSoma, PncpAnual, PncpJanela, PncpDia, PncpContrato, PncpSuspeito):
        session.query(modelo).delete()
    session.flush()
    return pacote.ler(destino, destino.with_suffix(".manifesto.json"))


def test_carregar_e_idempotente(acervo, tmp_path):
    manifesto, tabelas = _producao(acervo, tmp_path)
    pacote.carregar(acervo, manifesto, tabelas)
    primeiro = _estado(acervo)
    assert len(primeiro["anual"]) == 3 and len(primeiro["janela"]) == 2
    assert primeiro["contrato"] == 1
    pacote.carregar(acervo, manifesto, tabelas)
    assert _estado(acervo) == primeiro
    assert acervo.get(PncpDia, date(2026, 9, 29)).compactado is True
    assert acervo.get(PncpDia, date(2026, 9, 30)).compactado is False


def test_diario_depois_do_pacote_nao_soma_duas_vezes(acervo, tmp_path):
    manifesto, tabelas = _producao(acervo, tmp_path)
    pacote.carregar(acervo, manifesto, tabelas)
    antes = _estado(acervo)["anual"]
    # o diário relê um dia já compactado: nada muda na soma anual nem na janela
    d = contratos.Dia(dia=date(2026, 9, 29), total_api=1, lidos=1)
    d.municipais[(IBGE, CNPJ_A)] = [9, Decimal("9999"), "X"]
    contratos.gravar_dia_producao(acervo, d)
    assert _estado(acervo)["anual"] == antes
    assert not acervo.scalars(select(PncpJanela).where(PncpJanela.dia == date(2026, 9, 29))).all()
    # compactar no mesmo dia do pacote: nenhum dia novo a somar
    assert anual.compactar(acervo, HOJE) == 0 and _estado(acervo)["anual"] == antes
    # onze dias depois, 30/09 e 09/10 saem da janela e entram uma única vez
    assert anual.compactar(acervo, date(2026, 10, 21)) == 2
    soma = {(x.ano, x.fornecedor_cnpj): x.valor_global for x in acervo.scalars(select(PncpAnual))}
    assert soma[(2026, CNPJ_A)] == Decimal("55.00") and soma[(2026, CNPJ_B)] == Decimal("76.00")
    assert anual.compactar(acervo, date(2026, 10, 21)) == 0


def test_recusa_pacote_se_o_diario_ja_somou_dia_posterior(acervo, tmp_path):
    manifesto, tabelas = _producao(acervo, tmp_path)
    pacote.carregar(acervo, manifesto, tabelas)
    acervo.add(_dia(date(2026, 10, 12), compactado=True))
    acervo.flush()
    with pytest.raises(pacote.PacoteInvalido):
        pacote.carregar(acervo, manifesto, tabelas)
    pacote.carregar(acervo, manifesto, tabelas, forcar=True)


def test_arquivo_adulterado_e_recusado(acervo, tmp_path):
    destino = tmp_path / "p.zip"
    pacote.gerar(acervo, destino, HOJE)
    externo = destino.with_suffix(".manifesto.json")
    dados = json.loads(externo.read_text())
    dados["arquivo_sha256"] = "0" * 64
    externo.write_text(json.dumps(dados))
    with pytest.raises(pacote.PacoteInvalido):
        pacote.ler(destino, externo)
