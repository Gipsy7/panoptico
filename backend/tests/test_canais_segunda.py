import asyncio

import httpx
import respx

from ingestion.canais import segunda_varredura as s
from ingestion.canais.varredura import Pagina


def test_variacoes_sem_particulas_e_sem_repetir_a_primeira_varredura():
    assert s.variacoes_slug("São Bento do Sul") == [
        "saobentodosul",
        "sao-bento-do-sul",
        "saobentosul",
        "sao-bento-sul",
    ]
    assert s.variacoes_slug("Ariquemes") == ["ariquemes"]
    hosts = s.variacoes("São Bento do Sul", "SC")
    assert "cmsaobentosul.sc.gov.br" in hosts
    assert "camaramunicipalsaobentosul.sc.gov.br" in hosts
    assert "saobentosul.sc.leg.br" in hosts
    assert "camarasaobentosul.org.br" in hosts
    assert "cmsaobentosul.com.br" in hosts
    # já testados pela primeira varredura
    assert "saobentodosul.sc.leg.br" not in hosts
    assert "camarasaobentodosul.sc.gov.br" not in hosts
    assert "cmsao-bento-do-sul.sc.gov.br" not in hosts


def test_validacao_de_conteudo():
    ok = Pagina("https://x.gov.br/", "Câmara Municipal de Alto Feliz", "Vereadores")
    assert s.e_camara_da_cidade(
        ok, "Alto Feliz", "RS", "Rio Grande do Sul", "cmaltofeliz.rs.gov.br"
    )
    # outra cidade
    outra = Pagina("https://x.gov.br/", "Câmara Municipal de Feliz", "")
    assert not s.e_camara_da_cidade(outra, "Alto Feliz", "RS", "Rio Grande do Sul", "x.rs.gov.br")
    # prefeitura, não câmara
    pref = Pagina("https://x.gov.br/", "Prefeitura de Alto Feliz", "Alto Feliz")
    assert not s.e_camara_da_cidade(pref, "Alto Feliz", "RS", "Rio Grande do Sul", "x.rs.gov.br")
    # domínio parado
    parado = Pagina("https://x.com.br/", "Câmara Alto Feliz - domínio à venda", "Alto Feliz")
    assert not s.e_camara_da_cidade(parado, "Alto Feliz", "RS", "Rio Grande do Sul", "x.rs.gov.br")
    # .com.br precisa dizer o estado (cidade homônima)
    sem_uf = Pagina("https://x.com.br/", "Câmara Municipal de Alto Feliz", "Vereadores")
    assert not s.e_camara_da_cidade(
        sem_uf, "Alto Feliz", "RS", "Rio Grande do Sul", "cmaltofeliz.com.br"
    )
    com_uf = Pagina("https://x.com.br/", "Câmara Municipal de Alto Feliz", "Alto Feliz - RS")
    assert s.e_camara_da_cidade(
        com_uf, "Alto Feliz", "RS", "Rio Grande do Sul", "cmaltofeliz.com.br"
    )


def _html(titulo: str) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"content-type": "text/html"},
        text=f"<html><title>{titulo}</title>{titulo}</html>",
    )


@respx.mock
def test_acha_camara_e_sapl_com_robots_e_ignora_pagina_de_outra_cidade():
    async def rodar():
        v = s.Segunda(pausa=0)
        v.ips = {}  # sem DNS na rede de teste

        async def servidor(url):
            return asyncio.Lock()

        v._servidor = servidor
        try:
            return await v.cidade_sem_canal("4300000", "Alto Feliz", "RS", "Rio Grande do Sul")
        finally:
            await v.fechar()

    respx.get("https://camaraaltofeliz.rs.leg.br/robots.txt").respond(404)
    respx.get("https://camaraaltofeliz.rs.leg.br/").mock(return_value=_html("Câmara de Feliz"))
    respx.get("https://camaraaltofeliz.org.br/robots.txt").respond(
        200, headers={"content-type": "text/plain"}, text="User-agent: *\nDisallow: /"
    )
    respx.get("https://camaraaltofeliz.org.br/").mock(return_value=_html("Câmara de Alto Feliz"))
    respx.get("https://cmaltofeliz.rs.leg.br/robots.txt").respond(404)
    respx.get("https://cmaltofeliz.rs.leg.br/").mock(
        return_value=_html("Câmara Municipal de Alto Feliz")
    )
    respx.get("https://sapl.cmaltofeliz.rs.leg.br/robots.txt").respond(404)
    respx.get(
        "https://sapl.cmaltofeliz.rs.leg.br/api/parlamentares/parlamentar/?page_size=1"
    ).respond(200, text='{"results": []}')
    respx.get("https://sapl.cmaltofeliz.rs.leg.br/").mock(
        return_value=_html("Câmara Municipal de Alto Feliz - SAPL")
    )
    respx.route().respond(404)

    achados = asyncio.run(rodar())
    assert [(a["tipo"], a["url"]) for a in achados] == [
        ("camara", "https://cmaltofeliz.rs.leg.br/"),
        ("sapl", "https://sapl.cmaltofeliz.rs.leg.br/"),
    ]


def test_lista_sem_canal(tmp_path):
    cat = tmp_path / "c.csv"
    cat.write_text("ibge,municipio,uf,tipo,url,sistema,verificado_em\n1,A,RS,camara,u,,\n")
    cur = tmp_path / "cur.csv"
    cur.write_text("ibge,municipio,uf,tipo,url,sistema,verificado_em\n2,B,RS,prefeitura,u,,\n")
    cidades = [("1", "A", "RS", "x"), ("2", "B", "RS", "x"), ("3", "C", "RS", "x")]
    assert s.sem_canal(cidades, cat, cur) == [("3", "C", "RS", "x")]
    destino = tmp_path / "sem.csv"
    s.gravar_sem_canal([("3", "C", "RS", "x")], destino, "2026-10-10")
    assert destino.read_text().splitlines() == ["ibge,municipio,uf,buscado_em", "3,C,RS,2026-10-10"]
