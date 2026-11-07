"""Avisar erro, direito de resposta e correções públicas (docs/DECISOES.md, 2026-11-07, Frente 7).

Nada muda no site sem revisão humana (`python -m ingestion.revisar --tipo sugestao`). A
resposta de quem é citado só é publicada depois de confirmada a identidade pelo canal oficial.
O contato fica em `sugestao_contato`, fora do backup, e é apagado em 180 dias ou ao fechar.
"""

import secrets
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Candidatura, MandatoLocal, Parlamentar
from app.models.sugestao import Correcao, Sugestao, SugestaoContato

DIAS_DO_CONTATO = 180
FUSO = ZoneInfo("America/Sao_Paulo")
# Sem 0/O, 1/I/L e 5/S: o protocolo é ditado por telefone e copiado à mão.
_ALFABETO = "234679ACDEFGHJKMNPQRTUVWXYZ"
_TAMANHO = 5

# O site usa o caminho da página; outras rotas da API usam o nome interno. Aceita os dois.
_TIPOS = {
    "parlamentar": "parlamentar",
    "deputado-estadual": "deputado-estadual",
    "deputado_estadual": "deputado-estadual",
    "vereador": "vereador",
    "eleito": "eleito",
    "candidatura": "eleito",
}


def normalizar_tipo(tipo: str | None) -> str | None:
    return _TIPOS.get(tipo) if tipo else None


def _novo_protocolo(session: Session) -> str:
    while True:
        codigo = "PAN-" + "".join(secrets.choice(_ALFABETO) for _ in range(_TAMANHO))
        if session.scalar(select(Sugestao.id).where(Sugestao.protocolo == codigo)) is None:
            return codigo


def criar(session: Session, dados: dict) -> str:
    """Grava o aviso ou a resposta na fila e devolve o protocolo."""
    contato = dados.pop("contato", None)
    dados["perfil_tipo"] = normalizar_tipo(dados.get("perfil_tipo"))
    sugestao = Sugestao(**dados, protocolo=_novo_protocolo(session), status="nova")
    session.add(sugestao)
    session.flush()
    if contato:
        session.add(SugestaoContato(sugestao_id=sugestao.id, contato=contato))
    session.commit()
    return sugestao.protocolo


def _dia_local(momento: datetime) -> date:
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento.astimezone(FUSO).date()


def respostas_publicadas(session: Session, tipo: str, perfil_id: str) -> list[dict]:
    """Respostas de quem é citado já revisadas e publicadas no perfil, da mais nova à mais
    antiga. Só o texto, a seção e as datas."""
    tipo_site = normalizar_tipo(tipo)
    if tipo_site is None:
        return []
    linhas = session.scalars(
        select(Sugestao)
        .where(
            Sugestao.tipo == "resposta",
            Sugestao.status == "publicada",
            Sugestao.perfil_tipo == tipo_site,
            Sugestao.perfil_id == perfil_id,
        )
        .order_by(Sugestao.publicada_em.desc(), Sugestao.id.desc())
    )
    return [
        {
            "id": s.id,
            "texto": s.texto,
            "secao": s.secao,
            "recebida_em": _dia_local(s.criada_em),
            "publicada_em": s.publicada_em,
        }
        for s in linhas
    ]


def nome_do_perfil(session: Session, tipo: str | None, perfil_id: str | None) -> str | None:
    """Nome que o perfil mostra no site (o mesmo do cabeçalho da página)."""
    if not tipo or not perfil_id or not perfil_id.isdigit():
        return None
    numero = int(perfil_id)
    if tipo == "parlamentar":
        p = session.get(Parlamentar, numero)
        return p.nome_parlamentar if p else None
    if tipo == "eleito":
        c = session.get(Candidatura, numero)
        return c.nome_urna if c else None
    if tipo in ("vereador", "deputado-estadual"):
        m = session.get(MandatoLocal, numero)
        casa = "camara" if tipo == "vereador" else "assembleia"
        return m.nome if m and m.casa == casa else None
    return None


def correcoes(session: Session, tipo: str | None = None, perfil_id: str | None = None) -> dict:
    """Correções públicas, da mais recente à mais antiga. Sem nada de quem avisou."""
    consulta = select(Correcao)
    if tipo:
        tipo_site = normalizar_tipo(tipo)
        if tipo_site is None:
            return {"itens": [], "total": 0}
        consulta = consulta.where(Correcao.perfil_tipo == tipo_site)
    if perfil_id:
        consulta = consulta.where(Correcao.perfil_id == perfil_id)
    linhas = list(session.scalars(consulta.order_by(Correcao.data.desc(), Correcao.id.desc())))
    nomes: dict[tuple, str | None] = {}
    itens = []
    for c in linhas:
        chave = (c.perfil_tipo, c.perfil_id)
        if chave not in nomes:
            nomes[chave] = nome_do_perfil(session, c.perfil_tipo, c.perfil_id)
        itens.append(
            {
                "id": c.id,
                "data": c.data,
                "dado": c.dado,
                "antes": c.antes,
                "depois": c.depois,
                "motivo": c.motivo,
                "fonte": c.fonte,
                "perfil_tipo": c.perfil_tipo,
                "perfil_id": c.perfil_id,
                "perfil_nome": nomes[chave],
            }
        )
    return {"itens": itens, "total": len(itens)}


