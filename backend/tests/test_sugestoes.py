import csv
import re
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api import sugestoes as rotas
from app.models import Parlamentar
from app.models.sugestao import Correcao, Sugestao, SugestaoContato
from app.services import sugestoes as servico
from ingestion import sugestoes_revisao

ERRO = {
    "tipo": "erro",
    "categoria": "numero",
    "texto": "O gasto de março está diferente do portal da Câmara.",
    "pagina": "/parlamentar/2",
    "secao": "Gastos do gabinete",
    "perfil_tipo": "parlamentar",
    "perfil_id": "2",
}
RESPOSTA = {
    "tipo": "resposta",
    "texto": "Esclareço que a viagem de março foi em missão oficial da comissão.",
    "pagina": "/parlamentar/2",
    "secao": "Gastos do gabinete",
    "perfil_tipo": "parlamentar",
    "perfil_id": "2",
    "confirmacao": "email_funcional",
}


@pytest.fixture(autouse=True)
def _zerar_limite():
    rotas._pedidos.clear()
    yield
    rotas._pedidos.clear()


def _parlamentar(session, nome="Fulana de Tal") -> Parlamentar:
    p = Parlamentar(
        casa="camara", id_externo="999", nome_parlamentar=nome, partido="XYZ", uf="SC",
        em_exercicio=True, fonte_url="https://www.camara.leg.br", atualizado_em=datetime.now(UTC),
    )  # fmt: skip
    session.add(p)
    session.flush()
    return p


def test_aviso_de_erro_devolve_protocolo_e_guarda_contato_a_parte(client, session):
    r = client.post("/sugestoes", json={**ERRO, "contato": "fulano@exemplo.com"})
    assert r.status_code == 201
    assert r.headers["cache-control"] == "no-store"
    protocolo = r.json()["protocolo"]
    assert re.fullmatch(r"PAN-[234679ACDEFGHJKMNPQRTUVWXYZ]{5}", protocolo)
    s = session.scalars(select(Sugestao)).one()
    assert (s.protocolo, s.status, s.tipo, s.categoria) == (protocolo, "nova", "erro", "numero")
    assert s.confirmacao is None
    assert session.get(SugestaoContato, s.id).contato == "fulano@exemplo.com"
    # Sem IP nem user-agent em lugar nenhum.
    for modelo in (Sugestao, SugestaoContato, Correcao):
        colunas = {c.name for c in modelo.__table__.columns}
        assert not colunas & {"ip", "user_agent", "origem"}


def test_protocolos_sao_unicos(client):
    vistos = {client.post("/sugestoes", json=ERRO).json()["protocolo"] for _ in range(5)}
    assert len(vistos) == 5


def test_resposta_ignora_categoria_e_tipo_do_site_e_normalizado(client, session):
    corpo = {**RESPOSTA, "categoria": "foto", "perfil_tipo": "deputado-estadual"}
    assert client.post("/sugestoes", json=corpo).status_code == 201
    s = session.scalars(select(Sugestao)).one()
    assert s.categoria is None and s.confirmacao == "email_funcional"
    assert s.perfil_tipo == "deputado-estadual"


@pytest.mark.parametrize(
    "mudanca",
    [
        {"tipo": "elogio"},
        {"categoria": None},
        {"categoria": "outra"},
        {"texto": "curto"},
        {"texto": "          espaços          "},
        {"texto": "x" * 2001},
        {"pagina": "https://site.com/x"},
        {"pagina": "/" + "a" * 300},
        {"secao": "s" * 121},
        {"perfil_tipo": "prefeito"},
        {"perfil_id": None},
        {"contato": "não sei"},
        {"contato": "c" * 201},
    ],
)
def test_validacao_do_aviso(client, session, mudanca):
    assert client.post("/sugestoes", json={**ERRO, **mudanca}).status_code == 422
    assert session.scalars(select(Sugestao)).all() == []


@pytest.mark.parametrize(
    "mudanca", [{"confirmacao": None}, {"confirmacao": "whatsapp"}, {"texto": "y" * 3001}]
)
def test_validacao_da_resposta(client, mudanca):
    assert client.post("/sugestoes", json={**RESPOSTA, **mudanca}).status_code == 422


