from datetime import UTC, datetime
from decimal import Decimal

from app.models import (
    ArrecadacaoUF,
    ContasMunicipio,
    FonteIngestao,
    Municipio,
    PopulacaoIbge,
    TransferenciaUniao,
)

BLU, FLN = "4202404", "4205407"


def _t(ano, mes, bloco, valor, ibge=None, uf="SC", fonte="tesouro"):
    return TransferenciaUniao(
        ano=ano, mes=mes, uf=uf, municipio_ibge=ibge, bloco=bloco, fonte=fonte, valor=Decimal(valor)
    )


def _popular(session):
    session.add_all(
        [
            Municipio(ibge=BLU, nome="Blumenau", uf="SC", nome_chave="BLUMENAU"),
            Municipio(ibge=FLN, nome="Florianópolis", uf="SC", nome_chave="FLORIANOPOLIS"),
            Municipio(ibge="4200051", nome="Sem repasse", uf="SC", nome_chave="SEM REPASSE"),
        ]
    )
    session.add(
        FonteIngestao(
            fonte="tesouro_transferencias",
            url="https://x",
            arquivo_raw="x",
            status="ok",
            concluido_em=datetime(2026, 10, 1, tzinfo=UTC),
        )
    )
    session.flush()
    session.add_all(
        [
            ArrecadacaoUF(uf="SC", ano=2024, mes=1, total=Decimal("10"), previdencia=Decimal("3")),
            ArrecadacaoUF(uf="SC", ano=2024, mes=2, total=Decimal("20"), previdencia=Decimal("4")),
            PopulacaoIbge(codigo="1", ano=2024, valor=200, origem="estimativa"),
            PopulacaoIbge(codigo="42", ano=2024, valor=5000, origem="estimativa"),
            PopulacaoIbge(codigo="42", ano=2022, valor=4800, origem="censo"),
            PopulacaoIbge(codigo=BLU, ano=2024, valor=1000, origem="estimativa"),
            PopulacaoIbge(codigo=FLN, ano=2024, valor=2000, origem="estimativa"),
            PopulacaoIbge(codigo=BLU, ano=2022, valor=900, origem="censo"),
            _t(2024, 1, "FPE", "70"),
            _t(2024, 1, "FPM", "100", BLU),
            _t(2024, 2, "FUNDEB_UNIAO", "50", BLU, fonte="portal"),
            _t(2024, 1, "FPM", "100", FLN),
            _t(2024, 2, "ROYALTIES", "50", FLN, fonte="portal"),
            _t(2023, 1, "FPM", "40", BLU),
            ContasMunicipio(
                municipio_ibge=BLU, ano=2023, receita_total=Decimal("400"),
                receita_propria=Decimal("100"), transf_uniao=Decimal("200"), despesa_por_area={},
            ),
        ]
    )  # fmt: skip
    session.flush()


def test_painel_totais_e_bloco_sem_dado(client, session):
    _popular(session)
    corpo = client.get("/dinheiro-federal?ano=2024").json()
    assert corpo["meses_com_dado"] == [1, 2]
    assert corpo["ano_em_curso"] is False and corpo["avisos"] == []
    brasil = corpo["brasil"]
    assert (brasil["populacao"], brasil["arrecadacao"], brasil["previdencia"]) == (200, 30, 7)
    assert brasil["repasse"] == 370
    assert brasil["blocos"]["FPM"] == 200 and brasil["blocos"]["IPI_EXP"] is None
    assert brasil["blocos_sem_dado"] == ["LEGAIS_VOLUNTARIAS", "IPI_EXP", "OUTRAS_OBRIG"]
    ufs = corpo["ufs"]
    assert len(ufs) == 27
    sc = next(u for u in ufs if u["uf"] == "SC")
    assert (sc["regiao"], sc["populacao"], sc["repasse"]) == ("Sul", 5000, 370)
    # Estado sem nenhum dado: nulo, nunca zero.
    ac = next(u for u in ufs if u["uf"] == "AC")
    assert ac["repasse"] is None and ac["arrecadacao"] is None and ac["populacao"] is None
    assert len(corpo["fontes"]) == 4
    assert corpo["fontes"][1]["atualizado_em"] is not None


def test_populacao_cai_para_o_censo_quando_o_ano_nao_tem(client, session):
    _popular(session)
    uf = client.get("/dinheiro-federal/SC?ano=2023").json()
    assert (uf["populacao"], uf["populacao_ano"], uf["populacao_origem"]) == (4800, 2022, "censo")
    cidade = next(c for c in uf["cidades"] if c["ibge"] == BLU)
    assert (cidade["populacao"], cidade["repasse"]) == (900, 40)


def test_estado_com_cidades_e_media(client, session):
    _popular(session)
    corpo = client.get("/dinheiro-federal/sc?ano=2024").json()
    assert (corpo["uf"], corpo["nome"], corpo["repasse"]) == ("SC", "Santa Catarina", 370)
    por_ibge = {c["ibge"]: c for c in corpo["cidades"]}
    assert (por_ibge[BLU]["repasse"], por_ibge[BLU]["fpm"], por_ibge[BLU]["outros"]) == (
        150,
        100,
        50,
    )
    assert por_ibge["4200051"]["repasse"] is None
    # (150 + 150) / (1000 + 2000): a cidade sem repasse não entra na média.
    assert corpo["media_estado_por_habitante"] == 0.1


def test_municipio_serie_e_contas(client, session):
    _popular(session)
    corpo = client.get(f"/municipios/{BLU}/dinheiro-federal").json()
    assert corpo["municipio"] == {"ibge": BLU, "nome": "Blumenau", "uf": "SC"}
    anos = {s["ano"]: s for s in corpo["serie"]}
    assert set(anos) == {2023, 2024}
    assert (anos[2024]["repasse"], anos[2024]["por_habitante"]) == (150, 0.15)
    assert anos[2024]["media_estado_por_habitante"] == 0.1
    assert anos[2023]["populacao"] == 900
    assert corpo["contas"]["ano"] == 2023
    assert (corpo["contas"]["parte_uniao"], corpo["contas"]["parte_propria"]) == (50.0, 25.0)


def test_404s(client, session):
    _popular(session)
    assert client.get("/dinheiro-federal/XX").status_code == 404
    assert client.get("/dinheiro-federal?ano=1999").status_code == 404
    assert client.get("/municipios/0000000/dinheiro-federal").status_code == 404
