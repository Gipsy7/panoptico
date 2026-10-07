import io
import json
import zipfile

from sqlalchemy import func, select

from app.models import ProposicaoTema
from ingestion.camara import temas
from tests.test_api import _ingestao

CABECALHO = '"uriProposicao";"siglaTipo";"numero";"ano";"codTema";"tema";"relevancia"'
URI = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/"


def _zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(
            "temas_2025.csv",
            "﻿"
            + "\n".join(
                [
                    CABECALHO,
                    f'"{URI}1";"PL";"1";"2025";"40";"Economia";"0"',
                    f'"{URI}1";"PL";"1";"2025";"70";"Finanças Públicas e Orçamento";"0"',
                    f'"{URI}2";"PL";"2";"2025";"20";"";"0"',  # sem tema: ignora
                ]
            ),
        )
        z.writestr(
            temas.API_JSON,
            json.dumps({"1029018": [{"codTema": 57, "tema": "Defesa e Segurança"}]}),
        )
    return buffer.getvalue()


def test_normalizar_temas_junta_arquivos_e_api():
    registros = temas.normalizar(_zip())
    assert [(r["proposicao_id_externo"], r["tema"]) for r in registros] == [
        ("1", "Economia"),
        ("1", "Finanças Públicas e Orçamento"),
        ("1029018", "Defesa e Segurança"),
    ]
    assert {r["casa"] for r in registros} == {"camara"}


def test_carregar_temas_substitui_os_anteriores(session):
    temas.carregar(session, _zip(), _ingestao(session))
    temas.carregar(session, _zip(), _ingestao(session))
    assert session.scalar(select(func.count()).select_from(ProposicaoTema)) == 3
