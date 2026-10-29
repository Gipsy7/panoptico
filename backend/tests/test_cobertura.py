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


def test_alep_tem_conector_e_pedido_so_no_que_falta():
    alep = [x for x in cobertura.montar() if x["uf"] == "PR" and x["casa"] == "ALPR"]
    legislativas = {x["secao"]: x for x in alep if x["secao"] in cobertura.ROTULO}
    assert len(legislativas) == 4
    assert legislativas["votos"]["situacao"] == legislativas["presenca"]["situacao"] == "sim"
    for secao in ("projetos", "gastos"):  # certificado autoassinado/403 e reCAPTCHA
        assert legislativas[secao]["situacao"] == "pedido"
        assert legislativas[secao]["pedido"] == "alep_certificado.md"


def _projetos(linhas, uf):
    return next(
        x
        for x in linhas
        if x["uf"] == uf and x["secao"] == "projetos" and x["casa"] in (f"AL{uf}", "CLDF")
    )


def test_geobloqueio_vira_bloqueado(monkeypatch):
    # BA, ES e SE saíram em 27/10/2026 e as demais em 29/10/2026: rodam na VPS de São Paulo
    # (acesso "aberto"). A regra continua valendo para fonte com acesso "brasil".
    ufs = ("MG", "PE", "RS", "RR", "AP", "MA", "DF")
    for uf in ufs:
        assert _projetos(cobertura.montar(), uf)["situacao"] == "sim", uf
    real = cobertura._acessos()
    monkeypatch.setattr(cobertura, "_acessos", lambda: dict.fromkeys(real, "brasil"))
    linhas = cobertura.montar()
    for uf in ufs:
        assert _projetos(linhas, uf)["situacao"] == "bloqueado", uf
