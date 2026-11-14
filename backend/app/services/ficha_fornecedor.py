"""Ficha do fornecedor: o que os dados do site registram sobre uma empresa, pelo CNPJ.

Junta o que hoje aparece espalhado (docs/DECISOES.md, 2026-11-14): pagamentos de gabinetes
(cota parlamentar), pagamentos de prefeituras e câmaras (Tribunais de Contas), contratos no PNCP,
emendas em que a empresa é a favorecida e sanções da CGU. Só soma e conta: nenhuma nota, selo ou
leitura do que os números querem dizer.

Regras:
- Só CNPJ válido de 14 dígitos. O campo `despesa.cnpj_cpf` também guarda CPF de fornecedor pessoa
  física: a consulta compara os 14 dígitos exatos, então CPF nunca casa, e o nome passa por
  `sem_cpf` (MEI traz o CPF na razão social).
- A ligação é o CNPJ exato, como a fonte publica: não há ligação por nome.
- Cada bloco diz a fonte, a data da última carga e o que ficou de fora.
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Integer, func, literal_column, select
from sqlalchemy.orm import Session

from app.cnpj import cnpj_valido, normalizar_cnpj
from app.models import (
    Despesa,
    DespesaFornecedor,
    EmendaPagamento,
    EmendaTransferencia,
    Empresa,
    FonteIngestao,
    Municipio,
    Parlamentar,
    PncpAnual,
    SancaoEmpresa,
)
from app.textos import sem_cpf

# A mesma expressão do índice ix_despesa_documento (migração 0079): em texto, não em parâmetro,
# para o planejador reconhecer o índice.
DOC_DESPESA = literal_column("regexp_replace(coalesce(despesa.cnpj_cpf, ''), '\\D', '', 'g')")
LIMITE_LISTA = 20
SITUACOES = {"02": "ativa", "03": "suspensa", "04": "inapta", "08": "baixada", "01": "nula"}


def _atualizado(session: Session, fontes: Sequence[str]) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte.in_(fontes), FonteIngestao.status == "ok"
        )
    )


def _gabinetes(session: Session, cnpj: str) -> dict:
    por_ano = session.execute(
        select(
            Despesa.ano,
            func.sum(Despesa.valor),
            func.count(func.distinct(Despesa.parlamentar_id)),
            func.count(),
        )
        .where(DOC_DESPESA == cnpj)
        .group_by(Despesa.ano)
        .order_by(Despesa.ano.desc())
    ).all()
    ano = por_ano[0][0] if por_ano else None
    quem = (
        session.execute(
            select(
                Parlamentar.id,
                Parlamentar.nome_parlamentar,
                Parlamentar.casa,
                Parlamentar.partido,
                Parlamentar.uf,
                func.sum(Despesa.valor).label("valor"),
            )
            .join(Parlamentar, Parlamentar.id == Despesa.parlamentar_id)
            .where(DOC_DESPESA == cnpj, Despesa.ano == ano)
            .group_by(Parlamentar.id)
            .order_by(func.sum(Despesa.valor).desc(), Parlamentar.nome_parlamentar)
            .limit(LIMITE_LISTA)
        ).all()
        if ano
        else []
    )
    nome = session.scalar(
        select(Despesa.fornecedor)
        .where(DOC_DESPESA == cnpj, Despesa.fornecedor.is_not(None))
        .group_by(Despesa.fornecedor)
        .order_by(func.count().desc(), Despesa.fornecedor)
        .limit(1)
    )
    return {
        "por_ano": [
            {"ano": a, "valor": float(v), "gabinetes": g, "lancamentos": n}
            for a, v, g, n in por_ano
        ],
        "ano_da_lista": ano,
        "maiores": [
            {
                "parlamentar_id": i,
                "nome": n,
                "casa": casa,
                "partido": partido,
                "uf": uf,
                "valor": float(valor),
            }
            for i, n, casa, partido, uf, valor in quem
        ],
        "limite_da_lista": LIMITE_LISTA,
        "recorte": "Cota parlamentar da Câmara e do Senado, ano atual e anterior.",
        "fonte_nome": "Dados Abertos da Câmara (CEAP) e do Senado (CEAPS)",
        "atualizado_em": _atualizado(session, ("camara_despesas", "senado_despesas")),
        "_nome": nome,
    }


def _prefeituras(session: Session, cnpj: str) -> dict:
    por_ano = session.execute(
        select(
            DespesaFornecedor.ano,
            func.sum(DespesaFornecedor.valor_pago),
            func.count(func.distinct(DespesaFornecedor.municipio_ibge)),
        )
        .where(DespesaFornecedor.documento == cnpj)
        .group_by(DespesaFornecedor.ano)
        .order_by(DespesaFornecedor.ano.desc())
    ).all()
    ano = por_ano[0][0] if por_ano else None
    onde = (
        session.execute(
            select(
                Municipio.ibge,
                Municipio.nome,
                Municipio.uf,
                DespesaFornecedor.orgao,
                func.sum(DespesaFornecedor.valor_pago).label("valor"),
            )
            .join(Municipio, Municipio.ibge == DespesaFornecedor.municipio_ibge)
            .where(DespesaFornecedor.documento == cnpj, DespesaFornecedor.ano == ano)
            .group_by(Municipio.ibge, DespesaFornecedor.orgao)
            .order_by(func.sum(DespesaFornecedor.valor_pago).desc(), Municipio.nome)
            .limit(LIMITE_LISTA)
        ).all()
        if ano
        else []
    )
    nome = session.scalar(
        select(DespesaFornecedor.fornecedor).where(DespesaFornecedor.documento == cnpj).limit(1)
    )
    fontes = session.scalars(
        select(func.distinct(DespesaFornecedor.fonte)).where(DespesaFornecedor.documento == cnpj)
    ).all()
    return {
        "por_ano": [{"ano": a, "valor": float(v), "municipios": m} for a, v, m in por_ano],
        "ano_da_lista": ano,
        "maiores": [
            {"ibge": i, "municipio": n, "uf": uf, "orgao": orgao, "valor": float(v)}
            for i, n, uf, orgao, v in onde
        ],
        "limite_da_lista": LIMITE_LISTA,
        "recorte": (
            "Só os maiores fornecedores de cada prefeitura e câmara, e só nos estados cujo "
            "Tribunal de Contas publica os pagamentos em dados abertos."
        ),
        "fonte_nome": "Tribunais de Contas dos estados (pagamentos a fornecedores)",
        "atualizado_em": _atualizado(session, tuple(fontes)) if fontes else None,
        "_nome": nome,
    }


def _pncp(session: Session, cnpj: str) -> dict:
    por_ano = session.execute(
        select(
            PncpAnual.ano,
            func.sum(PncpAnual.valor_global),
            func.sum(PncpAnual.quantidade),
            func.count(func.distinct(PncpAnual.municipio_ibge)),
        )
        .where(PncpAnual.fornecedor_cnpj == cnpj)
        .group_by(PncpAnual.ano)
        .order_by(PncpAnual.ano.desc())
    ).all()
    nome = session.scalar(
        select(PncpAnual.fornecedor_nome).where(PncpAnual.fornecedor_cnpj == cnpj).limit(1)
    )
    return {
        "por_ano": [
            {"ano": a, "valor": float(v), "contratos": int(q), "municipios": m}
            for a, v, q, m in por_ano
        ],
        "recorte": (
            "Contratos de órgãos municipais publicados no PNCP, ano atual e anterior, e só "
            "quando a empresa está entre os maiores fornecedores do município no ano. O valor "
            "é o do contrato, não o que já foi pago."
        ),
        "fonte_nome": "Portal Nacional de Contratações Públicas (PNCP)",
        "atualizado_em": _atualizado(session, ("pncp_contratos",)),
        "_nome": nome,
    }


def _emendas(session: Session, cnpj: str) -> dict:
    ano = func.cast(func.floor(EmendaPagamento.ano_mes / 100), Integer)
    pagas = session.execute(
        select(
            ano,
            func.sum(EmendaPagamento.valor),
            func.count(func.distinct(EmendaPagamento.autor_codigo)),
        )
        .where(EmendaPagamento.favorecido_codigo == cnpj)
        .group_by(ano)
        .order_by(ano.desc())
    ).all()
    transferencias = session.execute(
        select(
            func.count(),
            func.coalesce(func.sum(EmendaTransferencia.valor_repassado), 0),
        ).where(EmendaTransferencia.beneficiario_cnpj == cnpj)
    ).one()
    nome = session.scalar(
        select(EmendaPagamento.favorecido).where(EmendaPagamento.favorecido_codigo == cnpj).limit(1)
    )
    return {
        "pagas_por_ano": [{"ano": a, "valor": float(v), "autores": n} for a, v, n in pagas],
        "convenios": {"quantidade": transferencias[0], "valor_repassado": float(transferencias[1])},
        "recorte": (
            "Emendas parlamentares em que este CNPJ é o favorecido do pagamento (prefeituras, "
            "fundos e entidades sem fins lucrativos) e convênios ou transferências especiais "
            "em que é o beneficiário. Os dois números podem contar o mesmo dinheiro."
        ),
        "fonte_nome": "Portal da Transparência (CGU) e Transferegov",
        "atualizado_em": _atualizado(
            session, ("transparencia_emendas", "transferegov_convenios", "transferegov_especiais")
        ),
        "_nome": nome,
    }


def _sancoes(session: Session, cnpj: str) -> dict:
    linhas = session.scalars(
        select(SancaoEmpresa)
        .where(SancaoEmpresa.cnpj == cnpj)
        .order_by(SancaoEmpresa.inicio.desc().nulls_last(), SancaoEmpresa.id)
    ).all()
    return {
        "itens": [
            {
                "cadastro": s.cadastro,
                "categoria": s.categoria,
                "abrangencia": s.abrangencia,
                "orgao": s.orgao,
                "inicio": s.inicio,
                "fim": s.fim,
                "processo": s.processo,
            }
            for s in linhas
        ],
        "recorte": (
            "Registros dos cadastros de sanções da CGU (CEIS e CNEP) com este CNPJ. A "
            "abrangência diz onde a sanção vale; sem data de fim, a fonte não informa o prazo."
        ),
        "fonte_nome": "Portal da Transparência (CGU): CEIS e CNEP",
        "fonte_url": "https://portaldatransparencia.gov.br/sancoes",
        "atualizado_em": _atualizado(session, ("cgu_sancoes",)),
        "_nome": linhas[0].nome if linhas else None,
    }


def ficha(session: Session, cnpj_bruto: str) -> dict | None:
    """None quando o CNPJ é inválido ou não aparece em nenhum dos dados."""
    cnpj = normalizar_cnpj(cnpj_bruto)
    if not cnpj or len(cnpj) != 14 or not cnpj_valido(cnpj):
        return None
    blocos = {
        "gabinetes": _gabinetes(session, cnpj),
        "prefeituras": _prefeituras(session, cnpj),
        "pncp": _pncp(session, cnpj),
        "emendas": _emendas(session, cnpj),
        "sancoes": _sancoes(session, cnpj),
    }
    cadastro = session.get(Empresa, cnpj)
    tem_dado = (
        blocos["gabinetes"]["por_ano"]
        or blocos["prefeituras"]["por_ano"]
        or blocos["pncp"]["por_ano"]
        or blocos["emendas"]["pagas_por_ano"]
        or blocos["emendas"]["convenios"]["quantidade"]
        or blocos["sancoes"]["itens"]
    )
    if not tem_dado and cadastro is None:
        return None
    # O nome do cadastro da Receita vale primeiro; sem ele, o que as fontes escreveram.
    nomes_das_fontes = [b.pop("_nome") for b in blocos.values()]
    nome = (cadastro.razao_social if cadastro else None) or next(
        (n for n in (sem_cpf(x) for x in nomes_das_fontes) if n), None
    )
    return {
        "cnpj": cnpj,
        "nome": sem_cpf(nome),
        "nome_omitido": bool(cadastro and cadastro.nome_omitido),
        "nome_fantasia": sem_cpf(cadastro.nome_fantasia) if cadastro else None,
        "uf": cadastro.uf if cadastro else None,
        "situacao": SITUACOES.get(cadastro.situacao or "") if cadastro else None,
        "cadastro_referencia": cadastro.referencia if cadastro else None,
        **blocos,
    }
