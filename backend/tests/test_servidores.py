import csv
import io
import zipfile
from datetime import date

import httpx
import respx
from sqlalchemy import select

from app.models import Evento, Pessoa, PessoaVinculo, ServidorFederal
from ingestion import comum
from ingestion.transparencia import servidores

COLUNAS = ["Id_SERVIDOR_PORTAL", "NOME", "CPF", "SIGLA_FUNCAO", "NIVEL_FUNCAO", "FUNCAO",
           "ATIVIDADE", "ORG_EXERCICIO", "ORGSUP_EXERCICIO", "SITUACAO_VINCULO",
           "DATA_INGRESSO_CARGOFUNCAO", "DATA_NOMEACAO_CARGOFUNCAO", "COD_ORG_EXERCICIO",
           "UF_EXERCICIO"]  # fmt: skip
# Formato real do Cadastro de agosto/2026 (nomes de pessoas inventados, CPFs trocados).
LINHAS = [
    ["1001", "MARIA APARECIDA DE TESTE", "***.123.456-**", "CCX", "0117",
     "CARGO COMISSIONADO EXECUTIVO", "SECRETARIO(A)", "MINISTERIO DAS MULHERES",
     "Ministério das Mulheres", "ATIVO PERMANENTE", "09/06/2025", "", "63000", "DF"],
    ["1002", "JOAO DA SILVA TESTE", "***.222.333-**", "CD", "0004",
     "CARGO DE DIRECAO - CD - IFES", "DIRETOR(A)", "Universidade Federal de Teste",
     "Ministério da Educação",
     "ATIVO PERMANENTE", "02/04/2026", "", "26001", "MG"],
    # Função gratificada de servidor de carreira: não é cargo de confiança.
    ["1003", "MARIA APARECIDA DE TESTE", "***.123.456-**", "FG", "0000",
     "FUNCAO GRATIFICADA - IFES", "CHEFE", "Universidade Federal de Teste",
     "Ministério da Educação",
     "ATIVO PERMANENTE", "01/01/2020", "", "26001", "MG"],
    # Mesmo nome, outros dígitos do meio: outra pessoa.
    ["1004", "MARIA APARECIDA DE TESTE", "***.999.888-**", "CCX", "0113",
     "CARGO COMISSIONADO EXECUTIVO", "ASSESSOR(A)", "MINISTERIO DA PESCA E AQUICULTURA",
     "Ministério da Pesca", "ATIVO PERMANENTE", "26/03/2026", "", "1", "DF"],
    # Sem CPF no cadastro (militar/exterior): não liga.
    ["1005", "JOAO DA SILVA TESTE", "", "CCX", "0101", "CARGO COMISSIONADO EXECUTIVO",
     "ASSESSOR(A)", "MINISTERIO X", "Ministério X", "ATIVO PERMANENTE", "", "", "2", "DF"],
]  # fmt: skip


def _zip(linhas=LINHAS) -> bytes:
    texto = io.StringIO()
    escritor = csv.writer(texto, delimiter=";")
    escritor.writerow(COLUNAS)
    escritor.writerows(linhas)
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("202608_Cadastro.csv", texto.getvalue().encode("latin-1"))
        z.writestr("202608_Remuneracao.csv", b"ANO;MES\n")
    return saida.getvalue()


def _pessoas(session):
    maria = Pessoa(nome="Maria Aparecida de Teste", chave_nome="MARIA APARECIDA DE TESTE",
                   cpf="00012345600")  # fmt: skip
    joao = Pessoa(nome="João da Silva Teste", chave_nome="JOAO DA SILVA TESTE", cpf="00022233300")
    sem_cpf = Pessoa(nome="Sem Cpf", chave_nome="SEM CPF")
    session.add_all([maria, joao, sem_cpf])
    session.flush()
    return maria, joao


def _indice(session):
    pessoas = session.execute(select(Pessoa.id, Pessoa.cpf, Pessoa.chave_nome)).all()
    return servidores.indice_pessoas(pessoas)


