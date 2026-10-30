"""Registro do chat Argos: limpeza do texto, gravação e prazo de guarda.

O que se guarda é decisão do dono (docs/DECISOES.md, 2026-10-30): frase não entendida (só o
texto e o dia), avaliação "ajudou?" (sim ou não, assunto, dia) e, só com consentimento, a
conversa. A limpeza do site (frontend/lib/argos/limpar.ts) e esta são as mesmas regras: o
servidor nunca confia no cliente.
"""

import re
from datetime import date, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.argos import ArgosAvaliacao, ArgosConversa, ArgosFraseNaoEntendida

MARCA = "[removido]"
MAX_FRASE = 300
MAX_MENSAGEM = 500
MAX_MENSAGENS = 30
DIAS_DE_GUARDA = 180

# Ordem importa: padrões específicos antes do genérico "5 ou mais dígitos".
_PADROES = [
    re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE),  # URLs
    re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),  # e-mails
    re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)"),  # CPF
    re.compile(r"(?<!\d)\d{5}\s?-?\s?\d{3}(?!\d)"),  # CEP
    re.compile(r"(?<!\d)(?:\+?55\s?)?\(?\d{2}\)?\s?9?\s?\d{4}[\s-]?\d{4}(?!\d)"),  # telefone
    re.compile(r"\d{5,}"),  # qualquer sequência de 5 ou mais dígitos
]


def limpar(texto: str, limite: int = MAX_FRASE) -> str:
    """Troca por "[removido]" URL, e-mail, CPF, CEP, telefone e qualquer sequência de 5+
    dígitos; junta espaços e corta no limite."""
    for padrao in _PADROES:
        texto = padrao.sub(MARCA, texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:limite]


def so_marca(texto: str) -> bool:
    """A frase ficou sem conteúdo útil depois da limpeza."""
    return not texto.replace(MARCA, "").strip(" .,;:!?-")


_ultima_limpeza: date | None = None


def apagar_antigos(session: Session, hoje: date | None = None) -> int:
    """Apaga o que passou de 180 dias. Devolve quantos registros saíram."""
    limite = (hoje or date.today()) - timedelta(days=DIAS_DE_GUARDA)
    total = 0
    for modelo in (ArgosFraseNaoEntendida, ArgosAvaliacao, ArgosConversa):
        total += session.execute(delete(modelo).where(modelo.dia < limite)).rowcount or 0
    return total


def _limpeza_diaria(session: Session) -> None:
    """Roda a limpeza de prazo no máximo uma vez por dia por processo, ao gravar."""
    global _ultima_limpeza
    hoje = date.today()
    if _ultima_limpeza != hoje:
        _ultima_limpeza = hoje
        apagar_antigos(session, hoje)


def registrar_nao_entendida(session: Session, texto: str) -> bool:
    limpo = limpar(texto)
    if not limpo or so_marca(limpo):
        return False
    _limpeza_diaria(session)
    session.add(ArgosFraseNaoEntendida(texto=limpo, dia=date.today()))
    session.commit()
    return True


def registrar_avaliacao(
    session: Session, util: bool, assunto: str, conversa: list[dict] | None = None
) -> None:
    _limpeza_diaria(session)
    hoje = date.today()
    session.add(ArgosAvaliacao(util=util, assunto=assunto, dia=hoje))
    if conversa:
        mensagens = [
            {"autor": m["autor"], "texto": limpar(m["texto"], MAX_MENSAGEM)}
            for m in conversa[-MAX_MENSAGENS:]
        ]
        session.add(ArgosConversa(mensagens=mensagens, dia=hoje))
    session.commit()
