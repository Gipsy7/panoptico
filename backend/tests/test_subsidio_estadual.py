from app.models import MandatoLocal
from app.services import subsidio_estadual

UFS = ("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO").split()


def test_csv_tem_as_27_ufs_e_so_numero_publicado_com_fonte():
    tabela = subsidio_estadual._tabela()
    assert sorted(tabela) == sorted(UFS)
    com_valor = 0
    for uf in UFS:
        d = subsidio_estadual.da_uf(uf)
        assert d is not None and d["observacao"]  # sem valor: o motivo; com valor: a nota
        if d["valor"] is not None:
            com_valor += 1
            # Com valor, a fonte oficial é obrigatória; teto: 75% do subsídio federal.
            assert d["fonte_url"] and d["ato_normativo"]
            assert 20_000 < d["valor"] <= 34_777
        else:
            assert d["fonte_url"] is None
    assert com_valor >= 10


def test_valor_de_sao_paulo_e_do_ato():
    d = subsidio_estadual.da_uf("sp")
    assert d["valor"] == 34774.64
    assert "18.384" in d["ato_normativo"]
    assert str(d["vigente_desde"]) == "2026-01-01"


def test_perfil_do_deputado_estadual_traz_o_subsidio(session, client):
    def mandato(uf, ibge_externo):
        m = MandatoLocal(
            casa="assembleia", uf=uf, id_externo=ibge_externo, nome="Fulana", titular=True,
            em_exercicio=True, proposicoes_por_tipo={}, sapl_url="https://exemplo.leg.br/",
        )  # fmt: skip
        session.add(m)
        session.flush()
        return m.id

    sp, ac = mandato("SP", "1"), mandato("AC", "2")
    com = client.get(f"/vereadores/{sp}").json()["subsidio"]
    assert com["valor"] == 34774.64 and com["fonte_url"].startswith("https://")
    sem = client.get(f"/vereadores/{ac}").json()["subsidio"]
    assert sem["valor"] is None and sem["observacao"]
