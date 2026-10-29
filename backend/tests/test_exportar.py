"""Exportação aberta: provas de que CPF, título, nascimento, pessoa sem vínculo publicável,
sugestões não revisadas e casos sem evento publicável nunca saem nos arquivos."""

import gzip
import json
import re
from datetime import UTC, date, datetime
from decimal import Decimal

import pyarrow.parquet as pq
import pytest

from app.models import (
    AgendaCompromisso,
    Candidatura,
    Caso,
    CasoDocumento,
    Cpi,
    CpiIndiciamentoSugestao,
    Despesa,
    DespesaFornecedor,
    DiarioAto,
    DouAto,
    Emenda,
    EmendaEstadual,
    EmendaPagamento,
    EmendaPagamentoSemCodigo,
    EmendaTransferencia,
    Empresa,
    Evento,
    FonteIngestao,
    GastoLocalFora,
    MandatoLocal,
    Municipio,
    Parlamentar,
    Pessoa,
    PessoaVinculo,
    PncpAnual,
    ServidorFederal,
)
from app.models.pessoa import REGRAS_FORTES
from exportar.conjuntos import CONJUNTOS, PUBLICAVEL
from exportar.documentacao import escrever_documentacao
from exportar.escrita import exportar_conjunto
from exportar.filtros import limpar

CPF_FORMATADO = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
CPFS = ["12345678901", "98765432100", "11122233344", "55566677788"]
TITULOS = ["123456789012", "210987654321"]
NASCIMENTO = "1971-03-04"


def _candidatura(sq: str, nome: str, turno: str, cpf: str, titulo: str) -> Candidatura:
    return Candidatura(
        ano_eleicao=2022, sq_candidato=sq, cargo="DEPUTADO FEDERAL", uf="SP", unidade="SP",
        nome=nome, nome_urna=nome, partido="XYZ", situacao_turno=turno, cpf=cpf,
        titulo=titulo, data_nascimento=date(1971, 3, 4), cor_raca="PARDA", estado_civil="CASADO",
        data_eleicao=date(2022, 10, 2),
    )  # fmt: skip


