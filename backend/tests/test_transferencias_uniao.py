"""Transferências da União: Tesouro (FPE, FPM, IPI-Exp, outras) e Portal (Fundeb, royalties,
legais e voluntárias). Fixtures: recortes de arquivos reais (tests/fixtures/tesouro_transf e
tests/fixtures/portal_transferencias_202404.zip)."""

import gzip
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import sessionmaker

from app.models import FonteIngestao, TransferenciaUniao
from ingestion import comum
from ingestion.portal import transferencias as portal
from ingestion.tesouro import transferencias as tesouro

FIX = Path(__file__).parent / "fixtures"
TES = FIX / "tesouro_transf"
PORTAL_ZIP = FIX / "portal_transferencias_202404.zip"
# Código SIAFI -> (UF, IBGE) como na tabela oficial (tabmun.csv)
TABELA_PORTAL = {"1301": ("CE", "2300101"), "1231": ("CE", "2300150")}


def _lido(nome: str) -> str:
    return tesouro.decodificar((TES / nome).read_bytes())


def _recorte_tesouro(**trocas: str) -> bytes:
    nomes = [
        *tesouro.ARQUIVOS_ESTADUAIS,
        tesouro.ARQUIVO_CONFERENCIA,
        *tesouro.ARQUIVOS_MUNICIPAIS,
        tesouro.ARQUIVO_TABELA,
    ]
    return tesouro.montar_recorte({n: trocas.get(n, _lido(n)).encode() for n in nomes})


@pytest.fixture
def tabela_curta(monkeypatch):
    """O fixture da tabela SIAFI tem 3 linhas (a real, 5.589)."""
    monkeypatch.setattr(tesouro, "MIN_TABELA", 3)


def _ingestao(session, fonte: str) -> FonteIngestao:
    ingestao = FonteIngestao(fonte=fonte, url="x", arquivo_raw="x")
    session.add(ingestao)
    session.flush()
    return ingestao


def _linhas(session, fonte: str) -> list[TransferenciaUniao]:
    return list(
        session.scalars(
            select(TransferenciaUniao)
            .where(TransferenciaUniao.fonte == fonte)
            .order_by(
                TransferenciaUniao.ano,
                TransferenciaUniao.mes,
                TransferenciaUniao.bloco,
                TransferenciaUniao.uf,
                TransferenciaUniao.municipio_ibge,
            )
        )
    )


# --- Tesouro: leitura -------------------------------------------------------------------


def test_numero_formatos_do_tesouro():
    assert tesouro.numero(" 1.234.567,89 ") == Decimal("1234567.89")
    assert tesouro.numero(" -   ") is None
    assert tesouro.numero("") is None
    assert tesouro.numero("-1.500,00") == Decimal("-1500.00")
    assert tesouro.numero("(1,50)") == Decimal("-1.50")
    with pytest.raises(ValueError):
        tesouro.numero("#REF!")


def test_ler_estadual_arquivo_original_cabecalhos_e_ano_de_2_digitos():
    texto = _lido("original_fpe_excerto.csv")
    assert tesouro.anos_estadual(texto) == {1991, 1992, 1993}
    linhas = list(tesouro.ler_estadual(texto))
    assert {uf for uf, *_ in linhas} == {"AC", "CE"}  # só linhas de UF
    ac_jan91 = next(v for uf, a, m, v in linhas if (uf, a, m) == ("AC", 1991, 1))
    assert ac_jan91 == Decimal("1900781748.49")
    assert len(list(tesouro.ler_estadual(texto, anos={1992}))) == 2 * 12


def test_ler_municipal_mantem_zero_a_esquerda_e_pula_vazios():
    texto = _lido("original_cide_municipio_excerto.csv")
    linhas = list(tesouro.ler_municipal(texto))
    assert {c for c, *_ in linhas} == {"0643"}  # código SIAFI com zero à esquerda
    jan2005 = [v for c, n, uf, a, m, v in linhas if (a, m) == (2005, 1)]
    assert jan2005 == [Decimal("16956.70")]  # 2004 vinha como " -   " e não entra
    assert not [1 for c, n, uf, a, m, v in linhas if a == 2004 and m == 1]
    assert tesouro.anos_municipal(texto) == set(range(2004, 2011))


