from ingestion.assembleias import alesc

# Recortes reais das páginas da ALESC (09/10/2026).
DEPUTADOS = """
<a href="https://www.alesc.sc.gov.br/deputado/altair-silva/">
<div class="row align-items-center gx-3">
<div class="col-auto">
<img src="https://www.alesc.sc.gov.br/wp-content/uploads/2026/01/Dep.-Altair-Silva-PP.jpg"
 alt="Altair Silva">
</div>
<div class="col">
<h3 class="lab-title-news">Altair Silva</h3>
<span class="lab-button px-2 py-1 lab-text mt-2" style="background: #404040;">PP</span>
</div>
</div>
</a>
<a href="https://www.alesc.sc.gov.br/deputado/altair-silva/">
<div class="d-flex align-items-center mt-2"></div></a>
"""
LISTA = """
<div class="card card-alesc mb-3">
<div class="card-body">
<h4 class="card-title">
<a href="/proposicoes/NQeb8">PL./0640/2026</a>        </h4>
<p class="mb-1 fst-italic" style="-webkit-line-clamp: 3;">Altera a Lei Estadual nº 19.720.</p>
<div>
<div class="row">
<div class="col-lg-2 text-lg-end fw-bold no-wrap">Entrada</div>
<div class="col-lg-10">07/10/2026</div>
</div>
<div class="row">
<div class="col-lg-2 text-lg-end fw-bold">Autoria</div>
<div class="col-lg-10"><ul class="m-0 list-unstyled"><li>Deputado Altair Silva</li>
<li>Deputada Paulinha</li></ul></div>
</div>
</div>
</div>
</div>
<div class="card card-alesc mb-3">
<div class="card-body">
<h4 class="card-title">
<a href="/proposicoes/X1">RQS/0012/2026</a>        </h4>
<div class="row">
<div class="col-lg-2 text-lg-end fw-bold">Autoria</div>
<div class="col-lg-10"><ul class="m-0 list-unstyled"><li>Deputada Paulinha</li></ul></div>
</div>
</div>
</div>
"""


def test_deputados_e_proposicoes():
    assert alesc.deputados(DEPUTADOS) == [{
        "slug": "altair-silva", "nome": "Altair Silva", "partido": "PP",
        "foto": "https://www.alesc.sc.gov.br/wp-content/uploads/2026/01/Dep.-Altair-Silva-PP.jpg",
    }]  # fmt: skip
    props = alesc.proposicoes(LISTA)
    assert [(p["id"], p["sigla"], p["autores"]) for p in props] == [
        ("NQeb8", "PL./0640/2026", ["Altair Silva", "Paulinha"]),
        ("X1", "RQS/0012/2026", ["Paulinha"]),
    ]
    assert alesc.tipo_e_numero("PL./0640/2026") == ("Projeto de Lei", 640, 2026)
    assert alesc.tipo_e_numero("RQS/0012/2026") == ("Requerimento", 12, 2026)
    props[0]["lista"], props[1]["lista"] = "processo-legislativo", "atividade-parlamentar"
    por = alesc.distribuir(props, {"Altair Silva", "Paulinha"})
    assert por["Paulinha"]["contagem"] == {"Projeto de Lei": 1, "Requerimento": 1}
    assert por["Altair Silva"]["projetos"][0]["primeiro_autor"] is True
    assert por["Paulinha"]["projetos"][0]["data_apresentacao"] == "2026-10-07"
