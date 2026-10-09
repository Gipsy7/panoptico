import io
from datetime import date
from decimal import Decimal

import analises.__main__ as analises
from app.models import DespesaFornecedor, Municipio, SancaoEmpresa


def test_fornecedores_sancionados_so_no_ano_da_vigencia(session, monkeypatch):
    session.add(Municipio(ibge="3500000", nome="Exemplo", uf="SP", nome_chave="EXEMPLO"))
    session.flush()
    for ano in (2022, 2024):
        session.add(
            DespesaFornecedor(municipio_ibge="3500000", ano=ano, orgao="prefeitura",
                              fornecedor="EMPRESA X", documento="12345678000199",
                              valor_pago=Decimal("100.00"), pagamentos=1, fonte="tce_sp")
        )  # fmt: skip
    session.add(
        SancaoEmpresa(cadastro="CEIS", codigo="1", cnpj="12345678000199", nome="EMPRESA X",
                      categoria="Suspensão", abrangencia="No órgão sancionador",
                      inicio=date(2023, 6, 1), fim=date(2025, 6, 1))
    )  # fmt: skip
    session.flush()

    class Sessao:
        def __enter__(self):
            return session

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(analises, "SessionLocal", Sessao)
    saida = io.StringIO()
    assert analises.rodar("fornecedores_sancionados", saida) == 1  # 2022 é antes da sanção
    assert "No órgão sancionador" in saida.getvalue()
    assert "fornecedores_sancionados" in analises.disponiveis()
