"""Destino das emendas (app/services/destino_emendas.py): os ramos que a rota em
test_transferegov.py não exercita (convênio de duas emendas contado uma vez, recorte da
legislatura, só emendas individuais, relatórios de gestão e a data da fonte mais antiga)."""

from datetime import UTC, datetime
from decimal import Decimal

from app.models import Emenda, EmendaTransferencia, FonteIngestao, Parlamentar
from app.services import destino_emendas


def _parlamentar(session, ext="1"):
    p = Parlamentar(
        casa="camara", id_externo=ext, nome_parlamentar=f"P{ext}", uf="AC",
        fonte_url="https://x", atualizado_em=datetime(2026, 1, 1, tzinfo=UTC),
    )  # fmt: skip
    session.add(p)
    session.flush()
    return p


def _emenda(session, p, codigo, ano=2024, individual=True):
    session.add(Emenda(
        codigo=codigo, ano=ano, tipo="Emenda Individual" if individual else "Emenda de Bancada",
        individual=individual, autor_codigo="1", autor_nome="X", parlamentar_id=p.id,
        localidade="AC", valor_empenhado=1, valor_pago=1,
    ))  # fmt: skip


def _transf(session, tipo, ident, emenda, valor, situacao="Em execução", relatorio=None):
    session.add(EmendaTransferencia(
        tipo=tipo, emenda_codigo=emenda, ano_emenda=2024, identificador=ident,
        situacao=situacao, relatorio_gestao=relatorio, valor_total=Decimal(valor),
        valor_repassado=Decimal(valor) / 2,
    ))  # fmt: skip


def _carga(session, fonte, quando, status="ok"):
    session.add(FonteIngestao(
        fonte=fonte, url="https://x", arquivo_raw="x", status=status, concluido_em=quando,
    ))  # fmt: skip


def test_sem_transferencia_devolve_none(session):
    p = _parlamentar(session)
    _emenda(session, p, "E1")
    session.flush()
    assert destino_emendas.resumo(session, p) is None


def test_conta_uma_vez_recorta_legislatura_e_so_individual(session):
    p = _parlamentar(session)
    _emenda(session, p, "E1")
    _emenda(session, p, "E2")
    _emenda(session, p, "BANCADA", individual=False)
    _emenda(session, p, "ANTIGA", ano=2022)
    # O mesmo convênio nasce de duas emendas do parlamentar: conta uma vez.
    _transf(session, "convenio", "C1", "E1", 1000, situacao="Concluído")
    _transf(session, "convenio", "C1", "E2", 1000, situacao="Concluído")
    _transf(session, "especial", "P1", "E1", 300, situacao="Ciente", relatorio="Enviado")
    _transf(session, "especial", "P2", "E2", 200, situacao="Ciente", relatorio=None)
    _transf(session, "especial", "P3", "E2", 100, situacao="Ciente", relatorio="Enviado")
    _transf(session, "convenio", "C9", "BANCADA", 9_000_000)  # não individual
    _transf(session, "convenio", "C8", "ANTIGA", 8_000_000)  # antes da legislatura
    _carga(session, "transferegov_convenios", datetime(2026, 9, 10, tzinfo=UTC))
    _carga(session, "transferegov_especiais", datetime(2026, 9, 1, tzinfo=UTC))
    _carga(session, "transferegov_especiais", datetime(2026, 10, 1, tzinfo=UTC), status="erro")
    session.flush()

    r = destino_emendas.resumo(session, p)
    assert r["desde"] == 2023
    assert r["quantidade"] == 4  # C1, P1, P2, P3
    assert r["valor_total"] == Decimal("1600.00")
    assert r["valor_repassado"] == Decimal("800.00")
    assert {(s["tipo"], s["situacao"]): s["quantidade"] for s in r["por_situacao"]} == {
        ("convenio", "Concluído"): 1,
        ("especial", "Ciente"): 3,
    }
    # Relatório de gestão só das transferências especiais, mais frequente primeiro.
    assert r["relatorios_de_gestao"] == [
        {"situacao": "Enviado", "quantidade": 2},
        {"situacao": None, "quantidade": 1},
    ]
    identificadores = {i["identificador"] for i in r["itens"]}
    assert "C9" not in identificadores and "C8" not in identificadores
    links = {i["identificador"]: i["fonte_url"] for i in r["itens"]}
    assert links["C1"] == destino_emendas.LINK_CONVENIO
    assert links["P1"].endswith("codigo_plano_acao=eq.P1")
    # Com duas fontes, vale a data da que está mais desatualizada (a carga com erro não conta).
    assert r["atualizado_em"] == datetime(2026, 9, 1, tzinfo=UTC)


def test_sem_carga_registrada_data_fica_vazia(session):
    p = _parlamentar(session)
    _emenda(session, p, "E1")
    _transf(session, "especial", "P1", "E1", 10)
    session.flush()
    assert destino_emendas.resumo(session, p)["atualizado_em"] is None
