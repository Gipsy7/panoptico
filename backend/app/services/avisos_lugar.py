"""Avisos por lugar (cidade, estado, Brasil): os fatos novos de cada lugar seguido, por assunto.

Só gera fatos de lugares que algum aparelho segue (chave do alvo: `br`, `uf:SC`, `mun:4205902`).
O assunto vai na categoria do evento (politica, dinheiro, obras, seguranca, saude, escolas,
economia), que o aparelho pode filtrar por lugar.

Fontes sem data de mudança (situação de obra, "saiu o dado do ano") usam linha de base: a primeira
vez que o detector vê o fato de um lugar, grava com `detectado_em` antigo (BASE), que nunca é
enviado (o envio exige detectado_em depois de o alvo entrar); só a mudança seguinte vira aviso.
Frases literais, com fonte; nada de "bom" ou "ruim".
"""

from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AvisoAlvo,
    AvisoEvento,
    EmendaPagamento,
    FonteIngestao,
    HomicidioSim,
    IdebResultado,
    Municipio,
    ObraFederal,
    ObraFederalMunicipio,
    PibIbge,
    PopulacaoIbge,
    Proposicao,
    SaudeCnes,
    Tramitacao,
    VotacaoLocal,
)
from app.services.pib import CODIGO_UF

ASSUNTOS = ("politica", "dinheiro", "obras", "seguranca", "saude", "escolas", "economia")
BASE = datetime(2000, 1, 1, tzinfo=UTC)  # "já existia": nunca é enviado
UF_NOME = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará",
    "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}  # fmt: skip
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro")  # fmt: skip


def inteiro(n: int) -> str:
    """1234567 -> '1.234.567'."""
    return f"{n:,}".replace(",", ".")


def decimal(v: float, casas: int = 1) -> str:
    """1234.5 -> '1.234,5'."""
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def chave_valida(session: Session, chave: str) -> bool:
    if chave == "br":
        return True
    if chave.startswith("uf:"):
        return chave[3:] in CODIGO_UF
    if chave.startswith("mun:"):
        return session.get(Municipio, chave[4:]) is not None
    return False


def nome_e_caminho(session: Session, chave: str) -> tuple[str, str]:
    if chave == "br":
        return "Brasil", "/impostos-e-repasses"
    if chave.startswith("uf:"):
        uf = chave[3:]
        return UF_NOME.get(uf, uf), f"/estado/{uf}"
    m = session.get(Municipio, chave[4:])
    return (f"{m.nome} ({m.uf})", f"/cidade/{m.ibge}") if m else (chave, "/avisos")


def nome_curto(session: Session, chave: str, cache: dict[str, str]) -> str:
    """Rótulo da notificação: 'Gaspar', 'SC', 'Brasil'."""
    if chave not in cache:
        if chave == "br":
            cache[chave] = "Brasil"
        elif chave.startswith("uf:"):
            cache[chave] = chave[3:]
        else:
            m = session.get(Municipio, chave[4:])
            cache[chave] = m.nome if m else chave
    return cache[chave]


def _seguidos(session: Session) -> tuple[set[str], set[str], bool]:
    chaves = set(
        session.scalars(
            select(AvisoAlvo.alvo_chave).where(AvisoAlvo.alvo_tipo == "lugar").distinct()
        )
    )
    muns = {c[4:] for c in chaves if c.startswith("mun:")}
    ufs = {c[3:] for c in chaves if c.startswith("uf:")}
    return muns, ufs, "br" in chaves


def _ja_tem(session: Session, alvo: str, prefixo: str) -> set[str]:
    """Chaves naturais já gravadas deste lugar com o prefixo (para a linha de base)."""
    return set(
        session.scalars(
            select(AvisoEvento.chave_natural).where(
                AvisoEvento.alvo_tipo == "lugar",
                AvisoEvento.alvo_chave == alvo,
                AvisoEvento.chave_natural.like(f"{prefixo}%"),
            )
        )
    )


def _evento(alvo: str, assunto: str, chave: str, titulo: str, caminho: str, fonte: str,
            dia: date, base: bool = False) -> dict:  # fmt: skip
    return {
        "alvo_tipo": "lugar",
        "alvo_chave": alvo,
        "categoria": assunto,
        "chave_natural": chave[:200],
        "titulo": titulo[:240],
        "caminho": caminho,
        "fonte": fonte[:120],
        "data_fato": dia,
        **({"detectado_em": BASE} if base else {}),
    }


