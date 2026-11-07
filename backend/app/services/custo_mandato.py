"""Quanto custa o mandato de um deputado federal ou senador.

Os valores (salário, verba para assessores, limite da cota por UF e auxílio-moradia) são fixados
por ato da Mesa ou da Presidência, não por arquivo de dados. Ficam em
`data/custo_mandato_congresso.csv`, versionado (cópia empacotada em `app/dados/`, porque a imagem
da API não leva a pasta `data/`; um teste confere que as duas são iguais), com o ato, a data e o
link de cada número. Só entra valor que a própria Casa publica; sem ele, a linha fica sem valor e
a observação diz o que falta (e há pedido em docs/pedidos/).

"Usou de verdade" só onde o Panóptico tem o dado: o salário (igual para todos) e a cota (gastos
já carregados, média por mês do ano corrente). A média da Casa usa a mesma regra do resto do
site: parlamentares em exercício, quem não gastou entra com zero.
"""

import csv
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Despesa, FonteIngestao, Parlamentar, ResumoParlamentar
from app.services import gastos

CSV = Path(__file__).resolve().parents[1] / "dados" / "custo_mandato_congresso.csv"

CARGO = {"camara": "deputado_federal", "senado": "senador"}
ORDEM = ("subsidio", "verba_gabinete", "cota", "auxilio_moradia")
NOMES = {
    "subsidio": ("Salário", "Subsídio mensal, valor bruto"),
    "verba_gabinete": ("Verba para pagar assessores", "Verba de gabinete"),
    "cota": ("Gastos do gabinete", None),  # oficial depende da Casa e da UF
    "auxilio_moradia": (
        "Moradia em Brasília",
        "Auxílio-moradia, para quem não ocupa imóvel funcional",
    ),
}
COTA_OFICIAL = {
    "camara": "Cota para o Exercício da Atividade Parlamentar (CEAP)",
    "senado": "Cota para o Exercício da Atividade Parlamentar dos Senadores (CEAPS)",
}
SENADO_MORADIA_URL = (
    "https://www12.senado.leg.br/transparencia/sen/coapat/auxilio-moradia-e-imoveis-funcionais"
)


def _data(valor: str) -> date | None:
    return date.fromisoformat(valor) if valor else None


@lru_cache(maxsize=1)
def tabela() -> tuple[dict, ...]:
    with CSV.open(encoding="utf-8", newline="") as f:
        linhas = []
        for linha in csv.DictReader(f):
            linhas.append(
                {
                    **linha,
                    "uf": linha["uf"] or None,
                    "valor_mensal": Decimal(linha["valor_mensal"])
                    if linha["valor_mensal"]
                    else None,
                    "ato_data": _data(linha["ato_data"]),
                    "vigente_desde": _data(linha["vigente_desde"]),
                    "vigente_ate": _data(linha["vigente_ate"]),
                    "consultado_em": date.fromisoformat(linha["consultado_em"]),
                }
            )
        return tuple(linhas)


def vigente(cargo: str, item: str, uf: str | None = None, em: date | None = None) -> dict | None:
    """A linha do item que vale em `em` (hoje, por padrão). Sem início de vigência (valor sem
    ato ou não publicado), vale sempre; entre várias, a de início mais recente."""
    em = em or date.today()
    candidatas = [
        linha
        for linha in tabela()
        if linha["cargo"] == cargo
        and linha["item"] == item
        and linha["uf"] in (None, uf)
        and (linha["vigente_desde"] is None or linha["vigente_desde"] <= em)
        and (linha["vigente_ate"] is None or em <= linha["vigente_ate"])
    ]
    if not candidatas:
        return None
    return max(candidatas, key=lambda linha: linha["vigente_desde"] or date.min)


