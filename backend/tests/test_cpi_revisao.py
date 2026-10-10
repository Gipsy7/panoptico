from datetime import date

from sqlalchemy import select

from app.models import Cpi, CpiIndiciamentoSugestao, Evento, Pessoa, PessoaVinculo
from app.services import pessoas as servico
from ingestion import comum
from ingestion.congresso import cpi_indiciamentos
from ingestion.congresso import cpi_revisao as revisao

PDF = "https://legis.senado.leg.br/relatorio.pdf"


def _pessoa(session, nome, id_externo):
    p = Pessoa(nome=nome, chave_nome=comum.chave_nome(nome))
    session.add(p)
    session.flush()
    session.add(
        PessoaVinculo(pessoa_id=p.id, fonte="parlamentar", id_externo=id_externo, regra="origem")
    )
    session.flush()
    return p


def _cenario(session):
    cpi = Cpi(
        casa="senado", id_externo="2441", tipo="CPI", nome="CPI da Pandemia",
        data_fim=date(2021, 11, 26), relatorio_url=PDF,
    )  # fmt: skip
    session.add(cpi)
    session.flush()
    for nome, pagina, pj in (
        ("Fulano de Tal", 10, False),
        ("Beltrano Silva", 11, False),
        ("Empresa Exemplo S.A.", 12, True),
    ):
        session.add(
            CpiIndiciamentoSugestao(
                cpi_id=cpi.id, nome_citado=nome, trecho=f"1) {nome}: art. 1", pagina=pagina,
                url=PDF, pessoa_juridica=pj,
            )
        )  # fmt: skip
    pessoa = _pessoa(session, "Fulano de Tal", "senado:1")
    session.flush()
    return cpi, pessoa


def _eventos(session):
    return list(session.scalars(select(Evento).where(Evento.tipo == "cpi_indiciamento")))


def _item(fila, nome):
    return next(i for i in fila if i["nome_citado"] == nome)


def test_fila_so_com_nao_decididos_e_com_candidatos(session, tmp_path):
    csv = tmp_path / "ind.csv"
    _, pessoa = _cenario(session)
    fila = revisao.pendentes(session, csv)
    # Pessoa jurídica fica fora; os outros dois esperam.
    assert {i["nome_citado"] for i in fila} == {"Fulano de Tal", "Beltrano Silva"}
    item = _item(fila, "Fulano de Tal")
    assert item["cpi"] == "CPI da Pandemia" and item["url"] == PDF and item["pagina"] == 10
    assert item["chave"] == "senado:2441|10|FULANO DE TAL"
    assert [c["pessoa_chave"] for c in item["candidatos"]] == ["parlamentar:senado:1"]
    assert item["candidatos"][0]["nome"] == pessoa.nome
    assert _item(fila, "Beltrano Silva")["candidatos"] == []
    revisao.gravar_decisao(item, "recusado", "Fulano", caminho=csv)
    assert [i["nome_citado"] for i in revisao.pendentes(session, csv)] == ["Beltrano Silva"]
    # Nada publicável antes do aceite.
    assert _eventos(session) == []
    assert "cpi_indiciamento" not in [
        i["tipo"] for i in servico.eventos(session, pessoa.id)["itens"]
    ]


