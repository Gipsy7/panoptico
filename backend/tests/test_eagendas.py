import csv
import io
import zipfile
from datetime import date, time

from sqlalchemy import select

from app.models import AgendaCompromisso, Pessoa, PessoaVinculo
from ingestion.executivo import eagendas

COLUNAS = ["Nome", "Cargo/Função", "Tipo de exercício", "Órgão/Entidade", "Tipo de registro",
           "ID do registro", "Data de início", "Data de término", "Hora de início",
           "Hora de término", "Origem", "Destino", "Forma de realização", "Data da publicação",
           "Última modificação", "Assunto do Compromisso", "Local", "Participantes",
           "Vinculações", "Objetivos", "Informações complementares", "Detalhes"]  # fmt: skip


def _linha(**campos):
    base = dict.fromkeys(COLUNAS, "ND")
    base.update(campos)
    return [base[c] for c in COLUNAS]


# Formato real do arquivo mensal da CGU (nomes e CPFs de pessoas inventados).
MINISTRA = "MARIA APARECIDA DE TESTE"
PUBLICOS = (
    f"Agentes públicos participantes: {MINISTRA} (CPF: ***.123.456-**) / MINISTRA DE ESTADO / "
    "Ministério de Teste | Joao Sem Cpf / Coordenador / Ministério de Teste || "
    "Agentes privados participantes: Fulano de Tal representando FENATRAD | "
    "Beltrano representando - Presidente - Instituto Exemplo | Solicitante"
)
LINHAS = [
    _linha(
        Nome=MINISTRA,
        **{
            "Cargo/Função": "MINISTRA DE ESTADO",
            "Órgão/Entidade": "Ministério de Teste",
            "Tipo de registro": "Reunião",
            "ID do registro": "100",
            "Data de início": "01-09-2026",
            "Hora de início": "08:00",
            "Hora de término": "09:30",
            "Forma de realização": "Presencial",
            "Data da publicação": "31-08-2026 18:06",
            "Assunto do Compromisso": "Pauta do dia",
            "Local": "Brasília",
            "Participantes": PUBLICOS,
        },
    ),
    # Mesmo registro declarado por outro agente (não está na base): não entra.
    _linha(
        Nome="JOAO SEM CPF",
        **{
            "Tipo de registro": "Reunião",
            "ID do registro": "100",
            "Data de início": "01-09-2026",
            "Participantes": PUBLICOS,
        },
    ),
    # Viagem: sem participantes (a ligação vem do nome visto em outro registro); CPF do
    # ofertante pessoa física some.
    _linha(
        Nome=MINISTRA,
        **{
            "Tipo de registro": "Viagem",
            "ID do registro": "9",
            "Data de início": "03-10-2026",
            "Data de término": "06-10-2026",
            "Origem": "Brasília - DF - BRA",
            "Destino": "Paris - FRA",
            "Detalhes": "Hospitalidade(s) recebida(s) na viagem: Tipo: Diária Item: Diárias "
            "Valor: 387.00 Ofertante: Olivo Dambros (CPF: ***.305.729-**) Tipo: Passagem "
            "Item: REC&gt;POA Ofertante: PUC-RS (CNPJ: 88.630.413/0002-81)",
        },
    ),
    _linha(
        Nome=MINISTRA,
        **{
            "Tipo de registro": "Presentes e hospitalidades",
            "ID do registro": "3",
            "Data de início": "10-10-2026",
            "Vinculações": "Ocasião: Reunião - Delegação / 10-10-2026;",
            "Detalhes": "Item(ns) recebido(s): Tipo: Presente Item: Estátua Ofertante: Delegação",
        },
    ),
    # Afastamento não entra.
    _linha(
        Nome=MINISTRA,
        **{
            "Tipo de registro": "Afastamento",
            "ID do registro": "11",
            "Data de início": "03-10-2026",
        },
    ),
]


def _zip(linhas=LINHAS) -> bytes:
    texto = io.StringIO()
    escritor = csv.writer(texto, quoting=csv.QUOTE_ALL)
    escritor.writerow(COLUNAS)
    escritor.writerows(linhas)
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("2026-09.csv", texto.getvalue().encode("utf-8"))
    return saida.getvalue()


