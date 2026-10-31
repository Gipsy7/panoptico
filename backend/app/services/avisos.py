"""Avisos por Web Push: detector de novidades, resumo diário e inscrições.

Nada no banco diz o que é novo (as cargas apagam e reinserem), então o detector varre os últimos
30 dias todo dia e grava cada fato uma vez, pela chave natural. Fonte que falhou é vista na
varredura seguinte. Fato com data fora da janela nunca gera aviso: isso cobre vínculo revisado
depois e pessoa nova ligando evento antigo.

O envio manda no máximo uma notificação por aparelho. Tempo: cada aparelho leva até TEMPO_LIMITE
segundos, com PARALELO envios ao mesmo tempo, e PRAZO_ENVIO corta a rodada; quem sobrou recebe no
dia seguinte. Com 10 mil aparelhos a 300 ms são cerca de 3 min; com tudo em tempo limite, 12 min
mais um lote (até 50 s). Cabe nos 15 min do passo da diária.

Endpoint, p256dh e auth nunca vão para log (docs/DECISOES.md, 2026-10-30).
"""

import hashlib
import hmac
import json
import logging
import re
import time
import unicodedata
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from urllib.parse import urlsplit

from sqlalchemy import delete, func, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AvisoAlvo,
    AvisoCursor,
    AvisoEvento,
    AvisoInscricao,
    Evento,
    Parlamentar,
    PessoaVinculo,
    Proposicao,
    Tramitacao,
    Votacao,
    Voto,
)
from app.services.cruzamentos import _titulo
from app.services.pessoas import publicavel
from app.services.votos import VOTO_EFETIVO

JANELA_DIAS = 30
GUARDA_EVENTO_DIAS = 90
GUARDA_INSCRICAO_DIAS = 180
MAX_ALVOS = 20
MAX_NOVIDADES = 50
MAX_TITULO = 240
MAX_CORPO = 300

TTL_SEGUNDOS = 24 * 3600
TEMPO_LIMITE = 5  # segundos, por requisição
PARALELO = 20
LOTE_ENVIO = 200
PRAZO_ENVIO = 12 * 60  # segundos

LOTE_GRAVACAO = 2000
BRASILIA = timezone(timedelta(hours=-3))
CASAS = {"camara": "Câmara dos Deputados", "senado": "Senado Federal"}
ARTIGO_FEMININO = {"PEC", "MPV", "MP"}
ARTIGO_MASCULINO = {"PL", "PLP", "PDL", "PDC", "PLN", "PRC", "PRS", "PLS", "PLC", "PLV", "REQ"}

HOSTS_EXATOS = {"fcm.googleapis.com", "web.push.apple.com"}
HOSTS_SUFIXO = (".push.services.mozilla.com", ".notify.windows.com")

logger = logging.getLogger("panoptico.avisos")


class SemSemente(Exception):
    """O ambiente nunca rodou --semear: enviar agora mandaria 30 dias de fatos antigos."""


@dataclass(frozen=True)
class Destino:
    endpoint: str
    p256dh: str
    auth: str


@dataclass
class Relatorio:
    """Só contagens: nada que identifique um aparelho."""

    detectados: int = 0
    inscricoes: int = 0
    com_novidade: int = 0
    enviados: int = 0
    removidas: int = 0
    chave_recusada: int = 0
    falhas: int = 0
    adiadas: int = 0
    eventos_apagados: int = 0
    inscricoes_apagadas: int = 0


Envio = Callable[[Destino, str], int]


def ligado() -> bool:
    """Chave, contato e AVISOS_ATIVOS: sem qualquer um deles, nada acontece."""
    return bool(
        settings.avisos_ativos
        and settings.vapid_privada
        and settings.vapid_contato.startswith(("mailto:", "https://"))
    )


def endpoint_permitido(endpoint: str) -> bool:
    """Só https e host de serviço de push conhecido: o servidor faz POST nesse endereço, e
    aceitar qualquer um o transformaria em ponte para a rede interna (SSRF)."""
    if re.search(r"[\s\\]", endpoint):
        return False
    try:
        partes = urlsplit(endpoint)
        porta = partes.port
    except ValueError:
        return False
    if partes.scheme != "https" or porta not in (None, 443) or "@" in partes.netloc:
        return False
    if len(partes.path) < 2:
        return False
    host = (partes.hostname or "").lower()
    return host in HOSTS_EXATOS or host.endswith(HOSTS_SUFIXO)