def _cota_usada(session: Session, p: Parlamentar) -> dict | None:
    """Média por mês da cota no ano mais recente com gastos da Casa, do parlamentar e da Casa.
    Lê o `resumo_parlamentar` (somas por ano); se a Casa não tiver resumo completo, recalcula."""
    anos_meses = gastos.anos_e_ultimo_mes(session, p.casa)
    if not anos_meses:
        return None
    ano = next(iter(anos_meses))
    meses = anos_meses[ano]
    total = session.scalar(
        select(ResumoParlamentar.gastos).where(
            ResumoParlamentar.parlamentar_id == p.id, ResumoParlamentar.ano == ano
        )
    )
    media = gastos._media_guardada(session, p.casa, ano)
    if total is None or media is None:
        total = session.scalar(
            select(func.coalesce(func.sum(Despesa.valor), 0)).where(
                Despesa.parlamentar_id == p.id, Despesa.ano == ano
            )
        )
        media = gastos.media_da_casa(session, p.casa, ano)
    fonte = gastos.FONTES[p.casa]
    atualizado: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte["fonte"], FonteIngestao.status == "ok"
        )
    )
    return {
        "ano": ano,
        "ultimo_mes": meses,
        "usou": (Decimal(total) / meses).quantize(Decimal("0.01")),
        "media": (Decimal(media) / meses).quantize(Decimal("0.01")),
        "fonte_nome": fonte["nome"],
        "fonte_url": fonte["url"],
        "atualizado_em": atualizado,
    }


def resumo(session: Session, p: Parlamentar, em: date | None = None) -> dict | None:
    cargo = CARGO.get(p.casa)
    if cargo is None:
        return None
    cota = _cota_usada(session, p)
    itens = []
    for item in ORDEM:
        linha = vigente(cargo, item, p.uf, em)
        if linha is None:
            continue
        nome, oficial = NOMES[item]
        if item == "cota":
            oficial = f"{COTA_OFICIAL[p.casa]}, limite de {p.uf}"
        valor = linha["valor_mensal"]
        usou = media = None
        usou_url = None
        if item == "subsidio":
            situacao, usou, media = "fixo", valor, valor
        elif item == "cota" and cota is not None:
            situacao, usou, media = "carregado", cota["usou"], cota["media"]
        elif valor is None:
            situacao = "nao_publicado"
        elif p.casa == "camara":
            # A Câmara mostra a verba usada e o auxílio na página do deputado, sem arquivo aberto.
            situacao, usou_url = "na_pagina_da_casa", p.pagina_url
        else:
            situacao = "nao_carregado"
            usou_url = SENADO_MORADIA_URL if item == "auxilio_moradia" else None
        itens.append(
            {
                "item": item,
                "nome": nome,
                "oficial": oficial,
                "valor": valor,
                "ato": linha["ato"] or None,
                "ato_data": linha["ato_data"],
                "ato_url": linha["ato_url"] or None,
                "valor_url": linha["valor_url"] or None,
                "vigente_desde": linha["vigente_desde"],
                "consultado_em": linha["consultado_em"],
                "observacao": linha["observacao"] or None,
                "usou": usou,
                "media_casa": media,
                "usou_situacao": situacao,
                "usou_url": usou_url,
            }
        )
    com_valor = [i for i in itens if i["valor"] is not None]
    medidos = [i for i in itens if i["usou"] is not None]
    return {
        "itens": itens,
        "total_se_usar_tudo": sum((i["valor"] for i in com_valor), Decimal(0)),
        "faltando": [i["nome"] for i in itens if i["valor"] is None],
        "usou_total": sum((i["usou"] for i in medidos), Decimal(0)),
        "media_total": sum((i["media_casa"] for i in medidos), Decimal(0)),
        "medidos": [i["nome"] for i in medidos],
        "ano": cota["ano"] if cota else None,
        "ultimo_mes": cota["ultimo_mes"] if cota else None,
        "gastos_fonte_nome": cota["fonte_nome"] if cota else None,
        "gastos_fonte_url": cota["fonte_url"] if cota else None,
        "gastos_atualizado_em": cota["atualizado_em"] if cota else None,
    }
