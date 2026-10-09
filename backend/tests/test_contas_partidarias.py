# ruff: noqa: E501  (linhas reais do TSE são longas)
import csv
import io
import zipfile
from datetime import date
from decimal import Decimal

import httpx
import pytest
import respx
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.models import (
    PartidoContaSoma,
    PartidoCotaMensal,
    PartidoDespesaVinculada,
    PartidoFefcFp,
    Pessoa,
)
from ingestion.tse import contas_partidarias as contas
from ingestion.tse import fefc_fp

# Cabeçalhos reais do exercício de 2024 (o de receitas grafa "ESPERA", sic).
COLUNAS_RECEITA = [
    "DT_GERACAO", "HH_GERACAO", "CD_TP_ESFERA_PARTIDARIA", "DS_TP_ESPERA_PARTIDARIA", "SG_UF",
    "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_CNPJ_PRESTADOR_CONTA", "SG_PARTIDO",
    "NM_PARTIDO", "CD_TP_ORIGEM_DOACAO", "DS_TP_ORIGEM_DOACAO", "NR_CPF_CNPJ_DOADOR", "NM_DOADOR",
    "SQ_CANDIDATO_DOADOR", "CD_TP_FONTE_RECURSO", "DS_TP_FONTE_RECURSO", "DT_RECEITA",
    "DS_RECEITA", "VR_RECEITA",
]  # fmt: skip
COLUNAS_DESPESA = [
    "DT_GERACAO", "HH_GERACAO", "AA_EXERCICIO", "TP_DESPESA", "CD_TP_ESFERA_PARTIDARIA",
    "DS_TP_ESFERA_PARTIDARIA", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA",
    "NR_CNPJ_PRESTADOR_CONTA", "SG_PARTIDO", "NM_PARTIDO", "DS_TP_FORNECEDOR",
    "NR_CPF_CNPJ_FORNECEDOR", "NM_FORNECEDOR", "DS_GASTO", "DT_PAGAMENTO", "VR_GASTO",
    "VR_PAGAMENTO", "DS_FONTE_DESPESA", "SQ_DESPESA",
]  # fmt: skip

CNPJ_SANCIONADA = "14286903000195"
CNPJ_SOCIA = "11222333000181"
CPF_PESSOA = "11144477735"  # CPF de teste (dígitos válidos, de ninguém)


def receita(**campos: str) -> dict[str, str]:
    base = {c: "#NULO#" for c in COLUNAS_RECEITA} | {"DT_GERACAO": "26/09/2026", "VR_RECEITA": "0"}
    return base | campos


def despesa(**campos: str) -> dict[str, str]:
    base = {c: "#NULO#" for c in COLUNAS_DESPESA} | {
        "DT_GERACAO": "26/09/2026",
        "VR_PAGAMENTO": "0",
    }
    return base | campos