# Detector


def _rotulo(p: Proposicao) -> str:
    return f"{p.sigla_tipo} {p.numero}/{p.ano}"


def _espacos(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def _cortar(texto: str, limite: int = MAX_TITULO) -> str:
    return texto if len(texto) <= limite else texto[: limite - 3].rstrip() + "..."


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return _espacos(sem_acento).lower()


def _chave_tramitacao(casa: str, proposicao: str, dia: date, descricao: str) -> str:
    base = f"{casa}|{proposicao}|{dia.isoformat()}|{_normalizar(descricao)}"
    return hashlib.sha256(base.encode()).hexdigest()


def _titulo_voto(nome: str, voto: str, rotulo: str | None, dia: date) -> str:
    if not rotulo:
        return f"{nome} votou {voto} em votação no Plenário em {dia:%d/%m/%Y}"
    sigla = rotulo.split()[0].upper()
    artigo = "na" if sigla in ARTIGO_FEMININO else "no" if sigla in ARTIGO_MASCULINO else "em"
    return f"{nome} votou {voto} {artigo} {rotulo}"


def _votos(session: Session, inicio: date, hoje: date) -> Iterable[dict]:
    """Só voto efetivo em votação aberta. Ausência fica de fora: a Câmara só publica quem votou,
    e avisar só a do Senado trataria as duas Casas de forma diferente."""
    q = (
        select(
            Votacao.casa,
            Votacao.id_externo,
            Votacao.data,
            Votacao.proposicao,
            Voto.voto,
            Parlamentar.id,
            Parlamentar.id_externo,
            Parlamentar.nome_parlamentar,
        )
        .join(Voto, Voto.votacao_id == Votacao.id)
        .join(Parlamentar, Parlamentar.id == Voto.parlamentar_id)
        .where(
            Votacao.data.between(inicio, hoje),
            Votacao.secreta.is_(False),
            Voto.voto.in_(VOTO_EFETIVO),
        )
    )
    for casa, votacao, dia, rotulo, voto, parlamentar_id, parlamentar, nome in session.execute(q):
        yield {
            "alvo_tipo": "parlamentar",
            "alvo_chave": f"{casa}:{parlamentar}",
            "categoria": "voto",
            "chave_natural": f"{casa}:{votacao}:{parlamentar}",
            "titulo": _cortar(_titulo_voto(nome, voto, rotulo, dia)),
            "caminho": f"/parlamentar/{parlamentar_id}",
            "fonte": CASAS.get(casa, casa),
            "data_fato": dia,
        }


def _tramitacoes(session: Session, inicio: date, hoje: date) -> Iterable[dict]:
    """Sem linha em `proposicao` não há como acompanhar o projeto, então o join não perde nada."""
    q = (
        select(Tramitacao.casa, Tramitacao.data, Tramitacao.descricao, Proposicao)
        .join(
            Proposicao,
            (Proposicao.casa == Tramitacao.casa)
            & (Proposicao.id_externo == Tramitacao.proposicao_id_externo),
        )
        .where(Tramitacao.data >= inicio, Tramitacao.data < hoje + timedelta(days=1))
    )
    for casa, momento, descricao, p in session.execute(q):
        dia = momento.date()
        yield {
            "alvo_tipo": "projeto",
            "alvo_chave": f"{casa}:{p.id_externo}",
            "categoria": "tramitacao",
            "chave_natural": _chave_tramitacao(casa, p.id_externo, dia, descricao),
            "titulo": _cortar(f"{_rotulo(p)}: {_espacos(descricao)}"),
            "caminho": f"/projeto/{casa}/{p.id_externo}",
            "fonte": CASAS.get(casa, casa),
            "data_fato": dia,
        }


def _eventos_oficiais(session: Session, inicio: date, hoje: date) -> Iterable[dict]:
    """Eventos cujo vínculo passa em publicavel(), de pessoa cujo mandato também passa."""
    mandatos: dict[int, list[str]] = {}
    for pessoa_id, chave in session.execute(
        select(PessoaVinculo.pessoa_id, PessoaVinculo.id_externo).where(
            PessoaVinculo.fonte == "parlamentar", publicavel()
        )
    ):
        mandatos.setdefault(pessoa_id, []).append(chave)
    if not mandatos:
        return
    parlamentares = {
        f"{casa}:{id_externo}": (pid, nome)
        for pid, casa, id_externo, nome in session.execute(
            select(
                Parlamentar.id,
                Parlamentar.casa,
                Parlamentar.id_externo,
                Parlamentar.nome_parlamentar,
            )
        )
    }
    q = (
        select(Evento)
        .join(PessoaVinculo, PessoaVinculo.id == Evento.vinculo_id)
        .where(Evento.data.between(inicio, hoje), publicavel())
    )
    for e in session.scalars(q):
        for chave in mandatos.get(e.pessoa_id, []):
            parlamentar = parlamentares.get(chave)
            if parlamentar is None:
                continue
            parlamentar_id, nome = parlamentar
            yield {
                "alvo_tipo": "parlamentar",
                "alvo_chave": chave,
                "categoria": "evento",
                "chave_natural": f"{e.fonte}|{e.id_externo}|{e.tipo}",
                "titulo": _cortar(f"{nome}: {_titulo({'tipo': e.tipo, 'orgao': e.orgao})}"),
                "caminho": f"/parlamentar/{parlamentar_id}",
                "fonte": e.orgao or e.fonte,
                "data_fato": e.data,
            }


def detectar(session: Session, agora: datetime | None = None) -> int:
    """Grava os fatos novos da janela. Não faz commit: quem chama decide. Devolve quantos."""
    agora = agora or datetime.now(UTC)
    hoje = agora.astimezone(BRASILIA).date()
    inicio = hoje - timedelta(days=JANELA_DIAS)
    linhas = [
        {**linha, "detectado_em": agora}
        for origem in (_votos, _tramitacoes, _eventos_oficiais)
        for linha in origem(session, inicio, hoje)
    ]
    novos = 0
    for i in range(0, len(linhas), LOTE_GRAVACAO):
        stmt = (
            insert(AvisoEvento)
            .values(linhas[i : i + LOTE_GRAVACAO])
            .on_conflict_do_nothing(constraint="uq_aviso_evento_chave")
            .returning(AvisoEvento.id)
        )
        novos += len(session.execute(stmt).all())
    return novos


def _teto(session: Session) -> int:
    return session.scalar(select(func.max(AvisoEvento.id))) or 0


def semear(session: Session, agora: datetime | None = None) -> int:
    """Grava o que já existe sem enviar nada e põe o cursor do ambiente depois disso."""
    novos = detectar(session, agora)
    teto = _teto(session)
    stmt = insert(AvisoCursor).values(ambiente=settings.ambiente, ultimo_evento_id=teto)
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=[AvisoCursor.ambiente], set_={"ultimo_evento_id": teto}
        )
    )
    session.commit()
    return novos


