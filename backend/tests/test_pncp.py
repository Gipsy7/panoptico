from datetime import date
from decimal import Decimal

import httpx
import respx
from sqlalchemy import func, select

from app.models import PncpContrato, PncpDia, PncpOrgao, PncpSoma
from ingestion.pncp import contratos
from tests.conftest import carregar_fixture

# Amostra real da API (contratos publicados em 01/10/2025), com os CPFs trocados:
# 8 contratos de tipos e fornecedores diferentes. Fornecedor MEI: o CPF vinha na razão social.
AMOSTRA = carregar_fixture("pncp_contratos_dia.json")
MEI = "28419096000146"  # MEI da amostra
DIA = date(2025, 10, 1)


def _dia(alvo: set[str]) -> contratos.Dia:
    d = contratos.Dia(DIA)
    contratos.somar(d, AMOSTRA["data"], alvo)
    return d


def test_sem_cpf_tira_so_cpf():
    assert contratos.sem_cpf("JOSE DA SILVA 12345678901") == "JOSE DA SILVA"
    assert contratos.sem_cpf("JOSE 123.456.789-01 ME") == "JOSE ME"
    # CNPJ e números longos não são tocados
    assert contratos.sem_cpf("EMPRESA 12345678000195") == "EMPRESA 12345678000195"
    assert contratos.sem_cpf(None) is None


def test_fornecedor_so_tem_cnpj_para_pj():
    assert contratos.fornecedor_de({"tipoPessoa": "PJ", "niFornecedor": "55420878000178"}) == (
        "PJ",
        "55420878000178",
    )
    # pessoa física: o CPF nunca sai daqui
    assert contratos.fornecedor_de({"tipoPessoa": "PF", "niFornecedor": "11111111102"}) == (
        "PF",
        "",
    )
    assert contratos.fornecedor_de({"tipoPessoa": "PE", "niFornecedor": "x"}) == ("PE", "")
    assert contratos.fornecedor_de({"tipoPessoa": "PJ", "niFornecedor": "123"}) == ("PJ", "")
    assert contratos.fornecedor_de({}) == ("XX", "")


def test_somas_excluem_receita_separam_empenho_e_anonimizam_pf():
    d = _dia(alvo=set())
    assert d.lidos == 8
    assert d.receitas == 1  # a alienação (receita=true) fica fora
    assert d.empenhos == 2
    assert d.pessoas_fisicas == 2
    assert sum(q for q, _ in d.somas.values()) == 7  # 8 lidos - 1 receita
    assert not d.alvo  # sem conjunto-alvo, nenhuma linha inteira
    # nenhuma chave de soma carrega CPF: pessoa física e estrangeiro têm fornecedor vazio
    assert all(k[3] == "" for k in d.somas if k[2] != "PJ")
    assert not any(k[3].startswith("1111111") for k in d.somas)
    assert {k[4] for k in d.somas} == {"Outros", "Contrato (termo inicial)", "Empenho"}
    empenho = d.somas[("42498600000171", "3304557", "PJ", "12499494000180", "Empenho")]
    assert empenho == [1, Decimal("366540.00")]
    assert len(d.orgaos) == 6  # a alienação não registra órgão; o Ceará aparece duas vezes
    assert d.orgaos["03222337000131"]["esfera"] == "N"  # consórcio: esfera N existe


def test_linha_inteira_so_do_conjunto_alvo_e_sem_cpf_no_nome():
    d = _dia(alvo={MEI, "97518975000148"})
    # o contrato do MEI entra; o de receita=true do outro alvo também (guarda a flag)
    assert set(d.alvo) == {"07954480000179-2-026131/2025", "00394460005887-2-004690/2025"}
    mei = d.alvo["07954480000179-2-026131/2025"]
    assert mei["fornecedor_cnpj"] == MEI
    assert "11111111111" not in (mei["fornecedor_nome"] or "")
    assert mei["valor_global"] == Decimal("990.00")
    assert mei["publicado_em"] == DIA
    assert d.alvo["00394460005887-2-004690/2025"]["receita"] is True


def _pagina(numero: int, total: int, paginas: int, data: list) -> dict:
    return {
        "data": data,
        "totalRegistros": total,
        "totalPaginas": paginas,
        "numeroPagina": numero,
        "paginasRestantes": paginas - numero,
        "empty": not data,
    }


