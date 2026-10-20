# ruff: noqa: E501  (recortes reais das páginas e do CSV da ALESC)
from decimal import Decimal
from pathlib import Path

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


# Recortes reais do CSV de gastos (transparencia.alesc.sc.gov.br) e das páginas do e-Legis.
def _csv() -> bytes:
    return (Path(__file__).parent / "fixtures" / "alesc_gastos.csv").read_bytes()


def test_gastos_somam_por_conta_mes_e_descricao():
    contas = alesc.gastos_do_csv(_csv())  # UTF-8 com BOM, ";" e vírgula decimal
    assert contas["Ana Paula da Silva (Paulinha)"] == {
        (2025, 5, "Jornais e Revistas"): Decimal("1657.00")
    }  # duas notas no mesmo mês
    altair = contas["Altair Silva"]
    assert altair[(2025, 10, "Jornais e Revistas")] == Decimal("924.00")
    assert altair[(2025, 5, "Devolução Diária Deputado")] == Decimal("-1035.00")  # devolução


def test_gastos_ligam_ao_deputado_pelo_nome_e_apontam_sobras():
    contas = alesc.gastos_do_csv(_csv())
    por, sobras = alesc.distribuir_gastos(contas, ["Altair Silva", "Paulinha", "Berlanda"])
    assert {g["categoria"] for g in por["Altair Silva"]} == {
        "Jornais e Revistas",
        "Devolução Diária Deputado",
    }
    assert por["Paulinha"] == [
        {"ano": 2025, "mes": 5, "categoria": "Jornais e Revistas", "valor": Decimal("1657.00")}
    ]  # o apelido entre parênteses liga "Ana Paula da Silva (Paulinha)"
    assert "Berlanda" not in por and sobras == ["Marquito"]  # ex-deputado: fica de fora


SESSOES = """
<div class="card card-alesc mb-4">
  <div class="card-body">
    <h4 class="mb-1">
        95ª Sessão Ordinária                </h4>
    <span class="text-nowrap"><i class="far fa-clock"></i> 14/10/2026 às 14:00 </span>
    <span class="badge rounded-pill bg-light text-secondary-emphasis"><i class="fas fa-circle fa-2xs text-success"></i> Realizada</span>
    <a href="/sessoes-plenarias/zlmlK/presenca" class="btn btn-sm">Presença</a>
  </div>
</div>
<div class="card card-alesc mb-4">
  <h4 class="mb-1"> 97ª Sessão Ordinária </h4> 20/10/2026
  <span class="badge rounded-pill bg-light"><i class="fas fa-circle"></i> Horário regimental</span>
  <a href="/sessoes-plenarias/KvZvK/presenca">Presença</a>
</div>
"""
PRESENCA = """
<table class="table table-hover">
  <tr>
    <td>Altair Silva</td>
    <td>Presente</td>
  </tr>
  <tr>
    <td>Paulinha</td>
    <td>Ausência justificada</td>
  </tr>
  <tr>
    <td>Alguém Que Saiu</td>
    <td>Presente</td>
  </tr>
</table>
"""


def test_presenca_das_sessoes_realizadas():
    sessoes = alesc.sessoes_realizadas(SESSOES)
    assert [(s["id"], s["data"], s["situacao"]) for s in sessoes] == [
        ("zlmlK", "2026-10-14", "Realizada"),
        ("KvZvK", "2026-10-20", "Horário regimental"),
    ]
    assert alesc.presenca_da_sessao(PRESENCA)[1] == ("Paulinha", "Ausência justificada")
    for s in sessoes:
        s["linhas"] = alesc.presenca_da_sessao(PRESENCA)
    frequencia = alesc.contar_presenca(sessoes, ["Altair Silva", "Paulinha"])
    # Só a sessão realizada conta; a que ainda não aconteceu não entra nem como falta.
    assert frequencia == {"Altair Silva": (1, 1), "Paulinha": (1, 0)}