def _novos(s, parl, forte, fraca) -> None:
    """Linhas dos conjuntos de emendas, empresas, agenda e servidores."""
    mand = MandatoLocal(
        casa="camara",
        uf="SP",
        municipio_ibge="3550308",
        id_externo="9",
        nome="Vereador Teste",
        sapl_url="https://sapl.exemplo",
    )
    s.add(mand)
    s.flush()
    hoje = date(2026, 1, 5)
    agora = datetime.now(UTC)
    s.add_all([
        GastoLocalFora(mandato_id=mand.id, ano=2025, linhas=3, valor=Decimal("10"),
                       motivo="Sem data"),
        Emenda(codigo="20250001", ano=2025, tipo="Individual", individual=True,
               autor_codigo="1", autor_nome="Fulana Eleita", parlamentar_id=parl.id,
               localidade="SAO PAULO", municipio_ibge="3550308", uf="SP",
               valor_empenhado=Decimal("5"), valor_pago=Decimal("4")),
        EmendaPagamento(emenda_codigo="20250001", ano_emenda=2025, ano_mes=202501,
                        autor_codigo="1", autor_nome="Fulana Eleita", parlamentar_id=parl.id,
                        pessoa_id=forte.id, tipo="individual", favorecido="PREFEITURA SA",
                        favorecido_codigo="12.345.678/0001-90", natureza="Municipal",
                        grupo="prefeitura", municipio_ibge="3550308", valor=Decimal("3")),
        EmendaPagamento(emenda_codigo="20250002", ano_emenda=2025, ano_mes=202501,
                        autor_codigo="2", autor_nome="Autor X", pessoa_id=fraca.id,
                        favorecido="PF FAVORECIDO EMENDA", favorecido_codigo="***.456.789-**",
                        natureza="Pessoa", grupo="entidade", municipio_ibge="3550308",
                        valor=Decimal("1")),
        EmendaPagamentoSemCodigo(ano_mes=202501, autor_codigo="-", autor_nome="Sem informação",
                                 favorecido="PF SEM CODIGO NOME", favorecido_codigo="12345678901",
                                 natureza="Pessoa", grupo="entidade",
                                 municipio_ibge="3550308", valor=Decimal("1")),
        EmendaTransferencia(tipo="convenio", emenda_codigo="20250001", ano_emenda=2025,
                            identificador="900", beneficiario="PF BENEFICIARIO NOME",
                            beneficiario_cnpj="12345678901", uf="SP",
                            objeto="Obra, CPF 123.456.789-01", valor_total=Decimal("2")),
        EmendaTransferencia(tipo="especial", emenda_codigo="20250001", ano_emenda=2025,
                            identificador="901", beneficiario="ASSOCIACAO LTDA",
                            beneficiario_cnpj="12345678000190", uf="SP"),
        EmendaEstadual(uf="SC", ano=2025, codigo="2025EP1", proposta="p1", tipo="individual",
                       autor_nome="Deputado Estadual", autor_chave="DEPUTADO ESTADUAL",
                       pessoa_id=fraca.id, municipio_nome="X", favorecido_nome="PF ESTADUAL NOME",
                       favorecido_cnpj="98765432100", valor_previsto=Decimal("1"),
                       valor_pago=Decimal("1"), fonte="sctransferencias_emendas"),
        EmendaEstadual(uf="SC", ano=2025, codigo="2025EP2", proposta="p2", tipo="bancada",
                       autor_nome="Bancada", autor_chave="BANCADA", pessoa_id=forte.id,
                       municipio_nome="X", favorecido_nome="ASSOCIACAO ESTADUAL LTDA",
                       favorecido_cnpj="12345678000190", valor_previsto=Decimal("1"),
                       valor_pago=Decimal("1"), fonte="sctransferencias_emendas"),
        Empresa(cnpj="12345678000190", razao_social="EMPRESA REAL LTDA", nome_omitido=False,
                referencia="2026-10", atualizado_em=agora),
        Empresa(cnpj="11111111000111", razao_social="MEI SEM NOME 12345678901",
                nome_omitido=False, referencia="2026-10", atualizado_em=agora),
        Empresa(cnpj="22222222000122", razao_social=None, nome_omitido=True,
                referencia="2026-10", atualizado_em=agora),
        AgendaCompromisso(pessoa_id=forte.id, tipo="reuniao", id_registro=1,
                          data_inicio=hoje, assunto="Reunião sobre obra",
                          participantes_publicos=[{"nome": "Servidor Publico", "cargo": "X"}],
                          entidades_privadas=["Associação Comercial"]),
        AgendaCompromisso(pessoa_id=forte.id, tipo="presente", id_registro=2,
                          data_inicio=hoje, detalhes="DETALHE-PRESENTE-OFERTANTE"),
        AgendaCompromisso(pessoa_id=fraca.id, tipo="reuniao", id_registro=3,
                          data_inicio=hoje, assunto="AGENDA DA PESSOA FRACA"),
        ServidorFederal(pessoa_id=forte.id, id_externo="12345678901:FULANA", sigla="CCX",
                        funcao="Assessora", primeiro_mes=hoje, ultimo_mes=hoje),
        ServidorFederal(pessoa_id=fraca.id, id_externo="x:FRACA", sigla="CCX",
                        funcao="CARGO-PESSOA-FRACA", primeiro_mes=hoje, ultimo_mes=hoje),
    ])  # fmt: skip


