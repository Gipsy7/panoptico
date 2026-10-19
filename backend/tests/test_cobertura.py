"""Régua de cobertura: a matriz sai completa e fiel aos fatos conhecidos (sem banco)."""

from ingestion import cobertura


def test_27_ufs_com_as_cinco_casas():
    linhas = cobertura.montar()
    for uf in cobertura.UFS:
        casas = {x["casa"] for x in linhas if x["uf"] == uf}
        assert len(casas) == 5  # assembleia, Câmara, Senado, governo, prefeituras
    for uf, casa in {(x["uf"], x["casa"]) for x in linhas}:
        secoes = {x["secao"] for x in linhas if (x["uf"], x["casa"]) == (uf, casa)}
        assert {"gastos", "projetos", "bens_campanha"} <= secoes


def test_nenhuma_celula_sem_situacao_ou_motivo():
    for x in cobertura.montar():
        assert x["situacao"] in cobertura.SITUACOES, x
        assert x["motivo"].strip(), x


def test_alep_aparece_sem_conector():
    alep = [x for x in cobertura.montar() if x["uf"] == "PR" and x["casa"] == "ALPR"]
    legislativas = [x for x in alep if x["secao"] in cobertura.ROTULO]
    assert len(legislativas) == 4
    assert all("sem conector" in x["motivo"].lower() for x in legislativas)
    assert all(x["situacao"] != "sim" for x in legislativas)


def test_geobloqueio_vira_bloqueado():
    linhas = cobertura.montar()
    for uf in ("MG", "PE", "BA", "ES", "RS", "RR", "AP", "MA", "DF"):
        proj = next(
            x
            for x in linhas
            if x["uf"] == uf and x["secao"] == "projetos" and x["casa"] in (f"AL{uf}", "CLDF")
        )
        assert proj["situacao"] == "bloqueado", (uf, proj)
