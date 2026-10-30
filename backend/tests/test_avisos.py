import base64
import json
import logging
import os
from datetime import UTC, date, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import delete, func, select

from app import avisos_diario
from app.api import avisos as rotas
from app.config import settings
from app.db import get_session
from app.main import app
from app.models import (
    AvisoAlvo,
    AvisoCursor,
    AvisoEvento,
    AvisoInscricao,
    DouAto,
    Evento,
    Parlamentar,
    Pessoa,
    PessoaVinculo,
    Proposicao,
    Tramitacao,
    Votacao,
    Voto,
)
from app.services import avisos as servico

ENDPOINT = "https://fcm.googleapis.com/fcm/send/segredo-do-aparelho"
P256DH = "B" * 87
AUTH = "a" * 22
BASE = {"endpoint": ENDPOINT, "auth": AUTH}
INSCRICAO = {**BASE, "p256dh": P256DH}
AGORA = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
HOJE = date(2026, 10, 30)


@pytest.fixture(autouse=True)
def _ligar(monkeypatch):
    monkeypatch.setattr(settings, "ambiente", "release")
    monkeypatch.setattr(settings, "avisos_ativos", True)
    monkeypatch.setattr(settings, "vapid_privada", "chave-de-teste")
    monkeypatch.setattr(settings, "vapid_contato", "mailto:contato@exemplo.org")
    rotas._limite.pedidos.clear()


class Correio:
    """Envio injetável: nenhum teste faz rede."""

    def __init__(self, status=201):
        self.status = status
        self.enviados = []

    def __call__(self, destino, carga):
        self.enviados.append((destino.endpoint, json.loads(carga)))
        return self.status


def _parlamentar(session, id_externo="100", casa="camara", nome="Fulana de Tal"):
    p = Parlamentar(
        casa=casa,
        id_externo=id_externo,
        nome_parlamentar=nome,
        uf="SC",
        fonte_url="https://exemplo",
        atualizado_em=AGORA,
    )
    session.add(p)
    session.flush()
    return p


def _proposicao(session, id_externo="900", casa="camara"):
    p = Proposicao(
        casa=casa,
        id_externo=id_externo,
        sigla_tipo="PEC",
        numero=12,
        ano=2026,
        ementa="Ementa",
        data_apresentacao=date(2026, 1, 1),
        url="https://exemplo",
    )
    session.add(p)
    session.flush()
    return p


def _votacao(session, parlamentar, id_externo="v1", dia=HOJE, voto="Sim", **campos):
    campos.setdefault("proposicao", "PEC 12/2026")
    v = Votacao(casa=parlamentar.casa, id_externo=id_externo, data=dia, descricao="d", **campos)
    session.add(v)
    session.flush()
    session.add(Voto(votacao_id=v.id, parlamentar_id=parlamentar.id, voto=voto))
    session.flush()
    return v


def _tramitacao(session, proposicao, dia=HOJE, descricao="Aprovado o parecer"):
    t = Tramitacao(
        casa=proposicao.casa,
        proposicao_id_externo=proposicao.id_externo,
        ordem=1,
        data=datetime(dia.year, dia.month, dia.day, 10, 30),
        descricao=descricao,
    )
    session.add(t)
    session.flush()
    return t


def _pessoa(session, parlamentar, regra="origem", revisado=False):
    pessoa = Pessoa(nome=parlamentar.nome_parlamentar, chave_nome="fulana")
    session.add(pessoa)
    session.flush()
    vinculo = PessoaVinculo(
        pessoa_id=pessoa.id,
        fonte="parlamentar",
        id_externo=f"{parlamentar.casa}:{parlamentar.id_externo}",
        regra=regra,
        revisado=revisado,
    )
    session.add(vinculo)
    session.flush()
    return pessoa, vinculo


def _evento(session, pessoa, vinculo_id, dia=HOJE, id_externo="e1"):
    session.add(
        Evento(
            pessoa_id=pessoa.id,
            vinculo_id=vinculo_id,
            data=dia,
            tipo="sancao",
            descricao="Sanção",
            orgao="TCU",
            fonte="tcu",
            id_externo=id_externo,
        )
    )
    session.flush()


