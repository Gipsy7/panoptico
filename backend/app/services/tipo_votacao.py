"""Tipo de cada votação nominal do Plenário, pelo texto oficial da descrição: "mérito" (decide o
conteúdo) ou "procedimento" (decide como e quando votar). Um lugar só para as regras que antes
ficavam espalhadas (votação principal do projeto, etapa "Votado no Plenário" da tramitação).
Decisão e exemplos em docs/DECISOES.md (2026-11-07, "Votação de mérito e de procedimento").

- Procedimento: requerimento (urgência, adiamento, retirada de pauta, votação por artigos, quebra
  de interstício...), preferência, recurso, questão de ordem, apreciação preliminar (pressupostos
  da medida provisória) e inclusão em pauta. Vale antes de tudo: "Requerimento de urgência para o
  Projeto..." é procedimento.
- Mérito: o projeto, o substitutivo, a emenda, o destaque (inclusive "Mantido o texto" e
  "Suprimido o texto", que é como a Câmara publica o destaque para votação em separado), a
  redação final, a PEC em cada turno, a medida provisória, o parecer que decide (sustação de ação
  penal, representação) e a escolha de autoridades (mensagem e ofício no Senado; "Votos: Sra.
  Fulana" na Câmara).
- O que não casa com nenhuma das duas fica em procedimento e é contado à parte (raro: "Aprovadas.",
  "Resultado.").
"""

import re

from app.services.texto_busca import normalizar

MERITO = "merito"
PROCEDIMENTO = "procedimento"
TIPOS = (MERITO, PROCEDIMENTO)

ROTULO = {MERITO: "Sobre o texto", PROCEDIMENTO: "Procedimento"}

_PROCEDIMENTO = re.compile(
    r"\brequerimento|\burgencia\b|solicita urgencia|\bpreferencia\b|\brecurso\b"
    r"|questao de ordem|apreciacao preliminar|\badiamento\b|retirada de pauta|\bintersticio\b"
    r"|^\(?(aprovad|rejeitad)[oa]s? a inclusao"
)
_MERITO = re.compile(
    r"projeto|proposta|\b(pec|plp|plv|pdl|pl|mpv?)\b|medida provisoria|substitutivo|emenda"
    r"|destaque|destacad|redacao final|\btexto\b"
    r"|dispositivo|\bart\b|\bartigo|expressao|\bturno\b|mensagem|oficio|parecer|^votos:"
)
# Votação de uma parte do texto (emenda, destaque, trecho) ou de procedimento: não é a votação do
# texto inteiro. "Proposta de emenda" é o próprio texto da PEC, e "ressalvados os destaques" diz
# só que os destaques ficam para depois.
_PARTE_DO_TEXTO = re.compile(
    r"requerimento|destaque|destacad|(?<!proposta de )\bemenda|recurso|preferencia"
    r"|\b(mantid|suprimid)[oa]s? o texto|\bdispositivos?\b|questao de ordem"
    r"|apreciacao preliminar"
)
_RESSALVA = re.compile(
    r"ressalvad[oa]s? (o|a|os|as) (destaques?|emendas?)|na forma d[ao] (sub)?emenda[^,.;]*"
)


def classificar(descricao: str | None) -> str:
    """'merito' ou 'procedimento' para a descrição oficial de uma votação."""
    texto = normalizar(descricao or "")
    if _PROCEDIMENTO.search(texto):
        return PROCEDIMENTO
    if _MERITO.search(texto):
        return MERITO
    return PROCEDIMENTO


def eh_procedimento(texto: str | None) -> bool:
    """Para outros textos oficiais (passo da tramitação): fala em pedido de procedimento?"""
    return bool(_PROCEDIMENTO.search(normalizar(texto or "")))


def eh_texto_inteiro(descricao: str | None) -> bool:
    """Votação do texto inteiro (base da "votação principal" do projeto): mérito e não é emenda,
    destaque nem trecho."""
    texto = _RESSALVA.sub("", normalizar(descricao or ""))
    return classificar(descricao) == MERITO and not _PARTE_DO_TEXTO.search(texto)
