"""Dinheiro federal: o que a União arrecada em cada estado e o que repassa a estados e cidades."""

from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ArrecadacaoUF,
    ContasMunicipio,
    FonteIngestao,
    Municipio,
    PopulacaoIbge,
    TransferenciaUniao,
)
from app.services.representantes import UFS

ANO_INICIAL = 2019
ANO_PADRAO = 2025
BLOCOS = [
    "FPE",
    "FPM",
    "FUNDEB_UNIAO",
    "LEGAIS_VOLUNTARIAS",
    "ROYALTIES",
    "IPI_EXP",
    "OUTRAS_OBRIG",
]
MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]  # fmt: skip

CODIGO_UF = {
    "AC": "12", "AL": "27", "AP": "16", "AM": "13", "BA": "29", "CE": "23", "DF": "53",
    "ES": "32", "GO": "52", "MA": "21", "MT": "51", "MS": "50", "MG": "31", "PA": "15",
    "PB": "25", "PR": "41", "PE": "26", "PI": "22", "RJ": "33", "RN": "24", "RS": "43",
    "RO": "11", "RR": "14", "SC": "42", "SP": "35", "SE": "28", "TO": "17",
}  # fmt: skip
REGIAO = {
    **dict.fromkeys(["AC", "AM", "AP", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MS", "MT"], "Centro-Oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
}

_TESOURO_URL = (
    "https://www.tesourotransparente.gov.br/temas/estados-e-municipios/"
    "transferencias-obrigatorias-da-uniao-para-estados-e-municipios"
)
FONTES = {
    "receita_arrecadacao_uf": (
        "Arrecadação por estado (Receita Federal)",
        "https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/receitadata/arrecadacao",
    ),
    "tesouro_transferencias": (
        "Transferências obrigatórias da União (Tesouro Transparente)",
        _TESOURO_URL,
    ),
    "portal_transferencias": (
        "Transferências de recursos (Portal da Transparência)",
        "https://portaldatransparencia.gov.br/transferencias",
    ),
    "ibge_populacao": (
        "População residente (IBGE, SIDRA 6579 e Censo 2022)",
        "https://sidra.ibge.gov.br/tabela/6579",
    ),
}
FONTE_CONTAS = (
    "Declaração de Contas Anuais (SICONFI, Tesouro Nacional)",
    "https://siconfi.tesouro.gov.br/",
)
AVISO_DF = (
    "Entre fevereiro de 2025 e janeiro de 2026 a Receita Federal registrou no Distrito Federal "
    "parte da arrecadação de contribuintes de outros estados; a comparação entre estados em "
    "2025 fica afetada."
)


def _f(v) -> float | None:
    return None if v is None else float(v)


def anos_disponiveis() -> list[int]:
    return list(range(ANO_INICIAL, date.today().year + 1))


def _fontes(session: Session, chaves: list[str]) -> list[dict]:
    ultimas = dict(
        session.execute(
            select(FonteIngestao.fonte, func.max(FonteIngestao.concluido_em))
            .where(FonteIngestao.status == "ok", FonteIngestao.fonte.in_(chaves))
            .group_by(FonteIngestao.fonte)
        ).all()
    )
    return [
        {"nome": FONTES[c][0], "url": FONTES[c][1], "atualizado_em": ultimas.get(c)} for c in chaves
    ]


def _populacoes(session: Session, ano: int, filtro) -> dict[str, tuple[int, int, str]]:
    """codigo -> (valor, ano, origem), do ano pedido ou do mais recente anterior."""
    resultado: dict[str, tuple[int, int, str]] = {}
    linhas = session.execute(
        select(PopulacaoIbge.codigo, PopulacaoIbge.ano, PopulacaoIbge.valor, PopulacaoIbge.origem)
        .where(PopulacaoIbge.ano <= ano, filtro)
        .order_by(PopulacaoIbge.ano)
    )
    for codigo, a, valor, origem in linhas:
        resultado[codigo] = (valor, a, origem)  # ordem crescente: o último é o mais recente
    return resultado


def _totais(
    pop: tuple[int, int, str] | None, arrecadacao: tuple | None, blocos: dict[str, float]
) -> dict:
    presentes = [blocos[b] for b in BLOCOS if b in blocos]
    return {
        "populacao": pop[0] if pop else None,
        "populacao_ano": pop[1] if pop else None,
        "populacao_origem": pop[2] if pop else None,
        "arrecadacao": _f(arrecadacao[0]) if arrecadacao else None,
        "previdencia": _f(arrecadacao[1]) if arrecadacao else None,
        "repasse": round(sum(presentes), 2) if presentes else None,
        "blocos": {b: blocos.get(b) for b in BLOCOS},
        "blocos_sem_dado": [b for b in BLOCOS if b not in blocos],
    }


def _mes_limite(session: Session, ano: int) -> tuple[int | None, list[tuple[str, int]]]:
    """No ano em curso, as fontes param em meses diferentes: só se soma até o último mês que
    todas já publicaram. Devolve (limite, [(rotulo, ultimo_mes)]); anos fechados: (None, [])."""
    if ano != date.today().year:
        return None, []
    candidatos = [
        ("arrecadação", select(func.max(ArrecadacaoUF.mes)).where(ArrecadacaoUF.ano == ano)),
        (
            "Tesouro",
            select(func.max(TransferenciaUniao.mes)).where(
                TransferenciaUniao.ano == ano, TransferenciaUniao.fonte == "tesouro"
            ),
        ),
        (
            "Portal",
            select(func.max(TransferenciaUniao.mes)).where(
                TransferenciaUniao.ano == ano, TransferenciaUniao.fonte == "portal"
            ),
        ),
    ]
    maximos = [(r, m) for r, q in candidatos if (m := session.scalar(q)) is not None]
    if not maximos:
        return None, []
    return min(m for _, m in maximos), maximos


def _filtro_mes(coluna_ano, coluna_mes, ano: int, limite: int | None):
    return coluna_ano == ano if limite is None else (coluna_ano == ano) & (coluna_mes <= limite)


def _contexto_ano(session: Session, ano: int, limite: int | None, maximos: list) -> dict:
    if limite is not None:
        ordenados = list(range(1, limite + 1))
    else:
        meses = set(
            session.scalars(select(ArrecadacaoUF.mes).where(ArrecadacaoUF.ano == ano).distinct())
        ) | set(
            session.scalars(
                select(TransferenciaUniao.mes).where(TransferenciaUniao.ano == ano).distinct()
            )
        )
        ordenados = sorted(meses)
    em_curso = ano == date.today().year
    avisos = []
    if ano in (2025, 2026):
        avisos.append(AVISO_DF)
    if em_curso and ordenados:
        fim = MESES[ordenados[-1] - 1]
        if limite is not None and len({m for _, m in maximos}) > 1:
            detalhe = ", ".join(f"{r} até {MESES[m - 1]}" for r, m in maximos)
            avisos.append(
                f"Ano em curso: soma de janeiro a {fim}, último mês publicado em todas as "
                f"fontes ({detalhe})."
            )
        else:
            avisos.append(f"Ano em curso: soma de janeiro a {fim}.")
    return {
        "ano": ano,
        "anos_disponiveis": anos_disponiveis(),
        "meses_com_dado": ordenados,
        "ano_em_curso": em_curso,
        "avisos": avisos,
        "sem_dados": not ordenados,
    }


def _blocos_por_uf(
    session: Session, ano: int, uf: str | None = None, limite: int | None = None
) -> dict[str, dict[str, float]]:
    consulta = select(
        TransferenciaUniao.uf, TransferenciaUniao.bloco, func.sum(TransferenciaUniao.valor)
    ).where(_filtro_mes(TransferenciaUniao.ano, TransferenciaUniao.mes, ano, limite))
    if uf:
        consulta = consulta.where(TransferenciaUniao.uf == uf)
    por_uf: dict[str, dict[str, float]] = defaultdict(dict)
    for u, bloco, soma in session.execute(
        consulta.group_by(TransferenciaUniao.uf, TransferenciaUniao.bloco)
    ):
        por_uf[u][bloco] = float(soma)
    return por_uf


def _arrecadacao_por_uf(session: Session, ano: int, limite: int | None = None) -> dict[str, tuple]:
    return {
        u: (total, prev)
        for u, total, prev in session.execute(
            select(
                ArrecadacaoUF.uf, func.sum(ArrecadacaoUF.total), func.sum(ArrecadacaoUF.previdencia)
            )
            .where(_filtro_mes(ArrecadacaoUF.ano, ArrecadacaoUF.mes, ano, limite))
            .group_by(ArrecadacaoUF.uf)
        )
    }


SEM_UF = "ND"  # valor que o Portal não regionaliza: soma no Brasil, nunca vira estado


def _soma_ou_none(valores) -> float | None:
    v = [float(x) for x in valores if x is not None]
    return round(sum(v), 2) if v else None


def painel(session: Session, ano: int) -> dict:
    limite, maximos = _mes_limite(session, ano)
    blocos_uf = _blocos_por_uf(session, ano, limite=limite)
    arrec = _arrecadacao_por_uf(session, ano, limite)
    pops = _populacoes(session, ano, func.length(PopulacaoIbge.codigo) <= 2)
    brasil_arrec = (
        (_soma_ou_none(a[0] for a in arrec.values()), _soma_ou_none(a[1] for a in arrec.values()))
        if arrec
        else None
    )
    soma_blocos: dict[str, float] = {}
    for d in blocos_uf.values():
        for b, v in d.items():
            soma_blocos[b] = soma_blocos.get(b, 0.0) + v
    ufs = [
        {
            "uf": uf,
            "nome": nome,
            "regiao": REGIAO[uf],
            **_totais(pops.get(CODIGO_UF[uf]), arrec.get(uf), blocos_uf.get(uf, {})),
        }
        for uf, nome in sorted(UFS.items(), key=lambda kv: kv[1])
    ]
    return {
        **_contexto_ano(session, ano, limite, maximos),
        "brasil": {
            **_totais(pops.get("1"), brasil_arrec, soma_blocos),
            "sem_estado": _soma_ou_none(blocos_uf.get(SEM_UF, {}).values()),
        },
        "ufs": ufs,
        "fontes": _fontes(session, list(FONTES)),
    }


def _municipal_por_cidade(
    session: Session, uf: str, ano: int | None = None, corte: tuple[int, int] | None = None
):
    """(ibge, ano) -> {bloco: soma}: uma consulta agregada para todas as cidades do estado."""
    consulta = select(
        TransferenciaUniao.municipio_ibge,
        TransferenciaUniao.ano,
        TransferenciaUniao.bloco,
        func.sum(TransferenciaUniao.valor),
    ).where(TransferenciaUniao.uf == uf, TransferenciaUniao.municipio_ibge.is_not(None))
    if ano is not None:
        consulta = consulta.where(TransferenciaUniao.ano == ano)
    if corte is not None:  # (ano em curso, último mês comum a todas as fontes)
        consulta = consulta.where(
            (TransferenciaUniao.ano != corte[0]) | (TransferenciaUniao.mes <= corte[1])
        )
    dados: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
    for ibge, a, bloco, soma in session.execute(
        consulta.group_by(
            TransferenciaUniao.municipio_ibge, TransferenciaUniao.ano, TransferenciaUniao.bloco
        )
    ):
        dados[(ibge, a)][bloco] = float(soma)
    return dados


def _repasse_fpm_outros(blocos: dict[str, float]) -> tuple[float, float, float]:
    total = sum(blocos.values())
    fpm = blocos.get("FPM", 0.0)
    return round(total, 2), round(fpm, 2), round(total - fpm, 2)


def estado(session: Session, uf: str, ano: int) -> dict | None:
    if uf not in UFS:
        return None
    codigo = CODIGO_UF[uf]
    limite, maximos = _mes_limite(session, ano)
    blocos_uf = _blocos_por_uf(session, ano, uf, limite)
    arrec = _arrecadacao_por_uf(session, ano, limite).get(uf)
    pop_uf = _populacoes(session, ano, PopulacaoIbge.codigo == codigo).get(codigo)
    municipios = session.execute(
        select(Municipio.ibge, Municipio.nome)
        .where(Municipio.uf == uf)
        .order_by(Municipio.nome_chave)
    ).all()
    pops = _populacoes(session, ano, PopulacaoIbge.codigo.like(codigo + "_____"))
    dados = _municipal_por_cidade(session, uf, ano, (ano, limite) if limite else None)
    cidades = []
    soma_repasse = soma_pop = 0.0
    for ibge, nome in municipios:
        blocos = dados.get((ibge, ano))
        pop = pops.get(ibge)
        repasse = fpm = outros = None
        if blocos:
            repasse, fpm, outros = _repasse_fpm_outros(blocos)
            if pop:
                soma_repasse += repasse
                soma_pop += pop[0]
        cidades.append(
            {
                "ibge": ibge,
                "nome": nome,
                "populacao": pop[0] if pop else None,
                "repasse": repasse,
                "fpm": fpm,
                "outros": outros,
            }
        )
    return {
        **_contexto_ano(session, ano, limite, maximos),
        "uf": uf,
        "nome": UFS[uf],
        "regiao": REGIAO[uf],
        **_totais(pop_uf, arrec, blocos_uf.get(uf, {})),
        "cidades": cidades,
        "media_estado_por_habitante": round(soma_repasse / soma_pop, 2) if soma_pop else None,
        "fontes": _fontes(session, list(FONTES)),
    }


def municipio(session: Session, mun: Municipio) -> dict:
    hoje = date.today().year
    limite, _ = _mes_limite(session, hoje)
    dados = _municipal_por_cidade(session, mun.uf, corte=(hoje, limite) if limite else None)
    pops_linhas = session.execute(
        select(PopulacaoIbge.codigo, PopulacaoIbge.ano, PopulacaoIbge.valor).where(
            PopulacaoIbge.codigo.like(CODIGO_UF[mun.uf] + "_____")
        )
    ).all()
    por_cidade: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for codigo, a, valor in pops_linhas:
        por_cidade[codigo].append((a, valor))

    def pop_de(ibge: str, ano: int) -> int | None:
        validos = [(a, v) for a, v in por_cidade.get(ibge, []) if a <= ano]
        return max(validos)[1] if validos else None

    serie = []
    for ano in sorted({a for (i, a) in dados if i == mun.ibge}):
        soma_repasse = soma_pop = 0.0
        for (ibge, a), blocos in dados.items():
            pop = pop_de(ibge, ano) if a == ano else None
            if pop:
                soma_repasse += sum(blocos.values())
                soma_pop += pop
        repasse, fpm, outros = _repasse_fpm_outros(dados[(mun.ibge, ano)])
        pop = pop_de(mun.ibge, ano)
        serie.append(
            {
                "ano": ano,
                "repasse": repasse,
                "fpm": fpm,
                "outros": outros,
                "populacao": pop,
                "por_habitante": round(repasse / pop, 2) if pop else None,
                "media_estado_por_habitante": round(soma_repasse / soma_pop, 2)
                if soma_pop
                else None,
            }
        )
    c = session.scalar(
        select(ContasMunicipio)
        .where(
            ContasMunicipio.municipio_ibge == mun.ibge, ContasMunicipio.receita_total.is_not(None)
        )
        .order_by(ContasMunicipio.ano.desc())
        .limit(1)
    )
    contas = None
    fontes = _fontes(session, ["tesouro_transferencias", "portal_transferencias", "ibge_populacao"])
    if c is not None:
        total = float(c.receita_total)

        def parte(v) -> float | None:
            return round(100 * float(v) / total, 1) if v is not None and total else None

        contas = {
            "ano": c.ano,
            "receita_total": total,
            "receita_propria": _f(c.receita_propria),
            "transf_uniao": _f(c.transf_uniao),
            "parte_uniao": parte(c.transf_uniao),
            "parte_propria": parte(c.receita_propria),
        }
        ate: datetime | None = session.scalar(
            select(func.max(FonteIngestao.concluido_em)).where(
                FonteIngestao.fonte == "siconfi_contas", FonteIngestao.status == "ok"
            )
        )
        fontes.append({"nome": FONTE_CONTAS[0], "url": FONTE_CONTAS[1], "atualizado_em": ate})
    return {
        "municipio": {"ibge": mun.ibge, "nome": mun.nome, "uf": mun.uf},
        "serie": serie,
        "sem_dados": not serie,
        "contas": contas,
        "fontes": fontes,
    }