@pytest.fixture
def banco(session):
    s = session
    s.add(Municipio(ibge="3550308", nome="São Paulo", uf="SP", nome_chave="SAO PAULO"))
    parl = Parlamentar(
        casa="camara", id_externo="1", nome_parlamentar="Fulana Eleita", uf="SP",
        cpf=CPFS[0], email="x@camara.leg.br", telefone="(61) 3215-0000", em_exercicio=True,
        fonte_url="https://exemplo", atualizado_em=datetime.now(UTC),
    )  # fmt: skip
    s.add(parl)
    eleita = _candidatura("1", "Fulana Eleita", "ELEITO POR QP", CPFS[0], TITULOS[0])
    perdeu = _candidatura("2", "Beltrano Nao Eleito", "NAO ELEITO", CPFS[1], TITULOS[1])
    s.add_all([eleita, perdeu])
    forte = Pessoa(nome="Fulana Eleita", chave_nome="FULANA", cpf=CPFS[0], titulo=TITULOS[0],
                   data_nascimento=date(1971, 3, 4))  # fmt: skip
    fraca = Pessoa(nome="Pessoa Vinculo Fraco", chave_nome="FRACO", cpf=CPFS[2])
    revisada = Pessoa(nome="Pessoa Revisada", chave_nome="REVISADA", cpf=CPFS[3])
    s.add_all([forte, fraca, revisada])
    s.flush()
    v_forte = PessoaVinculo(
        pessoa_id=forte.id, fonte="candidatura", id_externo="2022:1", regra="cpf"
    )
    v_fraco = PessoaVinculo(
        pessoa_id=fraca.id, fonte="parlamentar", id_externo="camara:1", regra="nome_casa"
    )
    v_rev = PessoaVinculo(pessoa_id=revisada.id, fonte="parlamentar", id_externo="camara:2",
                          regra="nome_casa", revisado=True)  # fmt: skip
    s.add_all([v_forte, v_fraco, v_rev])
    s.add_all([
        Caso(slug="caso-publico", nome="Caso Publico", resumo="Resumo",
             conferido_em=date(2026, 1, 1)),
        Caso(slug="caso-sem-evento", nome="CASO SEM EVENTO PUBLICAVEL", resumo="x",
             conferido_em=date(2026, 1, 1)),
    ])  # fmt: skip
    s.flush()
    s.add_all([
        CasoDocumento(caso_slug="caso-publico", codigo="d1", tipo="acordao", orgao="STF",
                      data=date(2020, 1, 1), url="https://oficial/d1", resumo="Documento"),
        CasoDocumento(caso_slug="caso-sem-evento", codigo="d2", tipo="acordao", orgao="STF",
                      data=date(2020, 1, 1), url="https://oficial/d2", resumo="DOC DO CASO OCULTO"),
        Evento(pessoa_id=forte.id, vinculo_id=v_forte.id, data=date(2023, 5, 5), tipo="sancao",
               descricao="Evento publico CPF 123.456.789-01 citado", fonte="cgu_sancoes",
               id_externo="e1", caso_slug="caso-publico"),
        Evento(pessoa_id=fraca.id, vinculo_id=v_fraco.id, data=date(2023, 5, 5), tipo="sancao",
               descricao="EVENTO DE VINCULO FRACO", fonte="cgu_sancoes", id_externo="e2"),
        Evento(pessoa_id=revisada.id, vinculo_id=v_rev.id, data=date(2023, 5, 5), tipo="sancao",
               descricao="Evento de vinculo revisado", fonte="cgu_sancoes", id_externo="e3"),
    ])  # fmt: skip
    # Sugestões não revisadas: nada disso pode sair.
    s.add_all([
        DiarioAto(pessoa_id=forte.id, municipio_ibge="3550308", data=date(2024, 1, 1),
                  tipo_ato="nomeacao", trecho="SUGESTAO-DIARIO-NAO-REVISADA", url="https://qd/1"),
        DouAto(pessoa_id=forte.id, id_materia="9", data=date(2024, 1, 1), tipo_ato="nomeacao",
               orgao="Min", trecho="SUGESTAO-DOU-NAO-REVISADA", url="https://dou/1"),
    ])  # fmt: skip
    cpi = Cpi(casa="senado", id_externo="1", tipo="CPI", nome="CPI de Teste")
    s.add(cpi)
    s.flush()
    s.add(
        CpiIndiciamentoSugestao(
            cpi_id=cpi.id,
            nome_citado="NOME-INDICIADO-SUGERIDO",
            trecho="SUGESTAO-CPI-NAO-REVISADA",
            url="https://cpi/1",
        )
    )
    s.add_all([
        Despesa(parlamentar_id=parl.id, casa="camara", ano=2025, mes=1, categoria="Passagens",
                fornecedor="EMPRESA SA", cnpj_cpf="12.345.678/0001-90", valor=Decimal("10.50")),
        Despesa(parlamentar_id=parl.id, casa="camara", ano=2025, mes=1, categoria="Taxi",
                fornecedor="JOAO PESSOA FISICA", cnpj_cpf="123.456.789-01", valor=Decimal("5")),
        Despesa(parlamentar_id=parl.id, casa="senado", ano=2025, mes=2, categoria="Taxi",
                fornecedor="MARIA CPF MASCARADO", cnpj_cpf="***.456.789-**", valor=Decimal("7")),
        DespesaFornecedor(municipio_ibge="3550308", ano=2025, orgao="prefeitura",
                          fornecedor="PF DOCUMENTO CPF", documento="98765432100",
                          valor_pago=Decimal("1"), pagamentos=1, fonte="tce_sp"),
        DespesaFornecedor(municipio_ibge="3550308", ano=2025, orgao="prefeitura",
                          fornecedor="FORNECEDOR LTDA", documento="12345678000190",
                          valor_pago=Decimal("2"), pagamentos=1, fonte="tce_sp"),
        PncpAnual(ano=2026, municipio_ibge="3550308", fornecedor_cnpj="12345678000190",
                  fornecedor_nome="MEI FULANO 12345678901", quantidade=1,
                  valor_global=Decimal("9")),
        PncpAnual(ano=2026, municipio_ibge="3550308", fornecedor_cnpj="98765432100",
                  fornecedor_nome="PESSOA FISICA COM CPF NO CNPJ", quantidade=1,
                  valor_global=Decimal("9")),
    ])  # fmt: skip
    _novos(s, parl, forte, fraca)
    s.flush()
    return s