# Linhas parecidas com as reais de 2024 (valores e textos como no arquivo do TSE).
RECEITAS = [
    receita(DS_TP_ESPERA_PARTIDARIA="Nacional", SG_UF="BR", SG_PARTIDO="PL",
            DS_TP_ORIGEM_DOACAO="Cotas do Fundo Partidário", DS_TP_FONTE_RECURSO="Fundo Partidário",
            DT_RECEITA="05/02/2024", VR_RECEITA="1500000,50",
            DS_RECEITA="FUNDO PARTIDÁRIO - DIREÇÃO NACIONAL - COTAS RECEBIDAS EM RECURSOS FINANCEIROS"),
    receita(DS_TP_ESPERA_PARTIDARIA="Nacional", SG_UF="BR", SG_PARTIDO="PL",
            DS_TP_ORIGEM_DOACAO="Cotas do Fundo Partidário", DS_TP_FONTE_RECURSO="FUNDO PARTIDÁRIO",
            DT_RECEITA="20/02/2024", VR_RECEITA="500000,00",
            DS_RECEITA="FUNDO PARTIDÁRIO - DIREÇÃO NACIONAL - COTAS RECEBIDAS EM RECURSOS FINANCEIROS"),
    receita(DS_TP_ESPERA_PARTIDARIA="Nacional", SG_UF="BR", SG_PARTIDO="PL",
            DS_TP_ORIGEM_DOACAO="Cotas do Fundo Especial de Financiamento de Campanha",
            DS_TP_FONTE_RECURSO="Fundo Especial de Financiamento de Campanha",
            DT_RECEITA="10/08/2024", VR_RECEITA="2000000,00",
            DS_RECEITA="FUNDO ESPECIAL DE FINANCIAMENTO DE CAMPANHA - DIREÇÃO NACIONAL - COTAS"),
    receita(DS_TP_ESPERA_PARTIDARIA="Estadual", SG_UF="AP", SG_PARTIDO="CIDADANIA",
            DS_TP_ORIGEM_DOACAO="Recursos de Partidos Políticos", DS_TP_FONTE_RECURSO="Fundo Partidário",
            DT_RECEITA="01/02/2024", VR_RECEITA="5000",
            DS_RECEITA="TRANSFERÊNCIAS DE RECURSOS FINANCEIROS PARA MANUTENÇÃO DO PARTIDO - RECEBIDAS DA DIREÇÃO NACIONAL"),
    receita(DS_TP_ESPERA_PARTIDARIA="Municipal", SG_UF="AC", SG_PARTIDO="PT",
            DS_TP_ORIGEM_DOACAO="Recursos de Pessoas Físicas", DS_TP_FONTE_RECURSO="Outros recursos",
            NR_CPF_CNPJ_DOADOR="98765432100", NM_DOADOR="FULANO DE TAL",
            DT_RECEITA="03/03/2024", VR_RECEITA="300,00",
            DS_RECEITA="CONTRIBUIÇÕES - DE FILIADOS"),
    # Prestador sem movimento: o arquivo traz uma linha zerada com tudo nulo.
    receita(DS_TP_ESPERA_PARTIDARIA="Estadual", SG_UF="AP", SG_PARTIDO="AGIR"),
]  # fmt: skip
DESPESAS = [
    despesa(DS_TP_ESFERA_PARTIDARIA="Nacional", SG_UF="BR", SG_PARTIDO="PL", SQ_DESPESA="1",
            DS_GASTO="TRANSFERÊNCIAS FINANCEIRAS EFETUADAS - FUNDO PARTIDÁRIO - DIREÇÃO ESTADUAL - ORDINÁRIAS",
            DS_FONTE_DESPESA="FUNDO PARTIDÁRIO", VR_PAGAMENTO="1000000,00",
            DT_PAGAMENTO="07/03/2024"),
    despesa(DS_TP_ESFERA_PARTIDARIA="Nacional", SG_UF="BR", SG_PARTIDO="PL", SQ_DESPESA="2",
            DS_GASTO="TRANSFERÊNCIAS FINANCEIRAS EFETUADAS - FUNDO ESPECIAL DE FINANCIAMENTO DE CAMPANHA - CANDIDATAS (MULHERES) - DESPESAS COM FINS ELEITORAIS",
            DS_FONTE_DESPESA="Fundo Especial de Financiamento de Campanha", VR_PAGAMENTO="400000,00",
            DT_PAGAMENTO="09/09/2024"),
    despesa(DS_TP_ESFERA_PARTIDARIA="Nacional", SG_UF="BR", SG_PARTIDO="PL", SQ_DESPESA="3",
            DS_GASTO="SERVIÇOS TÉCNICO-PROFISSIONAIS - SERVIÇOS DE CONSULTORIA JURÍDICA - ORDINÁRIAS",
            DS_FONTE_DESPESA="Fundo Partidário", VR_PAGAMENTO="1.000,00",
            DS_TP_FORNECEDOR="PESSOA JURÍDICA", NR_CPF_CNPJ_FORNECEDOR=CNPJ_SANCIONADA,
            NM_FORNECEDOR="SALOC SERVICOS", DT_PAGAMENTO="15/04/2024"),
    despesa(DS_TP_ESFERA_PARTIDARIA="Municipal", SG_UF="AC", SG_PARTIDO="PT", SQ_DESPESA="4",
            NM_MUNICIPIO="PLÁCIDO DE CASTRO",
            DS_GASTO="PESSOAL - SALÁRIOS E ORDENADOS - ORDINÁRIAS",
            DS_FONTE_DESPESA="OUTROS RECURSOS", VR_PAGAMENTO="1000,00",
            DS_TP_FORNECEDOR="PESSOA FÍSICA", NR_CPF_CNPJ_FORNECEDOR=CPF_PESSOA,
            NM_FORNECEDOR="BRUNO BARBOSA", DT_PAGAMENTO="31/01/2024"),
    despesa(DS_TP_ESFERA_PARTIDARIA="Municipal", SG_UF="AC", SG_PARTIDO="PT", SQ_DESPESA="5",
            DS_GASTO="PESSOAL - SALÁRIOS E ORDENADOS - ORDINÁRIAS",
            DS_FONTE_DESPESA="OUTROS RECURSOS", VR_PAGAMENTO="250,00",
            DS_TP_FORNECEDOR="PESSOA FÍSICA", NR_CPF_CNPJ_FORNECEDOR="55566677788",  # fora da base
            NM_FORNECEDOR="OUTRA PESSOA", DT_PAGAMENTO="31/01/2024"),
    despesa(DS_TP_ESFERA_PARTIDARIA="Municipal", SG_UF="AC", SG_PARTIDO="PT"),  # sem movimento
]  # fmt: skip


