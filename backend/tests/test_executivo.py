from datetime import UTC, date, datetime
from decimal import Decimal

from app.models import (
    AgendaCompromisso,
    Candidatura,
    ContasEstado,
    ContasMunicipio,
    FonteIngestao,
    Municipio,
    Pessoa,
    PessoaVinculo,
)
from ingestion.siconfi import contas_estados


def _ingestao(session, fonte):
    session.add(
        FonteIngestao(
            fonte=fonte,
            url="https://exemplo",
            arquivo_raw="x",
            status="ok",
            concluido_em=datetime.now(UTC),
        )
    )
    session.flush()


def _candidatura(session, sq, cargo, uf="SC", unidade="Santa Catarina", ibge=None, **extra):
    c = Candidatura(
        ano_eleicao=2022, sq_candidato=sq, cargo=cargo, uf=uf, unidade=unidade,
        nome="Fulano de Tal", nome_urna="Fulano", titulo=f"00000000{sq}",
        situacao_turno="ELEITO", genero="MASCULINO", partido="XX", municipio_ibge=ibge, **extra,
    )  # fmt: skip
    session.add(c)
    session.flush()
    return c


def _conta(uf, ano, populacao, despesa, receita=None):
    return ContasEstado(
        uf=uf,
        ano=ano,
        populacao=populacao,
        despesa_paga=despesa and Decimal(despesa),
        receita_total=Decimal(receita or 0) or None,
        despesa_por_area={"Saúde": 60.0, "Legislativa": 10.0} if despesa else {},
    )


def test_uf_por_codigo_cobre_27():
    assert len(contas_estados.UF_POR_CODIGO) == 27
    assert contas_estados.UF_POR_CODIGO["35"] == "SP" and contas_estados.UF_POR_CODIGO["53"] == "DF"


def test_contas_do_estado_com_media_e_ausentes(client, session):
    _ingestao(session, "siconfi_contas_estados")
    session.add_all(
        [
            _conta("SC", 2024, 1000, "70", "120"),
            _conta("SC", 2023, 1000, "50", "100"),
            _conta("SP", 2024, 2000, "300", "400"),  # 0,15 por habitante
            _conta("RJ", 2024, 1000, None, "10"),  # sem despesa informada: fora da média
        ]
    )
    session.flush()
    corpo = client.get("/estados/sc/contas").json()
    assert (corpo["ano"], corpo["despesa_por_habitante"], corpo["assembleia"]) == (2024, 0.07, 10.0)
    assert corpo["media_estados_despesa_por_habitante"] == 0.11  # (0,07 + 0,15) / 2
    assert (corpo["estados_na_media"], corpo["estados_sem_dado"]) == (2, 25)
    assert corpo["por_area"][0] == {"nome": "Saúde", "valor": 60.0, "percentual": 85.7}
    assert corpo["anterior"]["ano"] == 2023 and corpo["atualizado_em"] is not None
    assert client.get("/estados/AM/contas").status_code == 404  # estado sem contas
    assert client.get("/estados/XX/contas").status_code == 404


def test_painel_do_governador(client, session):
    _ingestao(session, "siconfi_contas_estados")
    session.add(_conta("SC", 2024, 1000, "70", "120"))
    gov = _candidatura(session, "11", "GOVERNADOR")
    vice = _candidatura(session, "12", "VICE-GOVERNADOR", chapa_titular_id=gov.id)
    session.flush()
    corpo = client.get(f"/executivo/{gov.id}/painel").json()
    assert corpo["ente"] == {"tipo": "estado", "nome": "Santa Catarina", "uf": "SC",
                             "municipio_ibge": None}  # fmt: skip
    assert corpo["titular"] is True and corpo["contas"]["disponivel"] is True
    assert corpo["contas"]["rota"] == "/estados/SC/contas"
    assert corpo["contas"]["dados"]["estados_sem_dado"] == 26
    assert corpo["emendas"]["disponivel"] is False and corpo["agenda"]["disponivel"] is False
    assert corpo["medidas_provisorias"]["disponivel"] is False
    assert client.get(f"/executivo/{vice.id}/painel").json()["titular"] is False