def test_cabecalho_inesperado_aborta():
    with pytest.raises(ValueError):
        list(tesouro.ler_municipal("A;B;C;D;E\n1;2;3;4;5\n"))
    with pytest.raises(ValueError):
        list(tesouro.ler_estadual("A;B\n1;2\n"))


def test_recorte_guarda_so_os_anos_pedidos_e_relido_igual():
    texto = _lido("original_fpe_excerto.csv")
    recorte = tesouro.recortar_estadual(texto, {1992})
    assert tesouro.anos_estadual(recorte) == {1992}
    assert list(tesouro.ler_estadual(recorte)) == list(tesouro.ler_estadual(texto, {1992}))
    municipal = _lido("original_cide_municipio_excerto.csv")
    corte = tesouro.recortar_municipal(municipal, {2005, 2006})
    assert list(tesouro.ler_municipal(corte)) == list(
        tesouro.ler_municipal(municipal, {2005, 2006})
    )


def test_recorte_zip_e_deterministico():
    assert _recorte_tesouro() == _recorte_tesouro()


def test_ler_recorte_blocos_niveis_e_ligacao_oficial(tabela_curta):
    linhas, anos, avisos = tesouro.ler_recorte(_recorte_tesouro())
    assert anos == {2024, 2025}
    blocos = {k[4] for k in linhas}
    assert blocos == {"FPE", "FPM", "IPI_EXP", "OUTRAS_OBRIG"}
    # FPE só por UF (sem município); FPM só por município
    assert all(k[3] is None for k in linhas if k[4] in ("FPE", "IPI_EXP"))
    assert all(k[3] is not None or k[2] == "MT" for k in linhas if k[4] == "FPM")
    assert len({k[2] for k in linhas if k[4] == "FPE"}) == 27
    # FPM de Fortaleza liga ao IBGE pela tabela oficial (SIAFI 1389 -> 2304400)
    fortaleza = [
        v for k, v in linhas.items() if k[3] == "2304400" and k[4] == "FPM" and k[0] == 2024
    ]
    assert len(fortaleza) == 12
    # o código fora da tabela (Boa Esperança do Norte, 1182) fica na UF, sem município, e avisa
    sem_ibge = [k for k in linhas if k[2] == "MT" and k[3] is None and k[4] == "FPM"]
    assert sem_ibge
    assert any("1182/MT" in a and "fora da tabela SIAFI x IBGE" in a for a in avisos)


def _fpm_das_ufs_igual_aos_municipios() -> str:
    """fpm.csv (por UF) montado com a soma dos municípios do fixture, no formato do Tesouro."""
    meses = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro"
    meses = (meses + " dezembro").split()
    colunas = [(a, m) for a in (24, 25) for m in range(1, 13)]
    soma: dict[tuple[str, int, int], Decimal] = {}
    for _, _, uf, ano, mes, valor in tesouro.ler_municipal(_lido("fpm-por-municipio.csv")):
        soma[(uf, ano, mes)] = soma.get((uf, ano, mes), Decimal(0)) + valor
    linhas = ["ESTADOS;UF;" + ";".join(f"{meses[m - 1]}/{a}" for a, m in colunas)]
    for uf in sorted(tesouro.UFS):
        valores = [soma.get((uf, 2000 + a, m), Decimal(0)) for a, m in colunas]
        linhas.append(f"{uf};{uf};" + ";".join(f"{v:.2f}".replace(".", ",") for v in valores))
    return "\n".join(linhas) + "\n"