def _inscricao(session, endpoint=ENDPOINT, ambiente="release", criada=None):
    i = AvisoInscricao(
        ambiente=ambiente,
        endpoint=endpoint,
        p256dh=P256DH,
        auth=AUTH,
        criada_em=criada or AGORA - timedelta(days=5),
    )
    session.add(i)
    session.flush()
    return i


def _alvo(session, inscricao, tipo="parlamentar", chave="camara:100", criado=None):
    session.add(
        AvisoAlvo(
            inscricao_id=inscricao.id,
            alvo_tipo=tipo,
            alvo_chave=chave,
            criado_em=criado or AGORA - timedelta(days=5),
        )
    )
    session.flush()


def _semear_vazio(session, ambiente="release"):
    session.add(AvisoCursor(ambiente=ambiente, ultimo_evento_id=0))
    session.flush()


def _eventos(session):
    return list(session.scalars(select(AvisoEvento).order_by(AvisoEvento.id)))


def _contar(session, modelo):
    return session.scalar(select(func.count()).select_from(modelo))


# Detector


def test_detector_e_idempotente(session):
    p = _parlamentar(session)
    _votacao(session, p)
    _tramitacao(session, _proposicao(session))
    assert servico.detectar(session, AGORA) == 2
    assert servico.detectar(session, AGORA + timedelta(days=1)) == 0
    assert len(_eventos(session)) == 2


def test_titulo_fonte_e_data_do_voto(session):
    p = _parlamentar(session)
    _votacao(session, p, dia=date(2026, 10, 20))
    servico.detectar(session, AGORA)
    e = _eventos(session)[0]
    assert e.titulo == "Fulana de Tal votou Sim na PEC 12/2026"
    assert (e.fonte, e.data_fato) == ("Câmara dos Deputados", date(2026, 10, 20))
    assert e.caminho == f"/parlamentar/{p.id}"
    assert (e.alvo_tipo, e.alvo_chave) == ("parlamentar", "camara:100")


def test_titulo_da_tramitacao_junta_rotulo_e_texto_oficial(session):
    p = _proposicao(session)
    _tramitacao(session, p, descricao="  Aprovado\no   parecer ")
    servico.detectar(session, AGORA)
    e = _eventos(session)[0]
    assert e.titulo == "PEC 12/2026: Aprovado o parecer"
    assert e.caminho == "/projeto/camara/900"
    assert (e.alvo_tipo, e.alvo_chave) == ("projeto", "camara:900")


def test_recarga_com_delete_e_insert_nao_gera_aviso_falso(session):
    p = _parlamentar(session)
    prop = _proposicao(session)
    v = _votacao(session, p)
    _tramitacao(session, prop)
    servico.detectar(session, AGORA)
    session.delete(v)
    session.execute(delete(Tramitacao))
    session.flush()
    novo = _votacao(session, p)
    _tramitacao(session, prop)
    assert novo.id != v.id
    assert servico.detectar(session, AGORA + timedelta(days=1)) == 0


def test_tramitacao_com_diferenca_de_acento_e_espaco_e_o_mesmo_fato(session):
    prop = _proposicao(session)
    _tramitacao(session, prop, descricao="Aprovação  do parecer")
    servico.detectar(session, AGORA)
    session.execute(delete(Tramitacao))
    _tramitacao(session, prop, descricao="aprovacao do parecer")
    assert servico.detectar(session, AGORA) == 0


def test_fato_fora_da_janela_nunca_gera_aviso(session):
    p = _parlamentar(session)
    limite = HOJE - timedelta(days=servico.JANELA_DIAS)
    _votacao(session, p, "velho", dia=limite - timedelta(days=1))
    _votacao(session, p, "borda", dia=limite)
    _tramitacao(session, _proposicao(session), dia=limite - timedelta(days=1))
    pessoa, vinculo = _pessoa(session, p)
    _evento(session, pessoa, vinculo.id, dia=limite - timedelta(days=1))
    assert servico.detectar(session, AGORA) == 1
    assert _eventos(session)[0].chave_natural == "camara:borda:100"


