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
    props, citadas = alesp.proposituras(io.BytesIO(PROPOSITURAS), {2025, 2026}, {"3631"})
    assert set(props) == {"500", "501"}  # a de 1996 fica de fora da autoria...
    assert set(citadas) == {"3631"}  # ...mas entra se foi votada numa comissão
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


# Recortes de comissoes_permanentes_reunioes.xml, comissoes.xml, comissoes_permanentes_votacoes.xml
# e proposituras (LDO de 2027, votada na Comissão de Finanças em 07/07 e 21/07/2026).
REUNIOES = """<?xml version="1.0" encoding="UTF-8"?><ComissoesReunioes>
<ReuniaoComissao><Situacao>REALIZADA</Situacao><Data>2026-07-21T00:00:00-03:00</Data><IdComissao>12445</IdComissao><IdPauta>1000008646</IdPauta><IdReuniao>1000007775</IdReuniao><Presidente>Deputado Gilmaci Santos</Presidente><NrConvocacao>2A. REUNIÃO</NrConvocacao><NrLegislatura>20</NrLegislatura><TipoConvocacao>E</TipoConvocacao><CodSituacao>R</CodSituacao></ReuniaoComissao>
<ReuniaoComissao><Situacao>REALIZADA</Situacao><Data>2026-07-07T00:00:00-03:00</Data><IdComissao>12445</IdComissao><IdPauta>1000008618</IdPauta><IdReuniao>1000007752</IdReuniao><Presidente>Deputado Gilmaci Santos</Presidente><NrConvocacao>1A. REUNIÃO</NrConvocacao><NrLegislatura>20</NrLegislatura><TipoConvocacao>E</TipoConvocacao><CodSituacao>R</CodSituacao></ReuniaoComissao>
<ReuniaoComissao><Situacao>ENCERRADA</Situacao><Data>2012-10-30T00:00:00-02:00</Data><IdComissao>12453</IdComissao><IdPauta>54572</IdPauta><IdReuniao>10894</IdReuniao><Presidente>Deputado Beto Trícoli</Presidente><NrConvocacao>7A. REUNIÃO</NrConvocacao><NrLegislatura>17</NrLegislatura><TipoConvocacao>O</TipoConvocacao><CodSituacao>E</CodSituacao></ReuniaoComissao>
</ComissoesReunioes>""".encode()
COMISSOES = """<?xml version="1.0" encoding="UTF-8"?><Comissoes>
<Comissao><IdComissao>12445</IdComissao><NomeComissao>Comissão de Finanças, Orçamento e Planejamento</NomeComissao><SiglaComissao>CFOP</SiglaComissao></Comissao>
</Comissoes>""".encode()
VOTOS = """<?xml version="1.0" encoding="UTF-8"?><ComissoesReunioesVotacao>
<ReuniaoComissaoVotacao><Voto>Favorável ao voto do relator </Voto><IdComissao>12445</IdComissao><IdDeputado>10603</IdDeputado><IdDocumento>1000688517</IdDocumento><IdPauta>1000008646</IdPauta><IdReuniao>1000007775</IdReuniao><Deputado>Gilmaci Santos</Deputado><TipoVoto>F</TipoVoto></ReuniaoComissaoVotacao>
<ReuniaoComissaoVotacao><Voto>Favorável ao voto do relator </Voto><IdComissao>12445</IdComissao><IdDeputado>431</IdDeputado><IdDocumento>1000688517</IdDocumento><IdPauta>1000008646</IdPauta><IdReuniao>1000007775</IdReuniao><Deputado>Enio Tatto</Deputado><TipoVoto>F</TipoVoto></ReuniaoComissaoVotacao>
<ReuniaoComissaoVotacao><Voto>Contrário ao voto do relator </Voto><IdComissao>12445</IdComissao><IdDeputado>12416</IdDeputado><IdDocumento>1000688517</IdDocumento><IdPauta>1000008646</IdPauta><IdReuniao>1000007775</IdReuniao><Deputado>João Paulo Rillo</Deputado><TipoVoto>C</TipoVoto></ReuniaoComissaoVotacao>
<ReuniaoComissaoVotacao><Voto>Não registrou voto</Voto><IdComissao>12445</IdComissao><IdDeputado>431</IdDeputado><IdDocumento>1000688517</IdDocumento><IdPauta>1000008618</IdPauta><IdReuniao>1000007752</IdReuniao><Deputado>Enio Tatto</Deputado><TipoVoto>F</TipoVoto></ReuniaoComissaoVotacao>
<ReuniaoComissaoVotacao><Voto>Favorável à moção e contrário ao voto do relator.</Voto><IdComissao>12445</IdComissao><IdDeputado>10603</IdDeputado><IdDocumento>1000688517</IdDocumento><IdPauta>1000008618</IdPauta><IdReuniao>1000007752</IdReuniao><Deputado>Gilmaci Santos</Deputado><TipoVoto>P</TipoVoto></ReuniaoComissaoVotacao>
<ReuniaoComissaoVotacao><Voto>Favorável ao parecer </Voto><IdComissao>8509</IdComissao><IdDeputado>4926</IdDeputado><IdDocumento>527812</IdDocumento><IdPauta>49344</IdPauta><IdReuniao>6599</IdReuniao><Deputado>Mauro Bragato</Deputado><TipoVoto>F</TipoVoto></ReuniaoComissaoVotacao>
<ReuniaoComissaoVotacao><Voto>Favorável ao voto do relator </Voto><IdComissao>12445</IdComissao><IdDeputado>12416</IdDeputado><IdDocumento>1000600000</IdDocumento><IdPauta>1000008646</IdPauta><IdReuniao>1000007775</IdReuniao><Deputado>João Paulo Rillo</Deputado><TipoVoto>F</TipoVoto></ReuniaoComissaoVotacao>
</ComissoesReunioesVotacao>""".encode()
LDO = """<?xml version="1.0" encoding="UTF-8"?><proposituras>
<propositura><AnoLegislativo>2026</AnoLegislativo><Ementa>Dispõe sobre as Diretrizes Orçamentárias para o exercício de 2027.</Ementa><DtEntradaSistema>2026-04-30T00:00:00-03:00</DtEntradaSistema><DtPublicacao>2026-05-04T00:00:00-03:00</DtPublicacao><IdDocumento>1000688517</IdDocumento><IdNatureza>1</IdNatureza><NroLegislativo>407</NroLegislativo></propositura>
</proposituras>""".encode()
EM_EXERCICIO = {"10603", "431"}  # IdSPL de Gilmaci Santos e Enio Tatto; Rillo não está no cargo
DIA_21 = "3b9ae85f-3ba54b85"  # reunião 1000007775 e documento 1000688517, em hexadecimal
DIA_7 = "3b9ae848-3ba54b85"  # reunião 1000007752


