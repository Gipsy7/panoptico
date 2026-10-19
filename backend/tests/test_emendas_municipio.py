"""Emendas por município completas, com as linhas reais de Gaspar (SC, IBGE 4205902).

Fixtures em tests/fixtures/emendas_gaspar/ (recortes dos arquivos oficiais, 18/10/2026):
- favorecidos.csv: as linhas de pessoa jurídica de Gaspar no arquivo por favorecido da CGU
  (sem pessoas físicas nem empresário individual);
- emendas.csv: as linhas do cadastro de emendas dos códigos de Gaspar;
- planos.json: os 26 planos de transferência especial da Prefeitura de Gaspar na API do
  TransfereGov (cnpj_beneficiario_plano_acao=eq.83102244000102), sem dados bancários;
- convenios.csv e emendas_convenios.csv: dois convênios reais com a prefeitura.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import insert, select

from app.models import (
    Candidatura,
    ContasMunicipio,
    EmendaPagamento,
    FonteIngestao,
    Municipio,
    Parlamentar,
    Pessoa,
    PessoaVinculo,
)
from ingestion.transferegov import convenios, especiais, municipio
from ingestion.transparencia import emendas
from tests.test_api import _ingestao
from tests.test_emendas import _zip
from tests.test_transferegov import CAB as CAB_CONVENIOS
from tests.test_transferegov import _zip_convenios

FIXTURES = Path(__file__).parent / "fixtures" / "emendas_gaspar"
GASPAR = "4205902"
CNPJ_PREFEITURA = "83102244000102"
CNPJ_FUNDO_SAUDE = "11436906000170"
ENTES = [
    {"cnpj": CNPJ_PREFEITURA, "ibge": GASPAR, "uf": "SC", "esfera": "M"},
    {"cnpj": "83108357000115", "ibge": "4202404", "uf": "SC", "esfera": "M"},  # Blumenau
    {"cnpj": "82951229000176", "ibge": "42", "uf": "SC", "esfera": "E"},  # Estado de SC
]


def _texto(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


def _arquivo_emendas(sem_codigo: str | None = None) -> bytes:
    """O zip da CGU com as linhas de Gaspar; `sem_codigo` tira os pagamentos de uma emenda
    (simula um convênio cujo pagamento não aparece por favorecido)."""
    favorecidos = [
        linha
        for linha in _texto("favorecidos.csv").splitlines()
        if not sem_codigo or not linha.startswith(f'"{sem_codigo}"')
    ]
    return _zip(
        **{
            emendas.ARQUIVO: _texto("emendas.csv"),
            emendas.ARQUIVO_FAVORECIDOS: "\n".join(favorecidos),
            emendas.ARQUIVO_CONVENIOS: _texto("emendas_convenios.csv"),
        }
    )


def _parlamentar(session, casa, id_externo, nome, em_exercicio=True) -> Parlamentar:
    p = Parlamentar(
        casa=casa, id_externo=id_externo, nome_parlamentar=nome, uf="SC",
        fonte_url="https://exemplo", atualizado_em=datetime.now(UTC), em_exercicio=em_exercicio,
    )  # fmt: skip
    session.add(p)
    session.flush()
    return p


def _pessoa(session, nome, fonte, id_externo, regra="cpf") -> Pessoa:
    pessoa = Pessoa(nome=nome, chave_nome=nome.upper())
    session.add(pessoa)
    session.flush()
    session.add(PessoaVinculo(pessoa_id=pessoa.id, fonte=fonte, id_externo=id_externo,
                              regra=regra))  # fmt: skip
    return pessoa


def _eleito(session, ano, sq, nome, nome_urna) -> None:
    session.add(
        Candidatura(ano_eleicao=ano, sq_candidato=sq, cargo="DEPUTADO FEDERAL", uf="SC",
                    unidade="SANTA CATARINA", nome=nome, nome_urna=nome_urna,
                    situacao_turno="ELEITO POR QP")
    )  # fmt: skip


@pytest.fixture
def gaspar(session):
    """Base com Gaspar carregada pelas três ingestões, como na produção."""

    def carregar(sem_codigo: str | None = None) -> dict:
        session.execute(
            insert(Municipio),
            [
                {"ibge": GASPAR, "nome": "Gaspar", "uf": "SC", "nome_chave": "GASPAR"},
                {"ibge": "4202404", "nome": "Blumenau", "uf": "SC", "nome_chave": "BLUMENAU"},
            ],
        )
        for ibge, pop in ((GASPAR, 78344), ("4202404", 361261)):
            session.add(ContasMunicipio(municipio_ibge=ibge, ano=2025, populacao=pop,
                                        despesa_por_area={}))  # fmt: skip
        ids = {
            "goetten": _parlamentar(session, "camara", "1", "Jorge Goetten").id,
            "ismael": _parlamentar(session, "camara", "2", "Ismael").id,
            "amin": _parlamentar(session, "senado", "3", "Esperidião Amin").id,
            # Fora do cargo, mas no cadastro da Câmara: liga pelo nome e não vira "em exercício".
            "peninha": _parlamentar(session, "camara", "4", "Rogério Peninha Mendonça", False).id,
        }
        ids["pessoa_peninha"] = _pessoa(
            session, "Rogério Peninha Mendonça", "parlamentar", "camara:4"
        ).id
        # Darci de Matos: só como eleito do TSE, nome idêntico -> vínculo forte com a pessoa.
        _eleito(session, 2018, "240000600001", "DARCI JOSE DE MATOS", "DARCI DE MATOS")
        ids["pessoa_darci"] = _pessoa(session, "Darci José de Matos", "candidatura",
                                      "2018:240000600001", regra="tse").id  # fmt: skip
        # Geovania: só um nome parecido entre os eleitos -> não liga (iria para revisão).
        _eleito(session, 2018, "240000600002", "GEOVANIA DE SA RODRIGUES", "GEOVANIA")
        _pessoa(session, "Geovania de Sá Rodrigues", "candidatura", "2018:240000600002",
                regra="tse")  # fmt: skip
        session.flush()

        emendas.carregar(session, _arquivo_emendas(sem_codigo), _ingestao(session, emendas.FONTE))
        recorte = {
            "planos": json.loads(_texto("planos.json")),
            "executores": [], "empenhos": [], "relatorios": [], "entes": ENTES,
        }  # fmt: skip
        especiais.carregar(
            session, json.dumps(recorte).encode(), _ingestao(session, especiais.FONTE)
        )
        linhas_conv = _texto("convenios.csv").splitlines()
        numeros = {linha.split(";")[0].strip('"') for linha in linhas_conv}
        bruto = {
            "convenios": convenios.recortar(_zip_convenios(*linhas_conv), numeros),
            "entes": ENTES,
        }
        convenios.carregar(session, json.dumps(bruto).encode(), _ingestao(session, convenios.FONTE))
        for i in session.scalars(select(FonteIngestao)):
            i.status, i.concluido_em = "ok", datetime.now(UTC)
        session.flush()
        return ids

    return carregar


def test_fixture_usa_o_cabecalho_real_dos_convenios():
    assert CAB_CONVENIOS.startswith("NÚMERO CONVÊNIO;UF;CÓDIGO SIAFI MUNICÍPIO")


def test_gaspar_completo_por_tipo_e_sem_dupla_contagem(client, session, gaspar):
    ids = gaspar()
    corpo = client.get(f"/municipios/{GASPAR}/emendas").json()

    # Pago (CGU, por favorecido), por tipo, desde o primeiro ano do arquivo.
    tipos = {t["tipo"]: t["total"] for t in corpo["tipos"]}
    assert tipos == {
        "individual": 9440887.65,
        "especial": 7489500.0,
        "bancada": 3268397.08,
        "comissao": 1613749.0,
        "relator": 1878733.64,
    }
    assert corpo["total_geral"] == pytest.approx(sum(tipos.values()))
    # Os campos antigos seguem só com as individuais (com destino definido + Pix).
    assert corpo["total"] == pytest.approx(9440887.65 + 7489500.0)
    assert corpo["total"] == pytest.approx(corpo["total_prefeitura"] + corpo["total_entidades"])
    assert corpo["periodo"] == {"inicio": 2015, "fim": 2026}
    assert corpo["desde"] == 2015
    # Antes da mudança o site mostrava só individuais pagas desde 2023 de quem está no cargo:
    # R$ 12,06 mi. Esse recorte continua dentro do novo total.
    recorte_antigo = sum(a["total"] for a in corpo["por_ano"] if a["ano"] >= 2023)
    assert recorte_antigo == pytest.approx(12063185.0)

    # Jorge Goetten: R$ 1.195.000 em Pix, no pago (CGU) e nos planos (TransfereGov). Conta
    # uma vez só: no pago. O plano dele está em "com pagamento", fora do previsto.
    goetten = next(p for p in corpo["parlamentares"] if p["parlamentar"]["id"] == ids["goetten"])
    assert goetten["total"] == 1195000.0
    previsto = corpo["previsto"]
    assert previsto["planos"] == 26
    assert previsto["valor_planos"] == 8186000.0
    assert previsto["planos_com_pagamento"] == 24
    assert previsto["valor_planos_com_pagamento"] == tipos["especial"]  # bate com o pago
    assert previsto["valor_sem_pagamento"] == 696500.0
    assert not any(i["emenda_codigo"].startswith("20244209") for i in previsto["sem_pagamento"])

    # Ismael: plano de 2026 ainda sem pagamento na CGU -> aparece no previsto, com mandato.
    ismael = next(i for i in previsto["sem_pagamento"] if i["autor_nome"] == "ISMAEL")
    assert (ismael["valor"], ismael["ano"], ismael["parlamentar_id"]) == (
        497500.0,
        2026,
        ids["ismael"],
    )
    assert ismael["com_mandato_atual"] is True
    assert ismael["fonte_url"].endswith("codigo_plano_acao=eq.09032026-094184")

    # Autores fora do cargo aparecem pelo nome, com a ligação forte quando há.
    outros = {a["autor_nome"]: a for a in corpo["outros_autores"]}
    peninha = outros["ROGERIO PENINHA MENDONCA"]
    assert peninha["total"] == pytest.approx(245850 + 292500 + 493100 + 460952.38 + 600000)
    assert (peninha["parlamentar_id"], peninha["pessoa_id"]) == (
        ids["peninha"],
        ids["pessoa_peninha"],
    )
    assert outros["DARCI DE MATOS"]["total"] == 150000.0
    assert outros["DARCI DE MATOS"]["pessoa_id"] == ids["pessoa_darci"]
    assert outros["GEOVANIA DE SA"]["total"] == pytest.approx(460952.38 + 200000)
    assert outros["GEOVANIA DE SA"]["pessoa_id"] is None  # nome só parecido: não liga
    assert all(not a["com_mandato_atual"] for a in corpo["outros_autores"])
    assert corpo["autores_sem_mandato"] == corpo["numero_outros_autores"] >= 3
    assert ids["peninha"] not in {p["parlamentar"]["id"] for p in corpo["parlamentares"]}

    # Colegiados com o próprio nome.
    colegiados = {(c["autor_nome"], c["tipo"]) for c in corpo["colegiados"]}
    assert ("BANCADA DE SANTA CATARINA", "bancada") in colegiados
    assert ("COM. TURISMO", "comissao") in colegiados
    assert ("RELATOR GERAL", "relator") in colegiados

    # Convênios: os dois já têm pagamento direto à prefeitura na CGU -> ficam de fora.
    assert corpo["convenios"]["quantidade"] == 0

    # Média do estado coerente: Blumenau, sem nenhuma linha, entra com zero.
    assert corpo["municipios_na_media"] == 2
    assert corpo["media_uf_por_habitante"] == pytest.approx(corpo["por_habitante"] / 2, abs=0.01)
    assert corpo["media_uf_por_habitante_geral"] == pytest.approx(
        corpo["por_habitante_geral"] / 2, abs=0.01
    )


def test_convenio_sem_pagamento_por_favorecido_aparece_uma_vez(client, session, gaspar):
    # Sem as linhas de pagamento da emenda 201528560004, o convênio 819285 dela não tem par no
    # pago e entra pelo valor liberado; o 846522 continua de fora (pago direto).
    gaspar(sem_codigo="201528560004")
    corpo = client.get(f"/municipios/{GASPAR}/emendas").json()
    conv = corpo["convenios"]
    assert conv["quantidade"] == 1
    assert conv["itens"][0]["identificador"] == "819285"
    assert conv["itens"][0]["emendas"] == ["201528560004"]
    assert conv["itens"][0]["autores"] == ["ROGERIO PENINHA MENDONCA"]
    assert conv["valor_liberado"] == 245850.0
    # O liberado não entra no total pago.
    assert corpo["tipos"][0]["total"] == pytest.approx(9440887.65 - 245850)


def test_carga_e_idempotente_e_guarda_o_tipo(session, gaspar):
    gaspar()
    conteudo = _arquivo_emendas()
    emendas.carregar(session, conteudo, _ingestao(session, emendas.FONTE))
    linhas = session.scalars(
        select(EmendaPagamento).where(EmendaPagamento.municipio_ibge == GASPAR)
    ).all()
    # 144 linhas PJ: 132 de prefeitura, fundo ou entidade, das quais 23 sem código de emenda.
    assert len(linhas) == 109
    assert {p.tipo for p in linhas} == {"individual", "especial", "bancada", "comissao", "relator"}
    # Colegiado nunca liga a parlamentar nem a pessoa.
    assert all(p.parlamentar_id is None and p.pessoa_id is None for p in linhas
               if p.tipo not in emendas.TIPOS_INDIVIDUAIS)  # fmt: skip


def test_mapa_cnpj_municipio():
    mapa = municipio.Mapa(
        ENTES,
        {CNPJ_FUNDO_SAUDE: GASPAR},
        [(GASPAR, "SC", "GASPAR"), ("4202404", "SC", "BLUMENAU")],
    )
    assert mapa.resolver(CNPJ_PREFEITURA) == (GASPAR, "siconfi")
    assert mapa.resolver("82.951.229/0001-76") == (None, "estado")
    assert mapa.resolver(CNPJ_FUNDO_SAUDE) == (GASPAR, "favorecido")
    # CNPJ fora do mapa: conferência pelo nome da prefeitura + UF.
    assert mapa.resolver("00000000000191", "SC", "MUNICIPIO DE BLUMENAU") == ("4202404", "nome")
    assert mapa.resolver("00000000000191", "SC", "ASSOCIACAO X") == (None, "sem")
    assert mapa.resolver("00000000000191", "SC", "ASSOCIACAO X", "GASPAR") == (GASPAR, "nome")


def test_resumo_parlamentar_mantem_individuais_desde_2023(session, gaspar):
    from ingestion import resumos

    ids = gaspar()
    linhas = {r["parlamentar_id"]: r for r in resumos.calcular(session, [date.today().year])}
    # Peninha (fora do cargo) não entra; Goetten: só individuais de 2023 em diante.
    assert ids["peninha"] not in linhas
    assert linhas[ids["goetten"]]["emendas_pagas"] == Decimal("1195000.00")
