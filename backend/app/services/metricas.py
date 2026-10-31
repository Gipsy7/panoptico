"""Contagem anônima de acessos: validação, gravação e resumo para o painel privado.

Regras (docs/DECISOES.md, 2026-10-31): só totais por dia; nada de IP, user-agent, identificador
ou hora; só valores de listas fechadas ou caminhos de rotas que existem no site. O servidor nunca
confia no navegador: tudo que chega é validado aqui e o que foge do formato é ignorado.
"""

import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.metrica import MetricaDiaria

ORIGENS = ("direto", "whatsapp", "google", "buscadores", "redes", "outro_site")
DISPOSITIVOS = ("celular", "computador")
RECURSOS = ("cep", "localizacao", "argos", "compartilhar", "pix")

MAX_CAMINHO = 120
CHAVE_VISITA = "total"

# Brasília não tem horário de verão desde 2019: o "dia" da contagem é o dia de lá.
FUSO = timezone(timedelta(hours=-3))

_ROBO = re.compile(r"bot|crawl|spider|headless|slurp|facebookexternalhit|preview|monitor", re.I)
_FORMATO = re.compile(r"^/[a-z0-9/_-]*$")

# Rotas fixas do site (app/ do frontend). Qualquer outra é descartada: a tabela não cresce com
# endereços inventados.
_FIXAS = frozenset(
    {
        "/",
        "/parlamentares",
        "/projetos",
        "/partidos",
        "/impostos-e-repasses",
        "/segundo-turno",
        "/comparar",
        "/comparar/local",
        "/sobre-as-fontes",
        "/sobre-as-fontes/cobertura",
        "/status",
        "/privacidade",
        "/acessibilidade",
        "/apoie",
        "/apoiadores",
        "/o-panoptico",
        "/perguntas",
        "/pergunte",
        "/representantes",
    }
)
# Rotas dinâmicas. Mantém o id só onde ele é de coisa pública e curta (deputado/senador federal
# com até 7 dígitos, município com 7 dígitos do IBGE, sigla de partido): mostra "quem mais se
# vê". Um CEP tem 8 dígitos e nunca passa por aqui. As demais viram um modelo ("/eleito/[id]"),
# pois têm ids longos ou numerosos e o que interessa é o tipo de página.
_ID_MANTIDO = (
    re.compile(r"^/parlamentar/\d{1,7}$"),
    re.compile(r"^/cidade/\d{7}$"),
    re.compile(r"^/partidos/[a-z-]{2,15}$"),
)
_MODELOS = (
    (re.compile(r"^/(eleito|vereador|deputado-estadual)/[^/]+$"), "/{0}/[id]"),
    (re.compile(r"^/(projeto|votacao)/[^/]+/[^/]+$"), "/{0}/[id]"),
    (re.compile(r"^/(impostos-e-repasses)/.+$"), "/{0}/[lugar]"),
)


def eh_robo(user_agent: str | None) -> bool:
    """Sem user-agent ou com cara de robô: não conta (o user-agent não é gravado)."""
    return not user_agent or bool(_ROBO.search(user_agent))


def limpar_caminho(bruto: object) -> str | None:
    """Devolve o caminho normalizado ou None se não deve ser contado. Aceita só o path:
    com query, fragmento, tamanho excessivo, caracteres fora do formato ou rota desconhecida,
    descarta (nunca tenta "consertar", para não guardar um CEP por acidente)."""
    if not isinstance(bruto, str) or not bruto or len(bruto) > MAX_CAMINHO:
        return None
    caminho = bruto.lower()
    if len(caminho) > 1:
        caminho = caminho.rstrip("/")
    if not _FORMATO.match(caminho):
        return None
    if caminho in _FIXAS:
        return caminho
    if any(p.match(caminho) for p in _ID_MANTIDO):
        return caminho
    for padrao, modelo in _MODELOS:
        achou = padrao.match(caminho)
        if achou:
            return modelo.format(achou.group(1))
    return None


def hoje() -> date:
    return datetime.now(FUSO).date()