def test_voto_secreto_e_ausencia_ficam_de_fora(session):
    p = _parlamentar(session, casa="senado")
    _votacao(session, p, "sec", secreta=True, voto="")
    _votacao(session, p, "aus", voto="LS")
    _votacao(session, p, "ok", voto="Não")
    assert servico.detectar(session, AGORA) == 1
    assert _eventos(session)[0].titulo == "Fulana de Tal votou Não na PEC 12/2026"


def test_evento_publicavel_entra_com_chave_da_fonte(session):
    p = _parlamentar(session)
    pessoa, vinculo = _pessoa(session, p)
    _evento(session, pessoa, vinculo.id)
    assert servico.detectar(session, AGORA) == 1
    e = _eventos(session)[0]
    assert e.chave_natural == "tcu|e1|sancao"
    assert e.titulo == "Fulana de Tal: Sanção registrada, TCU"
    assert e.fonte == "TCU"


def test_vinculo_fraco_nao_revisado_fica_de_fora_e_revisado_entra(session):
    p = _parlamentar(session)
    pessoa, vinculo = _pessoa(session, p, regra="nome_casa", revisado=False)
    _evento(session, pessoa, vinculo.id)
    assert servico.detectar(session, AGORA) == 0
    vinculo.revisado = True
    session.flush()
    assert servico.detectar(session, AGORA) == 1


def test_evento_sem_vinculo_ou_com_vinculo_de_fonte_fraco_fica_de_fora(session):
    p = _parlamentar(session)
    pessoa, _ = _pessoa(session, p)
    _evento(session, pessoa, None, id_externo="sem")
    fraco = PessoaVinculo(pessoa_id=pessoa.id, fonte="dou", id_externo="x", regra="nome_casa")
    session.add(fraco)
    session.flush()
    _evento(session, pessoa, fraco.id, id_externo="fraco")
    assert servico.detectar(session, AGORA) == 0


def test_sugestao_nao_revisada_nao_gera_aviso(session):
    p = _parlamentar(session)
    pessoa, _ = _pessoa(session, p)
    session.add(
        DouAto(
            pessoa_id=pessoa.id,
            id_materia="1",
            data=HOJE,
            tipo_ato="nomeacao",
            orgao="Órgão",
            trecho="Nomeia",
            url="https://exemplo",
        )
    )
    session.flush()
    assert servico.detectar(session, AGORA) == 0


# Semente e envio


def test_semear_grava_sem_enviar_e_o_envio_nao_repete(session):
    p = _parlamentar(session)
    _votacao(session, p)
    i = _inscricao(session)
    _alvo(session, i)
    assert servico.semear(session, AGORA) == 1
    assert session.get(AvisoCursor, "release").ultimo_evento_id == _eventos(session)[0].id
    correio = Correio()
    r = servico.executar(session, correio, agora=AGORA + timedelta(days=1))
    assert correio.enviados == []
    assert r.detectados == 0


def test_envio_sem_semente_e_recusado(session):
    with pytest.raises(servico.SemSemente):
        servico.executar(session, Correio(), agora=AGORA)
    assert _eventos(session) == []


def test_uma_notificacao_por_aparelho_com_varios_fatos(session):
    p = _parlamentar(session)
    _votacao(session, p, "v1")
    _votacao(session, p, "v2", dia=HOJE - timedelta(days=1))
    prop = _proposicao(session)
    _tramitacao(session, prop)
    _semear_vazio(session)
    i = _inscricao(session)
    _alvo(session, i)
    _alvo(session, i, "projeto", "camara:900")
    correio = Correio()
    r = servico.executar(session, correio, agora=AGORA)
    assert len(correio.enviados) == 1
    carga = correio.enviados[0][1]
    assert carga["titulo"] == "3 novidades de quem você acompanha"
    assert carga["caminho"] == "/avisos"
    assert "Câmara dos Deputados" in carga["corpo"] and "30/10/2026" in carga["corpo"]
    assert (r.enviados, r.com_novidade) == (1, 1)
    session.expire_all()
    assert session.get(AvisoCursor, "release").ultimo_evento_id == _eventos(session)[-1].id
    assert session.get(AvisoInscricao, i.id).ultimo_sucesso_em == AGORA
    correio.enviados.clear()
    servico.executar(session, correio, agora=AGORA + timedelta(days=1))
    assert correio.enviados == []


