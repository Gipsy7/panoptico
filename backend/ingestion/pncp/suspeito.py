"""Valor de contrato do PNCP que parece digitado errado (docs/DECISOES.md, "PNCP: valores
suspeitos").

O PNCP aceita o que o órgão digita: há `valorGlobal` em centavos, com dígitos a mais ou
"999999999999". Medido no acervo (2025 a 10/2026), 82 grupos municipais acima de R$ 1 bilhão
somavam R$ 10,2 trilhões dos R$ 10,7 trilhões de órgãos municipais.

Regra (objetiva, sem "corrigir" nada): o valor é suspeito quando passa do menor entre
- a despesa paga anual da prefeitura (SICONFI, `contas_municipio`, ano mais recente), para
  órgão municipal com contas conhecidas: um contrato maior que tudo que o município paga num
  ano inteiro não é plausível; e
- o teto absoluto de R$ 50 bilhões, que vale para qualquer esfera e para município sem contas.

Contrato suspeito fica fora das somas e do ranking, é guardado à parte (`pncp_suspeito`, ou
`pncp_contrato.valor_suspeito`) e aparece com o aviso "valor informado ao PNCP parece
incorreto; conferir na fonte". O valor original nunca é alterado.
"""

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

TETO_ABSOLUTO = Decimal("50000000000")  # R$ 50 bilhões
AVISO = "valor informado ao PNCP parece incorreto; conferir na fonte"

Limites = dict[str, Decimal]  # município (IBGE) -> despesa paga anual


def carregar_limites(session: Session) -> Limites:
    """Despesa paga anual (SICONFI, ano mais recente com valor) de cada município."""
    linhas = session.execute(
        text(
            """
            SELECT DISTINCT ON (municipio_ibge) municipio_ibge, despesa_paga
            FROM contas_municipio WHERE despesa_paga > 0
            ORDER BY municipio_ibge, ano DESC
            """
        )
    )
    return {ibge: Decimal(valor) for ibge, valor in linhas}


def limite(esfera: str | None, ibge: str | None, limites: Limites | None) -> Decimal:
    """Maior valor plausível para um contrato do órgão (esfera M usa as contas do município)."""
    despesa = (limites or {}).get(ibge or "") if esfera == "M" else None
    return min(despesa, TETO_ABSOLUTO) if despesa else TETO_ABSOLUTO


def eh_suspeito(
    valor: Decimal | None, esfera: str | None, ibge: str | None, limites: Limites | None
) -> bool:
    return valor is not None and valor > limite(esfera, ibge, limites)