def test_aceite_gera_evento_idempotente(session, tmp_path):
    csv = tmp_path / "ind.csv"
    cpi, pessoa = _cenario(session)
    item = _item(revisao.pendentes(session, csv), "Fulano de Tal")
    revisao.gravar_decisao(item, "aceito", "Fulano", "parlamentar:senado:1", caminho=csv)
    for _ in range(2):
        assert revisao.aplicar_indiciamentos(session, csv) == {"aceitos": 1, "recusados": 0}
    (e,) = _eventos(session)
    assert e.pessoa_id == pessoa.id and e.fonte == "cpi_indiciamentos" and e.fonte_url == PDF
    assert e.data == date(2021, 11, 26) and e.orgao == "CPI da Pandemia"
    assert "não é acusação formal nem condenação" in e.descricao
    assert "Ministério Público" in e.descricao
    assert e.id_externo == revisao.id_do_evento("parlamentar:senado:1", item["chave"])
    s = session.scalar(
        select(CpiIndiciamentoSugestao).where(
            CpiIndiciamentoSugestao.cpi_id == cpi.id,
            CpiIndiciamentoSugestao.nome_citado == "Fulano de Tal",
        )
    )
    assert s.revisado is True
    assert [i["nome_citado"] for i in revisao.pendentes(session, csv)] == ["Beltrano Silva"]
    assert [i["tipo"] for i in servico.eventos(session, pessoa.id)["itens"]].count(
        "cpi_indiciamento"
    ) == 1


def test_recusa_nao_gera_evento_e_desfaz_aceite_anterior(session, tmp_path):
    csv = tmp_path / "ind.csv"
    _cenario(session)
    item = _item(revisao.pendentes(session, csv), "Fulano de Tal")
    revisao.gravar_decisao(item, "recusado", "Fulano", caminho=csv)
    assert revisao.aplicar_indiciamentos(session, csv) == {"aceitos": 0, "recusados": 1}
    assert _eventos(session) == []
    revisao.gravar_decisao(item, "aceito", "Fulano", "parlamentar:senado:1", caminho=csv)
    revisao.aplicar_indiciamentos(session, csv)
    assert len(_eventos(session)) == 1
    revisao.gravar_decisao(item, "recusado", "Fulano", caminho=csv)
    revisao.aplicar_indiciamentos(session, csv)
    assert _eventos(session) == []


def test_reaplicacao_depois_de_recarga(session, tmp_path):
    csv = tmp_path / "ind.csv"
    cpi, pessoa = _cenario(session)
    item = _item(revisao.pendentes(session, csv), "Fulano de Tal")
    revisao.gravar_decisao(item, "aceito", "Fulano", "parlamentar:senado:1", caminho=csv)
    revisao.aplicar_indiciamentos(session, csv)
    # Recarga das pessoas: apagada e recriada com outro id.
    session.delete(pessoa)
    session.flush()
    nova = _pessoa(session, "Fulano de Tal", "senado:1")
    assert nova.id != pessoa.id and _eventos(session) == []
    assert revisao.aplicar_indiciamentos(session, csv)["aceitos"] == 1
    (e,) = _eventos(session)
    assert e.pessoa_id == nova.id
    # Recarga das CPIs: a sugestão é regravada (revisada fica) e o evento continua único.
    resultado = [{"casa": "senado", "id_externo": "2441", "url": PDF, "sugestoes": [
        {"nome_citado": "Fulano de Tal", "pessoa_juridica": False, "trecho": "x", "pagina": 10}
    ]}]  # fmt: skip
    cpi_indiciamentos.gravar(session, resultado)
    revisao.aplicar_indiciamentos(session, csv)
    assert len(_eventos(session)) == 1


def test_candidato_inexistente_recusado(session, tmp_path):
    csv = tmp_path / "ind.csv"
    _cenario(session)
    item = _item(revisao.pendentes(session, csv), "Beltrano Silva")
    assert item["candidatos"] == []
    revisao.gravar_decisao(item, "recusado", "Fulano", caminho=csv)
    # Aceite apontando para pessoa que não existe na base é ignorado: nada é publicado.
    revisao.gravar_decisao(
        _item(revisao.pendentes(session, csv), "Fulano de Tal"),
        "aceito", "Fulano", "parlamentar:senado:999", caminho=csv,
    )  # fmt: skip
    assert revisao.aplicar_indiciamentos(session, csv) == {"aceitos": 0, "recusados": 1}
    assert _eventos(session) == []
    assert revisao.pendentes(session, csv) == []
