"""Comparar no tempo e com cidades parecidas (redesenho, etapa 6), só com dados já carregados:

- `parecidas`: as cidades do Brasil com a população mais próxima (último ano do IBGE), lado a
  lado em população, PIB por morador, IDEB dos anos iniciais (rede pública) e salário médio. Não
  é ranking: a ordem é a da população.
- `vocacoes`: o peso de cada atividade na cidade comparado ao peso no Brasil, pelo PIB (valor
  adicionado, todas as cidades) e pelas pessoas ocupadas (CNAE, cidades com 50 mil habitantes
  ou mais). A razão (cidade ÷ Brasil) é o "quociente locacional" dos economistas: acima de 1, a
  atividade pesa mais aqui do que no país. O número é escrito; nada de "bom" ou "ruim".
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EmpregoIbge, EmpregoSetor, IdebResultado, Municipio, PibIbge, PopulacaoIbge
from app.services.pib import SETORES

PARECIDAS = 6


def _populacoes(session: Session) -> tuple[int | None, dict[str, int]]:
    ano = session.scalar(
        select(func.max(PopulacaoIbge.ano)).where(func.length(PopulacaoIbge.codigo) == 7)
    )
    if ano is None:
        return None, {}
    linhas = session.execute(
        select(PopulacaoIbge.codigo, PopulacaoIbge.valor).where(
            PopulacaoIbge.ano == ano, func.length(PopulacaoIbge.codigo) == 7
        )
    ).all()
    return ano, dict(linhas)


def _ultimo_por(session: Session, modelo, coluna, codigos: list[str], *filtros) -> dict:
    """Último ano com valor de `coluna`, por código: {codigo: (ano, valor)}."""
    linhas = session.execute(
        select(modelo.codigo, modelo.ano, coluna)
        .where(modelo.codigo.in_(codigos), coluna.is_not(None), *filtros)
        .order_by(modelo.ano)
    ).all()
    return {c: (a, v) for c, a, v in linhas}


def parecidas(session: Session, ibge: str) -> dict:
    ano_pop, pops = _populacoes(session)
    alvo = pops.get(ibge)
    if alvo is None:
        return {"ano_populacao": ano_pop, "cidades": []}
    vizinhas = sorted((c for c in pops if c != ibge), key=lambda c: abs(pops[c] - alvo))[:PARECIDAS]
    codigos = [ibge, *vizinhas]
    nomes = {
        m.ibge: m for m in session.scalars(select(Municipio).where(Municipio.ibge.in_(codigos)))
    }
    # PIB por morador: o último ano com PIB e população do mesmo ano.
    pibs = session.execute(
        select(PibIbge.codigo, PibIbge.ano, PibIbge.pib, PopulacaoIbge.valor)
        .join(
            PopulacaoIbge,
            (PopulacaoIbge.codigo == PibIbge.codigo) & (PopulacaoIbge.ano == PibIbge.ano),
        )
        .where(PibIbge.codigo.in_(codigos))
        .order_by(PibIbge.ano)
    ).all()
    pib_morador = {c: (a, float(p) * 1000 / v) for c, a, p, v in pibs if v}
    ideb = _ultimo_por(
        session,
        IdebResultado,
        IdebResultado.valor,
        codigos,
        IdebResultado.abrangencia == "municipio",
        IdebResultado.etapa == "iniciais",
        IdebResultado.rede == "publica",
    )
    salario = _ultimo_por(session, EmpregoIbge, EmpregoIbge.salario_medio, codigos)
    ordem = sorted(codigos, key=lambda c: -pops[c])
    return {
        "ano_populacao": ano_pop,
        "cidades": [
            {
                "ibge": c,
                "nome": nomes[c].nome if c in nomes else c,
                "uf": nomes[c].uf if c in nomes else "",
                "esta": c == ibge,
                "populacao": pops[c],
                "pib_por_morador": round(pib_morador[c][1], 2) if c in pib_morador else None,
                "pib_ano": pib_morador[c][0] if c in pib_morador else None,
                "ideb": float(ideb[c][1]) if c in ideb else None,
                "ideb_ano": ideb[c][0] if c in ideb else None,
                "salario_medio": float(salario[c][1]) if c in salario else None,
                "salario_ano": salario[c][0] if c in salario else None,
            }
            for c in ordem
        ],
    }


def vocacoes(session: Session, ibge: str) -> dict:
    # Pelo PIB: o último ano em que a cidade e o Brasil têm o valor adicionado por atividade.
    pib_ano = session.scalar(
        select(func.max(PibIbge.ano)).where(PibIbge.codigo == ibge, PibIbge.vab_total.is_not(None))
    )
    pib = []
    if pib_ano:
        cidade = session.get(PibIbge, (ibge, pib_ano))
        brasil = session.get(PibIbge, ("1", pib_ano))
        if cidade and brasil and cidade.vab_total and brasil.vab_total:
            for campo, nome in SETORES:
                aqui = float(100 * (getattr(cidade, campo) or 0) / cidade.vab_total)
                pais = float(100 * (getattr(brasil, campo) or 0) / brasil.vab_total)
                pib.append({"atividade": nome, "percentual": aqui, "percentual_brasil": pais,
                            "razao": aqui / pais if pais else None})  # fmt: skip
    # Pelas pessoas ocupadas (CNAE): só onde o IBGE publica (50 mil habitantes ou mais).
    setores = session.scalars(select(EmpregoSetor).where(EmpregoSetor.codigo == ibge)).all()
    emprego = []
    if setores:
        ano = setores[0].ano
        brasil = {
            s.secao: s.pessoal_ocupado
            for s in session.scalars(
                select(EmpregoSetor).where(EmpregoSetor.codigo == "1", EmpregoSetor.ano == ano)
            )
        }
        total, total_br = sum(s.pessoal_ocupado for s in setores), sum(brasil.values())
        for s in setores:
            if s.secao not in brasil or not total or not total_br:
                continue
            aqui = float(100 * s.pessoal_ocupado / total)
            pais = float(100 * brasil[s.secao] / total_br)
            emprego.append({"atividade": s.nome, "percentual": aqui, "percentual_brasil": pais,
                            "razao": aqui / pais if pais else None})  # fmt: skip
        emprego.sort(key=lambda x: -(x["razao"] or 0))
    return {
        "pib_ano": pib_ano if pib else None,
        "pib": pib,
        "emprego_ano": setores[0].ano if setores else None,
        "emprego": emprego,
    }
