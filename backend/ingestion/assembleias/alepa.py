"""Assembleia Legislativa do Pará (ALEPA): deputados no cargo hoje, pela página pública
"Deputados" do portal (www.alepa.pa.gov.br/Home/Page/Deputados), que traz os 41 cartões com
nome, partido e foto já no HTML.

As proposições não entram. A pesquisa do portal é um componente DevExpress que carrega os
resultados por chamadas de retorno (`/Legislativo/CallbackPanelProposicoes`): o filtro por
ano funciona (`model.Ano`), mas a paginação da lista (10 por página, ~2.800 itens por ano)
não responde fora do navegador, e sem ela só se alcança a primeira página. Os votos
nominais seguem o mesmo componente. Ver docs/DECISOES.md.
"""

import argparse
import html
import re
from datetime import UTC, datetime
from urllib.parse import quote

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "alepa"
SITE = "https://www.alepa.pa.gov.br"
LISTA = SITE + "/Home/Page/Deputados"
CARTAO = re.compile(
    r"<img class='deputado-image' src='(?P<foto>[^']*)' />.*?"
    r"<div class='card-info'><span>[^<]*</span><span>(?P<nome>[^<]*)</span>"
    r"<p>(?P<partido>[^<]*)</p>",
    re.S,
)


def _foto(url: str) -> str | None:
    """O endereço vem com barras invertidas e espaço no nome do arquivo."""
    url = url.strip().replace("\\", "/")
    if not url:
        return None
    base, _, consulta = url.partition("?")
    esquema, _, resto = base.partition("://")
    return f"{esquema}://{quote(resto, safe='/')}" + (f"?{consulta}" if consulta else "")


def deputados(pagina: str) -> list[dict[str, str | None]]:
    vistos, resultado = set(), []
    for c in CARTAO.finditer(pagina):
        nome = " ".join(html.unescape(c.group("nome")).split())
        chave = comum.chave_nome(nome)
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(
            {
                "id": chave.replace(" ", "-").lower()[:20],
                "nome": nome,
                "partido": " ".join(html.unescape(c.group("partido")).split()) or None,
                "foto": _foto(c.group("foto")),
            }
        )
    return resultado


def coletar() -> dict:
    with comum.criar_cliente() as client:
        pagina = comum._get(client, LISTA, None, 4).content.decode("utf-8", errors="replace")
    vereadores = [
        {
            "id_externo": d["id"],
            "nome": d["nome"],
            "nome_completo": None,
            "partido": d["partido"],
            "foto_url": d["foto"],
            "email": None,
            "telefone": None,
            "titular": True,
            "em_exercicio": True,
            "inicio": None,
            "fim": None,
            "proposicoes_por_tipo": {},
            "projetos": [],
            "sessoes": None,
            "presencas": None,
        }
        for d in deputados(pagina)
    ]
    return {
        "base": LISTA,
        "legislatura": None,
        "vereadores": vereadores,
        "votacoes": [],
        "votos": [],
    }


def executar() -> int:
    casa = coletar()
    if len(casa["vereadores"]) < 35:  # a ALEPA tem 41 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALEPA; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="PA")
        session.add(
            FonteIngestao(fonte=FONTE, url=LISTA, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(f"ALEPA: {total} deputados", flush=True)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