def _csv(colunas: list[str], linhas: list[dict[str, str]]) -> bytes:
    texto = io.StringIO()
    escritor = csv.DictWriter(texto, fieldnames=colunas, delimiter=";", quoting=csv.QUOTE_ALL)
    escritor.writeheader()
    escritor.writerows(linhas)
    return texto.getvalue().encode("latin-1")


def _zip_contas(receitas=RECEITAS, despesas=DESPESAS) -> bytes:
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("receita_anual_2024_BR.csv", _csv(COLUNAS_RECEITA, receitas[:3]))
        z.writestr("receita_anual_2024_AP.csv", _csv(COLUNAS_RECEITA, receitas[3:4] + receitas[5:]))
        z.writestr("receita_anual_2024_AC.csv", _csv(COLUNAS_RECEITA, receitas[4:5]))
        z.writestr("despesa_anual_2024_BR.csv", _csv(COLUNAS_DESPESA, despesas[:3]))
        z.writestr("despesa_anual_2024_AC.csv", _csv(COLUNAS_DESPESA, despesas[3:]))
        # O _BRASIL repete tudo: se entrasse, dobraria os totais.
        z.writestr("receita_anual_2024_BRASIL.csv", _csv(COLUNAS_RECEITA, receitas))
        z.writestr("despesa_anual_2024_BRASIL.csv", _csv(COLUNAS_DESPESA, despesas))
        z.writestr("leiame-despesas.pdf", b"%PDF")
    return saida.getvalue()


def test_rotulos_com_caixa_diferente_sao_o_mesmo():
    assert contas.fonte_recurso("FUNDO PARTIDÁRIO") == contas.fonte_recurso("Fundo Partidário")
    assert contas.fonte_recurso("Fundo Especial de Financiamento de Campanha") == "FEFC"
    assert contas.fonte_recurso("#NULO#") == "Não informado"


def test_transferencias_internas_ficam_separadas_do_gasto():
    gasto = (
        "TRANSFERÊNCIAS FINANCEIRAS EFETUADAS - FUNDO PARTIDÁRIO - DIREÇÃO ESTADUAL - ORDINÁRIAS"
    )
    assert contas.natureza_despesa(gasto) == "transferencia_diretorio"
    candidata = (
        "TRANSFERÊNCIAS FINANCEIRAS EFETUADAS - FUNDO ESPECIAL DE FINANCIAMENTO DE CAMPANHA - "
        "CANDIDATAS (MULHERES) - DESPESAS COM FINS ELEITORAIS"
    )
    assert contas.natureza_despesa(candidata) == "transferencia_candidato"
    assert contas.natureza_despesa("PESSOAL - SALÁRIOS E ORDENADOS - ORDINÁRIAS") == "gasto"
    assert contas.categoria_despesa(gasto) == "Transferências financeiras efetuadas"
    assert contas.categoria_despesa("PESSOAL - SALÁRIOS E ORDENADOS - ORDINÁRIAS") == "Pessoal"
    assert contas.natureza_receita("Cotas do Fundo Partidário") == "cota_tse"
    assert contas.natureza_receita("Recursos de Partidos Políticos") == "transferencia_partidaria"
    assert contas.natureza_receita("Recursos de Pessoas Físicas") == "outra"