def _comissoes():
    periodo = alesp.reunioes(io.BytesIO(REUNIOES), {2025, 2026})
    votos = alesp.votos_em_comissao(io.BytesIO(VOTOS), periodo)
    _, votadas = alesp.proposituras(
        io.BytesIO(LDO), {2025, 2026}, {v["IdDocumento"] for v in votos}
    )
    nomes = alesp.comissoes(io.BytesIO(COMISSOES))
    return alesp.votacoes_em_comissao(votos, periodo, nomes, votadas, EM_EXERCICIO)


def test_votacoes_em_comissao():
    periodo = alesp.reunioes(io.BytesIO(REUNIOES), {2025, 2026})
    assert set(periodo) == {"1000007775", "1000007752"}  # a de 2012 fica de fora
    resultado = _comissoes()
    votacoes = {v["id_externo"]: v for v in resultado["votacoes"]}
    # A reunião 6599 não está no arquivo de reuniões (sem data): fica de fora. A votação só
    # com quem não está no cargo (documento 1000600000) também.
    assert set(votacoes) == {DIA_21, DIA_7}
    assert votacoes[DIA_21] == {
        "id_externo": DIA_21,
        "materia": "Comissão de Finanças, Orçamento e Planejamento: Projeto de Lei nº 407 de 2026",
        "resultado": None,
        "sim": 2,
        "nao": 1,  # o voto de quem já saiu entra nos totais, não na lista de votos
        "abstencoes": 0,
        "data": "2026-07-21",
        "url": "https://www.al.sp.gov.br/propositura/?id=1000688517",
    }
    # "Não registrou voto" vem com a letra F, mas não é voto favorável.
    assert (votacoes[DIA_7]["sim"], votacoes[DIA_7]["nao"]) == (1, 0)
    votos = {(v["votacao"], v["parlamentar"]): v["voto"] for v in resultado["votos"]}
    assert votos == {
        (DIA_21, "10603"): "Favorável ao voto do relator",
        (DIA_21, "431"): "Favorável ao voto do relator",
        (DIA_7, "431"): "Não votou",
        (DIA_7, "10603"): "Favorável à proposição",  # texto longo demais: rótulo da letra
    }


def test_documento_sem_propositura():
    assert alesp.descrever("300798", None) == "documento 300798"


def test_gravar_votos_em_comissao(client, session):
    deputados = [
        {"id_externo": i, "nome": nome, "nome_completo": None, "partido": "PT", "foto_url": None,
         "email": None, "telefone": None, "titular": True, "em_exercicio": True, "inicio": None, "fim": None,
         "proposicoes_por_tipo": {}, "projetos": [], "sessoes": None, "presencas": None, "gastos": []}
        for i, nome in (("10603", "Gilmaci Santos"), ("431", "Enio Tatto"))
    ]  # fmt: skip
    casa = {"base": alesp.SITE, "legislatura": None, "vereadores": deputados, **_comissoes()}
    assert alesp.gravar(session, casa) == 2
    assert alesp.gravar(session, casa) == 2  # recarga substitui, não duplica
    session.flush()
    itens = client.get("/estados/SP/assembleia").json()["itens"]
    enio = next(i for i in itens if i["nome"] == "Enio Tatto")
    votos = client.get(f"/vereadores/{enio['id']}/votacoes").json()
    assert votos["casa_registra"] and (votos["total"], votos["votou"]) == (2, 1)
    recente = votos["itens"][0]
    assert recente["data"] == "2026-07-21"
    assert recente["materia"].startswith("Comissão de Finanças, Orçamento e Planejamento: ")
    assert recente["url"] == "https://www.al.sp.gov.br/propositura/?id=1000688517"
    assert votos["fonte_nome"] == "Dados abertos da Assembleia de São Paulo (ALESP)"
