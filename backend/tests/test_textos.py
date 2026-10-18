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


def test_sem_cpf_casos_reais_do_tce():
    from app.textos import sem_cpf

    # MEI: o CNPJ é válido, mas a fonte põe o CPF no nome
    assert sem_cpf("ELENISE FREIER BEIER 00594280079") == "ELENISE FREIER BEIER"
    assert sem_cpf("ALTEMAR CHAVES907994290078") == "ALTEMAR CHAVES"
    assert sem_cpf("KAIO CESAR CABRAL 138872521874-ME") == "KAIO CESAR CABRAL -ME"
    assert sem_cpf("JOSE 123.456.789-01 ME") == "JOSE ME"
    assert sem_cpf("TATIANI ZINN DE MOURA (MEI) CPF: 030121500-64") == "TATIANI ZINN DE MOURA (MEI)"
    assert sem_cpf("LEANDRO MARCO DA SILVA-141.804.818-63") == "LEANDRO MARCO DA SILVA"
    assert sem_cpf("EVANDRO MEZZOMO - 029.568.410-09") == "EVANDRO MEZZOMO"
    assert sem_cpf("EDUARDO PEREIRA 714659360-68") == "EDUARDO PEREIRA"
    assert sem_cpf("MARIA ***.123.456-** EPP") == "MARIA EPP"
    # CNPJ de 14 dígitos (solto, entre parênteses ou formatado) e nome comum ficam intactos
    assert sem_cpf("FRATERNIDADE CURUMIM 00938214000103") == "FRATERNIDADE CURUMIM 00938214000103"
    assert sem_cpf("RODRIGO LONGO MEI (14619280000125)") == "RODRIGO LONGO MEI (14619280000125)"
    assert sem_cpf("EMPRESA 12.345.678/0001-95") == "EMPRESA 12.345.678/0001-95"
    assert sem_cpf("BMS CONSTRUCOES LTDA") == "BMS CONSTRUCOES LTDA"
    assert sem_cpf(None) is None
    assert sem_cpf("12345678901") is None
    # CPF truncado ou com espaço no lugar do traço
    assert sem_cpf("MAURO RADUNZ CTA CPF 767.942.700 30") == "MAURO RADUNZ CTA"
    assert sem_cpf("DOUGLAS DE SOUZA-2270762061") == "DOUGLAS DE SOUZA"
    assert sem_cpf("ALEXANDRE PEIXOTO DA SILVA 288.898.078-9") == "ALEXANDRE PEIXOTO DA SILVA"
