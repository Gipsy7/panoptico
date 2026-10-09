"""Atos de nomeação, exoneração e designação nos diários oficiais municipais, por nome.

Fonte: API aberta do Querido Diário (Open Knowledge Brasil), que reúne os diários oficiais
de 510 municípios (degrau "espelho" da escada de acesso: o texto vem da OKBR; o link guardado
é o do diário publicado). Rota /gazettes com a frase do nome completo entre aspas, o
município e a data (desde 2025-01-01).

REGRA CRÍTICA: nome encontrado em texto nunca é vínculo. O que sai daqui são SUGESTÕES na
tabela `diario_ato` (revisado = falso), para a fila de revisão humana; nada vira evento
publicável. Homônimos e assinaturas ("Prefeito Fulano" ao pé de um decreto) são o risco.

Recorte mínimo: só as pessoas que já acompanhamos e que têm mandato em curso num município
coberto (prefeitos, vice-prefeitos e vereadores eleitos em 2024; vereadores em exercício
nas câmaras), com nome de pelo menos 3 palavras. Um achado precisa ter, no mesmo trecho, o
nome completo e uma palavra de ato (nomeia, exonera, designa e flexões). Educação com um
serviço comunitário: 1 requisição a cada 2 segundos e cache de 30 dias por pessoa.
"""

import argparse
import re
import time
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import func, literal, select, union
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Candidatura,
    DiarioAto,
    DiarioConsulta,
    FonteIngestao,
    MandatoLocal,
    Pessoa,
    PessoaVinculo,
)
from ingestion import comum
from ingestion.diarios.revisao import aplicar_atos

FONTE = "querido_diario_atos"
URL_CIDADES = "https://api.queridodiario.org.br/cities"
URL_DIARIOS = "https://api.queridodiario.org.br/gazettes"
DESDE = "2025-01-01"
PAUSA = 2.0
VALIDADE = timedelta(days=30)
DIARIOS_POR_BUSCA = 20
TRECHOS_POR_DIARIO = 5
TAMANHO_TRECHO = 500
JANELA = 230  # caracteres para cada lado do nome
MIN_PALAVRAS = 3

_VERBOS = (
    r"NOME(?:IA|AR|AM|ADO|ADA|ADOS|ADAS|ACAO)"
    r"|EXONER(?:A|AR|AM|E|ADO|ADA|ADOS|ADAS|ACAO)"
    r"|DESIGN(?:A|AR|AM|E|ADO|ADA|ADOS|ADAS|ACAO)"
)
# O texto dos PDFs sai com palavras coladas ("Praça daDESIGNA"): o verbo em maiúsculas pode
# vir logo depois de letras minúsculas, mas não no meio de outra palavra em maiúsculas.
ATO = re.compile(rf"(?<![A-Z])({_VERBOS})(?![A-Za-z])|\b((?i:{_VERBOS}))(?![A-Za-z])")
TIPOS = {"NOME": "nomeacao", "EXON": "exoneracao", "DESI": "designacao"}


def _sem_acento(texto: str) -> str:
    """Sem acento, caractere a caractere (mantém os índices e a caixa do original)."""
    return "".join(
        (unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode() or " ")
        if not c.isascii()
        else c
        for c in texto
    )


def padrao_nome(nome: str) -> re.Pattern | None:
    """Regex do nome completo, palavra por palavra, sem acento e com qualquer separador."""
    palavras = comum.chave_nome(nome).split()
    if len(palavras) < MIN_PALAVRAS:
        return None
    meio = r"[^A-Z0-9]+".join(map(re.escape, palavras))
    return re.compile(rf"(?<![A-Z0-9]){meio}(?![A-Z0-9])")


# O nome como título ou assinatura não é o nome como alvo do ato: "Gabinete Parlamentar do
# Vereador Fulano", "Prefeito Fulano", "Fulano : Secretário", "Fulano Presidente",
# "Autorização de diária - Fulano".
ANTES_TITULO = re.compile(
    r"(?:VEREADOR(?:A|ES)?|VER[A]?\.?|PREFEIT[OA]|VICE|PRESIDENTE|SECRETARI[OA]|SENHORA?"
    r"|SRA?\.?|DEPUTAD[OA]|DIARIA)[\s,:\-]*$"
)
DEPOIS_TITULO = re.compile(
    r"^[\s,:\-]*(?:\d\w?\s*)?(?:PRESIDENTE|SECRETARI[OA]|PREFEIT[OA]|VEREADOR|VICE|DIRETOR)"
)