# Envio

_http = None


def _sessao_http():
    """Sessão única, com conexões reaproveitadas entre os envios."""
    global _http
    if _http is None:
        import requests
        from requests.adapters import HTTPAdapter

        _http = requests.Session()
        _http.max_redirects = 0  # o host foi validado; um redirecionamento sairia da lista
        _http.mount("https://", HTTPAdapter(pool_connections=PARALELO, pool_maxsize=PARALELO))
    return _http


def enviar_webpush(destino: Destino, carga: str) -> int:
    """A única função que faz rede. Devolve o status HTTP; erro de conexão sobe como exceção.
    Importa o pywebpush aqui para a API, que não envia nada, não carregar a biblioteca."""
    from pywebpush import WebPushException, webpush

    try:
        resposta = webpush(
            subscription_info={
                "endpoint": destino.endpoint,
                "keys": {"p256dh": destino.p256dh, "auth": destino.auth},
            },
            data=carga,
            vapid_private_key=settings.vapid_privada,
            vapid_claims={"sub": settings.vapid_contato},
            ttl=TTL_SEGUNDOS,
            timeout=TEMPO_LIMITE,
            requests_session=_sessao_http(),
        )
    except WebPushException as erro:
        if erro.response is None:
            raise
        return erro.response.status_code
    return resposta.status_code


