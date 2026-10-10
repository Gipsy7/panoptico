# ruff: noqa: E501  (recortes das páginas reais da ALEPA e da ALMT)
from ingestion.assembleias import alepa, almt

PA = """
<div class='card-wrapper-deputado'><div class='card-container'><div class='skeleton-container'><div class='skeleton-image'></div><img class='deputado-image' src='https://alepa.quartertec.com.br\\Content\\Portal\\PerfilAgentePolitico\\DEPUTADA_Andreia Xarao.png?timestamp=638865363751209993' /></div></div><div class='card-info'><span>Deputada</span><span>Andréia Xarão</span><p>MDB</p></div></div>
<div class='card-wrapper-deputado'><div class='card-container'><div class='skeleton-container'><div class='skeleton-image'></div><img class='deputado-image' src='https://alepa.quartertec.com.br\\Content\\Portal\\PerfilAgentePolitico\\DEPUTADO_Zeca Pirao.jpg' /></div></div><div class='card-info'><span>Deputado</span><span>Zeca Pirão</span><p>MDB</p></div></div>
<div class='card-wrapper-deputado'><div class='card-container'><img class='deputado-image' src='x' /></div><div class='card-info'><span>Deputada</span><span>Andréia Xarão</span><p>MDB</p></div></div>
"""
MT = """
<div class="col-6 col-md-4 col-lg-3 col-xl-2"> <div class="card rounded-0 my-3"> <a href="/parlamento/deputados/129/perfil"> <img class="card-img-top rounded-0" src="https://storage.al.mt.gov.br/api/v1/download/image/558597?width=420px&amp;quality=80" alt="Carlos Avallone" loading="lazy"/> </a> <div class="card-body"> <span class="badge text-bg-secondary mb-1"> PSDB </span> <h6 class="card-title fw-semibold fs-14">CARLOS AVALLONE</h6> <div class="d-grid"> <a href="/parlamento/deputados/129/perfil" class="btn btn-sm btn-primary">Veja mais</a> </div> </div> </div> </div>
<div class="col-6 col-md-4 col-lg-3 col-xl-2"> <div class="card rounded-0 my-3"> <a href="/parlamento/deputados/401/perfil"> <img class="card-img-top rounded-0" src="https://storage.al.mt.gov.br/api/v1/download/image/750591" alt="Beto Dois a Um" loading="lazy"/> </a> <div class="card-body"> <span class="badge text-bg-secondary mb-1"> PODE </span> <h6 class="card-title fw-semibold fs-14">BETO DOIS A UM</h6> </div> </div> </div>
"""


def test_alepa_cartoes():
    lista = alepa.deputados(PA)
    assert [(d["id"], d["nome"], d["partido"]) for d in lista] == [
        ("andreia-xarao", "Andréia Xarão", "MDB"),
        ("zeca-pirao", "Zeca Pirão", "MDB"),
    ]  # o repetido entra uma vez
    assert (
        lista[0]["foto"]
        == "https://alepa.quartertec.com.br/Content/Portal/PerfilAgentePolitico/DEPUTADA_Andreia%20Xarao.png?timestamp=638865363751209993"
    )


def test_almt_cartoes_e_nome_civil():
    lista = almt.deputados(MT)
    assert [(d["id"], d["nome"], d["partido"]) for d in lista] == [
        ("129", "Carlos Avallone", "PSDB"),
        ("401", "Beto Dois A Um", "PODE"),
    ]
    assert lista[0]["foto"].endswith("558597?width=420px&quality=80")
    ficha = (
        "<p>Nome civil: <b>Carlos Avalone Junior</b></p><p>Nome parlamentar: Carlos Avallone</p>"
    )
    assert almt.nome_civil(ficha) == "Carlos Avalone Junior"
    assert almt.nome_civil("<html></html>") is None
