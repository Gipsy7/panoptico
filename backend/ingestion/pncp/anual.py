"""PNCP na produção: da janela de poucos dias para a soma anual que o site mostra.

O acervo local guarda uma linha por dia × órgão × município × fornecedor × tipo (centenas de
MB). A produção (Neon, pago por uso) guarda só:
- `pncp_janela`: os últimos dias de órgãos municipais por município × fornecedor, para reler
  um dia (o valor global muda com aditivos) sem somar duas vezes;
- `pncp_anual`: o ano atual e o anterior, por município × fornecedor, só os maiores de cada
  município. Um dia que sai da janela é somado aqui uma única vez (`pncp_dia.compactado`).

Aproximação assumida (docs/DECISOES.md): aditivo em contrato de dia já compactado não altera
a soma anual, e fornecedor fora dos maiores do município recomeça do zero se voltar a vender.
"""

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

JANELA_DIAS = 10  # maior que a releitura (7 dias): dia relido ainda está na janela
MAIORES_POR_MUNICIPIO = 30


def ano_minimo(hoje: date) -> int:
    """Ano atual e anterior."""
    return hoje.year - 1


def compactar(session: Session, hoje: date) -> int:
    """Soma em pncp_anual os dias que saíram da janela e apaga-os de pncp_janela.
    Devolve quantos dias foram compactados."""
    corte = hoje - timedelta(days=JANELA_DIAS)
    dias = (
        session.execute(
            text("SELECT dia FROM pncp_dia WHERE NOT compactado AND dia < :corte"),
            {"corte": corte},
        )
        .scalars()
        .all()
    )
    if not dias:
        return 0
    params = {"dias": dias}
    session.execute(
        text(
            """
            INSERT INTO pncp_anual
                (ano, municipio_ibge, fornecedor_cnpj, fornecedor_nome, quantidade, valor_global)
            SELECT EXTRACT(YEAR FROM dia)::int, municipio_ibge, fornecedor_cnpj,
                   max(fornecedor_nome), sum(quantidade), sum(valor_global)
            FROM pncp_janela
            WHERE dia = ANY(:dias) AND EXTRACT(YEAR FROM dia) >= :minimo
            GROUP BY 1, 2, 3
            ON CONFLICT (ano, municipio_ibge, fornecedor_cnpj) DO UPDATE SET
                quantidade = pncp_anual.quantidade + EXCLUDED.quantidade,
                valor_global = pncp_anual.valor_global + EXCLUDED.valor_global,
                fornecedor_nome = COALESCE(EXCLUDED.fornecedor_nome, pncp_anual.fornecedor_nome)
            """
        ),
        {**params, "minimo": ano_minimo(hoje)},
    )
    session.execute(text("DELETE FROM pncp_janela WHERE dia = ANY(:dias)"), params)
    session.execute(text("UPDATE pncp_dia SET compactado = true WHERE dia = ANY(:dias)"), params)
    session.commit()
    return len(dias)


def podar(session: Session, hoje: date, maiores: int = MAIORES_POR_MUNICIPIO) -> int:
    """Apaga anos antigos e, em cada município e ano, o que passa dos `maiores` fornecedores.
    Devolve quantas linhas apagou."""
    antigas = session.execute(
        text("DELETE FROM pncp_anual WHERE ano < :minimo"), {"minimo": ano_minimo(hoje)}
    ).rowcount
    session.execute(
        text("DELETE FROM pncp_suspeito WHERE dia < :inicio"),
        {"inicio": date(ano_minimo(hoje), 1, 1)},
    )
    excedentes = session.execute(
        text(
            """
            DELETE FROM pncp_anual a USING (
                SELECT ano, municipio_ibge, fornecedor_cnpj,
                       row_number() OVER (
                           PARTITION BY ano, municipio_ibge
                           ORDER BY valor_global DESC, fornecedor_cnpj
                       ) AS posicao
                FROM pncp_anual
            ) r
            WHERE a.ano = r.ano AND a.municipio_ibge = r.municipio_ibge
              AND a.fornecedor_cnpj = r.fornecedor_cnpj AND r.posicao > :maiores
            """
        ),
        {"maiores": maiores},
    ).rowcount
    session.commit()
    return antigas + excedentes