# Revisão humana (ingestion/revisar.py --tipo sugestao)


def pendentes(session: Session) -> list[dict]:
    """Sugestões novas, da mais antiga à mais nova. Sem o contato: ele só é lido à parte."""
    com_contato = set(session.scalars(select(SugestaoContato.sugestao_id)))
    return [
        {
            "id": s.id,
            "protocolo": s.protocolo,
            "tipo": s.tipo,
            "categoria": s.categoria or "",
            "criada_em": _dia_local(s.criada_em).isoformat(),
            "pagina": s.pagina,
            "secao": s.secao or "",
            "perfil_tipo": s.perfil_tipo or "",
            "perfil_id": s.perfil_id or "",
            "perfil_nome": nome_do_perfil(session, s.perfil_tipo, s.perfil_id) or "",
            "confirmacao": s.confirmacao or "",
            "texto": s.texto,
            "tem_contato": "sim" if s.id in com_contato else "não",
        }
        for s in session.scalars(
            select(Sugestao).where(Sugestao.status == "nova").order_by(Sugestao.id)
        )
    ]


def contato_de(session: Session, sugestao_id: int) -> str | None:
    return session.scalar(
        select(SugestaoContato.contato).where(SugestaoContato.sugestao_id == sugestao_id)
    )


def apagar_contato(session: Session, sugestao_id: int) -> None:
    session.execute(delete(SugestaoContato).where(SugestaoContato.sugestao_id == sugestao_id))
    session.commit()


def _fechar(session: Session, sugestao: Sugestao, status: str, nota: str | None) -> None:
    sugestao.status = status
    sugestao.revisada_em = datetime.now(UTC)
    sugestao.nota_revisao = nota or None


def recusar(session: Session, sugestao_id: int, nota: str = "") -> None:
    _fechar(session, session.get_one(Sugestao, sugestao_id), "recusada", nota)
    session.commit()


def aceitar(session: Session, sugestao_id: int, nota: str = "") -> None:
    """Aviso de erro conferido com a fonte (a correção, se houver, vai em registrar_correcao)."""
    sugestao = session.get_one(Sugestao, sugestao_id)
    if sugestao.tipo != "erro":
        raise ValueError("Resposta não se aceita: publica-se (publicar_resposta) ou recusa-se.")
    _fechar(session, sugestao, "aceita", nota)
    session.commit()


def publicar_resposta(
    session: Session,
    sugestao_id: int,
    identidade_confirmada: bool,
    texto: str | None = None,
    nota: str = "",
    hoje: date | None = None,
) -> None:
    """Publica a resposta no perfil. Exige que a identidade tenha sido confirmada pelo canal
    oficial (e-mail funcional da Casa ou ofício). `texto` só serve para tirar dados pessoais;
    o site não edita nem comenta a resposta."""
    sugestao = session.get_one(Sugestao, sugestao_id)
    if sugestao.tipo != "resposta":
        raise ValueError("Só resposta de quem é citado é publicada no perfil.")
    if not identidade_confirmada:
        raise ValueError("Confirme a identidade pelo canal oficial antes de publicar.")
    if sugestao.perfil_tipo is None or sugestao.perfil_id is None:
        raise ValueError("A resposta não está ligada a um perfil.")
    if texto and texto.strip():
        sugestao.texto = texto.strip()
    _fechar(session, sugestao, "publicada", nota)
    sugestao.publicada_em = hoje or datetime.now(FUSO).date()
    session.commit()


def registrar_correcao(
    session: Session,
    *,
    dado: str,
    antes: str,
    depois: str,
    motivo: str,
    fonte: str,
    perfil_tipo: str | None = None,
    perfil_id: str | None = None,
    sugestao_id: int | None = None,
    data: date | None = None,
) -> int:
    """Registra a correção pública. Com `sugestao_id`, o perfil vem do aviso se não for dado."""
    campos = {"dado": dado, "antes": antes, "depois": depois, "motivo": motivo, "fonte": fonte}
    vazios = [nome for nome, valor in campos.items() if not (valor or "").strip()]
    if vazios:
        raise ValueError(f"Faltou preencher: {', '.join(vazios)}.")
    if sugestao_id is not None and perfil_tipo is None:
        sugestao = session.get_one(Sugestao, sugestao_id)
        perfil_tipo, perfil_id = sugestao.perfil_tipo, sugestao.perfil_id
    correcao = Correcao(
        **{k: v.strip() for k, v in campos.items()},
        data=data or datetime.now(FUSO).date(),
        perfil_tipo=normalizar_tipo(perfil_tipo),
        perfil_id=perfil_id,
        sugestao_id=sugestao_id,
    )
    session.add(correcao)
    session.commit()
    return correcao.id


def apagar_contatos_antigos(session: Session, agora: datetime | None = None) -> int:
    """Apaga os contatos com mais de 180 dias. Devolve quantos saíram."""
    limite = (agora or datetime.now(UTC)) - timedelta(days=DIAS_DO_CONTATO)
    apagados = (
        session.execute(delete(SugestaoContato).where(SugestaoContato.criada_em < limite)).rowcount
        or 0
    )
    session.commit()
    return apagados