def test_resposta_aceita_texto_ate_3000(client):
    assert client.post("/sugestoes", json={**RESPOSTA, "texto": "z" * 3000}).status_code == 201


def test_contato_telefone_e_vazio(client, session):
    assert client.post("/sugestoes", json={**ERRO, "contato": "(48) 99999-1234"}).status_code == 201
    assert client.post("/sugestoes", json={**ERRO, "contato": "  "}).status_code == 201
    assert len(session.scalars(select(SugestaoContato)).all()) == 1


def test_limite_de_5_por_hora_por_origem(client):
    for _ in range(5):
        assert client.post("/sugestoes", json=ERRO).status_code == 201
    r = client.post("/sugestoes", json=ERRO)
    assert r.status_code == 429
    assert "5 avisos" in r.json()["detail"]
    outra = client.post("/sugestoes", json=ERRO, headers={"cf-connecting-ip": "203.0.113.9"})
    assert outra.status_code == 201
    assert rotas.limitar.janela == 3600


def test_respostas_so_publicadas_e_sem_contato(client, session):
    for _ in range(2):
        client.post("/sugestoes", json={**RESPOSTA, "contato": "assessoria@camara.leg.br"})
    client.post("/sugestoes", json=ERRO)
    assert client.get("/pessoas/de/respostas?tipo=parlamentar&id=2").json() == []

    primeira, segunda = session.scalars(
        select(Sugestao).where(Sugestao.tipo == "resposta").order_by(Sugestao.id)
    ).all()
    with pytest.raises(ValueError):
        servico.publicar_resposta(session, primeira.id, identidade_confirmada=False)
    servico.publicar_resposta(
        session, primeira.id, identidade_confirmada=True, hoje=date(2026, 11, 7)
    )
    servico.recusar(session, segunda.id)

    r = client.get("/pessoas/de/respostas?tipo=parlamentar&id=2")
    assert r.status_code == 200
    corpo = r.json()
    assert [x["id"] for x in corpo] == [primeira.id]
    assert set(corpo[0]) == {"id", "texto", "secao", "recebida_em", "publicada_em"}
    assert corpo[0]["publicada_em"] == "2026-11-07"
    assert "assessoria" not in r.text
    assert client.get("/pessoas/de/respostas?tipo=parlamentar&id=3").json() == []
    assert client.get("/pessoas/de/respostas?tipo=xyz&id=2").json() == []


def test_erro_nao_e_publicado_como_resposta(client, session):
    client.post("/sugestoes", json=ERRO)
    s = session.scalars(select(Sugestao)).one()
    with pytest.raises(ValueError):
        servico.publicar_resposta(session, s.id, identidade_confirmada=True)


def test_correcoes_filtradas_com_nome_do_perfil(client, session):
    p = _parlamentar(session)
    client.post("/sugestoes", json={**ERRO, "perfil_id": str(p.id), "contato": "a@b.com"})
    s = session.scalars(select(Sugestao)).one()
    servico.aceitar(session, s.id)
    servico.registrar_correcao(
        session, dado="Gastos do gabinete em 2026", antes="R$ 10.000,00",
        depois="R$ 1.000,00", motivo="Lançamento duplicado na carga",
        fonte="https://www.camara.leg.br/cota-parlamentar/", sugestao_id=s.id,
        data=date(2026, 11, 6),
    )  # fmt: skip
    servico.registrar_correcao(
        session, dado="Foto do perfil", antes="foto de outra pessoa", depois="foto oficial",
        motivo="Foto trocada", fonte="TSE", perfil_tipo="vereador", perfil_id="77",
        data=date(2026, 11, 7),
    )  # fmt: skip

    todas = client.get("/correcoes").json()
    assert todas["total"] == 2
    assert [i["dado"] for i in todas["itens"]] == ["Foto do perfil", "Gastos do gabinete em 2026"]

    r = client.get(f"/correcoes?tipo=parlamentar&id={p.id}")
    corpo = r.json()
    assert corpo["total"] == 1
    item = corpo["itens"][0]
    assert item["perfil_nome"] == "Fulana de Tal"
    assert item["data"] == "2026-11-06"
    assert set(item) == {
        "id", "data", "dado", "antes", "depois", "motivo", "fonte", "perfil_tipo", "perfil_id",
        "perfil_nome",
    }  # fmt: skip
    assert "a@b.com" not in r.text and "sugestao" not in r.text and "protocolo" not in r.text
    assert client.get("/correcoes?tipo=vereador").json()["total"] == 1
    assert client.get("/correcoes?tipo=eleito").json() == {"itens": [], "total": 0}