def _gerar(banco, destino):
    resultados = {}
    conn = banco.connection()
    for c in CONJUNTOS:
        resultados[c.nome] = exportar_conjunto(conn, c, destino)
    escrever_documentacao(conn, CONJUNTOS, resultados, destino)
    return resultados


def _texto_csv(destino) -> dict[str, str]:
    return {
        c.nome: gzip.open(destino / f"{c.nome}.csv.gz", "rt", encoding="utf-8").read()
        for c in CONJUNTOS
    }


def _texto_parquet(destino) -> dict[str, str]:
    return {
        c.nome: json.dumps(
            pq.read_table(destino / f"{c.nome}.parquet").to_pylist(),
            default=str,
            ensure_ascii=False,
        )
        for c in CONJUNTOS
    }


def test_nada_proibido_nos_arquivos(banco, tmp_path):
    _gerar(banco, tmp_path)
    textos = {f"{k}.csv": v for k, v in _texto_csv(tmp_path).items()}
    textos |= {f"{k}.parquet": v for k, v in _texto_parquet(tmp_path).items()}
    textos["dicionario.json"] = (tmp_path / "dicionario.json").read_text(encoding="utf-8")
    textos["LEIAME.md"] = (tmp_path / "LEIAME.md").read_text(encoding="utf-8")
    proibidos = [
        *CPFS, *TITULOS, NASCIMENTO,
        "Pessoa Vinculo Fraco", "EVENTO DE VINCULO FRACO",
        "SUGESTAO-DIARIO-NAO-REVISADA", "SUGESTAO-DOU-NAO-REVISADA", "SUGESTAO-CPI-NAO-REVISADA",
        "NOME-INDICIADO-SUGERIDO", "Beltrano Nao Eleito", "CASO SEM EVENTO PUBLICAVEL",
        "DOC DO CASO OCULTO", "JOAO PESSOA FISICA", "MARIA CPF MASCARADO", "PF DOCUMENTO CPF",
        "PESSOA FISICA COM CPF NO CNPJ", "x@camara.leg.br", "3215-0000",
        "PARDA", "CASADO",
        "PF FAVORECIDO EMENDA", "PF SEM CODIGO NOME", "PF BENEFICIARIO NOME",
        "PF ESTADUAL NOME", "DETALHE-PRESENTE-OFERTANTE", "AGENDA DA PESSOA FRACA",
        "CARGO-PESSOA-FRACA", "12345678901:FULANA",
    ]  # fmt: skip
    for arquivo, texto in textos.items():
        assert not CPF_FORMATADO.search(texto), f"CPF formatado em {arquivo}"
        for p in proibidos:
            assert p not in texto, f"{p!r} apareceu em {arquivo}"