def _somar(session: Session, dia: date, tipo: str, chave: str) -> None:
    stmt = insert(MetricaDiaria).values(dia=dia, tipo=tipo, chave=chave, total=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=["dia", "tipo", "chave"],
        set_={"total": MetricaDiaria.total + 1},
    )
    session.execute(stmt)


def registrar_visita(session: Session, corpo: object) -> bool:
    """Conta uma página vista. Se `nova` (primeira página da visita no navegador), conta também a
    visita, a origem e o dispositivo. Devolve False se o corpo não passou na validação."""
    if not isinstance(corpo, dict):
        return False
    caminho = limpar_caminho(corpo.get("caminho"))
    if caminho is None:
        return False
    nova = corpo.get("nova") is True
    origem = corpo.get("origem")
    dispositivo = corpo.get("dispositivo")
    if nova and (origem not in ORIGENS or dispositivo not in DISPOSITIVOS):
        return False
    dia = hoje()
    _somar(session, dia, "pagina", caminho)
    if nova:
        _somar(session, dia, "visita", CHAVE_VISITA)
        _somar(session, dia, "origem", origem)
        _somar(session, dia, "dispositivo", dispositivo)
    session.commit()
    return True


def registrar_recurso(session: Session, corpo: object) -> bool:
    if not isinstance(corpo, dict) or corpo.get("recurso") not in RECURSOS:
        return False
    _somar(session, hoje(), "recurso", corpo["recurso"])
    session.commit()
    return True


# ---------- Resumo para o painel ----------


def _soma_por_dia(session: Session, tipo: str, desde: date) -> dict[date, int]:
    linhas = session.execute(
        select(MetricaDiaria.dia, func.sum(MetricaDiaria.total))
        .where(MetricaDiaria.tipo == tipo, MetricaDiaria.dia >= desde)
        .group_by(MetricaDiaria.dia)
    ).all()
    return {d: int(t) for d, t in linhas}


def _ranking(session: Session, tipo: str, desde: date, limite: int) -> list[dict]:
    soma = func.sum(MetricaDiaria.total)
    linhas = session.execute(
        select(MetricaDiaria.chave, soma)
        .where(MetricaDiaria.tipo == tipo, MetricaDiaria.dia >= desde)
        .group_by(MetricaDiaria.chave)
        .order_by(soma.desc(), MetricaDiaria.chave)
        .limit(limite)
    ).all()
    return [{"chave": c, "total": int(t)} for c, t in linhas]


def resumo(session: Session, dias: int = 30) -> dict:
    """Totais agregados; nenhum dado individual existe para ser devolvido."""
    dias = max(1, min(dias, 90))
    fim = hoje()
    desde = fim - timedelta(days=dias - 1)
    desde_30 = fim - timedelta(days=29)
    visitas = _soma_por_dia(session, "visita", min(desde, desde_30))
    paginas = _soma_por_dia(session, "pagina", min(desde, desde_30))

    def janela(serie: dict[date, int], n: int) -> int:
        inicio = fim - timedelta(days=n - 1)
        return sum(t for d, t in serie.items() if d >= inicio)

    inicio_contagem = session.scalar(select(func.min(MetricaDiaria.dia)))
    return {
        "hoje": hoje().isoformat(),
        "inicio_da_contagem": inicio_contagem.isoformat() if inicio_contagem else None,
        "periodos": [
            {
                "rotulo": rotulo,
                "dias": n,
                "visitas": janela(visitas, n),
                "paginas_vistas": janela(paginas, n),
            }
            for rotulo, n in (("Hoje", 1), ("Últimos 7 dias", 7), ("Últimos 30 dias", 30))
        ],
        "por_dia": [
            {
                "dia": (d := desde + timedelta(days=i)).isoformat(),
                "visitas": visitas.get(d, 0),
                "paginas_vistas": paginas.get(d, 0),
            }
            for i in range(dias)
        ],
        "dias_do_recorte": dias,
        "paginas": _ranking(session, "pagina", desde, 15),
        "recursos": _ranking(session, "recurso", desde, len(RECURSOS)),
        "origens": _ranking(session, "origem", desde, len(ORIGENS)),
        "dispositivos": _ranking(session, "dispositivo", desde, len(DISPOSITIVOS)),
    }
