# ruff: noqa: E501  (URLs reais, mais legíveis numa linha só)
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
    [linha] = catalogo.ler(arquivo, tmp_path / "sem-curados.csv")
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


def test_filtros_de_portal_de_outra_cidade_e_noticia():
    assert v.de_outra_cidade(
        "https://transparencia.caldeiraogrande.ba.gov.br", "Oliveira dos Brejinhos"
    )
    assert not v.de_outra_cidade("https://transparencia.boninal.ba.gov.br/", "Boninal")
    assert not v.de_outra_cidade("https://transparencia.betha.cloud/#/abc", "Boninal")
    linhas = [
        {
            "municipio": "Turiúba",
            "tipo": "transparencia_prefeitura",
            "url": "https://www.turiuba.sp.gov.br/portal/noticias/0/3/586/audiencia-publica",
        },
        {"municipio": "Turiúba", "tipo": "camara", "url": "https://www.turiuba.sp.leg.br"},
    ]
    assert [x["tipo"] for x in v.limpar_catalogo(linhas)] == ["camara"]


def test_curados_substituem_a_varredura(tmp_path):
    from ingestion.canais import catalogo

    comum = {"municipio": "São Paulo", "uf": "SP", "sistema": "", "verificado_em": "2026-10-08"}
    varredura, curados = tmp_path / "v.csv", tmp_path / "c.csv"
    v.gravar_catalogo(
        [
            {**comum, "ibge": "3550308", "tipo": "prefeitura", "url": "https://www.sp.gov.br/sp"},
            {
                **comum,
                "ibge": "3550308",
                "tipo": "camara",
                "url": "https://www.saopaulo.sp.leg.br/",
            },
        ],
        varredura,
    )
    v.gravar_catalogo(
        [
            {
                **comum,
                "ibge": "3550308",
                "tipo": "prefeitura",
                "url": "https://prefeitura.sp.gov.br/",
            }
        ],
        curados,
    )
    resultado = {c["tipo"]: c["url"] for c in catalogo.ler(varredura, curados)}
    assert resultado == {
        "camara": "https://www.saopaulo.sp.leg.br/",
        "prefeitura": "https://prefeitura.sp.gov.br/",
    }


def test_migracoes_atuais_nao_pedem_recarga():
    from ingestion.precisa_recarga import precisa

    assert precisa("0014", "0017") is False