def test_resumo_nao_conta_o_brasil_e_separa_naturezas():
    resumo = contas.resumir(
        contas.comum_tse.linhas(_zip_contas(), "receita_anual_"),
        contas.comum_tse.linhas(_zip_contas(), "despesa_anual_"),
        2024,
        socios={CNPJ_SOCIA},
        sancionados={CNPJ_SANCIONADA},
        cpfs={CPF_PESSOA: 7},
    )
    somas = {
        (s["tipo"], s["partido"], s["natureza"], s["fonte_recurso"]): (s["valor"], s["lancamentos"])
        for s in resumo.linhas_somas()
    }
    # As duas cotas do Fundo Partidário (rótulos com caixa diferente) viram uma soma só.
    assert somas[("receita", "PL", "cota_tse", "Fundo Partidário")] == (Decimal("2000000.50"), 2)
    assert somas[("receita", "PL", "cota_tse", "FEFC")][0] == Decimal("2000000.00")
    assert (
        somas[("receita", "CIDADANIA", "transferencia_partidaria", "Fundo Partidário")][0] == 5000
    )
    assert somas[("despesa", "PL", "transferencia_diretorio", "Fundo Partidário")][0] == 1000000
    assert somas[("despesa", "PL", "transferencia_candidato", "FEFC")][0] == 400000
    assert somas[("despesa", "PL", "gasto", "Fundo Partidário")][0] == 1000
    # Linhas sem movimento (valor zero) não viram soma.
    assert not [s for s in somas if s[1] == "AGIR"]
    assert sum(v for v, _ in somas.values()) == Decimal("2000000.50") + Decimal("2000000.00") + 5000 + 300 + 1000000 + 400000 + 1000 + 1000 + 250  # fmt: skip


def test_cotas_mensais_so_do_diretorio_nacional():
    resumo = contas.resumir(contas.comum_tse.linhas(_zip_contas(), "receita_anual_"), [], 2024)
    cotas = {(c["mes"], c["partido"], c["fundo"]): c["valor"] for c in resumo.linhas_cotas()}
    assert cotas == {
        (date(2024, 2, 1), "PL", "Fundo Partidário"): Decimal("2000000.50"),
        (date(2024, 8, 1), "PL", "FEFC"): Decimal("2000000.00"),
    }


def test_despesas_vinculadas_por_cnpj_e_cpf_sem_gravar_cpf():
    resumo = contas.resumir(
        [],
        contas.comum_tse.linhas(_zip_contas(), "despesa_anual_"),
        2024,
        socios={CNPJ_SOCIA, CNPJ_SANCIONADA},
        sancionados={CNPJ_SANCIONADA},
        cpfs={CPF_PESSOA: 7},
    )
    por_sq = {v["sq_despesa"]: v for v in resumo.vinculadas}
    assert sorted(por_sq) == ["3", "4"]  # a pessoa fora da base não entra
    assert por_sq["3"]["motivo"] == "sancao_empresa,socio_pessoa"
    assert por_sq["3"]["fornecedor_nome"] == "SALOC SERVICOS"
    assert por_sq["3"]["data"] == date(2024, 4, 15)
    assert por_sq["4"]["pessoa_id"] == 7 and por_sq["4"]["motivo"] == "pessoa"
    assert por_sq["4"]["fornecedor_cnpj"] is None and por_sq["4"]["fornecedor_nome"] is None
    assert por_sq["4"]["municipio"] == "Plácido de Castro"
    assert CPF_PESSOA not in repr(resumo.vinculadas) and "98765432100" not in repr(resumo.somas)


