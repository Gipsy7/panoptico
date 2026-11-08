"""Nomes anteriores de municípios: a cópia empacotada (app/dados/) é a que a imagem Docker lê."""

from ingestion.ibge import nomes_anteriores


def test_copias_empacotadas_iguais_as_versionadas():
    """Se falhar: copie data/municipios_nomes_*.csv para backend/app/dados/."""
    for original in (nomes_anteriores.CSV_IBGE, nomes_anteriores.CSV_EXTRA):
        copia = nomes_anteriores.COPIA / original.name
        assert original.read_bytes() == copia.read_bytes(), original.name


def test_ares_e_tabocao_resolvem_pelo_nome_antigo():
    from ingestion import comum

    apelidos = nomes_anteriores.carregar_apelidos()
    assert apelidos.get(("RN", comum.chave_nome("ARÊS"))) is not None
    assert apelidos.get(("TO", comum.chave_nome("FORTALEZA DO TABOCÃO"))) is not None
