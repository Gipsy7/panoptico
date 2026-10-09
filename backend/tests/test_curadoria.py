import pytest
from sqlalchemy import select

from app.models import Caso, Evento
from ingestion import curadoria
from ingestion import pessoas as carga_pessoas
from tests.test_pessoas import _cenario

DOCUMENTOS = (
    "codigo,tipo,orgao,numero,numero_cnj,data,url,resumo\n"
    "den,denuncia,Ministério Público Federal,Inq 1,,2020-01-02,https://www.mpf.mp.br/x,Denúncia.\n"
    "abs,acordao,Supremo Tribunal Federal,AP 2,,2022-03-04,https://portal.stf.jus.br/y,Acórdão.\n"
)


def _caso(base, pessoas_csv, rascunho="false", slug="teste"):
    pasta = base / "casos" / slug
    pasta.mkdir(parents=True)
    (pasta / "caso.toml").write_text(
        f'nome = "Caso"\nresumo = "Fatos."\nconferido_em = 2026-10-09\nrascunho = {rascunho}\n',
        encoding="utf-8",
    )
    (pasta / "documentos.csv").write_text(DOCUMENTOS, encoding="utf-8")
    (pasta / "pessoas.csv").write_text(
        "pessoa,nome_conferencia,papel,documento,data,descricao\n" + pessoas_csv, encoding="utf-8"
    )


def test_caso_publica_os_papeis_e_absolvicao_tem_o_mesmo_peso(client, session, tmp_path):
    _cenario(session)
    carga_pessoas.processar(session)
    _caso(
        tmp_path,
        "parlamentar:camara:999,Ana Maria Souza,denunciado,den,,Denunciada pelo MPF.\n"
        "parlamentar:camara:999,Ana Souza,absolvido,abs,,Absolvida pelo STF.\n",
    )
    resultado = curadoria.processar(session, tmp_path)
    assert resultado.eventos == 2
    assert session.get(Caso, "teste").nome == "Caso"
    situacoes = session.scalars(select(Evento.situacao).where(Evento.caso_slug == "teste")).all()
    assert sorted(situacoes) == ["absolvido(a)", "denunciado(a)"]
    corpo = client.get("/casos/teste").json()
    assert [d["tipo"] for d in corpo["documentos"]] == ["denuncia", "acordao"]
    assert {p["papel"] for p in corpo["pessoas"]} == {"denunciado(a)", "absolvido(a)"}
    assert client.get("/casos").json() == [
        {"slug": "teste", "nome": "Caso", "periodo": None, "pessoas": 1}
    ]
    assert client.get("/casos/nao-existe").status_code == 404
    pessoa = session.scalar(select(Evento.pessoa_id).where(Evento.caso_slug == "teste"))
    tipos = [i["tipo"] for i in client.get(f"/pessoas/{pessoa}/eventos").json()["itens"]]
    assert tipos.count("caso") == 2


def test_rascunho_nao_publica_e_erro_reprova_tudo(session, tmp_path):
    _cenario(session)
    carga_pessoas.processar(session)
    _caso(tmp_path, "parlamentar:camara:999,Ana Maria Souza,denunciado,den,,X.\n", rascunho="true")
    assert curadoria.processar(session, tmp_path).rascunhos == 1
    _caso(
        tmp_path,
        "parlamentar:camara:999,Rui Lima,denunciado,den,,X.\n"  # nome não confere
        "parlamentar:camara:1,Ana,denunciado,den,,X.\n"  # pessoa inexistente
        "parlamentar:camara:999,Ana Maria Souza,culpado,den,,X.\n",  # papel desconhecido
        slug="erro",
    )
    with pytest.raises(curadoria.CuradoriaInvalida) as erro:
        curadoria.processar(session, tmp_path)
    mensagens = str(erro.value)
    assert "não confere" in mensagens and "não encontrada" in mensagens and "culpado" in mensagens


def test_vinculo_so_pelo_nome_nao_entra_e_processo_manual(session, tmp_path):
    _cenario(session)
    carga_pessoas.processar(session)
    (tmp_path / "curadoria").mkdir()
    cabecalho = ("pessoa,nome_conferencia,tribunal,classe,numero,numero_cnj,papel,relator,"
                 "data_autuacao,situacao,url,conferido_em,conferido_por,rascunho\n")  # fmt: skip
    (tmp_path / "curadoria" / "processos.csv").write_text(
        cabecalho + "mandato_local:assembleia:AC::77,Ana Maria Souza,STF,Inq,4000,,investigado,,,,"
        "https://portal.stf.jus.br/p,2026-10-09,Fulano,false\n",
        encoding="utf-8",
    )
    with pytest.raises(curadoria.CuradoriaInvalida, match="só pelo nome"):
        curadoria.processar(session, tmp_path)
    (tmp_path / "curadoria" / "processos.csv").write_text(
        cabecalho
        + "parlamentar:camara:999,Ana Maria Souza,STF,Inq,4000,,investigado,Min. X,2021-05-06,"
        "Em tramitação,https://portal.stf.jus.br/p,2026-10-09,Fulano,false\n",
        encoding="utf-8",
    )
    assert curadoria.processar(session, tmp_path).eventos == 1
    evento = session.scalar(select(Evento).where(Evento.tipo == "processo"))
    assert evento.descricao == (
        "Parte como investigado(a) no processo Inq 4000 no STF, relator(a) Min. X, "
        "autuado em 06/05/2021."
    )
    assert evento.situacao == "Em tramitação (conferido em 09/10/2026)"