def _so_titulo_ou_assinatura(dobrado_maiusculo: str, m: re.Match) -> bool:
    antes = dobrado_maiusculo[max(0, m.start() - 40) : m.start()]
    depois = dobrado_maiusculo[m.end() : m.end() + 40]
    return bool(ANTES_TITULO.search(antes) or DEPOIS_TITULO.search(depois))


def achar_ato(nome: str, trecho: str) -> tuple[str, str] | None:
    """(tipo do ato, trecho curto) se o nome completo e uma palavra de ato aparecem juntos
    no trecho do diário; senão None."""
    padrao = padrao_nome(nome)
    if padrao is None:
        return None
    dobrado = _sem_acento(trecho)
    maiusculo = dobrado.upper()
    for m in padrao.finditer(maiusculo):
        if _so_titulo_ou_assinatura(maiusculo, m):
            continue
        ini, fim = max(0, m.start() - JANELA), min(len(trecho), m.end() + JANELA)
        ato = ATO.search(dobrado[ini:fim])
        if ato:
            curto = " ".join(trecho[ini:fim].split())[:TAMANHO_TRECHO]
            palavra = (ato.group(1) or ato.group(2)).upper()
            return TIPOS[palavra[:4]], curto
    return None


def sugestoes(nome: str, ibge: str, resposta: dict) -> list[dict[str, Any]]:
    """Uma sugestão por diário (o primeiro trecho que tem nome e ato), com a URL do diário."""
    resultado = []
    for diario in resposta.get("gazettes") or []:
        for trecho in diario.get("excerpts") or []:
            achado = achar_ato(nome, trecho)
            if achado and diario.get("url") and diario.get("date"):
                resultado.append(
                    {
                        "municipio_ibge": ibge,
                        "data": date.fromisoformat(diario["date"]),
                        "tipo_ato": achado[0],
                        "trecho": achado[1],
                        "url": diario["url"],
                    }
                )
                break
    return resultado


def municipios_cobertos(client: httpx.Client) -> set[str]:
    """Municípios com diário já coletado pelo Querido Diário (têm data de disponibilidade)."""
    cidades = comum.get_json(client, URL_CIDADES, {"city_name": ""}).get("cities") or []
    return {c["territory_id"] for c in cidades if c.get("availability_date")}


def pessoas_alvo(session: Session, cobertos: set[str]) -> list[tuple[int, str, str]]:
    """(pessoa, nome completo, município) de quem tem mandato em curso num município coberto:
    prefeito, vice e vereador eleitos em 2024 e vereadores em exercício. Vínculos por nome
    aproximado ainda não revisados ficam de fora."""
    eleitos = (
        select(PessoaVinculo.pessoa_id, Candidatura.municipio_ibge)
        .join(
            Candidatura,
            (PessoaVinculo.fonte == "candidatura")
            & (
                PessoaVinculo.id_externo
                == func.concat(Candidatura.ano_eleicao, literal(":"), Candidatura.sq_candidato)
            ),
        )
        .where(
            Candidatura.ano_eleicao == 2024,
            Candidatura.situacao_turno.like("ELEITO%"),
            Candidatura.cargo.in_(["PREFEITO", "VICE-PREFEITO", "VEREADOR"]),
            Candidatura.municipio_ibge.in_(cobertos),
        )
    )
    camaras = (
        select(PessoaVinculo.pessoa_id, MandatoLocal.municipio_ibge)
        .join(
            MandatoLocal,
            (PessoaVinculo.fonte == "mandato_local")
            & (
                PessoaVinculo.id_externo
                == func.concat(
                    MandatoLocal.casa,
                    literal(":"),
                    MandatoLocal.uf,
                    literal(":"),
                    func.coalesce(MandatoLocal.municipio_ibge, ""),
                    literal(":"),
                    MandatoLocal.id_externo,
                )
            ),
        )
        .where(
            MandatoLocal.casa == "camara",
            MandatoLocal.em_exercicio.is_(True),
            MandatoLocal.municipio_ibge.in_(cobertos),
            (PessoaVinculo.regra != "nome_casa") | PessoaVinculo.revisado.is_(True),
        )
    )
    pares = union(eleitos, camaras).subquery()
    consulta = (
        select(Pessoa.id, Pessoa.nome, pares.c.municipio_ibge)
        .join(pares, pares.c.pessoa_id == Pessoa.id)
        .order_by(Pessoa.id, pares.c.municipio_ibge)
    )
    return [(p, n, m) for p, n, m in session.execute(consulta)]