def test_um_fato_leva_ao_caminho_dele_com_fonte_e_data(session):
    p = _parlamentar(session)
    _votacao(session, p)
    _semear_vazio(session)
    _alvo(session, _inscricao(session))
    correio = Correio()
    servico.executar(session, correio, agora=AGORA)
    assert correio.enviados[0][1] == {
        "titulo": "Fulana de Tal votou Sim na PEC 12/2026",
        "corpo": "Fonte: Câmara dos Deputados. Data: 30/10/2026.",
        "caminho": f"/parlamentar/{p.id}",
    }


def test_so_vai_fato_detectado_depois_de_o_alvo_entrar(session):
    p = _parlamentar(session)
    _votacao(session, p)
    _semear_vazio(session)
    # O fato é detectado nesta rodada, antes de o alvo existir.
    _alvo(session, _inscricao(session), criado=AGORA + timedelta(hours=1))
    correio = Correio()
    servico.executar(session, correio, agora=AGORA)
    assert correio.enviados == []


def test_outro_alvo_nao_recebe(session):
    p = _parlamentar(session)
    _votacao(session, p)
    _semear_vazio(session)
    _alvo(session, _inscricao(session), chave="camara:outro")
    correio = Correio()
    servico.executar(session, correio, agora=AGORA)
    assert correio.enviados == []


def test_ambientes_nao_se_misturam(session, monkeypatch):
    p = _parlamentar(session)
    _votacao(session, p)
    _semear_vazio(session)
    _semear_vazio(session, "producao")
    _alvo(session, _inscricao(session))
    outra = "https://web.push.apple.com/outro"
    _alvo(session, _inscricao(session, outra, ambiente="producao"))
    correio = Correio()
    servico.executar(session, correio, agora=AGORA)
    assert [e for e, _ in correio.enviados] == [ENDPOINT]
    session.expire_all()
    assert session.get(AvisoCursor, "producao").ultimo_evento_id == 0

    monkeypatch.setattr(settings, "ambiente", "producao")
    correio = Correio()
    servico.executar(session, correio, agora=AGORA)
    assert [e for e, _ in correio.enviados] == [outra]


def test_rota_nao_enxerga_inscricao_de_outro_ambiente(client, session, monkeypatch):
    _inscricao(session, ambiente="producao")
    assert client.post("/avisos/minhas", json=BASE).status_code == 404
    assert client.post("/avisos/cancelar", json=BASE).status_code == 404
    assert client.post("/avisos/inscrever", json=INSCRICAO).status_code == 200
    assert _contar(session, AvisoInscricao) == 2


@pytest.mark.parametrize("status", [404, 410])
def test_servico_diz_que_saiu_apaga_inscricao_e_alvos(session, status):
    _votacao(session, _parlamentar(session))
    _semear_vazio(session)
    _alvo(session, _inscricao(session))
    r = servico.executar(session, Correio(status), agora=AGORA)
    assert r.removidas == 1
    assert _contar(session, AvisoInscricao) == 0
    assert _contar(session, AvisoAlvo) == 0


@pytest.mark.parametrize("status", [401, 403])
def test_chave_recusada_nao_apaga_e_tenta_de_novo(session, status):
    _votacao(session, _parlamentar(session))
    _semear_vazio(session)
    _alvo(session, _inscricao(session))
    r = servico.executar(session, Correio(status), agora=AGORA)
    assert (r.chave_recusada, r.removidas) == (1, 0)
    assert _contar(session, AvisoInscricao) == 1
    correio = Correio()
    servico.executar(session, correio, agora=AGORA + timedelta(days=1))
    assert len(correio.enviados) == 1


@pytest.mark.parametrize("status", [429, 500, 503, 0])
def test_falha_passageira_recebe_no_dia_seguinte_mesmo_com_cursor_a_frente(session, status):
    _votacao(session, _parlamentar(session))
    _semear_vazio(session)
    i = _inscricao(session)
    _alvo(session, i)
    r = servico.executar(session, Correio(status), agora=AGORA)
    assert r.falhas == 1
    session.expire_all()
    assert session.get(AvisoCursor, "release").ultimo_evento_id == _eventos(session)[-1].id
    correio = Correio()
    servico.executar(session, correio, agora=AGORA + timedelta(days=1))
    assert len(correio.enviados) == 1
    correio.enviados.clear()
    servico.executar(session, correio, agora=AGORA + timedelta(days=2))
    assert correio.enviados == []


