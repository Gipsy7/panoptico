import json

from app.textos import limpar_texto


def test_tira_surrogate_solto_e_caractere_de_substituicao():
    # forma reportada para "ÁGUA": substituição + surrogate solto no lugar do "Á"
    assert limpar_texto("ABASTECIMENTO �\udc81GUA SANASA") == "ABASTECIMENTO GUA SANASA"
    json.dumps(limpar_texto("A\udc81B"), ensure_ascii=False).encode("utf-8")  # não levanta


def test_conserta_mojibake_de_utf8_lido_como_latin1():
    estragado = "SOCIEDADE ABASTECIMENTO ÁGUA".encode().decode("latin-1")
    assert estragado != "SOCIEDADE ABASTECIMENTO ÁGUA"
    assert limpar_texto(estragado) == "SOCIEDADE ABASTECIMENTO ÁGUA"
    assert limpar_texto("Ação".encode().decode("cp1252")) == "Ação"


def test_texto_normal_fica_igual():
    for t in ("ASSOCIAÇÃO BENEFICENTE", "CÂMARA MUNICIPAL", "TERMO Nº 2", "15ª REGIÃO"):
        assert limpar_texto(t) == t


def test_controles_e_espacos():
    assert limpar_texto("MA\x81QUINAS  LTDA\t") == "MAQUINAS LTDA"
    assert limpar_texto(None) is None