def test_normalizar_so_confianca_de_pessoa_da_base(session):
    maria, joao = _pessoas(session)
    linhas = servidores.ler_cadastro(_zip())
    registros = servidores.normalizar(linhas, _indice(session))
    assert [(r["pessoa_id"], r["sigla"], r["nivel"]) for r in registros] == [
        (maria.id, "CCX", "117"),
        (joao.id, "CD", "4"),
    ]
    maria_r = registros[0]
    assert maria_r["id_externo"] == "1001:CCX117:63000:2025-06-09"
    assert maria_r["funcao"] == "Cargo comissionado executivo"
    assert maria_r["atividade"] == "Secretario(a)"
    assert maria_r["data_ingresso"] == date(2025, 6, 9)
    assert maria_r["orgao"] == "Ministério das Mulheres"  # maiúsculas abreviadas: usa o superior
    assert registros[1]["funcao"] == "Cargo de Direção - CD - IFES"
    assert registros[1]["orgao"] == "Universidade Federal de Teste"


def test_homonimo_com_mesmo_meio_e_nome_nao_liga(session):
    maria, _ = _pessoas(session)
    outra = Pessoa(nome="Maria Aparecida de Teste", chave_nome="MARIA APARECIDA DE TESTE",
                   cpf="99912345699")  # fmt: skip
    session.add(outra)
    session.flush()
    registros = servidores.normalizar(servidores.ler_cadastro(_zip()), _indice(session))
    assert [r["sigla"] for r in registros] == ["CD"]  # a Maria ficou ambígua: ninguém é ligado


def test_gravar_acumula_historico_e_publica_eventos(session):
    maria, joao = _pessoas(session)
    registros = servidores.normalizar(servidores.ler_cadastro(_zip()), _indice(session))
    agosto, setembro = date(2026, 8, 1), date(2026, 9, 1)
    servidores.gravar(session, registros, agosto)
    assert servidores.publicar_eventos(session, None) == 2
    # Setembro: só a Maria continua; o João deixou de constar.
    servidores.gravar(session, [r for r in registros if r["sigla"] == "CCX"], setembro)
    assert servidores.publicar_eventos(session, None) == 2
    cargos = {c.sigla: c for c in session.scalars(select(ServidorFederal))}
    assert (cargos["CCX"].primeiro_mes, cargos["CCX"].ultimo_mes) == (agosto, setembro)
    assert (cargos["CD"].primeiro_mes, cargos["CD"].ultimo_mes) == (agosto, agosto)
    eventos = {e.id_externo: e for e in session.scalars(select(Evento).where(
        Evento.fonte == servidores.FONTE))}  # fmt: skip
    ev = eventos["1001:CCX117:63000:2025-06-09"]
    assert ev.tipo == "cargo_federal" and ev.data == date(2025, 6, 9)
    assert ev.descricao == (
        "Nomeado(a) para Cargo comissionado executivo (CCX 117), Secretario(a) em Ministério "
        "das Mulheres (Portal da Transparência, cadastro de agosto/2026)."
    )
    assert ev.situacao == "consta no cadastro de setembro/2026"
    assert ev.fonte_url == "https://portaldatransparencia.gov.br/servidores/1001"
    saiu = eventos["1002:CD4:26001:2026-04-02"]
    assert saiu.situacao == "último cadastro em que consta: agosto/2026"
    vinculos = session.scalars(select(PessoaVinculo).where(PessoaVinculo.fonte == servidores.FONTE))
    assert {v.regra for v in vinculos} == {"cpf_parcial_nome"}


def test_releitura_do_mes_apaga_o_que_sumiu(session):
    _pessoas(session)
    registros = servidores.normalizar(servidores.ler_cadastro(_zip()), _indice(session))
    mes = date(2026, 8, 1)
    servidores.gravar(session, registros, mes)
    servidores.gravar(session, registros[:1], mes)
    assert len(list(session.scalars(select(ServidorFederal)))) == 1


@respx.mock
def test_ultimo_mes_publicado_pela_pagina_do_portal():
    pagina = """
        arquivos.push({"ano" : "2026", "mes" : "07", "dia" : "", "origem" :  "Servidores_SIAPE"});
        arquivos.push({"ano" : "2026", "mes" : "08", "dia" : "", "origem" :  "Militares"});
        arquivos.push({"ano" : "2026", "mes" : "08", "dia" : "", "origem" :  "Servidores_SIAPE"});
    """
    respx.get(servidores.PAGINA).mock(return_value=httpx.Response(200, text=pagina))
    with comum.criar_cliente() as client:
        assert servidores.descobrir_mes(client) == (2026, 8)


def test_titulo_e_nomes():
    assert servidores.titulo("FUNCAO COMISSIONADA EXECUTIVA") == "Função comissionada executiva"
    assert servidores.titulo("") is None