def test_ler_recorte_confere_fpm_dos_municipios_com_a_uf(tabela_curta):
    # o fpm.csv real tem todas as UFs e o fixture só 3 municípios: o aviso diz a diferença
    _, _, avisos = tesouro.ler_recorte(_recorte_tesouro())
    assert any(a.startswith("FPM 2024: soma dos municípios difere") for a in avisos)
    # com o total das UFs igual à soma dos municípios, não há aviso de FPM
    _, _, avisos = tesouro.ler_recorte(
        _recorte_tesouro(**{"fpm.csv": _fpm_das_ufs_igual_aos_municipios()})
    )
    assert not [a for a in avisos if a.startswith("FPM ")]


# --- Tesouro: banco ---------------------------------------------------------------------


def test_tesouro_carregar_idempotente_corrige_e_apaga(session, tabela_curta):
    ingestao = _ingestao(session, tesouro.FONTE)
    total = tesouro.carregar(session, _recorte_tesouro(), ingestao)
    antes = _linhas(session, "tesouro")
    assert total == len(antes) > 0
    assert {r.fonte for r in antes} == {"tesouro"}
    assert ingestao.alertas and ingestao.total_fonte == total

    # carga repetida: nada muda (mesmos ids)
    ids = {r.id for r in antes}
    assert tesouro.carregar(session, _recorte_tesouro(), ingestao) == total
    assert {r.id for r in _linhas(session, "tesouro")} == ids

    # valor corrigido pela fonte: a linha é atualizada (mesmo id), não duplicada
    fpe_ce = next(
        r for r in antes if r.bloco == "FPE" and r.uf == "CE" and (r.ano, r.mes) == (2024, 1)
    )
    original = _lido("fpe.csv")
    celula = f"{fpe_ce.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    assert celula in original
    tesouro.carregar(
        session, _recorte_tesouro(**{"fpe.csv": original.replace(celula, "1,00", 1)}), ingestao
    )
    session.expire_all()
    assert session.get(TransferenciaUniao, fpe_ce.id).valor == Decimal("1.00")
    assert len(_linhas(session, "tesouro")) == total

    # linha que sumiu da fonte é apagada (aqui: FPE de CE em janeiro/2024 vazio)
    vazio = original.replace(celula, " -   ", 1)
    tesouro.carregar(session, _recorte_tesouro(**{"fpe.csv": vazio}), ingestao)
    assert len(_linhas(session, "tesouro")) == total - 1

    # FPE de 26 UFs (arquivo truncado): aborta
    sem_ce = "\n".join(linha for linha in original.splitlines() if not linha.startswith("Cear"))
    with pytest.raises(ValueError):
        tesouro.carregar(session, _recorte_tesouro(**{"fpe.csv": sem_ce}), ingestao)


def test_tesouro_nao_mexe_em_outros_anos_nem_no_portal(session, tabela_curta):
    session.add_all(
        [
            TransferenciaUniao(ano=2021, mes=5, uf="CE", bloco="FPE", fonte="tesouro",
                               valor=Decimal("7")),
            TransferenciaUniao(ano=2024, mes=4, uf="CE", bloco="ROYALTIES", fonte="portal",
                               valor=Decimal("9")),
        ]
    )  # fmt: skip
    session.flush()
    tesouro.carregar(session, _recorte_tesouro(), _ingestao(session, tesouro.FONTE))
    assert (
        session.scalar(
            select(func.count())
            .select_from(TransferenciaUniao)
            .where(TransferenciaUniao.ano == 2021)
        )
        == 1
    )
    assert len(_linhas(session, "portal")) == 1


def test_tesouro_recorte_incompleto_aborta(session, tabela_curta):
    with pytest.raises(ValueError):
        tesouro.ler_recorte(tesouro.montar_recorte({"fpe.csv": b"x"}))
    sem_tabela = tesouro.montar_recorte(
        {
            n: _lido(n).encode()
            for n in [
                *tesouro.ARQUIVOS_ESTADUAIS,
                *tesouro.ARQUIVOS_MUNICIPAIS,
                tesouro.ARQUIVO_CONFERENCIA,
            ]
        }
        | {tesouro.ARQUIVO_TABELA: b""}
    )
    with pytest.raises(ValueError):  # tabela SIAFI x IBGE truncada
        tesouro.ler_recorte(sem_tabela)


