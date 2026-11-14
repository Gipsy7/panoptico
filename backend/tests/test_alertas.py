from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.models.alerta import AlertaEnviado
from app.models.fonte_ingestao import FonteIngestao
from app.models.metrica import MetricaDiaria
from app.services import alertas

# 13/11/2026, 15h em Brasília.
AGORA = datetime(2026, 11, 13, 18, 0, tzinfo=UTC)
HOJE = AGORA.date()


@pytest.fixture(autouse=True)
def _config(monkeypatch):
    monkeypatch.setattr(settings, "alertas_ativos", True)
    monkeypatch.setattr(settings, "alerta_email_para", "dono@exemplo.test")
    monkeypatch.setattr(settings, "smtp_usuario", "robo@exemplo.test")
    monkeypatch.setattr(settings, "smtp_senha", "senha-de-teste")
    monkeypatch.setattr(settings, "alerta_fluxo_fator", 3.0)
    monkeypatch.setattr(settings, "alerta_fluxo_piso", 300)
    monkeypatch.setattr(settings, "alerta_disco_pct", 85)


@pytest.fixture
def sem_rede(monkeypatch):
    """`rodar` sem conferir endereços nem o disco de verdade."""
    monkeypatch.setattr(alertas, "saude", lambda agora: None)
    monkeypatch.setattr(alertas, "disco", lambda agora: None)


def _visitas(session, dia, total, aparelho="celular"):
    session.add(
        MetricaDiaria(
            dia=dia, tipo="visita", chave="-", aparelho=aparelho, origem="direto", total=total
        )
    )
    session.flush()


def test_fluxo_compara_hoje_com_a_media_dos_7_dias(session):
    for i in range(1, 8):
        _visitas(session, HOJE - timedelta(days=i), 200)
    _visitas(session, HOJE, 400)
    _visitas(session, HOJE, 150, aparelho="computador")
    assert alertas.fluxo(session, AGORA) is None  # 550 < 3 x 200

    session.add(
        MetricaDiaria(
            dia=HOJE, tipo="visita", chave="-", aparelho="celular", origem="whatsapp", total=100
        )
    )
    session.flush()
    alerta = alertas.fluxo(session, AGORA)  # 650 >= 600
    assert alerta is not None
    assert alerta.chave == "fluxo" and alerta.janela == "2026-11-13"
    assert "650 visitas" in alerta.assunto
    assert "3,2 vezes a média" in alerta.texto
    assert "Média dos 7 dias anteriores: 200 por dia." in alerta.texto


def test_fluxo_respeita_o_piso_e_conta_dia_vazio_como_zero(session):
    # Só um dia com visita na semana: média de 70 / 7 = 10. Hoje 250 é 25 vezes, mas abaixo do piso.
    _visitas(session, HOJE - timedelta(days=3), 70)
    _visitas(session, HOJE, 250)
    assert alertas.fluxo(session, AGORA) is None
    _visitas(session, HOJE, 60, aparelho="computador")
    alerta = alertas.fluxo(session, AGORA)
    assert alerta is not None and "Média dos 7 dias anteriores: 10 por dia." in alerta.texto


def test_fluxo_sem_historico_nao_divide_por_zero(session):
    _visitas(session, HOJE, 301)
    alerta = alertas.fluxo(session, AGORA)
    assert alerta is not None and "vezes a média" not in alerta.texto


def _carga(session, fonte, status, horas_atras):
    session.add(
        FonteIngestao(
            fonte=fonte,
            url="https://exemplo.test",
            arquivo_raw="x",
            status=status,
            iniciado_em=AGORA - timedelta(hours=horas_atras),
        )
    )
    session.flush()


def test_ingestao_lista_so_erros_das_ultimas_24_horas(session):
    _carga(session, "camara_despesas", "erro", 2)
    _carga(session, "camara_despesas", "erro", 5)
    _carga(session, "tse_bens", "erro", 30)  # fora da janela
    _carga(session, "senado_votacoes", "ok", 1)
    alerta = alertas.ingestao(session, AGORA)
    assert alerta is not None
    assert alerta.assunto == "Panóptico: 1 carga(s) com erro"
    assert "- camara_despesas: 2 erro(s), o último em 13/11 13:00" in alerta.texto
    assert "tse_bens" not in alerta.texto and "senado_votacoes" not in alerta.texto