def test_queda_no_meio_nao_repete_quem_ja_recebeu(session):
    _votacao(session, _parlamentar(session))
    _semear_vazio(session)
    _alvo(session, _inscricao(session))
    servico.executar(session, Correio(), agora=AGORA)
    # Como se a rodada tivesse caído antes de avançar o cursor.
    session.get(AvisoCursor, "release").ultimo_evento_id = 0
    session.flush()
    correio = Correio()
    servico.executar(session, correio, agora=AGORA + timedelta(days=1))
    assert correio.enviados == []


def test_prazo_estourado_adia_e_o_resto_recebe_depois(session):
    _votacao(session, _parlamentar(session))
    _semear_vazio(session)
    _alvo(session, _inscricao(session))
    correio = Correio()
    r = servico.executar(session, correio, agora=AGORA, prazo=-1)
    assert (r.adiadas, correio.enviados) == (1, [])
    servico.executar(session, correio, agora=AGORA + timedelta(days=1))
    assert len(correio.enviados) == 1


def test_simular_nao_envia_nem_grava(session):
    _votacao(session, _parlamentar(session))
    _semear_vazio(session)
    _alvo(session, _inscricao(session))
    session.commit()
    correio = Correio()
    r = servico.executar(session, correio, simular=True, agora=AGORA)
    assert (r.detectados, r.com_novidade) == (1, 1)
    assert correio.enviados == []
    assert _eventos(session) == []
    assert session.get(AvisoCursor, "release").ultimo_evento_id == 0


def test_limpeza_por_prazo_de_guarda(session):
    _semear_vazio(session)
    antigo = AGORA - timedelta(days=servico.GUARDA_INSCRICAO_DIAS + 1)
    _inscricao(session, "https://web.push.apple.com/velha", criada=antigo)
    _inscricao(session, "https://web.push.apple.com/nova", criada=AGORA - timedelta(days=170))
    _inscricao(session, "https://web.push.apple.com/prod", ambiente="producao", criada=antigo)
    for chave, dias in (("velho", servico.GUARDA_EVENTO_DIAS + 1), ("novo", 80)):
        session.add(
            AvisoEvento(
                alvo_tipo="projeto",
                alvo_chave="camara:1",
                categoria="tramitacao",
                chave_natural=chave,
                titulo="t",
                caminho="/x",
                fonte="f",
                data_fato=HOJE,
                detectado_em=AGORA - timedelta(days=dias),
            )
        )
    session.flush()
    r = servico.executar(session, Correio(), agora=AGORA)
    assert (r.eventos_apagados, r.inscricoes_apagadas) == (1, 1)
    assert [e.chave_natural for e in _eventos(session)] == ["novo"]
    # O prazo do outro ambiente é com a rodada dele.
    assert _contar(session, AvisoInscricao) == 2


def test_nenhum_dado_do_aparelho_vai_para_o_log(session, caplog):
    _votacao(session, _parlamentar(session))
    _semear_vazio(session)
    _alvo(session, _inscricao(session))
    _alvo(session, _inscricao(session, "https://web.push.apple.com/segundo"))

    def explode(destino, carga):
        raise RuntimeError(f"falha ao falar com {destino.endpoint}")

    with caplog.at_level(logging.DEBUG):
        r = servico.executar(session, explode, agora=AGORA)
    assert r.falhas == 2
    assert "avisos ambiente=release" in caplog.text
    for segredo in (ENDPOINT, "segundo", P256DH, AUTH):
        assert segredo not in caplog.text


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


class _Resposta:
    def __init__(self, status):
        self.status_code = status
        self.reason = "motivo"
        self.text = "corpo"
        self.headers = {}


class _SessaoFalsa:
    """Fica no lugar da sessão HTTP: a criptografia e o VAPID rodam de verdade, sem rede."""

    def __init__(self, status):
        self.status = status
        self.pedidos = []

    def post(self, url, **kwargs):
        self.pedidos.append((url, kwargs))
        return _Resposta(self.status)