# --- Portal: leitura --------------------------------------------------------------------


def test_meses_publicados_da_pagina_do_portal():
    pagina = (
        'arquivos.push({"ano" : "2026", "mes" : "09", "dia" : "", "origem" :  "Transferencias"})\n'
        'arquivos.push({"ano" : "2026", "mes" : "10", "dia" : "", "origem" :  "Transferencias"})\n'
        'arquivos.push({"ano" : "2026", "mes" : "10", "dia" : "", "origem" :  "CPGF"})\n'
    )
    assert portal.meses_publicados(pagina) == {(2026, 9), (2026, 10)}


@pytest.mark.parametrize(
    ("tipo", "acao", "nome", "esperado"),
    [
        (
            "Constitucionais e Royalties",
            "00SB",
            "COMPLEMENTACAO DA UNIAO AO FUNDO DE MANUTENCAO",
            "FUNDEB_UNIAO",
        ),
        (
            "Constitucionais e Royalties",
            "0E36",
            "COMPLEMENTACAO DA UNIAO AO FUNDO DE MANUTENCAO",
            "FUNDEB_UNIAO",
        ),
        ("Constitucionais e Royalties", "0A53", "PETROLEO", "ROYALTIES"),
        ("Constitucionais e Royalties", "0223", "ITAIPU", "ROYALTIES"),
        ("Legais, Voluntárias e Específicas", "219E", "SUS", "LEGAIS_VOLUNTARIAS"),
        ("Constitucionais e Royalties", "0044", "FPE", None),  # vale o Tesouro
        ("Constitucionais e Royalties", "0045", "FPM", None),
        ("Constitucionais e Royalties", "0C33", "TRANSFERENCIA AO FUNDO DE MANUTENCAO", None),
        ("Constitucionais e Royalties", "-1", "Sem informação", "SEM_ACAO"),
    ],
)
def test_bloco_da_linha(tipo, acao, nome, esperado):
    assert portal.bloco_da_linha(tipo, acao, nome) == esperado


def test_recortar_mes_soma_por_uf_municipio_e_bloco():
    recorte = portal.ler_recorte(portal.recortar_mes(PORTAL_ZIP))
    por_chave = {(r["uf"], r["cod_siafi"], r["bloco"]): Decimal(r["valor"]) for r in recorte}
    # FPE, FPM e 0C33 do arquivo ficam de fora
    assert {r["bloco"] for r in recorte} == set(portal.BLOCOS)
    assert por_chave[("CE", "", "FUNDEB_UNIAO")] == Decimal(
        "57939877.92"
    )  # estadual, sem município
    assert por_chave[("CE", "1301", "FUNDEB_UNIAO")] == Decimal("364473.31")
    assert por_chave[("CE", "1301", "ROYALTIES")] == Decimal("36071.26")
    # várias ações "legais" do mesmo município somam num valor só (10.496,46 + 18.400 + 12.567)
    assert por_chave[("CE", "1301", "LEGAIS_VOLUNTARIAS")] == Decimal("41463.46")
    assert por_chave[("CE", "", "LEGAIS_VOLUNTARIAS")] == Decimal("72260.11")
    # linha sem UF entra como "ND" (não regionalizada), sem município
    assert por_chave[("ND", "", "LEGAIS_VOLUNTARIAS")] == Decimal("6420.04")
    assert {r["ano"] + r["mes"] for r in recorte} == {"202404"}


def test_recorte_do_portal_e_deterministico():
    assert portal.recortar_mes(PORTAL_ZIP) == portal.recortar_mes(PORTAL_ZIP)
    assert gzip.decompress(portal.recortar_mes(PORTAL_ZIP)).startswith(b"ano;mes;uf;")