def test_o_que_deve_sair_sai(banco, tmp_path):
    r = _gerar(banco, tmp_path)
    csv = _texto_csv(tmp_path)
    assert "Fulana Eleita" in csv["pessoas_publicas"]
    assert "Pessoa Revisada" in csv["pessoas_publicas"]  # vínculo fraco, mas revisado
    assert "Evento publico CPF [CPF omitido] citado" in csv["eventos"]
    assert "Evento de vinculo revisado" in csv["eventos"]
    assert "caso-publico" in csv["casos"] and "d1" in csv["casos_documentos"]
    assert "FORNECEDOR LTDA" in csv["despesas_fornecedor_tce"]
    assert "MEI FULANO [CPF omitido]" in csv["pncp_anual"]
    assert "EMPRESA SA" in csv["despesas_cota"] and "12345678000190" in csv["despesas_cota"]
    assert r["candidaturas_eleitas"]["linhas"] == 1
    assert r["pessoas_publicas"]["linhas"] == 2
    assert r["eventos"]["linhas"] == 2
    assert r["pncp_anual"]["linhas"] == 1
    assert r["despesas_cota"]["linhas"] == 3


def test_csv_e_parquet_equivalentes(banco, tmp_path):
    _gerar(banco, tmp_path)
    for c in CONJUNTOS:
        tabela = pq.read_table(tmp_path / f"{c.nome}.parquet")
        csv = gzip.open(tmp_path / f"{c.nome}.csv.gz", "rt", encoding="utf-8").read()
        assert csv.splitlines()[0] == ",".join(k.nome for k in c.colunas)
        assert tabela.schema.names == [k.nome for k in c.colunas]
        assert len(csv.splitlines()) - 1 >= tabela.num_rows  # quebras de linha em textos


def test_nenhuma_coluna_sensivel():
    proibidas = {"cpf", "titulo", "data_nascimento", "cor_raca", "estado_civil", "email",
                 "telefone"}  # fmt: skip
    for c in CONJUNTOS:
        # cor_raca em partidos_fefc_fp é o grupo de uma soma, não dado de pessoa.
        permitidas = {"cor_raca"} if c.nome == "partidos_fefc_fp" else set()
        assert not (proibidas - permitidas) & {k.nome for k in c.colunas}, c.nome
        for tabela in ("diario_ato", "dou_ato", "cpi_indiciamento_sugestao"):
            assert tabela not in c.sql, c.nome


def test_regra_publicavel_igual_a_do_site():
    for regra in REGRAS_FORTES:
        assert f"'{regra}'" in PUBLICAVEL
    assert "revisado IS TRUE" in PUBLICAVEL


def test_dicionario_e_leiame(banco, tmp_path):
    banco.add(
        FonteIngestao(
            fonte="camara_deputados", url="u", arquivo_raw="a", status="ok",
            concluido_em=datetime(2026, 10, 9, 12, tzinfo=UTC),
        )
    )  # fmt: skip
    banco.flush()
    _gerar(banco, tmp_path)
    d = json.loads((tmp_path / "dicionario.json").read_text(encoding="utf-8"))
    por = {c["nome"]: c for c in d["conjuntos"]}
    assert set(por) == {c.nome for c in CONJUNTOS}
    parl = por["parlamentares_federais"]
    cargas = {c["fonte"]: c["ultima_carga"] for c in parl["cargas"]}
    assert cargas["camara_deputados"].startswith("2026-10-09")
    assert cargas["senado_senadores"] is None
    assert parl["fonte_oficial"]["orgao"] and parl["colunas"][0]["descricao"]
    assert len(parl["arquivos"]["parquet"]["sha256"]) == 64
    assert "O que nunca está aqui" in (tmp_path / "LEIAME.md").read_text(encoding="utf-8")
    assert d["licenca"]["url"] == "https://creativecommons.org/licenses/by/4.0/deed.pt-br"
    assert "CC BY 4.0" in d["licenca"]["nome"]
    assert "## Licença" in (tmp_path / "LEIAME.md").read_text(encoding="utf-8")


