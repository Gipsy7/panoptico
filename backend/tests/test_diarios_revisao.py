from datetime import date

from sqlalchemy import select

from app.models import Candidatura, DiarioAto, Evento, Municipio, Pessoa, PessoaVinculo
from app.services import pessoas as servico
from ingestion import comum
from ingestion.diarios import revisao

URL_A = "https://data.queridodiario.ok.org.br/4314902/2025-08-21/a.pdf"
URL_B = "https://data.queridodiario.ok.org.br/4314902/2025-09-01/b.pdf"


def _cenario(session):
    session.add(Municipio(ibge="4314902", nome="Porto Alegre", uf="RS", nome_chave="PORTO ALEGRE"))
    nome = "Ana Maria Souza"
    p = Pessoa(nome=nome, chave_nome=comum.chave_nome(nome))
    session.add(p)
    session.flush()
    session.add(
        Candidatura(
            ano_eleicao=2024,
            sq_candidato="77",
            cargo="VEREADOR",
            uf="RS",
            unidade="X",
            municipio_ibge="4314902",
            nome=nome,
            nome_urna="Ana",
            situacao_turno="ELEITO",
        )  # fmt: skip
    )
    session.add(
        PessoaVinculo(pessoa_id=p.id, fonte="candidatura", id_externo="2024:77", regra="origem")
    )
    for url, tipo in ((URL_A, "nomeacao"), (URL_B, "exoneracao")):
        session.add(
            DiarioAto(
                pessoa_id=p.id, municipio_ibge="4314902", data=date(2025, 8, 21),
                tipo_ato=tipo, trecho="ANA MARIA SOUZA ...", url=url,
            )
        )  # fmt: skip
    session.flush()
    return p


def _eventos(session):
    return list(session.scalars(select(Evento).where(Evento.tipo == "ato_pessoal")))


def test_fila_so_com_nao_decididos_e_com_contexto(session, tmp_path):
    csv = tmp_path / "atos.csv"
    p = _cenario(session)
    fila = revisao.pendentes(session, csv)
    assert {i["url"] for i in fila} == {URL_A, URL_B}
    item = next(i for i in fila if i["url"] == URL_A)
    assert item["pessoa_chave"] == "candidatura:2024:77"
    assert item["pessoa"] == "Ana Maria Souza" and item["cargo"] == "vereador"
    assert item["municipio"] == "Porto Alegre (RS)" and item["tipo_ato"] == "nomeacao"
    revisao.gravar_decisao(item, "recusado", "Fulano", caminho=csv)
    assert [i["url"] for i in revisao.pendentes(session, csv)] == [URL_B]
    # Nada publicável antes do aceite.
    assert _eventos(session) == []
    tipos = [i["tipo"] for i in servico.eventos(session, p.id)["itens"]]
    assert "ato_pessoal" not in tipos


def test_aceite_gera_evento_idempotente(session, tmp_path):
    csv = tmp_path / "atos.csv"
    p = _cenario(session)
    item = next(i for i in revisao.pendentes(session, csv) if i["url"] == URL_A)
    revisao.gravar_decisao(item, "aceito", "Fulano", "conferido", caminho=csv)
    for _ in range(2):
        assert revisao.aplicar_atos(session, csv) == {"aceitos": 1, "recusados": 0}
    (e,) = _eventos(session)
    assert e.fonte == "querido_diario_atos" and e.fonte_url == URL_A
    assert e.data == date(2025, 8, 21) and "Nomeação" in e.descricao
    assert e.orgao == "Diário Oficial de Porto Alegre"
    assert e.id_externo == revisao.id_do_evento("candidatura:2024:77", URL_A)
    ato = session.scalar(select(DiarioAto).where(DiarioAto.url == URL_A))
    assert ato.revisado is True
    # O aceito sai da fila e aparece na linha do tempo; o outro continua sem aparecer.
    assert [i["url"] for i in revisao.pendentes(session, csv)] == [URL_B]
    tipos = [i["tipo"] for i in servico.eventos(session, p.id)["itens"]]
    assert tipos.count("ato_pessoal") == 1


def test_recusa_nao_gera_evento_e_desfaz_aceite_anterior(session, tmp_path):
    csv = tmp_path / "atos.csv"
    _cenario(session)
    item = next(i for i in revisao.pendentes(session, csv) if i["url"] == URL_A)
    revisao.gravar_decisao(item, "recusado", "Fulano", caminho=csv)
    assert revisao.aplicar_atos(session, csv) == {"aceitos": 0, "recusados": 1}
    assert _eventos(session) == []
    # Mudou de ideia: aceito e depois recusado (a última linha vale).
    revisao.gravar_decisao(item, "aceito", "Fulano", caminho=csv)
    revisao.aplicar_atos(session, csv)
    assert len(_eventos(session)) == 1
    revisao.gravar_decisao(item, "recusado", "Fulano", caminho=csv)
    revisao.aplicar_atos(session, csv)
    assert _eventos(session) == []
    ato = session.scalar(select(DiarioAto).where(DiarioAto.url == URL_A))
    assert ato.revisado is False


def test_reaplicacao_depois_de_recarga(session, tmp_path):
    csv = tmp_path / "atos.csv"
    p = _cenario(session)
    item = next(i for i in revisao.pendentes(session, csv) if i["url"] == URL_A)
    revisao.gravar_decisao(item, "aceito", "Fulano", caminho=csv)
    revisao.aplicar_atos(session, csv)
    # Recarga: a pessoa é apagada e recriada com outro id (e a sugestão volta não revisada).
    session.delete(p)
    session.flush()
    nova = _cenario_sem_municipio(session)
    assert nova.id != p.id
    assert _eventos(session) == []
    assert revisao.aplicar_atos(session, csv)["aceitos"] == 1
    (e,) = _eventos(session)
    assert e.pessoa_id == nova.id and e.id_externo == revisao.id_do_evento(
        "candidatura:2024:77", URL_A
    )
    assert [i["url"] for i in revisao.pendentes(session, csv)] == [URL_B]


def _cenario_sem_municipio(session):
    session.expire_all()
    session.query(Candidatura).filter_by(sq_candidato="77", ano_eleicao=2024).delete()
    session.query(Municipio).filter_by(ibge="4314902").delete()
    return _cenario(session)


def test_cli_tipo_diario_exporta_a_fila(session, tmp_path, monkeypatch):
    from contextlib import nullcontext

    from ingestion import revisar

    monkeypatch.setattr(revisao, "ATOS_REVISADOS", tmp_path / "atos.csv")
    monkeypatch.setattr(revisar, "ATOS_REVISADOS", tmp_path / "atos.csv")
    monkeypatch.setattr(revisar, "SessionLocal", lambda: nullcontext(session))
    _cenario(session)
    saida = tmp_path / "fila.csv"
    assert revisar.main(["--tipo", "diario", "--exportar", str(saida)]) == 0
    linhas = saida.read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 3 and linhas[0].startswith("url,pessoa_chave,pessoa,cargo")