def test_linhas_do_recorte_liga_pela_tabela_oficial_e_avisa_o_que_sobra():
    recorte = portal.ler_recorte(portal.recortar_mes(PORTAL_ZIP))
    linhas, meses, avisos = portal.linhas_do_recorte(recorte, TABELA_PORTAL)
    assert meses == {(2024, 4)}
    assert linhas[(2024, 4, "CE", "2300101", "FUNDEB_UNIAO")] == Decimal("364473.31")
    assert linhas[(2024, 4, "CE", None, "FUNDEB_UNIAO")] == Decimal("57939877.92")
    # Boa Esperança do Norte (1182) não está na tabela: fica na UF e avisa
    assert linhas[(2024, 4, "MT", None, "LEGAIS_VOLUNTARIAS")] == Decimal("5035.00")
    assert any("1182/MT" in a for a in avisos)


def test_constitucional_sem_acao_vira_aviso_e_nao_entra_no_banco():
    recorte = [
        {"ano": "2021", "mes": "03", "uf": "CE", "cod_siafi": "", "municipio": "",
         "bloco": "SEM_ACAO", "valor": "1000.00"},
        {"ano": "2021", "mes": "03", "uf": "CE", "cod_siafi": "", "municipio": "",
         "bloco": "ROYALTIES", "valor": "5.00"},
    ]  # fmt: skip
    linhas, _, avisos = portal.linhas_do_recorte(recorte, {})
    assert list(linhas) == [(2021, 3, "CE", None, "ROYALTIES")]
    assert any("2021" in a and "sem ação identificada" in a for a in avisos)


# --- Portal: banco ----------------------------------------------------------------------


def test_portal_carregar_idempotente_e_so_mexe_no_proprio_mes(session, monkeypatch):
    monkeypatch.setattr(portal, "_TABELA", dict(TABELA_PORTAL))
    session.add_all(
        [
            TransferenciaUniao(ano=2024, mes=3, uf="CE", bloco="ROYALTIES", fonte="portal",
                               valor=Decimal("3")),
            TransferenciaUniao(ano=2024, mes=4, uf="CE", bloco="FPE", fonte="tesouro",
                               valor=Decimal("4")),
        ]
    )  # fmt: skip
    session.flush()
    payload = portal.recortar_mes(PORTAL_ZIP)
    ingestao = _ingestao(session, portal.FONTE)
    total = portal.carregar(session, payload, ingestao)
    do_mes = [r for r in _linhas(session, "portal") if r.mes == 4]
    assert total == len(do_mes)
    ids = {r.id for r in do_mes}
    assert portal.carregar(session, payload, ingestao) == total
    assert {r.id for r in _linhas(session, "portal") if r.mes == 4} == ids
    # abril/2024 do Tesouro e março do Portal ficaram como estavam
    assert [r.valor for r in _linhas(session, "tesouro")] == [Decimal("4")]
    assert [r.valor for r in _linhas(session, "portal") if r.mes == 3] == [Decimal("3")]
    assert {r.bloco for r in do_mes} <= set(portal.BLOCOS)
    assert {r.uf for r in do_mes} == {"CE", "MT", "ND"}
    assert not [r for r in do_mes if r.municipio_ibge and r.uf != "CE"]


def test_portal_recorte_vazio_aborta(session, monkeypatch):
    monkeypatch.setattr(portal, "_TABELA", dict(TABELA_PORTAL))
    vazio = gzip.compress(b"ano;mes;uf;cod_siafi;municipio;bloco;valor\n")
    with pytest.raises(ValueError):
        portal.carregar(session, vazio, _ingestao(session, portal.FONTE))


# --- Portal: download e bloqueio --------------------------------------------------------