@respx.mock
def test_ler_dia_percorre_paginas_e_conta_repetidos_uma_vez():
    contratos_ = AMOSTRA["data"]
    rota = respx.get(contratos.URL).mock(
        side_effect=[
            httpx.Response(200, json=_pagina(1, 8, 2, contratos_[:5])),
            # a lista andou entre as requisições: o 5º volta na página 2
            httpx.Response(200, json=_pagina(2, 8, 2, contratos_[4:])),
        ]
    )
    with httpx.Client() as client:
        d = contratos.ler_dia(client, DIA, set(), pausa=0)
    assert rota.call_count == 2
    primeira = rota.calls[0].request.url.params
    assert primeira["dataInicial"] == primeira["dataFinal"] == "20251001"
    assert primeira["tamanhoPagina"] == "500" and primeira["pagina"] == "1"
    assert (d.total_api, d.lidos, d.repetidos, d.paginas) == (8, 8, 1, 2)


@respx.mock
def test_ler_dia_sem_contratos_responde_204():
    respx.get(contratos.URL).mock(return_value=httpx.Response(204))
    with httpx.Client() as client:
        d = contratos.ler_dia(client, DIA, set(), pausa=0)
    assert (d.total_api, d.lidos, d.paginas) == (0, 0, 1)


@respx.mock
def test_tenta_de_novo_no_5xx(monkeypatch):
    monkeypatch.setattr("ingestion.comum.time.sleep", lambda s: None)
    respx.get(contratos.URL).mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(200, json=_pagina(1, 1, 1, AMOSTRA["data"][:1])),
        ]
    )
    with httpx.Client() as client:
        d = contratos.ler_dia(client, DIA, set(), pausa=0)
    assert d.lidos == 1


@respx.mock
def test_atualizacao_devolve_dias_de_publicacao_e_linhas_alvo():
    respx.get(contratos.URL_ATUALIZACAO).mock(
        return_value=httpx.Response(200, json=_pagina(1, 8, 1, AMOSTRA["data"]))
    )
    with httpx.Client() as client:
        publicados, linhas = contratos.ler_atualizacoes(client, DIA, {MEI}, pausa=0)
    assert publicados == {DIA}
    assert list(linhas) == ["07954480000179-2-026131/2025"]


def test_gravar_dia_e_idempotente_e_troca_o_dia(session):
    d = _dia(alvo={MEI})
    contratos.gravar_dia(session, d)
    contratos.gravar_dia(session, d)  # reler o dia não soma duas vezes
    assert session.scalar(select(func.sum(PncpSoma.quantidade))) == 7
    assert session.scalar(select(func.count()).select_from(PncpContrato)) == 1
    assert session.scalar(select(func.count()).select_from(PncpOrgao)) == 6
    dia = session.get(PncpDia, DIA)
    assert (dia.total_api, dia.lidos, dia.receitas, dia.empenhos, dia.linhas_alvo) == (
        0,
        8,
        1,
        2,
        1,
    )
    # nenhum CPF no banco: pessoa física fica com fornecedor vazio
    assert not session.scalars(
        select(PncpSoma).where(PncpSoma.fornecedor_cnpj.like("1111111%"))
    ).all()
    # aditivo: o valor do mesmo contrato muda; o dia relido troca as somas
    aditado = [dict(c) for c in AMOSTRA["data"]]
    aditado[3]["valorGlobal"] = 5000.0
    d2 = contratos.Dia(DIA, total_api=8)
    contratos.somar(d2, aditado, {MEI})
    contratos.gravar_dia(session, d2)
    assert session.scalar(select(PncpContrato.valor_global)) == Decimal("5000.00")
    assert session.scalar(select(func.count()).select_from(PncpDia)) == 1
    assert session.get(PncpDia, DIA).total_api == 8


def test_planejar_janela():
    hoje = date(2026, 10, 9)
    # primeira carga: janela inicial até hoje
    assert contratos.planejar(None, None, set(), hoje, 7) == (date(2023, 1, 1), hoje, False)
    completos = set(contratos.dias_da_janela(date(2023, 1, 1), date(2026, 10, 5)))
    # incremental: reler os últimos 7 dias a partir do cursor
    assert contratos.planejar(None, None, completos, hoje, 7) == (date(2026, 9, 29), hoje, True)
    # só uma semana de teste carregada: começa do primeiro dia que falta, sem incremental
    semana = set(contratos.dias_da_janela(date(2025, 10, 1), date(2025, 10, 7)))
    assert contratos.planejar(None, None, semana, hoje, 7) == (date(2023, 1, 1), hoje, False)
    buraco = completos - {date(2024, 3, 2)}
    assert contratos.planejar(None, None, buraco, hoje, 7) == (date(2024, 3, 2), hoje, False)
    # carga parcial explícita
    assert contratos.planejar(date(2025, 10, 1), date(2025, 10, 7), completos, hoje, 7) == (
        date(2025, 10, 1),
        date(2025, 10, 7),
        False,
    )
