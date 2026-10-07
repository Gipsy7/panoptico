import httpx
import pytest
import respx

from app.services.cep import (
    CepIndisponivel,
    CepInvalido,
    CepNaoEncontrado,
    buscar_cep,
    normalizar_cep,
)

URL_PAULISTA = "https://viacep.com.br/ws/01310100/json/"


@pytest.mark.parametrize("entrada", ["01310-100", "01310100", " 01.310-100 "])
def test_normalizar_cep_aceita_formatos(entrada):
    assert normalizar_cep(entrada) == "01310100"


@pytest.mark.parametrize("entrada", ["", "123", "0131010000", "abcdefgh"])
def test_normalizar_cep_rejeita_invalidos(entrada):
    with pytest.raises(CepInvalido):
        normalizar_cep(entrada)


@respx.mock
def test_buscar_cep_valido():
    respx.get(URL_PAULISTA).respond(
        json={"cep": "01310-100", "localidade": "São Paulo", "uf": "SP", "ibge": "3550308"}
    )
    local = buscar_cep("01310-100")
    assert (local.uf, local.municipio, local.codigo_ibge) == ("SP", "São Paulo", "3550308")


@respx.mock
def test_buscar_cep_usa_cache():
    rota = respx.get(URL_PAULISTA).respond(
        json={"localidade": "São Paulo", "uf": "SP", "ibge": "3550308"}
    )
    buscar_cep("01310100")
    buscar_cep("01310-100")
    assert rota.call_count == 1


@respx.mock
def test_buscar_cep_inexistente():
    respx.get("https://viacep.com.br/ws/99999999/json/").respond(json={"erro": "true"})
    with pytest.raises(CepNaoEncontrado):
        buscar_cep("99999999")


@respx.mock
def test_buscar_cep_timeout():
    respx.get(URL_PAULISTA).mock(side_effect=httpx.ConnectTimeout("timeout"))
    with pytest.raises(CepIndisponivel):
        buscar_cep("01310100")


@respx.mock
def test_buscar_cep_erro_500():
    respx.get(URL_PAULISTA).respond(status_code=503)
    with pytest.raises(CepIndisponivel):
        buscar_cep("01310100")