def test_carga_no_banco_e_idempotente(session):
    pessoa = Pessoa(nome="Bruno Barbosa", chave_nome="BRUNO BARBOSA", cpf=CPF_PESSOA)
    session.add(pessoa)
    session.flush()
    total = contas.carregar(session, _zip_contas(), 2024)
    assert total == contas.carregar(session, _zip_contas(), 2024)  # recarrega, não duplica
    soma = session.scalar(
        select(func.sum(PartidoContaSoma.valor)).where(
            PartidoContaSoma.tipo == "receita", PartidoContaSoma.natureza == "cota_tse"
        )
    )
    assert soma == Decimal("4000000.50")
    assert session.scalar(select(func.count()).select_from(PartidoCotaMensal)) == 2
    vinculada = session.scalars(select(PartidoDespesaVinculada)).one()
    assert (vinculada.pessoa_id, vinculada.sq_despesa) == (pessoa.id, "4")


def test_carga_sem_dados_aborta_sem_apagar(session):
    contas.carregar(session, _zip_contas(), 2024)
    vazio = io.BytesIO()
    with zipfile.ZipFile(vazio, "w") as z:
        z.writestr("receita_anual_2024_BR.csv", _csv(COLUNAS_RECEITA, []))
        z.writestr("despesa_anual_2024_BR.csv", _csv(COLUNAS_DESPESA, []))
    try:
        contas.carregar(session, vazio.getvalue(), 2024)
    except RuntimeError:
        pass
    else:
        raise AssertionError("deveria abortar")
    assert session.scalar(select(func.count()).select_from(PartidoContaSoma)) > 0


