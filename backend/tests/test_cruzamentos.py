from datetime import date
from xml.etree import ElementTree as ET

from app.models import (
    BemDeclarado,
    CpgfPortadorMes,
    Evento,
    Parlamentar,
    Pessoa,
    PessoaVinculo,
    ServidorFederal,
    ViagemFederalAno,
)
from app.models.candidatura import Candidatura


def _pessoa(session, nome="Ana Souza", cpf="12345678901"):
    p = Pessoa(nome=nome, chave_nome=nome.upper(), cpf=cpf, titulo="000111222333")
    session.add(p)
    session.flush()
    return p


def _vinculo(session, pessoa, fonte, id_externo, regra="cpf", revisado=False):
    v = PessoaVinculo(
        pessoa_id=pessoa.id, fonte=fonte, id_externo=id_externo, regra=regra, revisado=revisado
    )
    session.add(v)
    session.flush()
    return v


def _evento(session, pessoa, vinculo, tipo="sancao", **extra):
    e = Evento(
        pessoa_id=pessoa.id, vinculo_id=vinculo.id, tipo=tipo, fonte=vinculo.fonte,
        id_externo=vinculo.id_externo, descricao=extra.pop("descricao", "Registro de teste."),
        fonte_url="https://exemplo.gov.br/x", **extra,
    )  # fmt: skip
    session.add(e)
    session.flush()
    return e


def _sem_chaves_sensiveis(corpo: str):
    for proibido in ('"cpf":', '"titulo":', "nascimento", "12345678901", "000111222333"):
        assert proibido not in corpo


def test_sancoes_so_com_vinculo_publicavel(client, session):
    p = _pessoa(session)
    forte = _vinculo(session, p, "cgu_ceis", "1", "cpf_parcial_nome")
    fraco = _vinculo(session, p, "cgu_ceaf", "2", "nome_casa")
    _evento(session, p, forte, data=date(2024, 3, 1), orgao="CGU", situacao="vigente")
    _evento(session, p, fraco, data=date(2023, 1, 1), orgao="CGU")
    _evento(session, p, forte, tipo="processo", descricao="Outro tipo")
    r = client.get(f"/pessoas/{p.id}/sancoes")
    assert r.status_code == 200
    corpo = r.json()
    assert len(corpo["itens"]) == 1
    item = corpo["itens"][0]
    assert item["regra"] == "cpf_parcial_nome" and "parte do CPF" in item["ligacao"]
    assert item["fonte_url"] == "https://exemplo.gov.br/x"
    _sem_chaves_sensiveis(r.text)
    session.execute(
        PessoaVinculo.__table__.update().where(PessoaVinculo.id == fraco.id).values(revisado=True)
    )
    assert len(client.get(f"/pessoas/{p.id}/sancoes").json()["itens"]) == 2
    assert client.get("/pessoas/999999/sancoes").status_code == 404


def test_servico_federal_com_media_da_casa(client, session):
    p = _pessoa(session)
    outra = _pessoa(session, "Rui Lima", "98765432100")
    for n, (pes, ext) in enumerate([(p, "1"), (outra, "2"), (None, "3")]):
        session.add(
            Parlamentar(
                casa="camara",
                id_externo=ext,
                nome_parlamentar=f"P{n}",
                nome_civil=f"P{n}",
                uf="AC",
                fonte_url="https://x",
                atualizado_em=date(2026, 1, 1),
                em_exercicio=True,
            )  # fmt: skip
        )
        if pes:
            _vinculo(session, pes, "parlamentar", f"camara:{ext}", "origem")
    session.add(ServidorFederal(
        pessoa_id=p.id, id_externo="s1", funcao="Assessor", sigla="CCX", orgao="Ministério X",
        primeiro_mes=date(2024, 1, 1), ultimo_mes=date(2024, 6, 1),
    ))  # fmt: skip
    _vinculo(session, p, "cgu_servidores", "s1", "cpf_parcial_nome")
    for pes, qtd in ((p, 4), (outra, 2)):
        session.add(ViagemFederalAno(
            pessoa_id=pes.id, ano=2024, viagens=qtd, diarias=100, passagens=200, outros=0,
            devolucao=0, ultima_viagem=date(2024, 5, 1),
        ))  # fmt: skip
    _vinculo(session, p, "cgu_viagens", f"2024:{p.id}", "cpf_parcial_nome")
    _vinculo(session, outra, "cgu_viagens", f"2024:{outra.id}", "cpf_parcial_nome")
    session.add(CpgfPortadorMes(
        pessoa_id=p.id, orgao="Órgão A", ano=2024, mes=3, transacoes=2, total=300, saques=50,
    ))  # fmt: skip
    session.add(CpgfPortadorMes(
        pessoa_id=p.id, orgao="Órgão A", ano=2024, mes=4, transacoes=1, total=300, saques=0,
    ))  # fmt: skip
    _vinculo(session, p, "cgu_cpgf", f"2024:{p.id}:Órgão A", "cpf_parcial_nome")
    session.flush()
    r = client.get(f"/pessoas/{p.id}/servico-federal")
    assert r.status_code == 200
    c = r.json()
    assert c["regra"] == "cpf_parcial_nome" and c["cargos"][0]["funcao"] == "Assessor"
    v = c["viagens_por_ano"][0]
    assert v["viagens"] == 4 and v["media_casa_viagens"] == 2.0  # (4 + 2 + 0) / 3
    assert v["media_casa_valor"] == 200.0  # (300 + 300 + 0) / 3
    k = c["cartao_por_ano_e_orgao"][0]
    assert (k["transacoes"], k["total"], k["saques"], k["media_casa_total"]) == (
        3,
        600.0,
        50.0,
        200.0,
    )
    assert c["media_da_casa"]["parlamentares_em_exercicio"] == 3
    _sem_chaves_sensiveis(r.text)