def test_painel_do_prefeito_traz_contas_do_municipio(client, session):
    _ingestao(session, "siconfi_contas")
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    session.add(
        ContasMunicipio(municipio_ibge="4202404", ano=2024, populacao=1000,
                        receita_total=Decimal("120"), despesa_paga=Decimal("70"),
                        despesa_por_area={"Saúde": 60.0})
    )  # fmt: skip
    prefeito = _candidatura(session, "21", "PREFEITO", unidade="Blumenau", ibge="4202404")
    session.flush()
    corpo = client.get(f"/executivo/{prefeito.id}/painel").json()
    assert corpo["ente"]["tipo"] == "municipio" and corpo["ente"]["nome"] == "Blumenau"
    assert corpo["contas"]["rota"] == "/municipios/4202404/contas"
    assert corpo["contas"]["dados"]["despesa_por_habitante"] == 0.07
    assert corpo["emendas"]["disponivel"] is False  # nenhuma emenda no município
    assert corpo["contratos"]["disponivel"] is False
    assert "Nenhuma emenda" in corpo["emendas"]["motivo"]


def test_agenda_do_vice_ministro_e_painel_federal(client, session):
    _ingestao(session, "eagendas")
    pessoa = Pessoa(nome="Fulano de Tal", chave_nome="FULANO DE TAL", cpf="00012345600")
    session.add(pessoa)
    session.flush()
    vice = _candidatura(session, "31", "VICE-PRESIDENTE", uf="BR", unidade="Brasil")
    session.add(PessoaVinculo(pessoa_id=pessoa.id, fonte="candidatura",
                              id_externo=f"2022:{vice.sq_candidato}", regra="cpf"))  # fmt: skip
    for i, (tipo, dia, entidades) in enumerate(
        [("reuniao", date(2026, 9, 1), ["FENATRAD"]), ("reuniao", date(2026, 9, 2), ["FENATRAD"]),
         ("viagem", date(2025, 3, 3), None)]
    ):  # fmt: skip
        session.add(AgendaCompromisso(
            pessoa_id=pessoa.id, tipo=tipo, id_registro=i, data_inicio=dia, assunto="Pauta",
            entidades_privadas=entidades, n_participantes_privados=len(entidades or []),
            participantes_publicos=[{"nome": "Beltrano", "cargo": "X", "orgao": "Y"}],
            n_participantes_publicos=1,
        ))  # fmt: skip
    session.flush()
    corpo = client.get(f"/executivo/{vice.id}/painel").json()
    assert corpo["ente"]["tipo"] == "uniao" and corpo["pessoa_id"] == pessoa.id
    agenda = corpo["agenda"]
    assert agenda["disponivel"] is True and agenda["atualizado_em"] is not None
    assert agenda["dados"]["total"] == 3
    assert agenda["dados"]["por_tipo"] == {"Reunião": 2, "Viagem": 1}
    assert agenda["dados"]["entidades_mais_citadas"] == [{"nome": "FENATRAD", "registros": 2}]
    assert agenda["rota"] == f"/executivo/{vice.id}/agenda"
    assert corpo["viagens_cartao"]["disponivel"] is False

    lista = client.get(f"/executivo/{vice.id}/agenda").json()
    assert lista["total"] == 3 and lista["itens"][0]["data_inicio"] == "2026-09-02"
    assert lista["itens"][0]["participantes_publicos"][0]["nome"] == "Beltrano"
    assert "presidente da República" in lista["nota"]
    assert client.get(f"/executivo/{vice.id}/agenda?tipo=viagem").json()["total"] == 1
    assert client.get(f"/executivo/{vice.id}/agenda?ano=2026").json()["total"] == 2
    assert client.get(f"/executivo/{vice.id}/agenda?tipo=xx").status_code == 422


def test_painel_recusa_cargo_que_nao_e_executivo(client, session):
    vereador = _candidatura(session, "41", "VEREADOR")
    assert client.get(f"/executivo/{vereador.id}/painel").status_code == 404
    assert client.get("/executivo/999999/agenda").status_code == 404
