from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models import ArrecadacaoUF, FonteIngestao
from ingestion.receita import arrecadacao_uf as arr

AMOSTRA = Path(__file__).parent / "fixtures" / "receita_arrecadacao_estado.csv"
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
MESES = "Janeiro Fevereiro Março Abril Maio Junho Julho Agosto Setembro Outubro Novembro Dezembro"


def _csv_completo(ano: int = 2024, valor: str = "1.000,50") -> bytes:
    """CSV mínimo com o cabeçalho real: todas as UFs e meses de um ano."""
    cabecalho = AMOSTRA.read_text("latin-1").splitlines()[0]
    n = len(cabecalho.split(";"))
    linhas = [cabecalho]
    for mes in MESES.split():
        for uf in UFS:
            celulas = [str(ano), mes, uf, valor] + [""] * (n - 4)
            linhas.append(";".join(celulas))
    return "\n".join(linhas).encode("latin-1")


def test_normalizar_amostra_real():
    linhas = arr.normalizar(AMOSTRA.read_bytes())
    # 2018 fica de fora (antes de 2019); 2 linhas restantes
    assert [(x["uf"], x["ano"], x["mes"]) for x in linhas] == [("AC", 2024, 3), ("DF", 2025, 12)]
    ac, df = linhas
    assert ac["previdencia"] == Decimal("93086791.54")  # lida da coluna certa
    assert df["previdencia"] == Decimal("2908820062")
    # o total inclui a previdência e é maior que ela
    assert ac["total"] > ac["previdencia"] > 0
    assert df["total"] > df["previdencia"] > 0


def test_numero_decimal_virgula_e_negativo():
    assert arr.numero("1.234.567,89") == Decimal("1234567.89")
    assert arr.numero("-0,4") == Decimal("-0.4")
    assert arr.numero("") == 0


def test_cabecalho_inesperado_aborta():
    with pytest.raises(ValueError):
        arr.normalizar(b"A;B;C\n1;2;3\n")


def test_carregar_idempotente_e_reinsere_so_os_anos_presentes(session):
    ingestao = FonteIngestao(fonte=arr.FONTE, url=arr.URL, arquivo_raw="x")
    session.add(ingestao)
    session.flush()
    session.add(ArrecadacaoUF(uf="SP", ano=2018, mes=1, total=Decimal("1")))  # fora do arquivo
    session.flush()
    assert arr.carregar(session, _csv_completo(2024), ingestao) == 27 * 12
    assert arr.carregar(session, _csv_completo(2024, "2.000,00"), ingestao) == 27 * 12
    assert session.scalar(select(func.count()).select_from(ArrecadacaoUF)) == 27 * 12 + 1
    assert session.get(ArrecadacaoUF, ("SP", 2024, 5)).total == Decimal("2000.00")
    assert session.get(ArrecadacaoUF, ("SP", 2018, 1)).total == Decimal("1")
    assert session.get(ArrecadacaoUF, ("DF", 2024, 1)).previdencia == 0


def test_carregar_aborta_com_arquivo_vazio(session):
    ingestao = FonteIngestao(fonte=arr.FONTE, url=arr.URL, arquivo_raw="x")
    session.add(ingestao)
    session.flush()
    vazio = AMOSTRA.read_text("latin-1").splitlines()[0].encode("latin-1")
    with pytest.raises(ValueError):
        arr.carregar(session, vazio, ingestao)
