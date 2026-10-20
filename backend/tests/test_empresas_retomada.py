"""Cadastro de empresas na produção: conjunto de interesse lido do próprio banco e recomeço
seguro do download (a base da Receita tem 7,8 GB e o servidor já travou sem erro)."""

import zipfile
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.models import DespesaFornecedor, Municipio
from app.models.base import Base
from ingestion.receita import empresas as carga
from tests.test_empresas import EMPRESAS, ESTABELECIMENTOS, MUNICIPIOS


def test_tabelas_de_interesse_existem_no_modelo():
    """Tabela ou coluna renomeada não pode sumir do conjunto sem aviso: `cnpjs_de_interesse`
    pula tabela inexistente em silêncio (produção enxuta)."""
    tabelas = Base.metadata.tables
    for tabela, coluna in carga.INTERESSE:
        assert tabela in tabelas and coluna in tabelas[tabela].columns, (tabela, coluna)
    assert ("emenda_estadual", "favorecido_cnpj") in carga.INTERESSE
    assert ("emenda_transferencia", "beneficiario_cnpj") in carga.INTERESSE


def test_interesse_le_so_o_banco_onde_roda(session):
    """Sem data/raw nem outro banco: o conjunto vem das tabelas do próprio banco."""
    session.add(Municipio(ibge="4208203", nome="Ilhota", uf="SC", nome_chave="ILHOTA"))
    session.flush()
    session.add(
        DespesaFornecedor(
            fonte="tce_sp",
            municipio_ibge="4208203",
            ano=2025,
            orgao="prefeitura",
            fornecedor="X",
            documento="82892282000120",
            valor_pago=Decimal("1"),
            pagamentos=1,
        )
    )
    session.flush()
    assert "82892282000120" in carga.cnpjs_de_interesse(session)


def test_baixar_retoma_pelos_zips_ja_feitos(tmp_path, monkeypatch):
    """Cai no meio (Estabelecimentos2): a segunda execução só baixa o que faltou."""
    monkeypatch.setattr(carga.comum, "RAW_DIR", tmp_path)
    contador = iter(range(1000))

    def zip_de(conteudo: bytes) -> Path:
        destino = tmp_path / f"dl{next(contador)}.zip"
        with zipfile.ZipFile(destino, "w") as z:
            z.writestr("dados.csv", conteudo)
        return destino

    baixados: list[str] = []
    falhar_em = {"Estabelecimentos2.zip"}

    def falso(client, url, tentativas=3):
        nome = url.rsplit("/", 1)[-1]
        if nome in falhar_em:
            raise httpx.ReadTimeout("travou")
        baixados.append(nome)
        if nome.startswith("Municipios"):
            return zip_de(MUNICIPIOS)
        if nome.startswith("Naturezas"):
            return zip_de(b'"2062";"LTDA"\n')
        return zip_de(ESTABELECIMENTOS if nome.startswith("Estab") else EMPRESAS)

    monkeypatch.setattr(carga, "_baixar_arquivo", falso)
    cnpjs = {"82892282000120"}
    with pytest.raises(httpx.ReadTimeout):
        carga.baixar(None, "2026-10", cnpjs)
    assert (carga.pasta_parcial("2026-10", cnpjs) / "Estabelecimentos1.zip.csv").exists()
    baixados.clear()
    falhar_em.clear()
    recorte = carga.baixar(None, "2026-10", cnpjs)
    assert "Estabelecimentos0.zip" not in baixados and "Estabelecimentos1.zip" not in baixados
    assert "Estabelecimentos2.zip" in baixados and "Empresas0.zip" in baixados
    linhas, referencia, interesse = carga.ler_recorte(recorte)
    assert (referencia, interesse) == ("2026-10", 1)
    assert {x["cnpj"] for x in linhas} == {"82892282000120"}  # o falso repete o mesmo zip
    assert not carga.pasta_parcial("2026-10", cnpjs).exists()