def test_servico_federal_sem_vinculo_publicavel_nao_aparece(client, session):
    p = _pessoa(session)
    session.add(ViagemFederalAno(
        pessoa_id=p.id, ano=2024, viagens=1, diarias=1, passagens=1, outros=0, devolucao=0,
    ))  # fmt: skip
    _vinculo(session, p, "cgu_viagens", f"2024:{p.id}", "nome_casa")
    session.flush()
    c = client.get(f"/pessoas/{p.id}/servico-federal").json()
    assert c["viagens_por_ano"] == [] and c["media_da_casa"] is None


def test_carreira_lista_candidaturas_com_bens_e_recorte(client, session):
    p = _pessoa(session)
    ids = []
    for ano, sq, sit in ((2018, "1", "NÃO ELEITO"), (2022, "2", "ELEITO POR QP")):
        c = Candidatura(
            ano_eleicao=ano, sq_candidato=sq, cargo="DEPUTADO ESTADUAL", uf="AC", unidade="Acre",
            nome="Ana", nome_urna="Ana", partido="PT", situacao_turno=sit, votos=1000 * ano // 2000,
            cpf="12345678901", titulo="000111222333", data_nascimento=date(1980, 1, 1),
        )  # fmt: skip
        session.add(c)
        session.flush()
        ids.append(c.id)
        _vinculo(session, p, "candidatura", f"{ano}:{sq}", "titulo")
    session.add(BemDeclarado(candidatura_id=ids[1], ordem=1, tipo="Casa", descricao="x", valor=500))
    session.flush()
    r = client.get(f"/pessoas/{p.id}/carreira")
    assert r.status_code == 200
    corpo = r.json()
    assert [i["ano"] for i in corpo["itens"]] == [2022, 2018]
    a, b = corpo["itens"]
    assert a["eleito"] and a["bens_total"] == 500.0 and a["votos"] == 1011
    assert not b["eleito"] and b["bens_total"] is None and not b["bens_declarados"]
    assert corpo["recorte"]["anos_bens"] == [2018, 2022, 2024]
    _sem_chaves_sensiveis(r.text)


def test_feed_atom_e_xml_valido(client, session):
    p = _pessoa(session)
    v = _vinculo(session, p, "cgu_ceis", "1")
    _evento(session, p, v, data=date(2024, 3, 1), orgao="CGU & cia <teste>")
    r = client.get(f"/pessoas/{p.id}/eventos.rss")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/atom+xml")
    raiz = ET.fromstring(r.content)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    assert raiz.tag.endswith("feed")
    entradas = raiz.findall("a:entry", ns)
    assert len(entradas) == 1
    assert entradas[0].find("a:link", ns).get("href") == "https://exemplo.gov.br/x"
    assert "Cache-Control" in r.headers
    _sem_chaves_sensiveis(r.text)
    assert client.get("/pessoas/999999/eventos.rss").status_code == 404