@pytest.mark.parametrize("status", [201, 410])
def test_enviar_webpush_cifra_assina_e_devolve_o_status(monkeypatch, status):
    aparelho = ec.generate_private_key(ec.SECP256R1()).public_key()
    publica = aparelho.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    vapid = ec.generate_private_key(ec.SECP256R1()).private_numbers().private_value
    monkeypatch.setattr(settings, "vapid_privada", _b64(vapid.to_bytes(32, "big")))
    falsa = _SessaoFalsa(status)
    monkeypatch.setattr(servico, "_http", falsa)
    destino = servico.Destino(ENDPOINT, _b64(publica), _b64(os.urandom(16)))

    assert servico.enviar_webpush(destino, '{"titulo": "oi"}') == status

    url, pedido = falsa.pedidos[0]
    assert url == ENDPOINT
    assert pedido["timeout"] == servico.TEMPO_LIMITE
    assert pedido["headers"]["ttl"] == str(servico.TTL_SEGUNDOS)
    assert pedido["headers"]["Authorization"].startswith("vapid ")
    assert b"oi" not in pedido["data"]


# Rotas


def test_inscrever_e_idempotente(client, session):
    for _ in range(2):
        r = client.post("/avisos/inscrever", json=INSCRICAO)
        assert (r.status_code, r.json()) == (200, {"ok": True})
    i = session.scalars(select(AvisoInscricao)).one()
    assert (i.ambiente, i.endpoint, i.auth) == ("release", ENDPOINT, AUTH)


def test_inscrever_de_novo_nao_troca_as_chaves(client, session):
    client.post("/avisos/inscrever", json=INSCRICAO)
    assert client.post("/avisos/inscrever", json={**INSCRICAO, "auth": "b" * 22}).status_code == 200
    assert session.scalars(select(AvisoInscricao)).one().auth == AUTH
    assert client.post("/avisos/minhas", json={**BASE, "auth": "b" * 22}).status_code == 404


def test_alvo_adiciona_remove_e_valida_existencia(client, session):
    _parlamentar(session)
    _proposicao(session)
    client.post("/avisos/inscrever", json=INSCRICAO)

    def pedir(**campos):
        return client.post("/avisos/alvo", json={**BASE, **campos})

    p = {"alvo_tipo": "parlamentar", "alvo_chave": "camara:100"}
    assert pedir(**p, acao="adicionar").json() == {"ok": True, "alvos": 1}
    assert pedir(**p, acao="adicionar").json() == {"ok": True, "alvos": 1}
    r = pedir(alvo_tipo="projeto", alvo_chave="camara:900", acao="adicionar")
    assert r.json() == {"ok": True, "alvos": 2}
    assert pedir(**p, acao="remover").json() == {"ok": True, "alvos": 1}
    assert pedir(**p, acao="remover").json() == {"ok": True, "alvos": 1}
    assert pedir(alvo_tipo="projeto", alvo_chave="camara:1", acao="adicionar").status_code == 422
    assert pedir(alvo_tipo="projeto", alvo_chave="tse:1", acao="adicionar").status_code == 422
    assert pedir(alvo_tipo="vereador", alvo_chave="camara:1", acao="adicionar").status_code == 422


def test_maximo_de_alvos_por_aparelho(client, session):
    for n in range(servico.MAX_ALVOS + 1):
        _parlamentar(session, str(n))
    i = _inscricao(session)
    for n in range(servico.MAX_ALVOS):
        _alvo(session, i, chave=f"camara:{n}")
    corpo = {**BASE, "alvo_tipo": "parlamentar", "acao": "adicionar"}
    extra = client.post("/avisos/alvo", json={**corpo, "alvo_chave": f"camara:{servico.MAX_ALVOS}"})
    assert extra.status_code == 429
    # Quem já está na lista não conta como novo.
    assert client.post("/avisos/alvo", json={**corpo, "alvo_chave": "camara:0"}).status_code == 200


def test_teto_global_de_inscricoes(client, session, monkeypatch):
    monkeypatch.setattr(settings, "avisos_max_inscricoes", 1)
    assert client.post("/avisos/inscrever", json=INSCRICAO).status_code == 200
    outro = {**INSCRICAO, "endpoint": "https://web.push.apple.com/outro"}
    r = client.post("/avisos/inscrever", json=outro)
    assert r.status_code == 429
    assert r.headers["cache-control"] == "no-store"
    # Quem já está inscrito não esbarra no teto.
    assert client.post("/avisos/inscrever", json=INSCRICAO).status_code == 200


