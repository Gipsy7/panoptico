import io
import zipfile
from collections import Counter
from datetime import date

import httpx
import respx
from sqlalchemy import select

from app.models import DouAto, Evento, Pessoa, PessoaVinculo
from ingestion import comum
from ingestion.dou import atos, revisao

# Recortes reais da Seção 2 do DOU (ago/2026 e mar/2025).
NOMEAR = (
    '<p class="identifica">PORTARIA Nº 424</p><p>O PRESIDENTE DO TRIBUNAL, resolve:</p>'
    "<p>Art. 1º Nomear o professor Maurício Ferreira da Silva, SIAPE n° 1513852, para "
    "exercer o cargo de Diretor Pro-tempore.</p>"
    '<p class="assina">RICARDO HOFMEISTER DE ALMEIDA MARTINS COSTA</p>'
)
LOTACAO = (
    "<p>NOMEAR, na forma do artigo 9º, inciso II, da Lei nº 8.112, de 1990, ISSUR ISRAEL KOCH "
    "para exercer, no gabinete do(a) Deputado(a) PRISCILA BEZERRA DA COSTA, o cargo em "
    "comissão de Secretário Parlamentar, SP03.</p>"
)
MAIOR = (
    "<p>Art. 3º Remover o servidor Augusto Marcelo de Oliveira Santos, Analista Judiciário. "
    "Art. 4º Dispensar ANA PAULA FERREIRA DE CARVALHO, matrícula SIAPE nº 1222380.</p>"
)
ASSINATURA = "<p>Considerando o que consta, resolve nomear.</p><p>LUIZ INÁCIO LULA DA SILVA</p>"
PRORROGACAO = (
    "<p>PRORROGAR a designação para a função de Coordenador, prevista no art. 4º, "
    "de JOSÉ ROSA DA SILVA, matrícula 123.</p>"
)
DISPENSA = "<p>Nº 1.608 - Dispensar RICARDO DA SILVA, CPF nº XXX.482.120-XX, da função.</p>"


def _indice(*nomes: tuple[int, str]):
    indice: dict = {}
    for pessoa_id, nome in nomes:
        palavras = tuple(comum.chave_nome(nome).split())
        indice.setdefault(palavras[:3], []).append((pessoa_id, palavras))
    return indice


def _achar(html: str, *nomes: tuple[int, str]):
    return atos.achar_nomes(atos.linhas_do_texto(html), _indice(*nomes))


def test_nome_como_alvo_do_ato_e_achado_sem_acento_e_em_qualquer_caixa():
    ((pessoa, tipo, trecho),) = _achar(NOMEAR, (1, "MAURICIO FERREIRA DA SILVA"))
    assert (pessoa, tipo) == (1, "nomeacao")
    assert "Maurício Ferreira da Silva" in trecho and len(trecho) <= 500
    ((_, tipo, _),) = _achar(DISPENSA, (2, "Ricardo da Silva"))
    assert tipo == "dispensa"


def test_assinatura_lotacao_e_nome_dentro_de_nome_maior_nao_sao_achados():
    # A autoridade que assina não é o alvo (parágrafo de assinatura é descartado).
    assert _achar(NOMEAR, (3, "Ricardo Hofmeister de Almeida")) == []
    # Parlamentar como lotação do nomeado, não como alvo.
    assert _achar(LOTACAO, (4, "Priscila Bezerra da Costa")) == []
    assert [a[0] for a in _achar(LOTACAO, (5, "Issur Israel Koch"))] == [5]
    # "Marcelo de Oliveira" faz parte de "Augusto Marcelo de Oliveira Santos"; "Ana Paula
    # Ferreira" faz parte de "... Ferreira de Carvalho" (a partícula não encerra o nome).
    assert _achar(MAIOR, (6, "Marcelo de Oliveira Santos"), (7, "Marcelo de Oliveira")) == []
    assert _achar(MAIOR, (8, "Ana Paula Ferreira")) == []
    assert [a[0] for a in _achar(MAIOR, (9, "Ana Paula Ferreira de Carvalho"))] == [9]
    # Linha só com o nome (assinatura de decreto) e prorrogação não são nomeação.
    assert _achar(ASSINATURA, (10, "Luiz Inácio Lula da Silva")) == []
    assert _achar(PRORROGACAO, (11, "José Rosa da Silva")) == []


def test_nome_com_menos_de_tres_palavras_ou_ambiguo_fica_fora_do_indice(session):
    for nome in ("Ana Souza", "Maria da Silva Lima", "Maria da Silva Lima", "Rita Alves Dias"):
        session.add(Pessoa(nome=nome, chave_nome=comum.chave_nome(nome)))
    session.flush()
    indice, ambiguos = atos.indice_nomes(session)
    nomes = {n for lista in indice.values() for _, n in lista}
    assert nomes == {("RITA", "ALVES", "DIAS")}
    assert ambiguos == 1


def _xml(id_materia, texto, data="05/03/2025", pub="DO2"):
    return (
        f'<xml><article id="1{id_materia}" name="Portaria-1-2025" pubName="{pub}" '
        f'artType="Portaria" pubDate="{data}" artCategory="Poder Judiciário/TRT 4" '
        f'idMateria="{id_materia}" pdfPage="http://pesquisa.in.gov.br/imprensa/jsp/visualiza/'
        f'index.jsp?data={data}&amp;jornal=529&amp;pagina=108"><body><Texto><![CDATA[{texto}]]>'
        "</Texto></body></article></xml>"
    )


