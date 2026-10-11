# ruff: noqa: E501  (recortes reais das páginas de Palmas, Teófilo Otoni e Frutal)
import respx
from sqlalchemy import select

from app.models import Candidatura, MandatoLocal, Municipio
from ingestion.camaras import sistemas
from tests.test_api import _ingestao

DIGITALIZA = """
<div class="vereador__item"><a href="https://teofilootoni.mg.leg.br/vereadores/22/detalhes" aria-label="Abrir detalhes"></a>
 <div class="vereador__img"><img src="https://exemplo.s3.amazonaws.com/ota.png" alt="Paulo"></div>
 <div class="vereador__info"><h6> Paulo Otávio Cardoso Conceição (Ota Mandinha) </h6><p> PARTIDO LIBERAL </p></div></div>
<div class="vereador__item"><a href="https://teofilootoni.mg.leg.br/vereadores/2/detalhes" aria-label="Abrir detalhes"></a>
 <div class="vereador__img"><img src="https://exemplo.s3.amazonaws.com/fabio.png" alt="Fábio"></div>
 <div class="vereador__info"><h6> Fábio Lemes de Souza </h6><p> REDE SUSTENTABILIDADE </p></div></div>
"""
SISCAM = """
<div class="col-md-10"><h4><a href="/Vereadores/Vereador/290">Alexandre Jos&#233; Braz</a></h4>
<p><strong>Partido:</strong> SOLIDARIED </p><p><strong>Proposituras:</strong> <a href="/Vereadores/Contagem/290">Resumidas</a></p></div>
<div class="col-md-10"><h4><a href="/Vereadores/Vereador/17">Edivalder Fernandes da Silva</a></h4>
<p><strong>Partido:</strong> REPUBLICAN </p></div>
"""
CAPA = """
<a class="card-vereador vdr-01-full-width" href="https://palmas.to.leg.br/vereador/marilon-barbosa/" >
 <div class="image-wrapper"><img data-src="https://palmas.to.leg.br/wp-content/uploads/2025/02/Marilon.jpg" alt="" src="data:image/svg+xml;base64,AAA" class="lazyload"></div>
 <span class="cargo bold uppercase">Presidente</span><div class="title-wrapper"><p class="bold">Marilon Barbosa</p></div></a>
<a class="card-vereador vdr-01-full-width" href="https://palmas.to.leg.br/vereador/eudes-assis/" >
 <div class="image-wrapper"><img data-src="https://palmas.to.leg.br/wp-content/uploads/2025/02/Eudes.jpg" alt="" src="data:image/svg+xml;base64,AAA"></div>
 <span class="cargo bold uppercase">SUPLENTE</span><div class="title-wrapper"><p class="bold">Eudes Assis</p></div></a>
"""
FICHA = """
<p class="has-secondary-color" style="text-transform:uppercase">nome civil</p>
<div class="has-text-color wp-block-nwe-acf"> Marilon Barbosa Castro </div>
<p class="has-secondary-color" style="text-transform:uppercase">partido</p>
<div class="has-text-color wp-block-nwe-acf"> REPUBLICANOS </div>
"""


def test_digitaliza_nome_civil_apelido_e_partido_por_extenso():
    por_nome = {
        v["nome"]: v
        for v in sistemas.vereadores_digitaliza(DIGITALIZA, "https://t.mg.leg.br/vereadores")
    }
    ota = por_nome["Ota Mandinha"]
    assert (ota["nome_completo"], ota["partido"]) == ("Paulo Otávio Cardoso Conceição", "PL")
    assert por_nome["Fábio Lemes de Souza"]["nome_completo"] is None
    assert por_nome["Fábio Lemes de Souza"]["partido"] == "REDE"
    assert ota["foto_url"] == "https://exemplo.s3.amazonaws.com/ota.png"


def test_siscam_expande_a_sigla_cortada():
    vereadores = sistemas.vereadores_siscam(SISCAM, "x")
    assert [(v["nome"], v["partido"]) for v in vereadores] == [
        ("Alexandre José Braz", "SOLIDARIEDADE"),
        ("Edivalder Fernandes da Silva", "REPUBLICANOS"),
    ]


def test_nexlegis_tira_o_suplente_e_le_a_ficha():
    cartoes = sistemas.cartoes_nexlegis(CAPA)
    assert [c[1:3] for c in cartoes] == [("marilon-barbosa", "Marilon Barbosa")]
    link, slug, apelido, foto = cartoes[0]
    v = sistemas.ficha_nexlegis(FICHA, slug, apelido, foto)
    assert (v["nome_completo"], v["partido"]) == ("Marilon Barbosa Castro", "REPUBLICANOS")
    assert v["foto_url"].endswith("Marilon.jpg")


@respx.mock
def test_coletar_siscam_e_gravar_liga_ao_eleito(session):
    pagina = respx.get("https://frutal.siscam.com.br/Vereadores").respond(text=SISCAM)
    camara = sistemas.coletar("https://frutal.siscam.com.br/", "siscam")
    assert pagina.calls[0].request.headers["User-Agent"].startswith("Panoptico")
    session.add(Municipio(ibge="3127107", nome="Frutal", uf="MG", nome_chave="FRUTAL"))
    session.flush()
    session.add(Candidatura(ano_eleicao=2024, sq_candidato="1", cargo="VEREADOR", uf="MG", unidade="Frutal",
                            municipio_ibge="3127107", nome="ALEXANDRE JOSE BRAZ", nome_urna="ALEXANDRE BRAZ",
                            situacao_turno="ELEITO POR QP", ingestao_id=_ingestao(session).id))  # fmt: skip
    session.flush()
    from ingestion.camaras import sapl

    assert sapl.gravar(session, "3127107", camara) == 2
    mandatos = {m.nome: m for m in session.scalars(select(MandatoLocal))}
    assert mandatos["Alexandre José Braz"].candidatura_id is not None
    assert mandatos["Edivalder Fernandes da Silva"].candidatura_id is None
