import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx

from ingestion.assembleias import alrn

FIXTURES = Path(__file__).parent / "fixtures"
# Recortes reais da página "Verbas de ressarcimento" da ALRN (20/10/2026).
FORMULARIO = (FIXTURES / "alrn_verbas_formulario.html").read_text(encoding="utf-8")
BUSCA = (FIXTURES / "alrn_verbas_busca.html").read_text(encoding="utf-8")


def test_seletor_de_deputados_inclui_ex_deputados():
    assert alrn.seletor_de_deputados(FORMULARIO) == [
        ("109", "Albert Dickson"),
        ("111", "Cristiane Dantas"),
        ("110", "Galeno Torquato"),
        ("87", "Raimundo Fernandes"),
    ]


def test_notas_da_busca_so_data_e_valor_sem_fornecedor():
    notas = alrn.notas_da_busca(BUSCA)
    assert len(notas) == 6
    assert notas[0] == {"data": date(2023, 1, 31), "valor": Decimal("3500.00")}
    assert notas[-1] == {"data": date(2019, 10, 30), "valor": Decimal("0.01")}  # ".01" na fonte
    assert all(set(n) == {"data", "valor"} for n in notas)  # fornecedor (pode ser pessoa) fora


def test_soma_por_mes_do_ano_pedido_em_diante_e_notas_sem_data_vao_a_parte():
    notas = alrn.notas_da_busca(BUSCA)
    gastos, fora = alrn.somar_notas(notas, 2023)
    assert gastos == [
        {
            "ano": 2023,
            "mes": 1,
            "categoria": alrn.CATEGORIA_VERBAS,
            "valor": Decimal("25309.19"),  # 3.500 + 4.009,19 + 7.500 + 6.800 + 3.500
        }
    ]
    assert fora == []  # a nota de 2019 é anterior ao recorte, não é "fora da soma"
    gastos, fora = alrn.somar_notas(
        [{"data": None, "valor": Decimal("10.00")}, {"data": date(2026, 3, 1), "valor": None}], 2025
    )
    assert gastos == []
    assert [(f["ano"], f["linhas"], f["valor"], f["linhas_valor_ilegivel"]) for f in fora] == [
        (2025, 1, Decimal("10.00"), 0),
        (2026, 1, Decimal("0"), 1),
    ]


def test_nota_com_data_no_futuro_vai_para_fora_da_soma():
    # a fonte tem uma nota de 25/09/2029 (erro de digitação): não vira gasto de 2029
    notas = [
        {"data": date(2029, 9, 25), "valor": Decimal("1520.00")},
        {"data": date(2026, 9, 25), "valor": Decimal("100.00")},
    ]
    gastos, fora = alrn.somar_notas(notas, 2025, date(2026, 10, 20))
    assert [(g["ano"], g["mes"], g["valor"]) for g in gastos] == [(2026, 9, Decimal("100.00"))]
    assert [(f["ano"], f["linhas"], f["valor"]) for f in fora] == [(2026, 1, Decimal("1520.00"))]
    assert "futuro" in fora[0]["motivo"]


def test_notas_com_data_impossivel_ficam_sem_data():
    html = BUSCA.replace("31/01/2023", "31/02/2023", 1)
    assert alrn.notas_da_busca(html)[0]["data"] is None


def test_verbas_sem_nenhuma_nota_abortam(tmp_path):
    pacote = tmp_path / "verbas.zip"
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("formulario.html", FORMULARIO)
        z.writestr("87.html", "<html>Não foram encontradas verbas</html>")
    lista = [{"id": "1", "nome": "Raimundo Fernandes"}]
    with pytest.raises(ValueError, match="nenhuma nota"):
        alrn.gastos_dos_deputados(None, lista, [], 2025, pacote)


def test_de_raw_liga_por_nome_exato_e_avisa_quem_ficou_sem_busca(tmp_path):
    pacote = tmp_path / "verbas.zip"
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("formulario.html", FORMULARIO)
        z.writestr("87.html", BUSCA)
    lista = [{"id": "7", "nome": "Raimundo Fernandes"}, {"id": "8", "nome": "Outro Deputado"}]
    gastos, avisos = alrn.gastos_dos_deputados(None, lista, [], 2023, pacote)
    assert list(gastos) == ["7"] and gastos["7"][0][0]["valor"] == Decimal("25309.19")
    assert "3 nomes" in avisos[0] and "Albert Dickson" in avisos[0]


@respx.mock
def test_baixar_verbas_usa_o_token_do_formulario_e_busca_sem_mes(monkeypatch):
    monkeypatch.setattr(alrn, "PAUSA", 0)
    chamadas = []

    def busca(request):
        chamadas.append(request.content.decode())
        return httpx.Response(200, content=BUSCA.encode("utf-8"))

    respx.post(alrn.VERBAS + "/busca").side_effect = busca
    with httpx.Client() as client:
        arquivos = alrn.baixar_verbas(client, FORMULARIO, ["87"])
    assert (
        "_token=" in chamadas[0] and "mes_id=&" in chamadas[0] and "deputado_id=87" in chamadas[0]
    )
    assert sorted(arquivos) == ["87.html", "formulario.html"]
    with pytest.raises(ValueError, match="_token"):
        with httpx.Client() as client:
            alrn.baixar_verbas(client, "<html></html>", ["87"])


def test_fonte_de_verbas_fora_do_ar_mantem_os_gastos_anteriores(session, monkeypatch):
    from contextlib import contextmanager
    from datetime import date
    from decimal import Decimal

    import httpx

    from app.models import GastoLocal, MandatoLocal

    mandato = MandatoLocal(
        casa="assembleia", uf="RN", id_externo="42", nome="Fulana", sapl_url="https://x"
    )
    session.add(mandato)
    session.flush()
    session.add(
        GastoLocal(
            mandato_id=mandato.id, ano=2026, mes=3, categoria="Verba", valor=Decimal("100.50")
        )
    )
    session.flush()

    @contextmanager
    def sessao():
        yield session

    def falha(*a, **k):
        resposta = httpx.Response(404, request=httpx.Request("GET", "https://x"))
        raise httpx.HTTPStatusError("404", request=resposta.request, response=resposta)

    monkeypatch.setattr(alrn, "SessionLocal", sessao)
    monkeypatch.setattr(alrn, "gastos_dos_deputados", falha)
    gastos, avisos = alrn.gastos_ou_anteriores(None, [], [], date(2026, 10, 27), None)
    assert gastos["42"][0] == [
        {"ano": 2026, "mes": 3, "categoria": "Verba", "valor": Decimal("100.50")}
    ]
    assert len(avisos) == 1 and "mantidos os gastos da carga anterior" in avisos[0]
