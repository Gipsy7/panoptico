# ruff: noqa: E501  (recortes dos XML reais da ALESP)
import io
from decimal import Decimal

from ingestion.assembleias import alesp

DEPUTADOS = b"""<?xml version="1.0" encoding="UTF-8"?><Deputados>
<Deputado><IdDeputado>1139</IdDeputado><IdSPL>1000000335</IdSPL><Matricula>300607</Matricula><NomeParlamentar>Agente Federal Danilo Balas</NomeParlamentar><Partido>PL</Partido><Situacao>EXE</Situacao><Email>apfdanilobalas@al.sp.gov.br</Email></Deputado>
<Deputado><IdDeputado>1</IdDeputado><IdSPL>9</IdSPL><Matricula>1</Matricula><NomeParlamentar>Antigo</NomeParlamentar><Situacao>AFA</Situacao></Deputado>
</Deputados>"""
PROPOSITURAS = b"""<?xml version="1.0" encoding="UTF-8"?><proposituras>
<propositura><AnoLegislativo>2025</AnoLegislativo><Ementa>Institui o Dia  Estadual do Teste.</Ementa><DtPublicacao>2025-03-01T00:00:00-03:00</DtPublicacao><IdDocumento>500</IdDocumento><IdNatureza>1</IdNatureza><NroLegislativo>123</NroLegislativo></propositura>
<propositura><AnoLegislativo>2025</AnoLegislativo><Ementa>x</Ementa><IdDocumento>501</IdDocumento><IdNatureza>9</IdNatureza><NroLegislativo>9</NroLegislativo></propositura>
<propositura><AnoLegislativo>1996</AnoLegislativo><Ementa>antiga</Ementa><IdDocumento>3631</IdDocumento><IdNatureza>1</IdNatureza><NroLegislativo>728</NroLegislativo></propositura>
</proposituras>"""
AUTORES = b"""<?xml version="1.0" encoding="UTF-8"?><documentos_autores>
<DocumentoAutor><IdAutor>1000000335</IdAutor><IdDocumento>500</IdDocumento><NomeAutor>Danilo Balas</NomeAutor></DocumentoAutor>
<DocumentoAutor><IdAutor>1000000335</IdAutor><IdDocumento>501</IdDocumento><NomeAutor>Danilo Balas</NomeAutor></DocumentoAutor>
<DocumentoAutor><IdAutor>105</IdAutor><IdDocumento>3631</IdDocumento><NomeAutor>Governador</NomeAutor></DocumentoAutor>
</documentos_autores>"""
DESPESAS = """<?xml version="1.0" encoding="UTF-8"?><despesas>
<despesa><Ano>2025</Ano><Matricula>300607</Matricula><Mes>3</Mes><Valor>200.0</Valor><Tipo>A - COMBUSTÍVEIS E LUBRIFICANTES</Tipo></despesa>
<despesa><Ano>2025</Ano><Matricula>300607</Matricula><Mes>3</Mes><Valor>95.4</Valor><Tipo>A - COMBUSTÍVEIS E LUBRIFICANTES</Tipo></despesa>
<despesa><Ano>2015</Ano><Matricula>300607</Matricula><Mes>3</Mes><Valor>1.0</Valor><Tipo>N - MORADIA</Tipo></despesa>
</despesas>""".encode()


def test_deputados_em_exercicio():
    assert [d["NomeParlamentar"] for d in alesp.deputados(io.BytesIO(DEPUTADOS))] == [
        "Agente Federal Danilo Balas"
    ]


def test_projetos_contagem_e_periodo():
    props = alesp.proposituras(io.BytesIO(PROPOSITURAS), {2025, 2026})
    assert set(props) == {"500", "501"}  # a de 1996 fica de fora
    autores = alesp.autorias(io.BytesIO(AUTORES), set(props))
    dep = alesp.distribuir(props, autores, {"1000000335"})["1000000335"]
    assert dep["contagem"] == {"Projeto de Lei": 1, "Indicação": 1}
    projeto = dep["projetos"][0]
    assert projeto["ementa"] == "Institui o Dia Estadual do Teste."
    assert projeto["url"] == "https://www.al.sp.gov.br/propositura/?id=500"
    assert projeto["numero"] == 123 and projeto["primeiro_autor"]


def test_gastos_somados_por_mes_e_categoria():
    soma = alesp.gastos(io.BytesIO(DESPESAS), {2025, 2026}, {"300607"})
    assert soma["300607"] == [
        {
            "ano": 2025,
            "mes": 3,
            "categoria": "Combustíveis e lubrificantes",
            "valor": Decimal("295.4"),
        }
    ]
