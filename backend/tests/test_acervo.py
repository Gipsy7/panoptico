import importlib
from datetime import UTC, date, datetime, timedelta

import pytest

from ingestion import acervo
from ingestion.acervo import Fonte


def test_registro_valido_e_nomes_iguais_aos_dos_modulos():
    fontes = acervo.ler_registro()
    for f in fontes:
        modulo = importlib.import_module(f.modulo)
        assert hasattr(modulo, "executar"), f.modulo
        # O nome é a chave em fonte_ingestao: diferente do FONTE, a fonte nunca sairia de "vencida".
        assert getattr(modulo, "FONTE", f.nome) == f.nome, f.modulo
    assert acervo.ordenar(fontes, {f.nome for f in fontes})  # sem dependência circular


def test_registro_recusa_erros(tmp_path):
    arquivo = tmp_path / "fontes.toml"
    arquivo.write_text(
        '[[fonte]]\nnome = "a"\nmodulo = "m"\nfrequencia = "diaria"\ndepende = ["b"]\n'
    )
    with pytest.raises(ValueError, match="fora do registro"):
        acervo.ler_registro(arquivo)
    arquivo.write_text('[[fonte]]\nnome = "a"\nmodulo = "m"\nfrequencia = "anual"\n')
    with pytest.raises(ValueError, match="frequência"):
        acervo.ler_registro(arquivo)


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