def _mensagem(eventos: list) -> str:
    """Uma notificação só, com fonte e data literais. Mais de um fato abre a página /avisos."""
    eventos = sorted(eventos, key=lambda e: e.data_fato, reverse=True)
    recente = eventos[0]
    data = f"{recente.data_fato:%d/%m/%Y}"
    if len(eventos) == 1:
        titulo, caminho = recente.titulo, recente.caminho
        corpo = f"Fonte: {recente.fonte}. Data: {data}."
    else:
        titulo, caminho = f"{len(eventos)} novidades de quem você acompanha", "/avisos"
        fontes = ", ".join(dict.fromkeys(e.fonte for e in eventos))
        corpo = f"{recente.titulo}. Fontes: {fontes}. Data mais recente: {data}."
    carga = {"titulo": titulo, "corpo": _cortar(corpo, MAX_CORPO), "caminho": caminho}
    return json.dumps(carga, ensure_ascii=False)


def _pendentes(
    session: Session, lote: list[int], base: int, teto: int
) -> dict[int, tuple[Destino, list]]:
    """O que cada aparelho do lote ainda não recebeu. Lê por lote para não encher a memória."""
    q = (
        select(
            AvisoInscricao.id.label("inscricao_id"),
            AvisoInscricao.endpoint,
            AvisoInscricao.p256dh,
            AvisoInscricao.auth,
            AvisoEvento.titulo,
            AvisoEvento.caminho,
            AvisoEvento.fonte,
            AvisoEvento.data_fato,
        )
        .join(AvisoAlvo, AvisoAlvo.inscricao_id == AvisoInscricao.id)
        .join(
            AvisoEvento,
            (AvisoEvento.alvo_tipo == AvisoAlvo.alvo_tipo)
            & (AvisoEvento.alvo_chave == AvisoAlvo.alvo_chave)
            & (AvisoEvento.detectado_em > AvisoAlvo.criado_em),
        )
        .where(
            AvisoInscricao.id.in_(lote),
            AvisoInscricao.ambiente == settings.ambiente,
            AvisoEvento.id > func.coalesce(AvisoInscricao.ultimo_evento_id, base),
            AvisoEvento.id <= teto,
        )
    )
    pendentes: dict[int, tuple[Destino, list]] = {}
    for linha in session.execute(q):
        destino = Destino(linha.endpoint, linha.p256dh, linha.auth)
        pendentes.setdefault(linha.inscricao_id, (destino, []))[1].append(linha)
    return pendentes


def _fixar(session: Session, ids: list[int], base: int) -> None:
    """Quem não recebeu guarda o ponto de partida: o cursor do ambiente vai avançar."""
    session.execute(
        update(AvisoInscricao)
        .where(AvisoInscricao.id.in_(ids), AvisoInscricao.ultimo_evento_id.is_(None))
        .values(ultimo_evento_id=base)
    )


def _aplicar(
    session: Session,
    resultados: list[tuple[int, int]],
    base: int,
    teto: int,
    agora: datetime,
    r: Relatorio,
) -> None:
    """404/410: o aparelho saiu, apaga. 401/403: chave errada do nosso lado, não apaga. O resto
    tenta de novo no dia seguinte."""
    entregues, sumidas, fixar = [], [], []
    for inscricao_id, status in resultados:
        if 200 <= status < 300:
            entregues.append(inscricao_id)
        elif status in (404, 410):
            sumidas.append(inscricao_id)
        else:
            fixar.append(inscricao_id)
            if status in (401, 403):
                r.chave_recusada += 1
            else:
                r.falhas += 1
    r.enviados += len(entregues)
    r.removidas += len(sumidas)
    if entregues:
        session.execute(
            update(AvisoInscricao)
            .where(AvisoInscricao.id.in_(entregues))
            .values(ultimo_sucesso_em=agora, ultimo_evento_id=teto)
        )
    if sumidas:
        session.execute(delete(AvisoInscricao).where(AvisoInscricao.id.in_(sumidas)))
    if fixar:
        _fixar(session, fixar, base)


def limpar(session: Session, agora: datetime) -> tuple[int, int]:
    """Prazos de guarda. O evento dura mais que a janela: não pode sumir e voltar como novo."""
    eventos = session.execute(
        delete(AvisoEvento).where(
            AvisoEvento.detectado_em < agora - timedelta(days=GUARDA_EVENTO_DIAS)
        )
    )
    referencia = func.coalesce(AvisoInscricao.ultimo_sucesso_em, AvisoInscricao.criada_em)
    inscricoes = session.execute(
        delete(AvisoInscricao).where(
            AvisoInscricao.ambiente == settings.ambiente,
            referencia < agora - timedelta(days=GUARDA_INSCRICAO_DIAS),
        )
    )
    return eventos.rowcount or 0, inscricoes.rowcount or 0


