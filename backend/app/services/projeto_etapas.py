"""Etapa do dia a dia de cada passo da tramitação.

O texto oficial de cada passo (despacho na Câmara, informe legislativo no Senado) fica ao lado;
a etapa só ajuda a ler. Lista ordenada: vale a primeira regra que casa com o tipo e a
descrição (minúsculas, sem acento). Sem regra, "Outro andamento". As etapas dizem o que o
texto oficial diz, sem juízo; o que não se reconhece fica como "Outro andamento".
Decisão e regras em docs/DECISOES.md (2026-10-21)."""

import re
import unicodedata

OUTRO = "Outro andamento"

# (regex sobre "tipo | descrição" normalizado, etapa). Ordem importa: do mais específico
# (virou lei, veto, sanção, arquivo) para o mais geral (apresentado).
REGRAS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"transforma(d[oa]|cao) em norma juridica|sancionad[oa]|promulgad[oa]"),
        "Virou lei",
    ),
    (re.compile(r"\bveto\b|vetad[oa]"), "Vetado"),
    (re.compile(r"\bsancao\b"), "Enviado à sanção"),
    (re.compile(r"(?<!des)arquiv"), "Arquivado"),
    (
        re.compile(
            r"remessa a[o]? (senado|camara)|remetid[oa] a[o]? (senado|camara)"
            r"|vai a[o]? (senado|camara)|encaminhad[oa] a[o]? (senado|camara)|para revisao"
        ),
        "Enviado à outra Casa",
    ),
    (
        re.compile(
            r"^(?!.*(urgencia|requerimento)).*(\b(aprovacao|rejeicao) de proposicao \(plenario\)"
            r"|votacao \(plenario\)|plenario.{0,60}\b(aprov|rejeit)"
            r"|\b(aprov|rejeit)\w*.{0,60}plenario)"
        ),
        "Votado no Plenário",
    ),
    (
        re.compile(
            r"ordem do dia|pronta? para (a )?pauta|pronta? para deliberacao do plenario"
            r"|incluid[oa] na pauta"
        ),
        "Na pauta do Plenário",
    ),
    (
        re.compile(r"parecer|(?<!emitir )\brelatorio\b|apreciada em decisao terminativa"),
        "Parecer na comissão",
    ),
    (
        re.compile(
            r"^(?!.*aguardando).*(relator|distribuid[oa] a[o]? (senador|deputad)"
            r"|para emitir relatorio)"
        ),
        "Relator escolhido",
    ),
    (
        re.compile(r"distribuicao|despacho a[so]? |comissao|comissoes|aguardando designacao"),
        "Nas comissões",
    ),
    (
        re.compile(
            r"apresentacao de proposicao|iniciada a tramitacao|\bleitura\b"
            r"|\bapresentad[oa] (o|a) (projeto|proposta|materia)\b"
        ),
        "Apresentado",
    ),
]

ETAPAS = [etapa for _, etapa in REGRAS] + [OUTRO]


def _normalizar(texto: str) -> str:
    sem = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem if not unicodedata.combining(c)).lower()


def etapa_do_passo(tipo: str | None, descricao: str | None, situacao: str | None = None) -> str:
    """Etapa do passo. Primeiro pelo tipo e pelo texto; se nada casar, pela situação."""
    texto = _normalizar(f"{tipo or ''} | {descricao or ''}")
    for regra, etapa in REGRAS:
        if regra.search(texto):
            return etapa
    if situacao:
        sit = _normalizar(situacao)
        for regra, etapa in REGRAS:
            if etapa != "Apresentado" and regra.search(sit):
                return etapa
    return OUTRO