def buscar(client: httpx.Client, nome: str, ibge: str) -> dict:
    """Uma busca por frase (nome completo entre aspas) nos diários do município."""
    time.sleep(PAUSA)
    return comum.get_json(
        client,
        URL_DIARIOS,
        {
            "territory_ids": ibge,
            "querystring": f'"{nome}"',
            "published_since": DESDE,
            "excerpt_size": 600,
            "number_of_excerpts": TRECHOS_POR_DIARIO,
            "size": DIARIOS_POR_BUSCA,
            "sort_by": "descending_date",
        },
    )


def executar(municipios: list[str] | None = None, limite: int | None = None) -> int:
    hoje = date.today()
    novos, falhas, consultadas, bruto = 0, 0, 0, []
    with SessionLocal() as session, comum.criar_cliente() as client:
        ingestao = FonteIngestao(fonte=FONTE, url=URL_DIARIOS, arquivo_raw="(não guardado)")
        session.add(ingestao)
        session.flush()
        cobertos = municipios_cobertos(client)
        if municipios:
            cobertos &= set(municipios)
        recentes = {
            (p, m)
            for p, m in session.execute(
                select(DiarioConsulta.pessoa_id, DiarioConsulta.municipio_ibge).where(
                    DiarioConsulta.consultado_em >= hoje - VALIDADE
                )
            )
        }
        alvos = [
            a
            for a in pessoas_alvo(session, cobertos)
            if (a[0], a[2]) not in recentes and padrao_nome(a[1]) is not None
        ]
        if limite:
            alvos = alvos[:limite]
        session.commit()
        print(f"  {len(cobertos)} municípios cobertos; {len(alvos)} pessoas a buscar", flush=True)
        for i, (pessoa_id, nome, ibge) in enumerate(alvos, start=1):
            try:
                resposta = buscar(client, nome, ibge)
            except httpx.HTTPError:
                falhas += 1
                continue
            achados = sugestoes(nome, ibge, resposta)
            for a in achados:
                session.execute(
                    insert(DiarioAto)
                    .values(pessoa_id=pessoa_id, **a)
                    .on_conflict_do_nothing(index_elements=["pessoa_id", "url"])
                )
                bruto.append({"pessoa_id": pessoa_id, **a, "data": a["data"].isoformat()})
            stmt = insert(DiarioConsulta).values(
                pessoa_id=pessoa_id, municipio_ibge=ibge, consultado_em=hoje, achados=len(achados)
            )
            session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["pessoa_id", "municipio_ibge"],
                    set_={
                        "consultado_em": stmt.excluded.consultado_em,
                        "achados": stmt.excluded.achados,
                    },
                )
            )
            session.commit()  # aos poucos: uma interrupção não perde o que já foi feito
            consultadas += 1
            novos += len(achados)
            if i % 100 == 0:
                print(f"  {i} de {len(alvos)}; {novos} sugestões", flush=True)
        if bruto:
            comum.salvar_raw(FONTE, bruto)  # recorte: só as sugestões, não os diários
        ingestao = session.merge(ingestao)
        aplicar_atos(session)  # decisões já registradas valem para sugestões recarregadas
        ingestao.registros = session.scalar(select(func.count()).select_from(DiarioAto))
        ingestao.status = "ok"
        ingestao.concluido_em = datetime.now()
        session.commit()
    print(f"  {consultadas} pessoas buscadas; {novos} sugestões; {falhas} buscas sem resposta")
    return novos


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    p.add_argument("--municipios", nargs="+", help="só estes códigos IBGE (amostra)")
    p.add_argument("--limite", type=int, help="no máximo N pessoas nesta execução")
    a = p.parse_args()
    print(f"{FONTE}: {executar(a.municipios, a.limite)} sugestões")