def test_limite_por_ip(client):
    for _ in range(rotas.LIMITE_POR_MINUTO):
        client.post("/avisos/minhas", json=BASE)
    r = client.post("/avisos/minhas", json=BASE)
    assert r.status_code == 429
    assert r.headers["cache-control"] == "no-store"
    outra = client.post("/avisos/minhas", json=BASE, headers={"cf-connecting-ip": "203.0.113.9"})
    assert outra.status_code == 404


@pytest.mark.parametrize("rota", ["/avisos/minhas", "/avisos/cancelar"])
def test_endpoint_sem_auth_certo_nao_passa(client, session, rota):
    _alvo(session, _inscricao(session))
    assert client.post(rota, json={**BASE, "auth": "b" * 22}).status_code == 404
    assert client.post(rota, json={"endpoint": ENDPOINT}).status_code == 422
    assert _contar(session, AvisoInscricao) == 1


def test_alvo_sem_auth_certo_nao_passa(client, session):
    _parlamentar(session)
    _inscricao(session)
    corpo = {
        **BASE,
        "auth": "b" * 22,
        "alvo_tipo": "parlamentar",
        "alvo_chave": "camara:100",
        "acao": "adicionar",
    }
    assert client.post("/avisos/alvo", json=corpo).status_code == 404


def test_cancelar_apaga_de_verdade(client, session):
    _alvo(session, _inscricao(session))
    assert client.post("/avisos/cancelar", json=BASE).json() == {"ok": True}
    assert _contar(session, AvisoInscricao) == 0
    assert _contar(session, AvisoAlvo) == 0
    assert client.post("/avisos/minhas", json=BASE).status_code == 404


def test_minhas_lista_alvos_e_novidades_com_fonte_e_data(client, session):
    p = _parlamentar(session)
    prop = _proposicao(session)
    i = _inscricao(session)
    _alvo(session, i)
    _alvo(session, i, "projeto", "camara:900")
    _alvo(session, i, "projeto", "camara:sumiu")
    _votacao(session, p)
    servico.detectar(session, AGORA)
    r = client.post("/avisos/minhas", json=BASE)
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    corpo = r.json()
    assert corpo["alvos"] == [
        {
            "alvo_tipo": "parlamentar",
            "alvo_chave": "camara:100",
            "nome": "Fulana de Tal",
            "caminho": f"/parlamentar/{p.id}",
        },
        {
            "alvo_tipo": "projeto",
            "alvo_chave": "camara:900",
            "nome": "PEC 12/2026",
            "caminho": f"/projeto/{prop.casa}/{prop.id_externo}",
        },
        {
            "alvo_tipo": "projeto",
            "alvo_chave": "camara:sumiu",
            "nome": "camara:sumiu",
            "caminho": "/avisos",
        },
    ]
    assert len(corpo["novidades"]) == 1
    novidade = corpo["novidades"][0]
    assert novidade["titulo"] == "Fulana de Tal votou Sim na PEC 12/2026"
    assert novidade["fonte"] == "Câmara dos Deputados"
    assert novidade["data_fato"] == "2026-10-30"
    assert novidade["detectado_em"].startswith("2026-10-30")
    assert novidade["caminho"] == f"/parlamentar/{p.id}"


