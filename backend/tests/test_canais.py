from ingestion.canais import varredura as v


def test_slugs_e_enderecos_padrao():
    assert v.slugs("São Bento do Sul") == ["saobentodosul", "sao-bento-do-sul"]
    assert v.slugs("Herval d'Oeste") == ["hervaldoeste", "herval-doeste"]
    tentativas = v.candidatos("Alto Feliz", "RS")
    assert "https://altofeliz.rs.gov.br/" in tentativas["prefeitura"]
    assert "https://altofeliz.rs.leg.br/" in tentativas["camara"]
    assert "https://camaraaltofeliz.rs.gov.br/" in tentativas["camara"]


def test_pagina_e_da_cidade_pelo_titulo_ou_texto():
    pagina = v.Pagina("https://x.rs.gov.br/", "Prefeitura Municipal de Alto Feliz", "")
    assert v._da_cidade(pagina, "Alto Feliz")
    assert not v._da_cidade(pagina, "Feliz Natal")


def test_melhor_portal_ignora_campanhas_e_a_propria_pagina():
    pagina = v.Pagina(
        "https://ametistadosul.rs.gov.br/",
        "Prefeitura de Ametista do Sul",
        "",
        [
            ("https://ametistadosul.rs.gov.br/", "Transparência"),
            ("/transparenciacovid", "Transparência covid-19"),
            ("https://radardatransparencia.atricon.org.br/", "Radar da Transparência"),
            ("https://e-gov.betha.com.br/transparencia/01037-168/", "Portal da Transparência"),
        ],
    )
    assert v.melhor_portal(pagina) == "https://e-gov.betha.com.br/transparencia/01037-168/"
    assert v.sistema_de("https://alvorada.atende.net/?pg=transparencia") == "ipm"
    assert v.sistema_de("https://exemplo.gov.br/transparencia") is None


def test_catalogo_le_o_csv_e_ignora_ausente(tmp_path):
    from ingestion.canais import catalogo

    assert catalogo.ler(tmp_path / "nao-existe.csv") == []
    arquivo = tmp_path / "canais.csv"
    v.gravar_catalogo(
        [
            {
                "ibge": "4300703",
                "municipio": "Anta Gorda",
                "uf": "RS",
                "tipo": "camara",
                "url": "https://antagorda.rs.leg.br/",
                "sistema": "",
                "verificado_em": "2026-10-07",
            },
        ],  # fmt: skip
        arquivo,
    )
    [linha] = catalogo.ler(arquivo)
    assert (linha["municipio_ibge"], linha["tipo"], linha["sistema"]) == ("4300703", "camara", None)


def test_canais_do_municipio(client, session):
    from datetime import date

    from app.models import CanalOficial, Municipio

    session.add(Municipio(ibge="4300703", nome="Anta Gorda", uf="RS", nome_chave="ANTA GORDA"))
    session.flush()
    session.add_all(
        [
            CanalOficial(
                municipio_ibge="4300703",
                tipo="camara",
                url="https://c/",
                verificado_em=date(2026, 10, 7),
            ),
            CanalOficial(municipio_ibge="4300703", tipo="prefeitura", url="https://p/"),
        ]
    )
    session.flush()
    corpo = client.get("/municipios/4300703/canais").json()
    assert [c["tipo"] for c in corpo["itens"]] == ["prefeitura", "camara"]
    assert client.get("/municipios/0000000/canais").status_code == 404
