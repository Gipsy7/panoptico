"""Avisos por lugar (cidade, estado, Brasil): linha de base, fatos por assunto, filtro de assuntos,
frequência semanal e rotas."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.models import (
    AvisoAlvo,
    AvisoEvento,
    AvisoInscricao,
    EmendaPagamento,
    FonteIngestao,
    HomicidioSim,
    Municipio,
    ObraFederal,
    ObraFederalMunicipio,
)
from app.services import avisos as servico
from app.services import avisos_lugar
from tests.test_avisos import (  # noqa: F401  (_ligar: liga os avisos nestes testes também)
    AGORA,
    BASE,
    HOJE,
    Correio,
    _alvo,
    _inscricao,
    _ligar,
    _proposicao,
    _semear_vazio,
    _tramitacao,
)

DOMINGO = datetime(2026, 11, 1, 15, 0, tzinfo=UTC)


def _gaspar(session):
    session.add(Municipio(ibge="4205902", nome="Gaspar", uf="SC", nome_chave="GASPAR"))
    session.flush()


def _obra(session, situacao):
    o = session.get(ObraFederal, "1314.42-81")
    if o is None:
        session.add(ObraFederal(id_unico="1314.42-81", nome="BR-470", situacao=situacao, uf="SC"))
        session.flush()
        session.add(ObraFederalMunicipio(obra_id="1314.42-81", municipio_ibge="4205902"))
    else:
        o.situacao = situacao
    session.flush()


def _do_lugar(session, alvo):
    return list(
        session.scalars(
            select(AvisoEvento)
            .where(AvisoEvento.alvo_tipo == "lugar", AvisoEvento.alvo_chave == alvo)
            .order_by(AvisoEvento.id)
        )
    )


def test_obra_vista_pela_primeira_vez_e_linha_de_base_e_a_mudanca_avisa(session):
    _gaspar(session)
    i = _inscricao(session)
    _alvo(session, i, "lugar", "mun:4205902")
    _obra(session, "Em execução")
    servico.detectar(session, AGORA)
    primeiro = _do_lugar(session, "mun:4205902")
    assert len(primeiro) == 1 and primeiro[0].detectado_em == avisos_lugar.BASE
    _obra(session, "Concluída")
    servico.detectar(session, AGORA + timedelta(days=1))
    depois = _do_lugar(session, "mun:4205902")
    assert len(depois) == 2
    assert depois[1].detectado_em > avisos_lugar.BASE
    assert depois[1].titulo == "Obra federal em Gaspar, agora concluída: BR-470"
    assert depois[1].categoria == "obras"


def test_so_lugares_seguidos_geram_fatos(session):
    _gaspar(session)
    _obra(session, "Em execução")
    servico.detectar(session, AGORA)
    assert _do_lugar(session, "mun:4205902") == []


def test_emendas_do_mes_fechado_e_lei_do_brasil(session):
    _gaspar(session)
    i = _inscricao(session)
    _alvo(session, i, "lugar", "mun:4205902")
    _alvo(session, i, "lugar", "br")
    session.add(
        EmendaPagamento(
            emenda_codigo="1", ano_emenda=2026, ano_mes=202609, autor_codigo="1", autor_nome="X",
            favorecido="Prefeitura", favorecido_codigo="1", natureza="x", grupo="prefeitura",
            municipio_ibge="4205902", valor=Decimal("250000.00"),
        )
    )  # fmt: skip
    _tramitacao(session, _proposicao(session), descricao="Transformação em Norma Jurídica")
    servico.detectar(session, AGORA)
    emenda = _do_lugar(session, "mun:4205902")[0]
    assert emenda.titulo == (
        "Emendas parlamentares pagas para Gaspar em setembro de 2026: R$ 250.000 (1 pagamentos)"
    )
    lei = _do_lugar(session, "br")[0]
    assert (lei.titulo, lei.categoria) == ("PEC 12/2026 virou lei", "politica")


def test_dado_novo_tem_linha_de_base_e_formata_em_portugues(session):
    _gaspar(session)
    i = _inscricao(session)
    _alvo(session, i, "lugar", "mun:4205902")
    session.add(FonteIngestao(fonte="datasus_homicidios", url="u", arquivo_raw="x", status="ok",
                              concluido_em=AGORA - timedelta(days=1)))  # fmt: skip
    session.add(HomicidioSim(codigo="4205902", ano=2024, homicidios=3))
    session.flush()
    servico.detectar(session, AGORA)
    base = _do_lugar(session, "mun:4205902")[0]
    assert base.detectado_em == avisos_lugar.BASE
    session.add(HomicidioSim(codigo="4205902", ano=2025, homicidios=1234))
    session.flush()
    servico.detectar(session, AGORA + timedelta(days=1))
    novo = _do_lugar(session, "mun:4205902")[1]
    assert novo.titulo == "Saiu o dado de 2025: 1.234 homicídios de moradores"
    assert avisos_lugar.decimal(1234.5) == "1.234,5"


def _evento_lugar(session, alvo, categoria, titulo, dia=HOJE):
    session.add(
        AvisoEvento(
            alvo_tipo="lugar", alvo_chave=alvo, categoria=categoria, chave_natural=titulo,
            titulo=titulo, caminho="/cidade/4205902", fonte="F", data_fato=dia, detectado_em=AGORA,
        )
    )  # fmt: skip
    session.flush()


def test_envio_respeita_assuntos_e_conta_por_lugar(session):
    _gaspar(session)
    _semear_vazio(session)
    i = _inscricao(session)
    session.add(AvisoAlvo(inscricao_id=i.id, alvo_tipo="lugar", alvo_chave="mun:4205902",
                          criado_em=AGORA - timedelta(days=5), assuntos=["obras"]))  # fmt: skip
    _alvo(session, i, "lugar", "br")
    _evento_lugar(session, "mun:4205902", "obras", "Obra concluída")
    _evento_lugar(session, "mun:4205902", "dinheiro", "Emenda paga")
    _evento_lugar(session, "br", "politica", "Lei nova")
    correio = Correio()
    servico.executar(session, correio, agora=AGORA)
    ((_, carga),) = correio.enviados
    assert carga["titulo"] == "Novidades: Gaspar 1 · Brasil 1"
    assert carga["caminho"] == "/avisos"


def test_semanal_so_recebe_no_domingo_sem_perder(session):
    _gaspar(session)
    _semear_vazio(session)
    i = _inscricao(session)
    i.frequencia = "semana"
    _alvo(session, i, "lugar", "mun:4205902")
    _evento_lugar(session, "mun:4205902", "obras", "Obra concluída")
    correio = Correio()
    servico.executar(session, correio, agora=AGORA)  # sexta-feira
    assert correio.enviados == []
    servico.executar(session, correio, agora=DOMINGO)
    assert len(correio.enviados) == 1


def _seguir(client, chave, tipo="lugar", **extra):
    corpo = {**BASE, "alvo_tipo": tipo, "alvo_chave": chave, "acao": "adicionar", **extra}
    return client.post("/avisos/alvo", json=corpo)


def test_rotas_lugar_assuntos_e_frequencia(client, session):
    _gaspar(session)
    _inscricao(session)
    assert _seguir(client, "mun:4205902", assuntos=["obras", "dinheiro"]).status_code == 200
    alvo = session.scalar(select(AvisoAlvo).where(AvisoAlvo.alvo_chave == "mun:4205902"))
    assert alvo.assuntos == ["dinheiro", "obras"]
    _seguir(client, "mun:4205902")  # seguir de novo troca só os assuntos (nada = todos)
    session.refresh(alvo)
    assert alvo.assuntos is None
    assert _seguir(client, "mun:9999999").status_code == 422
    assert _seguir(client, "br", tipo="parlamentar").status_code == 422
    assert (
        client.post("/avisos/preferencias", json={**BASE, "frequencia": "semana"}).status_code
        == 200
    )
    i = session.scalar(select(AvisoInscricao))
    session.refresh(i)
    assert i.frequencia == "semana"
    minhas = client.post("/avisos/minhas", json=BASE).json()
    assert minhas["frequencia"] == "semana"
    assert minhas["alvos"][0]["nome"] == "Gaspar (SC)"
    assert minhas["alvos"][0]["caminho"] == "/cidade/4205902"