def test_limpar():
    assert limpar("CPF 123.456.789-01 e 12345678901") == "CPF [CPF omitido] e 12345678901"
    assert limpar("MEI 12345678901", livre=True) == "MEI [CPF omitido]"
    assert limpar("CPF ***.123.456-** x") == "CPF [CPF omitido] x"
    assert limpar("CNPJ 12345678000190", livre=True) == "CNPJ 12345678000190"


def test_leitura_em_lotes(banco, tmp_path, monkeypatch):
    from exportar import escrita

    monkeypatch.setattr(escrita, "LOTE", 1)
    r = _gerar(banco, tmp_path)
    assert r["despesas_cota"]["linhas"] == 3
    assert pq.read_table(tmp_path / "despesas_cota.parquet").num_rows == 3


def test_conjuntos_novos_saem_sem_dado_pessoal(banco, tmp_path):
    r = _gerar(banco, tmp_path)
    csv = _texto_csv(tmp_path)
    assert r["emendas_federais"]["linhas"] == 1 and "Fulana Eleita" in csv["emendas_federais"]
    assert r["emendas_pagamentos"]["linhas"] == 2
    assert "PREFEITURA SA" in csv["emendas_pagamentos"]
    assert "12345678000190" in csv["emendas_transferencias"]
    assert r["emendas_pagamentos_sem_codigo"]["linhas"] == 1
    assert r["emendas_transferencias"]["linhas"] == 2
    assert "ASSOCIACAO LTDA" in csv["emendas_transferencias"]
    assert "Obra, CPF [CPF omitido]" in csv["emendas_transferencias"]
    assert r["emendas_estaduais"]["linhas"] == 2
    assert "ASSOCIACAO ESTADUAL LTDA" in csv["emendas_estaduais"]
    assert "EMPRESA REAL LTDA" in csv["empresas"]
    assert r["empresas"]["linhas"] == 3
    assert "MEI SEM NOME [CPF omitido]" in csv["empresas"]  # defesa: CPF no nome some
    assert "22222222000122,,true" in csv["empresas"]  # nome omitido na origem
    assert r["gastos_locais_fora"]["linhas"] == 1
    assert "Reunião sobre obra" in csv["agenda_compromissos"]
    assert "Associação Comercial" in csv["agenda_compromissos"]


def test_pessoa_nao_publicavel_fica_de_fora_dos_conjuntos_novos(banco, tmp_path):
    r = _gerar(banco, tmp_path)
    # Agenda e servidor: só a pessoa de vínculo forte (a de vínculo fraco não sai).
    assert r["agenda_compromissos"]["linhas"] == 2
    assert r["servidores_federais"]["linhas"] == 1
    publicas = {p["id"] for p in pq.read_table(tmp_path / "pessoas_publicas.parquet").to_pylist()}
    for nome in ("emendas_pagamentos", "emendas_estaduais"):
        for linha in pq.read_table(tmp_path / f"{nome}.parquet").to_pylist():
            assert linha["pessoa_id"] is None or linha["pessoa_id"] in publicas, nome
    # Favorecido pessoa física: a linha existe, mas sem nome nem número.
    linhas = pq.read_table(tmp_path / "emendas_pagamentos.parquet").to_pylist()
    pf = next(x for x in linhas if x["emenda_codigo"] == "20250002")
    assert pf["favorecido"] is None and pf["favorecido_cnpj"] is None and pf["pessoa_id"] is None
    # Detalhe de viagem e presente (ofertante) nunca sai.
    ag = pq.read_table(tmp_path / "agenda_compromissos.parquet").to_pylist()
    assert all(x["detalhes"] is None for x in ag if x["tipo"] == "presente")


def test_nomes_dos_conjuntos_sao_unicos():
    nomes = [c.nome for c in CONJUNTOS]
    assert len(nomes) == len(set(nomes))
    assert {"emendas_estaduais", "empresas", "gastos_locais_fora", "agenda_compromissos"} <= set(
        nomes
    )