def executar(
    session: Session,
    envio: Envio = enviar_webpush,
    *,
    simular: bool = False,
    agora: datetime | None = None,
    prazo: float = PRAZO_ENVIO,
) -> Relatorio:
    """Roda a diária. O cursor só avança ao fim: se o processo cair no meio, quem já recebeu tem
    `ultimo_evento_id` gravado por lote e não recebe de novo. Em simulação nada é gravado."""
    agora = agora or datetime.now(UTC)
    ambiente = settings.ambiente
    cursor = session.get(AvisoCursor, ambiente)
    if cursor is None:
        raise SemSemente(ambiente)
    base = cursor.ultimo_evento_id
    r = Relatorio(detectados=detectar(session, agora))
    if not simular:
        session.commit()
    teto = _teto(session)
    ids = list(
        session.scalars(
            select(AvisoInscricao.id)
            .where(AvisoInscricao.ambiente == ambiente)
            .order_by(AvisoInscricao.id)
        )
    )
    r.inscricoes = len(ids)

    def chamar(item: tuple[int, tuple[Destino, list]]) -> tuple[int, int]:
        inscricao_id, (destino, eventos) = item
        try:
            return inscricao_id, envio(destino, _mensagem(eventos))
        except Exception:  # a mensagem do erro pode trazer o endpoint: não vai para o log
            return inscricao_id, 0

    inicio = time.monotonic()
    with ThreadPoolExecutor(max_workers=PARALELO) as pool:
        for i in range(0, len(ids), LOTE_ENVIO):
            if not simular and time.monotonic() - inicio > prazo:
                r.adiadas = len(ids) - i
                _fixar(session, ids[i:], base)
                session.commit()
                break
            pendentes = _pendentes(session, ids[i : i + LOTE_ENVIO], base, teto)
            r.com_novidade += len(pendentes)
            if simular:
                continue
            _aplicar(session, list(pool.map(chamar, pendentes.items())), base, teto, agora, r)
            session.commit()

    if simular:
        session.rollback()
        return r
    r.eventos_apagados, r.inscricoes_apagadas = limpar(session, agora)
    session.execute(
        update(AvisoCursor).where(AvisoCursor.ambiente == ambiente).values(ultimo_evento_id=teto)
    )
    session.commit()
    logger.info("avisos ambiente=%s %s", ambiente, r)
    return r


# Inscrições (rotas)


def buscar(
    session: Session, endpoint: str, auth: str, *, travar: bool = False
) -> AvisoInscricao | None:
    """A inscrição deste ambiente, só com endpoint e auth certos."""
    q = select(AvisoInscricao).where(
        AvisoInscricao.ambiente == settings.ambiente, AvisoInscricao.endpoint == endpoint
    )
    inscricao = session.scalar(q.with_for_update() if travar else q)
    if inscricao is None or not hmac.compare_digest(inscricao.auth, auth):
        return None
    return inscricao


def inscrever(session: Session, endpoint: str, p256dh: str, auth: str) -> bool:
    """Idempotente. Devolve False se o teto de inscrições foi atingido. Inscrição existente não
    troca de chaves: conhecer o endereço não pode bastar para assumir o aparelho."""
    ambiente = settings.ambiente
    existe = session.scalar(
        select(AvisoInscricao.id).where(
            AvisoInscricao.ambiente == ambiente, AvisoInscricao.endpoint == endpoint
        )
    )
    if existe is not None:
        return True
    total = session.scalar(
        select(func.count()).select_from(AvisoInscricao).where(AvisoInscricao.ambiente == ambiente)
    )
    if total >= settings.avisos_max_inscricoes:
        return False
    session.execute(
        insert(AvisoInscricao)
        .values(
            ambiente=ambiente,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            criada_em=datetime.now(UTC),
        )
        .on_conflict_do_nothing(constraint="uq_aviso_inscricao_ambiente_endpoint")
    )
    session.commit()
    return True


def alvo_existe(session: Session, tipo: str, chave: str) -> bool:
    casa, id_externo = chave.split(":", 1)
    modelo = Parlamentar if tipo == "parlamentar" else Proposicao
    q = select(modelo.id).where(modelo.casa == casa, modelo.id_externo == id_externo)
    return session.scalar(q) is not None


def _contar_alvos(session: Session, inscricao_id: int) -> int:
    q = select(func.count()).select_from(AvisoAlvo).where(AvisoAlvo.inscricao_id == inscricao_id)
    return session.scalar(q) or 0


