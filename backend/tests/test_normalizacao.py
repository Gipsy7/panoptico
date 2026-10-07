from ingestion.camara import deputados
from ingestion.senado import senadores
from tests.conftest import carregar_fixture


def test_normalizar_deputados():
    registros = deputados.normalizar(carregar_fixture("camara_deputados.json"))
    assert len(registros) == 3
    primeiro = registros[0]
    assert primeiro["id_externo"].isdigit()
    assert len(primeiro["uf"]) == 2
    assert primeiro["pagina_url"] == f"https://www.camara.leg.br/deputados/{primeiro['id_externo']}"
    assert primeiro["fonte_url"].startswith("https://dadosabertos.camara.leg.br/api/v2/deputados/")
    assert all(r["nome_parlamentar"] for r in registros)


def test_normalizar_senadores():
    registros = senadores.normalizar(carregar_fixture("senado_senadores.json"))
    assert len(registros) == 3
    for r in registros:
        assert r["id_externo"].isdigit()
        assert len(r["uf"]) == 2
        assert r["foto_url"] is None or r["foto_url"].startswith("https://")
        assert r["fonte_url"].endswith(f"/senador/{r['id_externo']}")
    # o primeiro tem o telefone como objeto (não lista) na fixture
    assert registros[0]["telefone"].startswith("(61) ")


def test_normalizar_senadores_suplente_sem_uf_na_identificacao():
    payload = carregar_fixture("senado_senadores.json")
    primeiro = payload["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"][0]
    uf = primeiro["IdentificacaoParlamentar"].pop("UfParlamentar")
    primeiro["Mandato"]["UfParlamentar"] = uf
    assert senadores.normalizar(payload)[0]["uf"] == uf


def test_normalizar_senadores_aceita_parlamentar_unico():
    payload = carregar_fixture("senado_senadores.json")
    lista = payload["ListaParlamentarEmExercicio"]["Parlamentares"]
    lista["Parlamentar"] = lista["Parlamentar"][0]
    assert len(senadores.normalizar(payload)) == 1