def _obras(session: Session, muns: set[str], hoje: date) -> Iterable[dict]:
    """Obra federal que muda de situação (iniciada, paralisada, concluída) numa cidade seguida."""
    if not muns:
        return
    nomes = dict(
        session.execute(
            select(Municipio.ibge, Municipio.nome).where(Municipio.ibge.in_(muns))
        ).all()
    )
    linhas = session.execute(
        select(ObraFederalMunicipio.municipio_ibge, ObraFederal)
        .join(ObraFederal, ObraFederal.id_unico == ObraFederalMunicipio.obra_id)
        .where(ObraFederalMunicipio.municipio_ibge.in_(muns), ObraFederal.situacao.is_not(None))
    ).all()
    por_mun: dict[str, list] = defaultdict(list)
    for ibge, o in linhas:
        por_mun[ibge].append(o)
    for ibge, obras in por_mun.items():
        alvo = f"mun:{ibge}"
        vistos = {c.rsplit(":", 1)[0] for c in _ja_tem(session, alvo, "obra:")}
        for o in obras:
            chave = f"obra:{o.id_unico}:{o.situacao}"
            titulo = (
                f"Obra federal em {nomes.get(ibge, ibge)}, agora {o.situacao.lower()}: {o.nome}"
            )
            yield _evento(alvo, "obras", chave, titulo, f"/cidade/{ibge}", "Obrasgov.br", hoje,
                          base=f"obra:{o.id_unico}" not in vistos)  # fmt: skip


def _emendas(session: Session, muns: set[str], hoje: date) -> Iterable[dict]:
    """Emendas pagas no último mês fechado, por cidade seguida (uma frase por mês)."""
    if not muns:
        return
    mes_passado = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
    ano_mes = mes_passado.year * 100 + mes_passado.month
    nomes = dict(
        session.execute(
            select(Municipio.ibge, Municipio.nome).where(Municipio.ibge.in_(muns))
        ).all()
    )
    for ibge, total, n in session.execute(
        select(EmendaPagamento.municipio_ibge, func.sum(EmendaPagamento.valor), func.count())
        .where(EmendaPagamento.municipio_ibge.in_(muns), EmendaPagamento.ano_mes == ano_mes)
        .group_by(EmendaPagamento.municipio_ibge)
    ):
        mes = f"{MESES[mes_passado.month - 1]} de {mes_passado.year}"
        titulo = (f"Emendas parlamentares pagas para {nomes.get(ibge, ibge)} em {mes}: "
                  f"R$ {decimal(float(total), 0)} ({n} pagamentos)")  # fmt: skip
        yield _evento(f"mun:{ibge}", "dinheiro", f"emenda:{ano_mes}", titulo, f"/cidade/{ibge}",
                      "Portal da Transparência", hoje)  # fmt: skip


def _leis(session: Session, br: bool, inicio: date, hoje: date) -> Iterable[dict]:
    """Projeto federal que virou lei (tramitação "Transformação em Norma Jurídica")."""
    if not br:
        return
    q = (
        select(Tramitacao.casa, Tramitacao.data, Proposicao)
        .join(
            Proposicao,
            (Proposicao.casa == Tramitacao.casa)
            & (Proposicao.id_externo == Tramitacao.proposicao_id_externo),
        )  # fmt: skip
        .where(
            Tramitacao.data >= inicio,
            Tramitacao.data < hoje + timedelta(days=1),
            func.lower(Tramitacao.descricao).like("%norma jur%"),
        )
    )
    for casa, momento, p in session.execute(q):
        rotulo = f"{p.sigla_tipo} {p.numero}/{p.ano}"
        yield _evento("br", "politica", f"lei:{casa}:{p.id_externo}", f"{rotulo} virou lei",
                      f"/projeto/{casa}/{p.id_externo}",
                      "Câmara dos Deputados" if casa == "camara" else "Senado Federal",
                      momento.date())  # fmt: skip


def _votacoes_locais(
    session: Session, muns: set[str], ufs: set[str], inicio: date, hoje: date
) -> Iterable[dict]:  # noqa: E501
    """Votação nominal na câmara municipal ou na Assembleia (onde a casa publica)."""
    if not muns and not ufs:
        return
    q = select(VotacaoLocal).where(VotacaoLocal.data.between(inicio, hoje))
    for v in session.scalars(q):
        if v.municipio_ibge and v.municipio_ibge in muns:
            alvo, onde, caminho = (
                f"mun:{v.municipio_ibge}",
                "Câmara de vereadores",
                f"/votacao/local/{v.id}",
            )
        elif not v.municipio_ibge and v.uf in ufs:
            alvo, onde, caminho = f"uf:{v.uf}", "Assembleia Legislativa", f"/votacao/local/{v.id}"
        else:
            continue
        resultado = (
            f" ({v.resultado.lower()}, {v.sim} a {v.nao})"
            if v.resultado
            else f" ({v.sim} a {v.nao})"
        )
        titulo = f"{onde} votou: {v.materia}{resultado}"
        yield _evento(alvo, "politica", f"vl:{v.casa}:{v.id_externo}", titulo,
                      caminho, onde, v.data)  # fmt: skip


def _carga_recente(session: Session, fonte: str, inicio: date) -> date | None:
    quando = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte, FonteIngestao.status == "ok"
        )
    )
    return quando.date() if quando and quando.date() >= inicio else None


