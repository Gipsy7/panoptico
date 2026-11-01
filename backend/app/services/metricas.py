"""Contagem anônima de acessos: validação, gravação e resumo para o painel privado.

Regras (docs/DECISOES.md, 2026-10-31): só totais por dia, aparelho e categoria de origem; nada de
IP, user-agent, identificador ou hora; só valores de listas fechadas, ids de formato estrito ou
caminhos de rotas que existem no site. O servidor nunca confia no navegador: tudo que chega é
validado aqui e o que foge do formato é ignorado. O CEP nunca é lido, nem quando vem num campo
inesperado: só os campos conhecidos são extraídos do corpo.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.camara_municipal import MandatoLocal, ProjetoLocal
from app.models.candidatura import Candidatura
from app.models.metrica import MetricaDiaria as M
from app.models.municipio import Municipio
from app.models.parlamentar import Parlamentar
from app.models.proposicao import Proposicao

ORIGENS = ("direto", "whatsapp", "google", "buscadores", "redes", "outro_site")
APARELHOS = ("celular", "computador")
RECURSOS = ("cep", "localizacao", "argos", "compartilhar", "pix")
FORMAS_BUSCA = ("cep", "cidade", "estado")
# Seções do perfil, pelos ids dos títulos (`<h2 id="gastos-titulo">`) nos componentes do site.
SECOES = (
    "gastos",
    "presenca",
    "projetos",
    "votos",
    "votos-tema",
    "remuneracao",
    "sancoes",
    "fornecedores",
    "fornecedores-pncp",
    "contratos-socio",
    "comissoes",
    "carreira",
    "canais",
    "candidatura",
    "temas",
    "linha-do-tempo",
    "servico-federal",
    "emendas-relator",
    "destino-emendas",
    "contas",
    "executivo",
)
REGIOES = {
    "Norte": ("AC", "AM", "AP", "PA", "RO", "RR", "TO"),
    "Nordeste": ("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"),
    "Centro-Oeste": ("DF", "GO", "MS", "MT"),
    "Sudeste": ("ES", "MG", "RJ", "SP"),
    "Sul": ("PR", "RS", "SC"),
}
UFS = frozenset(uf for ufs in REGIOES.values() for uf in ufs)
REGIAO_DA_UF = {uf: regiao for regiao, ufs in REGIOES.items() for uf in ufs}

MAX_CAMINHO = 120
CHAVE_VISITA = "total"
# Cidade só aparece no painel a partir deste total de buscas no período.
MIN_BUSCAS_CIDADE = 5
MAX_PERFIS = 150

# Brasília não tem horário de verão desde 2019: o "dia" da contagem é o dia de lá.
FUSO = timezone(timedelta(hours=-3))

_ROBO = re.compile(r"bot|crawl|spider|headless|slurp|facebookexternalhit|preview|monitor", re.I)
_FORMATO = re.compile(r"^/[a-z0-9/_-]*$")
_ID = r"\d{1,7}"  # um CEP tem 8 dígitos: nunca passa como id

# Rotas fixas do site (app/ do frontend). Qualquer outra é descartada: a tabela não cresce com
# endereços inventados. Conferido contra frontend/app em 31/10/2026.
FIXAS = (
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
    "/avisos",
)
_FIXAS = frozenset(FIXAS)
# Páginas que explicam o site ou pedem apoio: não entram nas "menos vistas" nem nas "sem visita".
FIXAS_SEM_CONTEUDO = frozenset(
    {"/", "/status", "/privacidade", "/acessibilidade", "/apoie", "/apoiadores", "/avisos"}
)

# Rotas com id: (expressão, modelo gravado em `pagina`, tipo do perfil ou None). O id só vai para
# `perfil` (e a sigla para `partido`), com formato estrito; a página vira o modelo.
_PERFIS = (
    (re.compile(rf"^/parlamentar/({_ID})$"), "/parlamentar/[id]", "parlamentar"),
    (re.compile(rf"^/eleito/({_ID})$"), "/eleito/[id]", "eleito"),
    (re.compile(rf"^/vereador/({_ID})$"), "/vereador/[id]", "vereador"),
    (re.compile(rf"^/deputado-estadual/({_ID})$"), "/deputado-estadual/[id]", "deputado-estadual"),
    (re.compile(rf"^/projeto/(camara|senado)/({_ID})$"), "/projeto/[id]", "projeto-"),
    (re.compile(rf"^/projeto/local/({_ID})$"), "/projeto/[id]", "projeto-local"),
)
_PARTIDO = re.compile(r"^/partidos/([a-z-]{2,15})$")
_MODELOS = (
    (re.compile(r"^/cidade/\d{7}$"), "/cidade/[ibge]"),
    (re.compile(r"^/(eleito|vereador|deputado-estadual)/[^/]+$"), "/{0}/[id]"),
    (re.compile(r"^/(projeto|votacao)/[^/]+/[^/]+$"), "/{0}/[id]"),
    (re.compile(r"^/(impostos-e-repasses)/.+$"), "/{0}/[lugar]"),
)
MODELOS_DE_PAGINA = frozenset(
    {
        "/parlamentar/[id]",
        "/cidade/[ibge]",
        "/partidos/[sigla]",
        "/eleito/[id]",
        "/vereador/[id]",
        "/deputado-estadual/[id]",
        "/projeto/[id]",
        "/votacao/[id]",
        "/impostos-e-repasses/[lugar]",
    }
)


@dataclass(frozen=True)
class Caminho:
    modelo: str  # o que vai em `pagina`
    perfil: str | None = None  # "parlamentar:204554", só para ids de formato estrito
    partido: str | None = None


def eh_robo(user_agent: str | None) -> bool:
    """Sem user-agent ou com cara de robô: não conta (o user-agent não é gravado)."""
    return not user_agent or bool(_ROBO.search(user_agent))


def analisar_caminho(bruto: object) -> Caminho | None:
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
        return Caminho(caminho)
    for padrao, modelo, tipo in _PERFIS:
        achou = padrao.match(caminho)
        if achou:
            ident = achou.group(achou.lastindex)
            kind = tipo + achou.group(1) if tipo == "projeto-" else tipo
            return Caminho(modelo, perfil=f"{kind}:{ident}")
    achou = _PARTIDO.match(caminho)
    if achou:
        return Caminho("/partidos/[sigla]", partido=achou.group(1))
    for padrao, modelo in _MODELOS:
        achou = padrao.match(caminho)
        if achou:
            return Caminho(modelo.format(achou.group(1)) if "{0}" in modelo else modelo)
    return None


def limpar_caminho(bruto: object) -> str | None:
    """Só o modelo da página (o que vai em `pagina`)."""
    caminho = analisar_caminho(bruto)
    return caminho.modelo if caminho else None


def hoje() -> date:
    return datetime.now(FUSO).date()


Dims = tuple[str, str]  # (aparelho, origem)


def _dims(corpo: dict) -> Dims | None:
    aparelho, origem = corpo.get("aparelho"), corpo.get("origem")
    if aparelho in APARELHOS and origem in ORIGENS:
        return aparelho, origem
    return None


def _somar(session: Session, dia: date, tipo: str, chave: str, dims: Dims) -> None:
    stmt = insert(M).values(
        dia=dia, tipo=tipo, chave=chave, aparelho=dims[0], origem=dims[1], total=1
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["dia", "tipo", "chave", "aparelho", "origem"],
        set_={"total": M.total + 1},
    )
    session.execute(stmt)


def registrar_visita(session: Session, corpo: object) -> bool:
    """Conta uma página vista. Se `nova` (primeira página da visita no navegador), conta também a
    visita e a página de entrada. Devolve False se o corpo não passou na validação."""
    if not isinstance(corpo, dict):
        return False
    caminho = analisar_caminho(corpo.get("caminho"))
    dims = _dims(corpo)
    if caminho is None or dims is None:
        return False
    dia = hoje()
    _somar(session, dia, "pagina", caminho.modelo, dims)
    if caminho.perfil:
        _somar(session, dia, "perfil", caminho.perfil, dims)
    if caminho.partido:
        _somar(session, dia, "partido", caminho.partido, dims)
    if corpo.get("nova") is True:
        _somar(session, dia, "visita", CHAVE_VISITA, dims)
        _somar(session, dia, "entrada", caminho.modelo, dims)
    session.commit()
    return True


def registrar_saida(session: Session, corpo: object) -> bool:
    """Última página da visita (beacon em pagehide): só o modelo da página."""
    if not isinstance(corpo, dict):
        return False
    caminho = analisar_caminho(corpo.get("caminho"))
    dims = _dims(corpo)
    if caminho is None or dims is None:
        return False
    _somar(session, hoje(), "ultima", caminho.modelo, dims)
    session.commit()
    return True


def registrar_recurso(session: Session, corpo: object) -> bool:
    if not isinstance(corpo, dict) or corpo.get("recurso") not in RECURSOS:
        return False
    dims = _dims(corpo)
    if dims is None:
        return False
    _somar(session, hoje(), "recurso", corpo["recurso"], dims)
    session.commit()
    return True


def registrar_secao(session: Session, corpo: object) -> bool:
    if not isinstance(corpo, dict) or corpo.get("secao") not in SECOES:
        return False
    dims = _dims(corpo)
    if dims is None:
        return False
    _somar(session, hoje(), "secao", corpo["secao"], dims)
    session.commit()
    return True


def registrar_busca(session: Session, corpo: object) -> bool:
    """Busca de representantes. Só o resultado (com ou sem) e, quando houve, o estado e a cidade
    (código do IBGE) que a busca devolveu. O CEP nunca é lido: nenhum outro campo é usado."""
    if not isinstance(corpo, dict) or corpo.get("forma") not in FORMAS_BUSCA:
        return False
    resultado = corpo.get("resultado")
    dims = _dims(corpo)
    if not isinstance(resultado, bool) or dims is None:
        return False
    dia = hoje()
    if corpo["forma"] == "cep":
        _somar(session, dia, "busca", "cep_com" if resultado else "cep_sem", dims)
    if resultado:
        uf, ibge = corpo.get("uf"), corpo.get("ibge")
        if isinstance(uf, str) and uf in UFS:
            _somar(session, dia, "uf", uf, dims)
        if isinstance(ibge, str) and re.fullmatch(r"\d{7}", ibge):
            _somar(session, dia, "cidade", ibge, dims)
    session.commit()
    return True


# ---------- Resumo para o painel ----------

DIAS_DA_SEMANA = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")


def _filtros(aparelho: str | None, origem: str | None) -> list:
    cond = []
    if aparelho:
        cond.append(M.aparelho == aparelho)
    if origem:
        cond.append(M.origem == origem)
    return cond


def _diario(session: Session, ini: date, fim: date, cond: list, *extra) -> dict[date, int]:
    linhas = session.execute(
        select(M.dia, func.sum(M.total))
        .where(M.dia >= ini, M.dia <= fim, *cond, *extra)
        .group_by(M.dia)
    ).all()
    return {d: int(t) for d, t in linhas}


def _soma(serie: dict[date, int], ini: date, fim: date) -> int:
    return sum(t for d, t in serie.items() if ini <= d <= fim)


def _por_chave(
    session: Session,
    tipo: str,
    janela: "Janela",
    cond: list,
    limite: int | None = None,
    coluna=None,
    so_atual: bool = True,
) -> list[tuple[str, int, int]]:
    """(chave, total atual, total anterior) por chave (ou por coluna, ex.: a origem)."""
    chave = coluna if coluna is not None else M.chave
    atual = func.coalesce(func.sum(case((M.dia >= janela.ini, M.total), else_=0)), 0)
    anterior = func.coalesce(func.sum(case((M.dia < janela.ini, M.total), else_=0)), 0)
    consulta = (
        select(chave, atual, anterior)
        .where(M.tipo == tipo, M.dia >= janela.ini_anterior, M.dia <= janela.fim, *cond)
        .group_by(chave)
        .having(atual > 0 if so_atual else (atual + anterior) > 0)
        .order_by(atual.desc(), chave)
    )
    if limite:
        consulta = consulta.limit(limite)
    return [(c, int(a), int(p)) for c, a, p in session.execute(consulta).all()]


@dataclass(frozen=True)
class Janela:
    dias: int
    fim: date

    @property
    def ini(self) -> date:
        return self.fim - timedelta(days=self.dias - 1)

    @property
    def ini_anterior(self) -> date:
        return self.ini - timedelta(days=self.dias)

    @property
    def fim_anterior(self) -> date:
        return self.ini - timedelta(days=1)

    @property
    def pontos(self) -> int:
        """Dias da linha do tempo: o período, no mínimo uma semana."""
        return max(self.dias, 7)

    @property
    def ini_serie(self) -> date:
        return self.fim - timedelta(days=self.pontos - 1)


def _nomes_de_perfis(session: Session, chaves: Sequence[str]) -> dict[str, dict]:
    """Nome, cargo, UF e partido dos perfis que existem no banco; o que não existe fica de fora."""
    por_tipo: dict[str, list[int]] = {}
    for chave in chaves:
        tipo, _, ident = chave.partition(":")
        if tipo in ("parlamentar", "eleito", "vereador", "deputado-estadual"):
            por_tipo.setdefault(tipo, []).append(int(ident))
    saida: dict[str, dict] = {}
    if ids := por_tipo.get("parlamentar"):
        for p in session.scalars(select(Parlamentar).where(Parlamentar.id.in_(ids))):
            saida[f"parlamentar:{p.id}"] = {
                "nome": p.nome_parlamentar,
                "cargo": "Senador" if p.casa == "senado" else "Deputado federal",
                "uf": p.uf,
                "partido": p.partido,
            }
    if ids := por_tipo.get("eleito"):
        for c in session.scalars(select(Candidatura).where(Candidatura.id.in_(ids))):
            saida[f"eleito:{c.id}"] = {
                "nome": c.nome_urna or c.nome,
                "cargo": c.cargo.capitalize(),
                "uf": c.uf,
                "partido": c.partido,
            }
    ids = por_tipo.get("vereador", []) + por_tipo.get("deputado-estadual", [])
    if ids:
        for m in session.scalars(select(MandatoLocal).where(MandatoLocal.id.in_(ids))):
            cargo = "Vereador" if m.casa == "camara" else "Deputado estadual"
            for tipo in ("vereador", "deputado-estadual"):
                saida[f"{tipo}:{m.id}"] = {
                    "nome": m.nome,
                    "cargo": cargo,
                    "uf": m.uf,
                    "partido": m.partido,
                }
    return saida


def _rotulos_de_projetos(session: Session, chaves: Sequence[str]) -> dict[str, dict]:
    saida: dict[str, dict] = {}
    federais: dict[str, list[str]] = {"camara": [], "senado": []}
    locais: list[int] = []
    for chave in chaves:
        tipo, _, ident = chave.partition(":")
        if tipo in ("projeto-camara", "projeto-senado"):
            federais[tipo.removeprefix("projeto-")].append(ident)
        elif tipo == "projeto-local":
            locais.append(int(ident))
    for casa, ids in federais.items():
        if not ids:
            continue
        for p in session.scalars(
            select(Proposicao).where(Proposicao.casa == casa, Proposicao.id_externo.in_(ids))
        ):
            saida[f"projeto-{casa}:{p.id_externo}"] = {
                "rotulo": f"{p.sigla_tipo} {p.numero}/{p.ano}",
                "casa": "Câmara dos Deputados" if casa == "camara" else "Senado Federal",
            }
    if locais:
        for p, nome in session.execute(
            select(ProjetoLocal, Municipio.nome)
            .join(Municipio, Municipio.ibge == ProjetoLocal.municipio_ibge, isouter=True)
            .where(ProjetoLocal.id.in_(locais))
        ):
            numero = f" {p.numero}/{p.ano}" if p.numero else f" ({p.ano})"
            saida[f"projeto-local:{p.id}"] = {
                "rotulo": f"{p.tipo}{numero}",
                "casa": f"Câmara de {nome}" if nome else "Câmara municipal",
            }
    return saida


def _partidos_existentes(session: Session) -> set[str]:
    achados = set(session.scalars(select(func.upper(Parlamentar.partido)).distinct()))
    achados |= set(session.scalars(select(func.upper(MandatoLocal.partido)).distinct()))
    return {p for p in achados if p}


def _diferenca(atual: int, anterior: int) -> dict:
    return {"atual": atual, "anterior": anterior}


def resumo(
    session: Session,
    dias: int = 7,
    aparelho: str | None = None,
    origem: str | None = None,
    uf: str | None = None,
    item: str | None = None,
) -> dict:
    """Totais agregados; nenhum dado individual existe para ser devolvido.

    `aparelho` e `origem` filtram tudo (menos a própria lista de origens, para que dê para trocar
    de origem). `uf` vale só para a lista de cidades. `item` ("pagina:/x", "perfil:eleito:1" ou
    "partido:pt") devolve a série daquele item e não filtra o resto.
    """
    dias = max(1, min(dias, 90))
    janela = Janela(dias=dias, fim=hoje())
    cond = _filtros(aparelho, origem)
    ini_busca = min(janela.ini_anterior, janela.ini_serie)

    visitas = _diario(session, ini_busca, janela.fim, cond, M.tipo == "visita")
    paginas = _diario(session, ini_busca, janela.fim, cond, M.tipo == "pagina")
    buscas = _diario(session, ini_busca, janela.fim, cond, M.tipo == "busca")
    compartilhou = _diario(
        session, ini_busca, janela.fim, cond, M.tipo == "recurso", M.chave == "compartilhar"
    )

    def par(serie: dict[date, int]) -> dict:
        return _diferenca(
            _soma(serie, janela.ini, janela.fim),
            _soma(serie, janela.ini_anterior, janela.fim_anterior),
        )

    dias_da_serie = [janela.ini_serie + timedelta(days=i) for i in range(janela.pontos)]
    inicio = session.scalar(select(func.min(M.dia)))

    paginas_linhas = _por_chave(session, "pagina", janela, cond, so_atual=False)
    perfis_linhas = _por_chave(session, "perfil", janela, cond, MAX_PERFIS)
    nomes = _nomes_de_perfis(session, [c for c, _, _ in perfis_linhas])
    rotulos = _rotulos_de_projetos(session, [c for c, _, _ in perfis_linhas])
    representantes = [
        {"chave": c, **nomes[c], "atual": a, "anterior": p}
        for c, a, p in perfis_linhas
        if c in nomes
    ]
    projetos = [
        {"chave": c, **rotulos[c], "atual": a, "anterior": p}
        for c, a, p in perfis_linhas
        if c in rotulos
    ][:10]
    existentes = _partidos_existentes(session)
    partidos = [
        {"chave": c.upper(), "atual": a, "anterior": p}
        for c, a, p in _por_chave(session, "partido", janela, cond, 60)
        if c.upper() in existentes
    ][:15]

    # Cidades: só com o mínimo de buscas e que existem na tabela de municípios.
    atual_c = func.coalesce(func.sum(case((M.dia >= janela.ini, M.total), else_=0)), 0)
    consulta = (
        select(M.chave, Municipio.nome, Municipio.uf, atual_c)
        .join(Municipio, Municipio.ibge == M.chave)
        .where(M.tipo == "cidade", M.dia >= janela.ini, M.dia <= janela.fim, *cond)
        .group_by(M.chave, Municipio.nome, Municipio.uf)
        .order_by(atual_c.desc(), M.chave)
        .limit(500)
    )
    if uf:
        consulta = consulta.where(Municipio.uf == uf)
    cidades_todas = [(i, n, u, int(t)) for i, n, u, t in session.execute(consulta).all()]
    cidades = [
        {"ibge": i, "nome": n, "uf": u, "total": t}
        for i, n, u, t in cidades_todas
        if t >= MIN_BUSCAS_CIDADE
    ][:10]
    cidades_fora = sum(1 for *_, t in cidades_todas if 0 < t < MIN_BUSCAS_CIDADE)

    ufs = [{"uf": c, "total": a} for c, a, _ in _por_chave(session, "uf", janela, cond)]
    regioes: dict[str, int] = {}
    for linha in ufs:
        regiao = REGIAO_DA_UF[linha["uf"]]
        regioes[regiao] = regioes.get(regiao, 0) + linha["total"]

    # Média por dia da semana, sobre os dias do período que já têm (ou terão) esse dia.
    dias_do_periodo = [janela.ini + timedelta(days=i) for i in range(janela.dias)]
    semana = []
    for numero, nome in enumerate(DIAS_DA_SEMANA):
        dias_n = [d for d in dias_do_periodo if d.weekday() == numero]
        total = sum(visitas.get(d, 0) for d in dias_n)
        semana.append(
            {"dia": nome, "dias": len(dias_n), "media": round(total / len(dias_n)) if dias_n else 0}
        )

    recursos = [
        {"chave": c, "atual": a, "anterior": p}
        for c, a, p in _por_chave(session, "recurso", janela, cond)
    ]
    resposta = {
        "hoje": janela.fim.isoformat(),
        "inicio_da_contagem": inicio.isoformat() if inicio else None,
        "dias": dias,
        "filtros": {"aparelho": aparelho, "origem": origem, "uf": uf},
        "tiles": {
            "visitas": par(visitas),
            "paginas_vistas": par(paginas),
            "buscas_cep": par(
                _diario(
                    session,
                    ini_busca,
                    janela.fim,
                    cond,
                    M.tipo == "busca",
                    M.chave.in_(("cep_com", "cep_sem")),
                )
            ),
            "compartilhamentos": par(compartilhou),
        },
        "serie": [
            {
                "dia": d.isoformat(),
                "semana": DIAS_DA_SEMANA[d.weekday()],
                "visitas": visitas.get(d, 0),
                "paginas_vistas": paginas.get(d, 0),
                "buscas_cep": buscas.get(d, 0),
                "compartilhamentos": compartilhou.get(d, 0),
            }
            for d in dias_da_serie
        ],
        # A lista de origens ignora o filtro de origem (senão só restaria a escolhida).
        "origens": [
            {"chave": c, "atual": a, "anterior": p}
            for c, a, p in _por_chave(
                session,
                "visita",
                janela,
                _filtros(aparelho, None),
                coluna=M.origem,
            )
        ],
        "paginas": [
            {"chave": c, "atual": a, "anterior": p, "conteudo": c not in FIXAS_SEM_CONTEUDO}
            for c, a, p in paginas_linhas
        ],
        "rotas_fixas": [c for c in FIXAS if c not in FIXAS_SEM_CONTEUDO],
        "representantes": representantes,
        "projetos": projetos,
        "partidos": partidos,
        "regioes": sorted(
            ({"chave": r, "total": t} for r, t in regioes.items()), key=lambda x: -x["total"]
        ),
        "ufs": ufs,
        "cidades": {"itens": cidades, "fora": cidades_fora, "minimo": MIN_BUSCAS_CIDADE},
        "uso": {
            "recursos": recursos,
            "entradas": [
                {"chave": c, "atual": a, "anterior": p}
                for c, a, p in _por_chave(session, "entrada", janela, cond, 8)
            ],
            "ultimas": [
                {"chave": c, "atual": a, "anterior": p}
                for c, a, p in _por_chave(session, "ultima", janela, cond, 8)
            ],
            "secoes": [
                {"chave": c, "atual": a, "anterior": p}
                for c, a, p in _por_chave(session, "secao", janela, cond)
            ],
            "cep": _cep_com_e_sem(session, janela, cond),
            "dia_da_semana": semana,
        },
        "item": _item(session, janela, cond, item, nomes) if item else None,
    }
    return resposta


def _cep_com_e_sem(session: Session, janela: Janela, cond: list) -> dict:
    linhas = {c: (a, p) for c, a, p in _por_chave(session, "busca", janela, cond)}
    return {
        "com": linhas.get("cep_com", (0, 0))[0],
        "sem": linhas.get("cep_sem", (0, 0))[0],
        "com_anterior": linhas.get("cep_com", (0, 0))[1],
        "sem_anterior": linhas.get("cep_sem", (0, 0))[1],
    }


def _item(
    session: Session, janela: Janela, cond: list, item: str, nomes_perfis: dict[str, dict]
) -> dict | None:
    """Série de um item (página, perfil ou partido), com os mesmos filtros de aparelho e origem."""
    tipo, _, chave = item.partition(":")
    if tipo not in ("pagina", "perfil", "partido") or not chave or len(chave) > 120:
        return None
    serie = _diario(
        session,
        min(janela.ini_anterior, janela.ini_serie),
        janela.fim,
        cond,
        M.tipo == tipo,
        M.chave == chave,
    )
    rotulo = chave
    if tipo == "perfil":
        if not re.fullmatch(r"[a-z-]+:\d{1,7}", chave):
            return None
        achado = nomes_perfis.get(chave) or _nomes_de_perfis(session, [chave]).get(chave)
        if achado is None:
            return None
        rotulo = achado["nome"]
    return {
        "tipo": tipo,
        "chave": chave,
        "rotulo": rotulo,
        **_diferenca(
            _soma(serie, janela.ini, janela.fim),
            _soma(serie, janela.ini_anterior, janela.fim_anterior),
        ),
        "serie": [
            {"dia": d.isoformat(), "total": serie.get(d, 0)}
            for d in (janela.ini_serie + timedelta(days=i) for i in range(janela.pontos))
        ],
    }