def test_correcao_exige_campos(session):
    with pytest.raises(ValueError):
        servico.registrar_correcao(session, dado="x", antes="", depois="y", motivo="z", fonte="w")


def test_expurgo_apaga_contato_com_mais_de_180_dias(client, session):
    client.post("/sugestoes", json={**ERRO, "contato": "velho@exemplo.com"})
    client.post("/sugestoes", json={**ERRO, "contato": "novo@exemplo.com"})
    velho, novo = session.scalars(select(SugestaoContato).order_by(SugestaoContato.contato)).all()
    novo, velho = (velho, novo) if velho.contato == "novo@exemplo.com" else (novo, velho)
    agora = datetime.now(UTC)
    velho.criada_em = agora - timedelta(days=181)
    novo.criada_em = agora - timedelta(days=179)
    session.commit()
    assert servico.apagar_contatos_antigos(session, agora) == 1
    restantes = [c.contato for c in session.scalars(select(SugestaoContato))]
    assert restantes == ["novo@exemplo.com"]
    # A sugestão continua; só o contato sai.
    assert len(session.scalars(select(Sugestao)).all()) == 2


def test_fila_interativa_publica_resposta_e_apaga_contato(client, session):
    client.post("/sugestoes", json={**RESPOSTA, "contato": "assessoria@camara.leg.br"})
    respostas = iter(["u", "confirmado", "", "", "s"])
    sugestoes_revisao.revisar(session, entrada=lambda _: next(respostas))
    s = session.scalars(select(Sugestao)).one()
    assert s.status == "publicada" and s.publicada_em is not None and s.revisada_em is not None
    assert session.scalars(select(SugestaoContato)).all() == []


def test_fila_interativa_nao_publica_sem_confirmar(client, session):
    client.post("/sugestoes", json=RESPOSTA)
    respostas = iter(["u", "não"])
    sugestoes_revisao.revisar(session, entrada=lambda _: next(respostas))
    assert session.scalars(select(Sugestao)).one().status == "nova"


def test_fila_interativa_aceita_erro_e_registra_correcao(client, session):
    client.post("/sugestoes", json={**ERRO, "contato": "a@b.com"})
    respostas = iter(
        ["a", "conferido no portal", "s", "Gastos de março", "R$ 5,00", "R$ 50,00",
         "Vírgula no lugar errado", "https://dadosabertos.camara.leg.br", "n"]
    )  # fmt: skip
    sugestoes_revisao.revisar(session, entrada=lambda _: next(respostas))
    s = session.scalars(select(Sugestao)).one()
    assert (s.status, s.nota_revisao) == ("aceita", "conferido no portal")
    c = session.scalars(select(Correcao)).one()
    assert (c.sugestao_id, c.perfil_tipo, c.perfil_id) == (s.id, "parlamentar", "2")
    # Respondeu "n" para apagar o contato: ele continua até o expurgo.
    assert session.get(SugestaoContato, s.id) is not None


def test_exportar_sem_contato(client, session, tmp_path):
    client.post("/sugestoes", json={**ERRO, "contato": "segredo@exemplo.com"})
    destino = tmp_path / "fila.csv"
    assert sugestoes_revisao.exportar(destino, session) == 0
    texto = destino.read_text(encoding="utf-8")
    assert "segredo@exemplo.com" not in texto
    linhas = list(csv.DictReader(destino.open(encoding="utf-8")))
    assert len(linhas) == 1 and linhas[0]["tem_contato"] == "sim"
    assert "contato" not in linhas[0]


def test_ingestao_diaria_chama_o_expurgo(monkeypatch):
    from ingestion import run_all

    chamadas = []
    monkeypatch.setattr(servico, "apagar_contatos_antigos", lambda session: chamadas.append(1) or 0)
    run_all._expurgar_contatos()
    assert chamadas == [1]

    def _falha(session):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(servico, "apagar_contatos_antigos", _falha)
    run_all._expurgar_contatos()  # não levanta
