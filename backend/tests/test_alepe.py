from ingestion.assembleias import alepe

# Recortes reais da API da ALEPE (09/10/2026).
PROJETOS = """<?xml version='1.0' encoding='utf-8'?><projetos>
<projeto docid="16370" numero="33" ano="2026" legislatura="VIGÉSIMA "
 tipo="PROPOSTA DE EMENDA A CONSTITUIÇÃO" subtipo=""
 ementa="Altera a Constituição do Estado de Pernambuco." dataPublicacao="31/03/2026">
 <autores><autor nome="João Paulo do PT" tipo="DEPUTADO"/>
 <autor nome="Dani Portela" tipo="DEPUTADO"/></autores></projeto>
<projeto docid="1" numero="1" ano="2026" tipo="PROJETO DE LEI ORDINÁRIA" ementa="X"
 dataPublicacao="01/02/2026">
 <autores><autor nome="Governadora" tipo="EXTERNO"/></autores></projeto>
</projetos>""".encode()  # fmt: skip
INDICACOES = b"""<?xml version='1.0' encoding='utf-8'?><indicacoes>
<indicacao docid="31056" numero="14789" ano="2026" tipo="indicacao"
 ementa="&lt;p&gt;Indicamos &amp;agrave; Mesa&lt;/p&gt;" dataPublicacao="03/02/2026">
 <autores><autor nome="Dani Portela" tipo="DEPUTADO"/></autores></indicacao>
</indicacoes>"""  # fmt: skip


def test_proposicoes_e_distribuicao():
    props = alepe.proposicoes(PROJETOS, "projetos") + alepe.proposicoes(INDICACOES, "indicacoes")
    assert len(props) == 2  # a do Executivo (autor EXTERNO) fica de fora
    assert alepe._texto(props[1]["ementa"]) == "Indicamos à Mesa"
    por = alepe.distribuir(props, {"João Paulo do PT", "Dani Portela"})
    assert por["Dani Portela"]["contagem"] == {
        "Proposta de Emenda a Constituição": 1,
        "Indicação": 1,
    }
    projeto = por["João Paulo do PT"]["projetos"][0]
    assert (projeto["primeiro_autor"], projeto["data_apresentacao"]) == (True, "2026-03-31")
    assert por["Dani Portela"]["projetos"][0]["primeiro_autor"] is False
    assert projeto["url"] == "https://www.alepe.pe.gov.br/proposicao-texto-completo/?docid=16370"
