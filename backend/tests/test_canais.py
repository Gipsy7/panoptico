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