def _dados_novos(
    session: Session, muns: set[str], ufs: set[str], br: bool, inicio: date
) -> Iterable[dict]:  # noqa: E501
    """ "Saiu o dado": homicídios do ano, leitos do mês, IDEB, PIB. Linha de base na 1ª vez."""
    codigos = {
        **{m: f"mun:{m}" for m in muns},
        **{CODIGO_UF[u]: f"uf:{u}" for u in ufs if u in CODIGO_UF},
    }
    if br:
        codigos["1"] = "br"
    if not codigos:
        return

    def pop(codigo: str, ano: int) -> int | None:
        return session.scalar(
            select(PopulacaoIbge.valor)
            .where(PopulacaoIbge.codigo == codigo, PopulacaoIbge.ano <= ano)
            .order_by(PopulacaoIbge.ano.desc())
            .limit(1)
        )

    def caminho(alvo: str) -> str:
        return (
            "/impostos-e-repasses"
            if alvo == "br"
            else f"/estado/{alvo[3:]}"
            if alvo.startswith("uf:")
            else f"/cidade/{alvo[4:]}"
        )

    def emitir(alvo: str, assunto: str, chave: str, titulo: str, fonte: str, dia: date) -> dict:
        prefixo = chave.rsplit(":", 1)[0] + ":"
        return _evento(alvo, assunto, chave, titulo, caminho(alvo), fonte, dia,
                       base=not _ja_tem(session, alvo, prefixo))  # fmt: skip

    if dia := _carga_recente(session, "datasus_homicidios", inicio):
        ano = session.scalar(select(func.max(HomicidioSim.ano)))
        for codigo, n in session.execute(
            select(HomicidioSim.codigo, HomicidioSim.homicidios).where(
                HomicidioSim.ano == ano, HomicidioSim.codigo.in_(list(codigos))
            )
        ):
            p = pop(codigo, ano)
            taxa = f" ({decimal(1e5 * n / p)} por 100 mil)" if p else ""
            yield emitir(codigos[codigo], "seguranca", f"dado:homicidios:{ano}",
                         f"Saiu o dado de {ano}: {inteiro(n)} homicídios de moradores{taxa}",
                         "Ministério da Saúde, DATASUS (SIM)", dia)  # fmt: skip
    if dia := _carga_recente(session, "datasus_cnes", inicio):
        for r in session.scalars(select(SaudeCnes).where(SaudeCnes.codigo.in_(list(codigos)))):
            p = pop(r.codigo, r.ano)
            mes = f"{MESES[r.mes - 1]} de {r.ano}"
            por_mil = f" ({decimal(1000 * r.leitos / p, 2)} por mil moradores)" if p else ""
            yield emitir(codigos[r.codigo], "saude", f"dado:cnes:{r.ano}{r.mes:02d}",
                         f"Leitos de internação em {mes}: {inteiro(r.leitos)}{por_mil}",
                         "Ministério da Saúde, DATASUS (CNES)", dia)  # fmt: skip
    if dia := _carga_recente(session, "inep_ideb", inicio):
        filtros = {"municipio": ("municipal", [c for c in codigos if len(c) == 7]),
                   "uf": ("publica", [a[3:] for a in codigos.values() if a.startswith("uf:")]),
                   "brasil": ("publica", ["BR"] if br else [])}  # fmt: skip
        for abr, (rede, cods) in filtros.items():
            if not cods:
                continue
            q = select(IdebResultado).where(
                IdebResultado.abrangencia == abr, IdebResultado.etapa == "iniciais",
                IdebResultado.rede == rede, IdebResultado.codigo.in_(cods),
            )  # fmt: skip
            ultimo: dict[str, IdebResultado] = {}
            for r in session.scalars(q):
                if r.codigo not in ultimo or r.ano > ultimo[r.codigo].ano:
                    ultimo[r.codigo] = r
            for cod, r in ultimo.items():
                alvo = "br" if abr == "brasil" else f"uf:{cod}" if abr == "uf" else f"mun:{cod}"
                yield emitir(alvo, "escolas", f"dado:ideb:{r.ano}",
                             f"IDEB {r.ano}, 1º ao 5º ano: {decimal(float(r.valor))}",
                             "INEP (IDEB)", dia)  # fmt: skip
    if dia := _carga_recente(session, "ibge_pib", inicio):
        ultimo_pib: dict[str, PibIbge] = {}
        for r in session.scalars(select(PibIbge).where(PibIbge.codigo.in_(list(codigos)))):
            if r.codigo not in ultimo_pib or r.ano > ultimo_pib[r.codigo].ano:
                ultimo_pib[r.codigo] = r
        for cod, r in ultimo_pib.items():
            bi = float(r.pib) * 1000 / 1e9
            yield emitir(codigos[cod], "economia", f"dado:pib:{r.ano}",
                         f"Saiu o PIB de {r.ano}: R$ {decimal(bi)} bi (valores da época)",
                         "IBGE (PIB dos Municípios)", dia)  # fmt: skip


def detectar(session: Session, inicio: date, hoje: date) -> Iterable[dict]:
    """Todos os fatos dos lugares seguidos (o detector principal grava e evita repetição)."""
    muns, ufs, br = _seguidos(session)
    yield from _obras(session, muns, hoje)
    yield from _emendas(session, muns, hoje)
    yield from _leis(session, br, inicio, hoje)
    yield from _votacoes_locais(session, muns, ufs, inicio, hoje)
    yield from _dados_novos(session, muns, ufs, br, inicio)