def alterar_alvo(
    session: Session, inscricao: AvisoInscricao, tipo: str, chave: str, adicionar: bool
) -> int | None:
    """Devolve quantos alvos o aparelho tem, ou None se passaria do máximo. O teste de existência
    fica na rota, que devolve 422."""
    atual = session.scalar(
        select(AvisoAlvo).where(
            AvisoAlvo.inscricao_id == inscricao.id,
            AvisoAlvo.alvo_tipo == tipo,
            AvisoAlvo.alvo_chave == chave,
        )
    )
    if adicionar and atual is None:
        if _contar_alvos(session, inscricao.id) >= MAX_ALVOS:
            return None
        session.add(
            AvisoAlvo(
                inscricao_id=inscricao.id,
                alvo_tipo=tipo,
                alvo_chave=chave,
                criado_em=datetime.now(UTC),
            )
        )
    elif not adicionar and atual is not None:
        session.delete(atual)
    session.flush()
    total = _contar_alvos(session, inscricao.id)
    session.commit()
    return total


def cancelar(session: Session, inscricao: AvisoInscricao) -> None:
    """Apaga de verdade; os alvos saem pela cascata."""
    session.execute(delete(AvisoInscricao).where(AvisoInscricao.id == inscricao.id))
    session.commit()


def _nomes(session: Session, alvos: list[AvisoAlvo]) -> dict[tuple[str, str], tuple[str, str]]:
    """(tipo, chave) -> (nome, caminho) de quem ainda existe nas tabelas."""

    def pares(tipo: str) -> list[tuple[str, str]]:
        return [tuple(a.alvo_chave.split(":", 1)) for a in alvos if a.alvo_tipo == tipo]

    achados: dict[tuple[str, str], tuple[str, str]] = {}
    if parlamentares := pares("parlamentar"):
        q = select(Parlamentar).where(
            tuple_(Parlamentar.casa, Parlamentar.id_externo).in_(parlamentares)
        )
        for p in session.scalars(q):
            chave = ("parlamentar", f"{p.casa}:{p.id_externo}")
            achados[chave] = (p.nome_parlamentar, f"/parlamentar/{p.id}")
    if projetos := pares("projeto"):
        q = select(Proposicao).where(tuple_(Proposicao.casa, Proposicao.id_externo).in_(projetos))
        for p in session.scalars(q):
            chave = ("projeto", f"{p.casa}:{p.id_externo}")
            achados[chave] = (_rotulo(p), f"/projeto/{p.casa}/{p.id_externo}")
    return achados


def minhas(session: Session, inscricao: AvisoInscricao) -> dict:
    """O que o aparelho acompanha e as novidades detectadas depois de cada alvo entrar, as mesmas
    que a diária mandaria."""
    alvos = list(
        session.scalars(
            select(AvisoAlvo).where(AvisoAlvo.inscricao_id == inscricao.id).order_by(AvisoAlvo.id)
        )
    )
    nomes = _nomes(session, alvos)
    novidades = session.scalars(
        select(AvisoEvento)
        .join(
            AvisoAlvo,
            (AvisoEvento.alvo_tipo == AvisoAlvo.alvo_tipo)
            & (AvisoEvento.alvo_chave == AvisoAlvo.alvo_chave)
            & (AvisoEvento.detectado_em > AvisoAlvo.criado_em),
        )
        .where(AvisoAlvo.inscricao_id == inscricao.id)
        .order_by(AvisoEvento.data_fato.desc(), AvisoEvento.id.desc())
        .limit(MAX_NOVIDADES)
    )
    return {
        "alvos": [
            {
                "alvo_tipo": a.alvo_tipo,
                "alvo_chave": a.alvo_chave,
                # Alvo que saiu das tabelas continua na lista, para poder ser removido.
                "nome": nomes.get((a.alvo_tipo, a.alvo_chave), (a.alvo_chave, ""))[0],
                "caminho": nomes.get((a.alvo_tipo, a.alvo_chave), ("", "/avisos"))[1],
            }
            for a in alvos
        ],
        "novidades": [
            {
                "titulo": e.titulo,
                "caminho": e.caminho,
                "fonte": e.fonte,
                "data_fato": e.data_fato,
                "detectado_em": e.detectado_em,
            }
            for e in novidades
        ],
    }
