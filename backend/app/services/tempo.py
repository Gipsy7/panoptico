"""Linha do tempo de um lugar (cidade ou estado): as séries anuais que já temos, no mesmo eixo de
anos, com quem governava em cada período. Alimenta "O que mudou", as perguntas e a aba "Ao longo
do tempo" (redesenho: combinação dos protótipos B e C).

Regras: dinheiro de anos diferentes vai em reais do último ano completo do IPCA (média anual do
índice); cada série diz quem responde pelo serviço (prefeitura, governo do estado) e a fonte; só
entram pontos que existem (nada é interpolado)."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ContasEstado, ContasMunicipio, IdebResultado, IpcaIndice, PibIbge
from app.services import resultados_eleicao, seguranca
from app.services.pib import CODIGO_UF

AREAS = (
    ("saude", "Saúde", "saude"),
    ("educacao", "Educação", "escolas"),
    ("seguranca", "Segurança Pública", "seguranca"),
)


def fatores_ipca(session: Session) -> tuple[int | None, dict[int, float]]:
    """(ano de referência, {ano: fator}) para levar valores do ano a reais do ano de referência,
    o último com os 12 meses do índice."""
    medias = {
        ano: (float(media), n)
        for ano, media, n in session.execute(
            select(IpcaIndice.ano, func.avg(IpcaIndice.indice), func.count()).group_by(
                IpcaIndice.ano
            )
        ).all()
    }
    completos = [a for a, (_, n) in medias.items() if n == 12]
    if not completos:
        return None, {}
    ref = max(completos)
    return ref, {a: medias[ref][0] / m for a, (m, _) in medias.items()}


def _real(valor: Decimal | float | None, ano: int, fat: dict[int, float]) -> float | None:
    if valor is None or ano not in fat:
        return None
    return float(valor) * fat[ano]


def _serie(id_, tema, rotulo, unidade, responsavel, pontos, fonte, nota=None, comparacoes=None,
           decimais=0) -> dict:  # fmt: skip
    return {
        "id": id_,
        "tema": tema,
        "rotulo": rotulo,
        "unidade": unidade,
        "responsavel": responsavel,
        "decimais": decimais,
        "pontos": [{"ano": a, "valor": v} for a, v in pontos if v is not None],
        "comparacoes": comparacoes or [],
        "fonte_nome": fonte,
        "nota": nota,
    }


def _gestoes(session: Session, cargo: str, uf: str | None, municipio: str | None) -> list[dict]:
    r = resultados_eleicao.antecessores(session, cargo, uf=uf, municipio=municipio)
    if not r:
        return []
    return [
        {
            "inicio": m["inicio"],
            "fim": m["fim"],
            "nome": ", ".join(p["nome"] for p in m["pessoas"]),
            "partido": ", ".join(p["partido"] or "" for p in m["pessoas"]),
        }
        for m in sorted(r["mandatos"], key=lambda m: m["inicio"])
        if m["pessoas"]
    ]


def _homicidios(session: Session, codigo: str, uf_codigo: str | None) -> list[dict]:
    lugar = seguranca._lugar(session, codigo)
    if not lugar["serie"]:
        return []
    comp = []
    if uf_codigo:
        est = seguranca._lugar(session, uf_codigo)
        comp.append({"rotulo": "estado", "pontos": [
            {"ano": p["ano"], "valor": p["por_100_mil"]} for p in est["serie"] if p["por_100_mil"]
        ]})  # fmt: skip
    br = seguranca._lugar(session, "1")
    comp.append({"rotulo": "Brasil", "pontos": [
        {"ano": p["ano"], "valor": p["por_100_mil"]} for p in br["serie"] if p["por_100_mil"]
    ]})  # fmt: skip
    fonte = seguranca.FONTE_NOME
    return [
        _serie("homicidios", "seguranca", "Homicídios de moradores", "por ano", "estado",
               [(p["ano"], p["homicidios"]) for p in lugar["serie"]], fonte,
               nota="Polícias e presídios são do governo do estado."),
        _serie("homicidios_taxa", "seguranca", "Homicídios por 100 mil moradores",
               "por 100 mil moradores", "estado",
               [(p["ano"], p["por_100_mil"]) for p in lugar["serie"]], fonte, comparacoes=comp,
               decimais=1, nota="Em cidade pequena, poucos casos mudam muito a taxa de um ano."),
    ]  # fmt: skip


def _ideb(session: Session, abrangencia: str, codigo: str, rede: str, responsavel: str) -> dict:
    def pontos(abr, cod):
        q = select(IdebResultado.ano, IdebResultado.valor).where(
            IdebResultado.abrangencia == abr,
            IdebResultado.etapa == "iniciais",
            IdebResultado.rede == rede,
        )
        if cod:
            q = q.where(IdebResultado.codigo == cod)
        return [
            {"ano": a, "valor": float(v)} for a, v in session.execute(q.order_by(IdebResultado.ano))
        ]

    rotulo_rede = {"municipal": "escolas da prefeitura", "publica": "escolas públicas"}[rede]
    principal = pontos(abrangencia, codigo)
    brasil = [{"rotulo": "Brasil", "pontos": pontos("brasil", None)}]
    return _serie("ideb", "escolas", f"IDEB, 1º ao 5º ano, {rotulo_rede}", "de 0 a 10",
                  responsavel, [(p["ano"], p["valor"]) for p in principal],
                  "INEP (IDEB)", comparacoes=brasil, decimais=1)  # fmt: skip


def _pib(session: Session, codigo: str, fat: dict[int, float], ref: int | None) -> dict:
    linhas = session.execute(
        select(PibIbge.ano, PibIbge.pib).where(PibIbge.codigo == codigo).order_by(PibIbge.ano)
    ).all()
    return _serie("pib", "economia", "PIB", f"R$ de {ref}", "—",
                  [(a, _real(v * 1000, a, fat)) for a, v in linhas], "IBGE (PIB dos Municípios)",
                  nota="Corrigido pela inflação (IPCA).")  # fmt: skip


def _gastos(contas, quem: str, rotulo_quem: str, fat, ref, fonte) -> list[dict]:
    series = []
    for id_, area, tema in AREAS:
        pontos = []
        for c in contas:
            valor = (c.despesa_por_area or {}).get(area)
            if valor is not None and c.populacao:
                pontos.append((c.ano, _real(valor / c.populacao, c.ano, fat)))
        series.append(_serie(f"gasto_{id_}_{quem}", tema,
                             f"{rotulo_quem}: gasto em {area.lower()} por morador",
                             f"R$ de {ref} por morador", quem, pontos, fonte,
                             nota="Despesa paga, corrigida pela inflação (IPCA)."))  # fmt: skip
    return series


def da_cidade(session: Session, ibge: str, uf: str) -> dict:
    ref, fat = fatores_ipca(session)
    uf_cod = CODIGO_UF.get(uf)
    contas = session.scalars(
        select(ContasMunicipio)
        .where(ContasMunicipio.municipio_ibge == ibge)
        .order_by(ContasMunicipio.ano)
    ).all()
    contas_uf = session.scalars(
        select(ContasEstado).where(ContasEstado.uf == uf).order_by(ContasEstado.ano)
    ).all()
    fonte = "Tesouro Nacional (SICONFI, contas anuais)"
    series = [
        *_homicidios(session, ibge, uf_cod),
        _ideb(session, "municipio", ibge, "municipal", "prefeitura"),
        _pib(session, ibge, fat, ref),
        *_gastos(contas, "prefeitura", "Prefeitura", fat, ref, fonte),
        *[s for s in _gastos(contas_uf, "estado", "Governo do estado", fat, ref, fonte)
          if s["id"] == "gasto_seguranca_estado"],
    ]  # fmt: skip
    return _resposta(ibge, uf, ref, series, {
        "prefeito": _gestoes(session, "PREFEITO", uf, ibge),
        "governador": _gestoes(session, "GOVERNADOR", uf, None),
    })  # fmt: skip


def do_estado(session: Session, uf: str) -> dict:
    ref, fat = fatores_ipca(session)
    codigo = CODIGO_UF[uf]
    contas = session.scalars(
        select(ContasEstado).where(ContasEstado.uf == uf).order_by(ContasEstado.ano)
    ).all()
    series = [
        *_homicidios(session, codigo, None),
        _ideb(session, "uf", uf, "publica", "estado e prefeituras"),
        _pib(session, codigo, fat, ref),
        *_gastos(contas, "estado", "Governo do estado", fat, ref,
                 "Tesouro Nacional (SICONFI, contas anuais)"),
    ]  # fmt: skip
    return _resposta(
        codigo, uf, ref, series, {"governador": _gestoes(session, "GOVERNADOR", uf, None)}
    )


def _resposta(codigo: str, uf: str, ref: int | None, series: list[dict], gestoes: dict) -> dict:
    series = [s for s in series if s["pontos"]]
    anos = sorted({p["ano"] for s in series for p in s["pontos"]})
    return {
        "codigo": codigo,
        "uf": uf,
        "ano_inicial": anos[0] if anos else None,
        "ano_final": anos[-1] if anos else None,
        "reais_de": ref,
        "series": series,
        "gestoes": gestoes,
    }