@pytest.fixture
def banco_de_teste(engine, tmp_path, monkeypatch):
    """executar() abre a própria sessão (cache de download, fonte_ingestao): no banco de
    teste, nunca no banco local de desenvolvimento."""
    monkeypatch.setattr(contas.comum, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(contas.comum, "RAW_DIR", tmp_path)


@respx.mock
def test_exercicio_nao_publicado_nao_e_erro(banco_de_teste):
    respx.head(contas.URL.format(ano=2026)).respond(404)
    rota = respx.get(contas.URL.format(ano=2026)).respond(404)
    assert contas.executar(2026) == 0
    assert rota.called
    respx.head(fefc_fp.URL.format(ano=2026)).respond(404)
    rota = respx.get(fefc_fp.URL.format(ano=2026)).respond(404)
    assert fefc_fp.executar(2026) == 0
    assert rota.called


@respx.mock
def test_erro_de_servidor_nao_e_engolido(banco_de_teste, monkeypatch):
    monkeypatch.setattr(contas.comum.time, "sleep", lambda _: None)
    respx.head(contas.URL.format(ano=2024)).respond(403)
    respx.get(contas.URL.format(ano=2024)).respond(403)
    try:
        contas.executar(2024)
    except httpx.HTTPStatusError:
        pass
    else:
        raise AssertionError("403 deve estourar")


# ---- fefc_fp: linhas reais de 2024 ----

FEFC_GENERO = (
    '"AA_ELEICAO";"SG_PARTIDO";"NR_PARTIDO";"DS_GENERO";"QT_CANDIDATO";"VR_PARTIDO_FEFC";'
    '"PE_CAND_PARTIDO_GENERO";"VR_REPASSE_MINIMO_COTA";"VR_TOTAL_RECEBIDO_FEFC";'
    '"PE_VALOR_FEFC_GENERO";"ST_RENUNCIA";"DT_GERACAO";"HH_GERACAO"\n'
    '2024;"AGIR";36;"Feminino";2468;"3421737,78";"33,99";"1163048,67";"1413257,55";"41,30";0;"28/09/2026";"11:06"\n'
    '2024;"AGIR";36;"Masculino";4794;"3421737,78";"66,01";"2258689,11";"1794102,48";"52,43";0;"28/09/2026";"11:06"\n'
)  # fmt: skip
FEFC_COR = (
    '"AA_ELEICAO";"SG_PARTIDO";"NR_PARTIDO";"DS_GENERO";"DS_COR_RACA";"QT_CANDIDATO";'
    '"VR_PARTIDO_FEFC";"PE_CAND_PARTIDO_GENERO";"VR_REPASSE_MINIMO_COTA";"VR_TOTAL_RECEBIDO_FEFC";'
    '"PE_VALOR_FEFC_GENERO";"ST_RENUNCIA";"DT_GERACAO";"HH_GERACAO"\n'
    '2024;"AGIR";36;"Feminino";"NEGRA";1444;"1163048,67";"58,51";"348914,60";"682229,95";"58,66";0;"28/09/2026";"11:06"\n'
    '2024;"AGIR";36;"Feminino";"NÃO NEGRA";1024;"1163048,67";"41,49";"814134,07";"731027,60";"62,85";0;"28/09/2026";"11:06"\n'
)  # fmt: skip
FP_GENERO = (
    '"AA_ELEICAO";"SG_PARTIDO";"NR_PARTIDO";"DS_ESFERA_PARTIDARIA";"SG_UF";"SG_UE";"DS_MUNICIPIO";'
    '"DS_GENERO";"QT_CANDIDATO";"VR_DESPESA_DIRETORIO_FP";"PE_CAND_PARTIDO_GENERO";'
    '"VR_DESPESA_MINIMO_COTA";"VR_TOTAL_RECEBIDO_FP";"PE_VALOR_FP_GENERO";"DT_GERACAO";"HH_GERACAO"\n'
    '2024;"AGIR";36;"Estadual";"AC";"";"";"Feminino";8;"0,00";"34,79";"0,00";"0,00";"0,00";"28/09/2026";"01:02"\n'
    '2024;"AGIR";36;"Municipal";"AC";"01120";"RIO BRANCO";"Feminino";3;"1000,00";"50,00";"0,00";"600,00";"60,00";"28/09/2026";"01:02"\n'
    '2024;"AGIR";36;"Municipal";"AC";"01015";"CRUZEIRO DO SUL";"Feminino";2;"500,00";"50,00";"0,00";"150,25";"30,00";"28/09/2026";"01:02"\n'
)  # fmt: skip
FP_COR = FP_GENERO.replace('"DS_GENERO";', '"DS_GENERO";"DS_COR_RACA";').replace(
    '"Feminino";', '"Feminino";"NEGRA";'
)


def _zip_fefc() -> bytes:
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("fefc_genero_2024.csv", FEFC_GENERO.encode("latin-1"))
        z.writestr("fefc_cor_raca_2024.csv", FEFC_COR.encode("latin-1"))
        z.writestr("fp_genero_2024.csv", FP_GENERO.encode("latin-1"))
        z.writestr("fp_cor_raca_2024.csv", FP_COR.encode("latin-1"))
    return saida.getvalue()


def test_fefc_fp_somado_por_partido_e_esfera():
    linhas = fefc_fp.resumir(_zip_fefc(), 2024)
    por_chave = {(f["fundo"], f["esfera"], f["genero"], f["cor_raca"]): f for f in linhas}
    feminino = por_chave[("FEFC", "Nacional", "Feminino", "")]
    assert (feminino["candidatos"], feminino["valor_recebido"]) == (2468, Decimal("1413257.55"))
    assert feminino["valor_partido"] == Decimal("3421737.78")
    assert por_chave[("FEFC", "Nacional", "Feminino", "Não negra")]["valor_recebido"] == Decimal(
        "731027.60"
    )
    # Fundo Partidário: os dois diretórios municipais viram uma linha só.
    municipal = por_chave[("FP", "Municipal", "Feminino", "")]
    assert (municipal["candidatos"], municipal["valor_recebido"]) == (5, Decimal("750.25"))
    assert por_chave[("FP", "Municipal", "Feminino", "Negra")]["candidatos"] == 5


def test_fefc_fp_carga_idempotente(session):
    def carregar():
        linhas = fefc_fp.resumir(_zip_fefc(), 2024)
        session.query(PartidoFefcFp).filter(PartidoFefcFp.ano == 2024).delete()
        session.execute(PartidoFefcFp.__table__.insert(), linhas)
        return len(linhas)

    assert carregar() == carregar()
    # Total do partido: um valor por partido, não a soma das linhas (que contaria em dobro).
    total = session.scalar(
        select(func.max(PartidoFefcFp.valor_partido)).where(PartidoFefcFp.fundo == "FEFC")
    )
    assert total == Decimal("3421737.78")
