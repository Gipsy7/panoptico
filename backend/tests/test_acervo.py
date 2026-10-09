import importlib
from datetime import UTC, date, datetime, timedelta

import pytest

from ingestion import acervo
from ingestion.acervo import Fonte


@pytest.fixture(autouse=True)
def _historico_temporario(monkeypatch, tmp_path):
    monkeypatch.setattr(acervo, "HISTORICO", tmp_path / "historico.json")


def test_registro_valido_e_nomes_iguais_aos_dos_modulos():
    fontes = acervo.ler_registro()
    for f in fontes:
        if f.situacao != "ativa":  # catalogada: o módulo pode ainda não existir
            continue
        modulo = importlib.import_module(f.modulo)
        assert hasattr(modulo, "executar"), f.modulo
        # O nome é a chave em fonte_ingestao: diferente do FONTE, a fonte nunca sairia de "vencida".
        assert getattr(modulo, "FONTE", f.nome) == f.nome, f.modulo
    assert acervo.ordenar(fontes, {f.nome for f in fontes})  # sem dependência circular


def test_registro_recusa_erros(tmp_path):
    arquivo = tmp_path / "fontes.toml"

    def registro(*campos):
        linhas = ["[[fonte]]", "nome = 'a'", "modulo = 'm'", *campos]
        arquivo.write_text("\n".join(linhas) + "\n")
        return acervo.ler_registro(arquivo)

    with pytest.raises(ValueError, match="fora do registro"):
        registro("uso = 'x'", "frequencia = 'diaria'", "depende = ['b']")
    with pytest.raises(ValueError, match="frequência"):
        registro("uso = 'x'", "frequencia = 'anual'")
    with pytest.raises(ValueError, match="guarda"):
        registro("uso = 'x'", "frequencia = 'diaria'", "guarda = 'tudo'")
    # Coleta mínima: fonte ativa precisa de uso declarado; catalogada não.
    with pytest.raises(ValueError, match="sem uso declarado"):
        registro("frequencia = 'diaria'")
    assert registro("frequencia = 'diaria'", "situacao = 'catalogada'")[0].situacao == "catalogada"


def test_anos():
    hoje = date(2026, 10, 8)
    assert acervo.anos_de(Fonte("a", "m", "diaria"), hoje) is None
    assert acervo.anos_de(Fonte("a", "m", "diaria", anos="padrao"), hoje) == [2025, 2026]
    assert acervo.anos_de(Fonte("a", "m", "diaria", anos="dois_anteriores"), hoje) == [2024, 2025]
    assert acervo.anos_de(Fonte("a", "m", "diaria", anos="desde_2023"), hoje) == [
        2023,
        2024,
        2025,
        2026,
    ]
    assert acervo.anos_de(Fonte("a", "m", "diaria", anos=[2018]), hoje) == [2018]


def test_ordem_respeita_dependencias_escolhidas():
    fontes = [
        Fonte("resumo", "m", "diaria", depende=["gastos", "votos"]),
        Fonte("gastos", "m", "diaria", depende=["pessoas"]),
        Fonte("votos", "m", "diaria", depende=["pessoas"]),
        Fonte("pessoas", "m", "diaria"),
    ]
    assert [f.nome for f in acervo.ordenar(fontes, {"resumo", "gastos", "pessoas", "votos"})] == [
        "pessoas", "gastos", "votos", "resumo"
    ]  # fmt: skip
    # Dependência fora da escolha não é puxada junto.
    assert [f.nome for f in acervo.ordenar(fontes, {"resumo", "gastos"})] == ["gastos", "resumo"]


def test_vencidas():
    agora = datetime(2026, 10, 8, 3, tzinfo=UTC)
    fontes = [
        Fonte("diaria_ontem", "m", "diaria"),
        Fonte("diaria_hoje", "m", "diaria"),
        Fonte("semanal_3_dias", "m", "semanal"),
        Fonte("nunca", "m", "mensal"),
        Fonte("manual", "m", "manual"),
    ]
    ultimo = {
        "diaria_ontem": agora - timedelta(hours=23, minutes=30),  # folga de uma hora
        "diaria_hoje": agora - timedelta(hours=2),
        "semanal_3_dias": agora - timedelta(days=3),
    }
    assert acervo.vencidas(fontes, ultimo, agora) == {"diaria_ontem", "nunca"}


def test_rodar_pula_quem_depende_de_falha(monkeypatch, capsys):
    chamadas = []

    def executar(fonte, hoje):
        chamadas.append(fonte.nome)
        if fonte.nome == "pessoas":
            raise RuntimeError("fora do ar")
        return 1

    monkeypatch.setattr(acervo, "_executar", executar)
    fontes = [Fonte("pessoas", "m", "diaria"), Fonte("gastos", "m", "diaria", depende=["pessoas"]),
              Fonte("ibge", "m", "diaria")]  # fmt: skip
    assert acervo.rodar({"pessoas", "gastos", "ibge"}, fontes) == 2
    assert chamadas == ["pessoas", "ibge"]
    assert "[pulada] gastos: depende de pessoas" in capsys.readouterr().out


def test_catalogada_nunca_roda(monkeypatch, capsys):
    agora = datetime(2026, 10, 8, 3, tzinfo=UTC)
    fontes = [
        Fonte("cnpj", "m", "mensal", situacao="catalogada"),
        Fonte("ibge", "m", "mensal", uso="x"),
    ]
    assert acervo.vencidas(fontes, {}, agora) == {"ibge"}
    chamadas = []
    monkeypatch.setattr(acervo, "_executar", lambda fonte, hoje: chamadas.append(fonte.nome) or 1)
    assert acervo.rodar({"cnpj", "ibge"}, fontes) == 0
    assert chamadas == ["ibge"]
    assert "[pulada] cnpj: catalogada" in capsys.readouterr().out


def test_queda_brusca():
    assert acervo.queda(1000, 700)  # 30% a menos
    assert not acervo.queda(1000, 850)
    assert not acervo.queda(None, 10) and not acervo.queda(0, 0)


def test_rodar_avisa_queda_e_guarda_historico(monkeypatch, capsys):
    totais = iter([100, 50])
    monkeypatch.setattr(acervo, "_executar", lambda fonte, hoje: next(totais))
    fontes = [Fonte("ibge", "m", "diaria", uso="x")]
    acervo.rodar({"ibge"}, fontes)
    acervo.rodar({"ibge"}, fontes)
    assert "[alerta] ibge: 50 registros, contra 100" in capsys.readouterr().out