def test_detalhe_do_parlamentar_devolve_casa_e_id_externo(client, session):
    p = _parlamentar(session)
    corpo = client.get(f"/parlamentares/{p.id}").json()
    assert (corpo["casa"], corpo["id_externo"]) == ("camara", "100")


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://fcm.googleapis.com/fcm/send/x",
        "https://localhost/x",
        "https://169.254.169.254/latest/meta-data",
        "https://10.0.0.1/x",
        "https://evil.example/x",
        "https://fcm.googleapis.com.evil.example/x",
        "https://evilfcm.googleapis.com/x",
        "https://fcm.googleapis.com@evil.example/x",
        "https://evil.example\\@fcm.googleapis.com/x",
        "https://evil.example#@fcm.googleapis.com/x",
        "https://fcm.googleapis.com:8443/x",
        "https://fcm.googleapis.com/",
        "https://fcm.googleapis.com:porta/x",
        "ftp://fcm.googleapis.com/x",
        "https://fcm.googleapis.com/a b",
        "https://notify.windows.com.evil.example/x",
    ],
)
def test_endpoint_fora_da_lista_e_recusado(client, session, endpoint):
    r = client.post("/avisos/inscrever", json={**INSCRICAO, "endpoint": endpoint})
    assert r.status_code == 422
    assert _contar(session, AvisoInscricao) == 0


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://fcm.googleapis.com/fcm/send/abc",
        "https://updates.push.services.mozilla.com/wpush/v2/abc",
        "https://web.push.apple.com/QAbc",
        "https://wns2-par02p.notify.windows.com/w/?token=abc",
        "https://FCM.googleapis.com:443/fcm/send/abc",
    ],
)
def test_servicos_conhecidos_sao_aceitos(endpoint):
    assert servico.endpoint_permitido(endpoint)


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {**INSCRICAO, "p256dh": "curto"},
        {**INSCRICAO, "auth": "curto"},
        {**INSCRICAO, "auth": "a" * 21 + "!"},
    ],
)
def test_inscrever_valida_corpo(client, corpo):
    assert client.post("/avisos/inscrever", json=corpo).status_code == 422


@pytest.mark.parametrize(
    "mudanca",
    [
        {"avisos_ativos": False},
        {"vapid_privada": ""},
        {"vapid_contato": ""},
        {"vapid_contato": "contato@exemplo.org"},
    ],
)
@pytest.mark.parametrize("rota", ["inscrever", "alvo", "cancelar", "minhas"])
def test_desligado_responde_503_sem_tocar_no_banco(monkeypatch, rota, mudanca):
    from fastapi.testclient import TestClient

    for campo, valor in mudanca.items():
        monkeypatch.setattr(settings, campo, valor)

    def sem_banco():
        raise AssertionError("tocou no banco")

    app.dependency_overrides[get_session] = sem_banco
    try:
        r = TestClient(app).post(f"/avisos/{rota}", json={})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert r.json() == {"detail": "avisos_desligados"}
    assert r.headers["cache-control"] == "no-store"


def test_rotas_sem_cache(client, session):
    respostas = [client.post("/avisos/inscrever", json=INSCRICAO)]
    respostas.append(client.post("/avisos/minhas", json=BASE))
    respostas.append(client.post("/avisos/minhas", json={**BASE, "auth": "b" * 22}))
    respostas.append(client.post("/avisos/cancelar", json=BASE))
    assert [r.status_code for r in respostas] == [200, 200, 404, 200]
    assert all(r.headers["cache-control"] == "no-store" for r in respostas)


def test_get_nao_existe(client):
    assert client.get("/avisos/minhas").status_code == 405


# Linha de comando


def test_diaria_desligada_nao_faz_nada(monkeypatch):
    monkeypatch.setattr(settings, "avisos_ativos", False)
    monkeypatch.setattr(avisos_diario, "engine", None)  # quebraria se tentasse o banco
    assert avisos_diario.main([]) == 0


@pytest.mark.parametrize(
    ("argv", "chamada"),
    [(["--semear"], "semear"), (["--simular"], "executar"), ([], "executar")],
)
def test_diaria_escolhe_o_modo(monkeypatch, engine, argv, chamada):
    feitas = []
    monkeypatch.setattr(avisos_diario, "engine", engine)
    monkeypatch.setattr(servico, "semear", lambda s: feitas.append("semear") or 0)
    monkeypatch.setattr(servico, "executar", lambda s, **k: feitas.append("executar") or k)
    assert avisos_diario.main(argv) == 0
    assert feitas == [chamada]


def test_diaria_sem_semente_sai_com_erro(monkeypatch, engine):
    def sem_semente(session, **_):
        raise servico.SemSemente("release")

    monkeypatch.setattr(avisos_diario, "engine", engine)
    monkeypatch.setattr(servico, "executar", sem_semente)
    assert avisos_diario.main([]) == 1