def test_ingestao_sem_erro_nao_alerta(session):
    _carga(session, "senado_votacoes", "ok", 1)
    assert alertas.ingestao(session, AGORA) is None


def test_saude_lista_o_que_nao_respondeu_e_vale_por_hora(monkeypatch):
    monkeypatch.setattr(settings, "alerta_urls", "http://api:8000/saude, http://web:3000/")
    respostas = {"http://api:8000/saude": "HTTP 503", "http://web:3000/": None}
    alerta = alertas.saude(AGORA, respostas.get)
    assert alerta is not None and alerta.janela == "2026-11-13T15"
    assert "- http://api:8000/saude: HTTP 503" in alerta.texto
    assert "web:3000" not in alerta.texto
    assert alertas.saude(AGORA, lambda url: None) is None


def test_disco_alerta_a_partir_do_limite():
    gb = 1024**3
    assert alertas.disco(AGORA, lambda: (70 * gb, 59 * gb)) is None  # 84%
    alerta = alertas.disco(AGORA, lambda: (70 * gb, 63 * gb))  # 90%
    assert alerta is not None and "disco em 90%" in alerta.assunto and "7,0 GB" in alerta.texto


def test_rodar_envia_uma_vez_por_janela(session, sem_rede):
    _carga(session, "camara_despesas", "erro", 2)
    enviados = []
    assert alertas.rodar(session, AGORA, enviados.append) == {
        "achados": 1,
        "novos": 1,
        "enviados": 1,
    }
    # Cinco minutos depois, a mesma falha: nada novo.
    depois = AGORA + timedelta(minutes=5)
    assert alertas.rodar(session, depois, enviados.append)["enviados"] == 0
    assert len(enviados) == 1
    registro = session.scalars(select(AlertaEnviado)).one()
    assert (registro.chave, registro.janela) == ("ingestao", "2026-11-13")
    assert "camara_despesas" in registro.texto
    # No dia seguinte, com erro novo, avisa de novo.
    amanha = AGORA + timedelta(days=1)
    _carga(session, "camara_despesas", "erro", -23)
    assert alertas.rodar(session, amanha, enviados.append)["enviados"] == 1


def test_rodar_nao_registra_quando_o_envio_falha(session, sem_rede):
    _carga(session, "camara_despesas", "erro", 2)

    def falhar(alerta):
        raise OSError("sem rede")

    assert alertas.rodar(session, AGORA, falhar)["enviados"] == 0
    assert session.scalar(select(func.count()).select_from(AlertaEnviado)) == 0
    # Na rodada seguinte, com o envio de volta, a mensagem sai.
    enviados = []
    assert alertas.rodar(session, AGORA, enviados.append)["enviados"] == 1


def test_rodar_sem_configuracao_so_registra_no_log(session, sem_rede, monkeypatch):
    monkeypatch.setattr(settings, "smtp_senha", "")
    _carga(session, "camara_despesas", "erro", 2)
    enviados = []
    assert alertas.rodar(session, AGORA, enviados.append) == {
        "achados": 1,
        "novos": 1,
        "enviados": 0,
    }
    assert enviados == []


def test_email_tem_assunto_destino_e_ambiente(monkeypatch):
    enviadas = []

    class Servidor:
        def __init__(self, host, porta, **kw):
            enviadas.append((host, porta))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, usuario, senha):
            enviadas.append(("login", usuario))

        def send_message(self, mensagem):
            enviadas.append(mensagem)

    monkeypatch.setattr(alertas.smtplib, "SMTP_SSL", Servidor)
    monkeypatch.setattr(settings, "ambiente", "producao")
    alertas.enviar_email(alertas.Alerta("disco", "2026-11-13", "Panóptico: disco em 90%", ("a",)))
    assert enviadas[0] == ("smtp.zoho.com", 465)
    assert enviadas[1] == ("login", "robo@exemplo.test")
    mensagem = enviadas[2]
    assert mensagem["To"] == "dono@exemplo.test" and mensagem["From"] == "robo@exemplo.test"
    assert mensagem["Subject"] == "Panóptico: disco em 90%"
    assert "ambiente: producao" in mensagem.get_content()