def _zip(*xmls: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("2_MEC_6_001.jpg", b"imagem")
        for n, xml in enumerate(xmls):
            z.writestr(f"529_20250305_{n}.xml", "﻿" + xml)
    return buffer.getvalue()


def test_varrer_le_so_xml_da_secao_2_e_guarda_o_link_oficial():
    conteudo = _zip(
        _xml("100", NOMEAR),
        _xml("101", NOMEAR, pub="DO1"),
        _xml("102", "<p>Sem nada</p>"),
        "<xml>quebrado",
    )
    estat: Counter = Counter()
    achados = atos.varrer(conteudo, _indice((1, "Maurício Ferreira da Silva")), estat)
    assert estat["materias"] == 4 and estat["xml_invalido"] == 1
    assert len(achados) == 1
    a = achados[0]
    assert (a["pessoa_id"], a["id_materia"], a["data"], a["tipo_ato"]) == (
        1, "100", date(2025, 3, 5), "nomeacao",
    )  # fmt: skip
    assert a["orgao"] == "Poder Judiciário/TRT 4" and a["tipo_materia"] == "Portaria"
    assert a["url"].startswith("https://pesquisa.in.gov.br/imprensa/") and "pagina=108" in a["url"]


@respx.mock
def test_url_do_mes_le_o_link_do_zip_da_pagina_da_base():
    pagina = (
        '<a href="https://www.in.gov.br/documents/49035712/629105016/S01032025.zip/aa?'
        'version=1.0&amp;t=1&amp;download=true">S01</a>'
        '<a href="https://www.in.gov.br/documents/49035712/629105016/S02032025.zip/bb?'
        'version=1.0&amp;t=2&amp;download=true">S02</a>'
    )
    rota = respx.get(atos.URL_BASE).mock(return_value=httpx.Response(200, text=pagina))
    with comum.criar_cliente() as client:
        url = atos.url_do_mes(client, 2025, 3)
    assert url == (
        "https://www.in.gov.br/documents/49035712/629105016/S02032025.zip/bb"
        "?version=1.0&t=2&download=true"
    )
    assert rota.calls[0].request.url.params["mes"] == "Março"
    respx.get(atos.URL_BASE).mock(return_value=httpx.Response(200, text="<html></html>"))
    with comum.criar_cliente() as client:
        assert atos.url_do_mes(client, 2026, 9) is None


def test_meses_desde_vai_ate_o_mes_corrente():
    assert atos.meses_desde((2025, 11), date(2026, 2, 10)) == [
        (2025, 11), (2025, 12), (2026, 1), (2026, 2),
    ]  # fmt: skip


def _pessoa(session, nome="Maurício Ferreira da Silva"):
    p = Pessoa(nome=nome, chave_nome=comum.chave_nome(nome))
    session.add(p)
    session.flush()
    session.add(
        PessoaVinculo(pessoa_id=p.id, fonte="candidatura", id_externo="2024:9", regra="origem")
    )
    session.flush()
    return p


def test_gravar_e_idempotente_e_preserva_o_revisado(session):
    p = _pessoa(session)
    a = {
        "pessoa_id": p.id, "id_materia": "100", "data": date(2025, 3, 5), "tipo_ato": "nomeacao",
        "orgao": "TRT 4", "tipo_materia": "Portaria", "trecho": "x", "url": "https://dou/1",
    }  # fmt: skip
    assert atos.gravar(session, [a], 2025, 3) == 1
    assert atos.gravar(session, [a], 2025, 3) == 1
    linhas = list(session.scalars(select(DouAto)))
    assert len(linhas) == 1 and linhas[0].revisado is False
    linhas[0].revisado = True
    session.flush()
    atos.gravar(session, [], 2025, 3)  # o que já foi revisado não é apagado
    assert session.scalar(select(DouAto.revisado)) is True


def test_revisao_aceito_vira_evento_e_recusado_sai(session, tmp_path):
    p = _pessoa(session)
    session.add(
        DouAto(
            pessoa_id=p.id, id_materia="100", data=date(2025, 3, 5), tipo_ato="nomeacao",
            orgao="Poder Judiciário/TRT 4", trecho="x", url="https://dou/1",
        )
    )  # fmt: skip
    session.flush()
    csv = tmp_path / "dou.csv"
    fila = revisao.pendentes(session, csv)
    assert [f["id_materia"] for f in fila] == ["100"]
    assert fila[0]["pessoa_chave"] == "candidatura:2024:9"
    revisao.gravar_decisao(fila[0], "aceito", "teste", caminho=csv)
    assert revisao.aplicar_atos_dou(session, csv) == {"aceitos": 1, "recusados": 0}
    ev = session.scalar(select(Evento).where(Evento.fonte == "dou_atos"))
    assert ev.tipo == "ato_pessoal" and ev.fonte_url == "https://dou/1"
    assert "Nomeação" in ev.descricao and "Diário Oficial da União" in ev.descricao
    assert revisao.pendentes(session, csv) == []
    revisao.aplicar_atos_dou(session, csv)  # idempotente
    assert len(list(session.scalars(select(Evento).where(Evento.fonte == "dou_atos")))) == 1
    revisao.gravar_decisao(fila[0], "recusado", "teste", caminho=csv)
    assert revisao.aplicar_atos_dou(session, csv) == {"aceitos": 0, "recusados": 1}
    assert session.scalar(select(Evento).where(Evento.fonte == "dou_atos")) is None
    assert session.scalar(select(DouAto.revisado)) is False
