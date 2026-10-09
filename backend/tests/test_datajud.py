from datetime import date

from sqlalchemy import select

from app.models import Evento, PessoaVinculo, Processo
from ingestion import pessoas as carga_pessoas
from ingestion.cnj import datajud
from tests.test_pessoas import _cenario


def test_tribunal_pelo_numero():
    assert datajud.alias("0600274-98.2024.6.14.0025") == "tre-pa"  # Justiça Eleitoral, TR 14
    assert datajud.alias("0601390-55.2022.6.00.0000") == "tse"
    assert datajud.alias("0600001-00.2024.6.07.0001") == "tre-dft"
    assert datajud.alias("0000125-91.2004.8.26.0627") == "tjsp"
    assert datajud.alias("0000001-00.2020.8.07.0001") == "tjdft"
    assert datajud.alias("0818338-75.2019.4.05.8300") == "trf5"
    assert datajud.alias("0000001-00.2020.1.00.0000") is None  # STF não está no DataJud
    assert datajud.alias("TC 001.825/2015-1") is None


def _hit(atualizado, sigilo=0, movimentos=()):
    return {"_source": {"numeroProcesso": "06002749820246140025", "tribunal": "TRE-PA",
                        "classe": {"nome": "Registro de Candidatura"},
                        "orgaoJulgador": {"nome": "025ª ZONA ELEITORAL DE CAPANEMA PA"},
                        "dataAjuizamento": "20240810144421",
                        "dataHoraUltimaAtualizacao": atualizado,
                        "nivelSigilo": sigilo, "movimentos": list(movimentos)}}  # fmt: skip


def test_normalizar_fica_o_grau_mais_recente_e_respeita_sigilo():
    hoje = date(2026, 10, 9)
    movimentos = [{"dataHora": "2024-09-07T14:18:21.000Z", "nome": "Baixa Definitiva"},
                  {"dataHora": "2024-08-10T10:00:00.000Z", "nome": "Distribuição"}]  # fmt: skip
    linha = datajud.normalizar(
        "0600274-98.2024.6.14.0025",
        [_hit("2025-01-01T00:00:00Z"), _hit("2026-07-15T07:31:55Z", movimentos=movimentos)],
        hoje,
    )
    assert (linha["ultimo_andamento"], linha["data_ultimo_andamento"]) == (
        "Baixa Definitiva",
        date(2024, 9, 7),
    )
    assert linha["data_ajuizamento"] == date(2024, 8, 10)
    sigiloso = datajud.normalizar(
        "x", [_hit("2026-01-01T00:00:00Z", sigilo=5, movimentos=movimentos)], hoje
    )
    assert sigiloso["sigiloso"] and "ultimo_andamento" not in sigiloso
    assert datajud.normalizar("y", [], hoje)["encontrado"] is False


def test_linha_do_tempo_mostra_o_andamento(client, session):
    _cenario(session)
    carga_pessoas.processar(session)
    vinculo, pessoa = session.execute(
        select(PessoaVinculo.id, PessoaVinculo.pessoa_id).where(
            PessoaVinculo.id_externo == "2024:3"
        )
    ).one()
    session.add(
        Evento(pessoa_id=pessoa, vinculo_id=vinculo, tipo="cassacao", descricao="x", fonte="t",
               id_externo="1", numero_processo="0600274-98.2024.6.14.0025")
    )  # fmt: skip
    session.add(
        Processo(numero="0600274-98.2024.6.14.0025", tribunal="TRE-PA",
                 classe="Registro de Candidatura",
                 ultimo_andamento="Baixa Definitiva", data_ultimo_andamento=date(2024, 9, 7),
                 consultado_em=date(2026, 10, 9))
    )  # fmt: skip
    session.flush()
    itens = client.get(f"/pessoas/{pessoa}/eventos").json()["itens"]
    cassacao = next(i for i in itens if i["tipo"] == "cassacao")
    assert cassacao["processo"]["ultimo_andamento"] == "Baixa Definitiva"
    assert next(i for i in itens if i["tipo"] == "eleito")["processo"] is None