@pytest.fixture
def ambiente(engine, tmp_path, monkeypatch):
    fabrica = sessionmaker(bind=engine)
    for modulo in (comum, portal):
        monkeypatch.setattr(modulo, "SessionLocal", fabrica)
    monkeypatch.setattr(comum, "RAW_DIR", tmp_path)
    monkeypatch.setattr(comum, "forcar", False)
    monkeypatch.setattr(comum.time, "sleep", lambda _: None)
    monkeypatch.setattr(portal, "_TABELA", dict(TABELA_PORTAL))
    yield fabrica
    with fabrica() as s:
        s.execute(delete(TransferenciaUniao).where(TransferenciaUniao.fonte == "portal"))
        s.execute(delete(FonteIngestao).where(FonteIngestao.fonte == portal.FONTE))
        s.commit()


@respx.mock
def test_mes_com_403_ou_405_para_a_carga_e_registra_erro(ambiente):
    for status in (403, 405):
        respx.get(portal.URL.format(ano=2024, mes=4)).mock(return_value=httpx.Response(status))
        with pytest.raises(portal.Bloqueio):
            portal.executar_mes(2024, 4)
    with ambiente() as s:
        status = s.scalars(
            select(FonteIngestao.status).where(FonteIngestao.fonte == portal.FONTE)
        ).all()
    assert status == ["erro", "erro"]


@respx.mock
def test_resposta_que_nao_e_zip_e_bloqueio(ambiente):
    respx.get(portal.URL.format(ano=2024, mes=4)).mock(
        return_value=httpx.Response(200, content=b"<html>Human Verification</html>")
    )
    with pytest.raises(portal.Bloqueio):
        portal.executar_mes(2024, 4)


@respx.mock
def test_executar_pula_mes_nao_publicado_para_no_bloqueio_e_nao_repete(ambiente):
    pagina = "\n".join(
        f'arquivos.push({{"ano" : "2024", "mes" : "{m:02d}", "dia" : "", '
        f'"origem" :  "Transferencias"}})'
        for m in (4, 5)
    )
    respx.get(portal.PAGINA).mock(return_value=httpx.Response(200, text=pagina))
    zip_abril = PORTAL_ZIP.read_bytes()
    abril = respx.get(portal.URL.format(ano=2024, mes=4)).mock(
        return_value=httpx.Response(200, content=zip_abril)
    )
    maio = respx.get(portal.URL.format(ano=2024, mes=5)).mock(return_value=httpx.Response(405))
    junho = respx.get(portal.URL.format(ano=2024, mes=6)).mock(return_value=httpx.Response(405))
    with pytest.raises(portal.Bloqueio):
        portal.executar(anos=[2024], meses=[4, 5, 6], pausa=0)
    assert abril.call_count == 1 and maio.call_count == 1
    assert junho.call_count == 0  # junho não está publicado: nem foi pedido
    with ambiente() as s:
        assert s.scalar(select(func.count()).select_from(TransferenciaUniao)) > 0
        assert s.scalars(
            select(FonteIngestao.status)
            .where(FonteIngestao.fonte == portal.FONTE)
            .order_by(FonteIngestao.id)
        ).all() == ["ok", "erro"]


@respx.mock
def test_mes_antigo_ja_carregado_nao_e_baixado_de_novo(ambiente):
    respx.get(portal.PAGINA).mock(
        return_value=httpx.Response(
            200,
            text="".join(
                f'arquivos.push({{"ano" : "2024", "mes" : "{m:02d}", "dia" : "", '
                f'"origem" :  "Transferencias"}})\n'
                for m in range(1, 13)
            ),
        )
    )
    rota = respx.get(portal.URL.format(ano=2024, mes=4)).mock(
        return_value=httpx.Response(200, content=PORTAL_ZIP.read_bytes())
    )
    portal.executar(anos=[2024], meses=[4], pausa=0)
    assert rota.call_count == 1
    # abril não está entre os 3 últimos publicados (out-dez): segunda vez não baixa
    portal.executar(anos=[2024], meses=[4], pausa=0)
    assert rota.call_count == 1
    portal.executar(anos=[2024], meses=[4], pausa=0, refazer=True)
    assert rota.call_count == 2
