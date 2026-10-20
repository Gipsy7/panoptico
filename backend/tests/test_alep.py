"""ALEP: deputados da página oficial, presença da Transparência e votos das planilhas de dados
abertos. Os arquivos de `tests/fixtures/alep/` são recortes reais (19/10/2026)."""

import io
import json
import zipfile
from pathlib import Path

from sqlalchemy import func, select

from app.models import MandatoLocal, VotacaoLocal, VotoLocal
from ingestion.assembleias import alep
from ingestion.camaras import sapl

FIXTURES = Path(__file__).parent / "fixtures" / "alep"
ELEITOS = [  # (id, nome de urna, nome civil) como na tabela de candidaturas do TSE
    (1, "ADEMAR TRAIANO", "ADEMAR LUIZ TRAIANO"),
    (2, "ALEXANDRE CURI", "ALEXANDRE CURI"),
    (3, "GUGU BUENO", "CIVIL FORA DA PLANILHA"),
]


def _pagina() -> str:
    return (FIXTURES / "deputados.html").read_text(encoding="utf-8")


def test_nunca_desliga_a_verificacao_do_certificado():
    codigo = Path(alep.__file__).read_text(encoding="utf-8")
    assert "verify=False" not in codigo and "CERT_NONE" not in codigo
    assert alep.TRANSPARENCIA.startswith("https://") and alep.LISTA.startswith("https://")


def test_deputados_da_pagina_oficial():
    lista = alep.deputados(_pagina())
    assert [d["slug"] for d in lista] == [
        "alexandre-curi", "gugu-bueno", "ademar-traiano", "ana-julia"
    ]  # fmt: skip
    curi = lista[0]  # o presidente tem o cargo no lugar de "Deputado" no cartão
    assert curi["nome"] == "ALEXANDRE CURI" and curi["partido"] == "REP"
    assert curi["foto"].startswith("https://storage2.assembleia.pr.leg.br/img/")
    assert all(d["partido"] for d in lista)


def test_presenca_conta_sessoes_e_presencas():
    lista = alep.deputados(_pagina())
    pagina = json.loads((FIXTURES / "presenca.json").read_text(encoding="utf-8"))
    frequencia = alep.presenca(pagina, lista)
    # Ademar: presente numa sessão e ausente na outra. "COBRA REPÓRTER" não é da lista.
    assert frequencia["ademar-traiano"] == (2, 1)
    assert frequencia["alexandre-curi"] == (2, 2) and frequencia["gugu-bueno"] == (2, 2)
    assert "ana-julia" not in frequencia and len(frequencia) == 3


def test_planilha_de_votacao_nominal():
    linhas = alep.ler_xlsx((FIXTURES / "item_pl_192.xlsx").read_bytes())
    dados, votos = alep.votacao(linhas)
    assert dados["data"] == "2026-08-26" and dados["resultado"] == "Aprovado"
    assert (dados["sim"], dados["nao"], dados["abstencoes"]) == (38, 0, 0)
    assert dados["materia"].startswith("Projeto de Lei 192/2026: Concede o Título de Utilidade")
    assert len(votos) == 54  # a planilha lista os 54 deputados, inclusive quem não votou
    por_nome = dict(votos)
    assert por_nome["ADEMAR LUIZ TRAIANO"] == "SIM"
    assert alep.texto_do_voto(por_nome["ALDINO JORGE BUENO"]) == "Não votou"
    assert alep.texto_do_voto("NÃO") == "Não" and alep.texto_do_voto("ABSTER") == "Abstenção"


def test_votacao_simbolica_nao_entra():
    linhas = [["ITEM 1.0", "REQUERIMENTO 1/2026"], ["TIPO VOTAÇÃO:", "SIMBÓLICA"]]
    assert alep.votacao(linhas) is None


def test_nomes_civis_ligam_urna_e_civil():
    lista = alep.deputados(_pagina())
    civis = alep.nomes_civis(lista, ELEITOS)
    assert civis == {
        "ademar-traiano": "ADEMAR LUIZ TRAIANO",
        "alexandre-curi": "ALEXANDRE CURI",
        "gugu-bueno": "CIVIL FORA DA PLANILHA",
    }


def _pacote() -> bytes:
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("deputados.html", _pagina())
        z.writestr("presenca_2026.json", (FIXTURES / "presenca.json").read_text(encoding="utf-8"))
        z.writestr("votacoes/2026/33609.xlsx", (FIXTURES / "item_pl_192.xlsx").read_bytes())
        z.writestr(
            "votacoes.json",
            json.dumps([{"id": "1761", "item": "33609", "arquivo": "votacoes/2026/33609.xlsx"}]),
        )
    return saida.getvalue()


def test_montar_liga_votos_aos_deputados():
    casa = alep.montar(_pacote(), ELEITOS)
    assert len(casa["vereadores"]) == 4 and len(casa["votacoes"]) == 1
    votos = {(v["parlamentar"], v["voto"]) for v in casa["votos"]}
    # Ademar e Curi votaram Sim; Gugu Bueno (nome civil não consta na planilha) fica de fora.
    assert ("ademar-traiano", "Sim") in votos
    assert {v["parlamentar"] for v in casa["votos"]} <= {"ademar-traiano", "alexandre-curi"}
    ademar = next(v for v in casa["vereadores"] if v["id_externo"] == "ademar-traiano")
    assert (ademar["sessoes"], ademar["presencas"]) == (2, 1)
    assert ademar["nome_completo"] == "Ademar Luiz Traiano"
    ana = next(v for v in casa["vereadores"] if v["id_externo"] == "ana-julia")
    assert ana["sessoes"] is None  # sem presença localizada: nada inventado


def test_gravar_e_recarga_idempotente(session):
    casa = alep.montar(_pacote(), ELEITOS)
    assert sapl.gravar(session, None, casa, uf="PR") == 4
    assert sapl.gravar(session, None, casa, uf="PR") == 4  # recarga substitui, não duplica
    assert session.scalar(select(func.count()).select_from(MandatoLocal)) == 4
    assert session.scalar(select(func.count()).select_from(VotacaoLocal)) == 1
    assert session.scalar(select(func.count()).select_from(VotoLocal)) == len(casa["votos"]) > 0