def _pessoas(session):
    ministra = Pessoa(nome="Maria Aparecida de Teste", chave_nome=MINISTRA, cpf="00012345600")
    session.add(ministra)
    session.flush()
    return ministra


def _indice(session):
    return eagendas.indice_pessoas(
        session.execute(select(Pessoa.id, Pessoa.cpf, Pessoa.chave_nome)).all()
    )


def test_agentes_e_entidades_privadas_sem_nome_de_pessoa():
    agentes = eagendas.agentes_com_cpf(PUBLICOS)
    assert agentes == [
        {"nome": MINISTRA, "meio": "123456", "cargo": "MINISTRA DE ESTADO",
         "orgao": "Ministério de Teste"}
    ]  # fmt: skip
    entidades, n = eagendas.entidades_privadas(PUBLICOS)
    assert entidades == ["FENATRAD", "Instituto Exemplo"]  # nunca "Fulano de Tal"
    assert n == 3  # a pessoa sem "representando" só entra na contagem


def test_limpar_detalhes_tira_cpf_do_ofertante():
    texto = eagendas.limpar_detalhes(LINHAS[2][-1])
    assert "Ofertante: pessoa física" in texto and "***" not in texto and "Dambros" not in texto
    assert "REC>POA" in texto and "PUC-RS (CNPJ: 88.630.413/0002-81)" in texto
    assert eagendas.limpar_detalhes("ND") is None


def test_liga_por_cpf_parcial_e_nome_e_normaliza(session):
    ministra = _pessoas(session)
    ligados = eagendas.mapa_ligacao(eagendas.ler_linhas(_zip()), _indice(session))
    assert ligados == {MINISTRA: ministra.id}  # "Joao Sem Cpf" não tem CPF: não liga
    registros = eagendas.normalizar(eagendas.ler_linhas(_zip()), ligados)
    assert [(r["tipo"], r["id_registro"]) for r in registros] == [
        ("reuniao", 100), ("viagem", 9), ("presente", 3),
    ]  # fmt: skip
    reuniao = registros[0]
    assert reuniao["data_inicio"] == date(2026, 9, 1) and reuniao["hora_inicio"] == time(8, 0)
    assert reuniao["publicado_em"] == date(2026, 8, 31)
    assert reuniao["participantes_publicos"] == [
        {"nome": MINISTRA, "cargo": "MINISTRA DE ESTADO", "orgao": "Ministério de Teste"}
    ]
    assert reuniao["n_participantes_publicos"] == 2
    assert reuniao["entidades_privadas"] == ["FENATRAD", "Instituto Exemplo"]
    viagem = registros[1]
    assert (viagem["origem"], viagem["destino"]) == ("Brasília - DF - BRA", "Paris - FRA")
    assert "pessoa física" in viagem["detalhes"] and viagem["assunto"] is None
    assert registros[2]["assunto"].startswith("Ocasião: Reunião")


def test_homonimo_com_mesmo_meio_nao_liga(session):
    _pessoas(session)
    session.add(Pessoa(nome="Maria Aparecida de Teste", chave_nome=MINISTRA, cpf="99912345699"))
    session.flush()
    assert eagendas.mapa_ligacao(eagendas.ler_linhas(_zip()), _indice(session)) == {}


def test_gravar_recarrega_tudo_e_cria_vinculo(session):
    ministra = _pessoas(session)
    ligados = eagendas.mapa_ligacao(eagendas.ler_linhas(_zip()), _indice(session))
    registros = eagendas.normalizar(eagendas.ler_linhas(_zip()), ligados)
    eagendas.gravar(session, registros, None)
    eagendas.gravar(session, registros[:1], None)  # recarga: o que sumiu do arquivo some
    assert len(list(session.scalars(select(AgendaCompromisso)))) == 1
    vinculos = list(session.scalars(select(PessoaVinculo).where(PessoaVinculo.fonte == "eagendas")))
    assert [(v.pessoa_id, v.regra) for v in vinculos] == [(ministra.id, "cpf_parcial_nome")]
