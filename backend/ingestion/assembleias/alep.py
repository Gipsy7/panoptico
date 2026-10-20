"""Assembleia Legislativa do Paraná (ALEP): deputados no cargo hoje, presença em plenário e
votos nominais, pelas páginas e rotas públicas do site e do Portal da Transparência da ALEP.

Por que não a API de dados abertos (`webservices.assembleia.pr.leg.br/api/public`): ela é
só de proposições e normas, usa um certificado autoassinado ("CN=BLACKHOLE", SHA-256
ae0f3aed...903c, visto em 19/10/2026) e respondeu 403 a toda rota, depois deixou de
responder. Fixar esse certificado não provaria que o servidor é da Assembleia, e o 403 é
tratado como bloqueio deliberado: não se contorna (ver docs/pedidos/alep_certificado.md). A
verificação de segurança nunca é desligada aqui.

O que há aberto, com certificado válido e `robots.txt` liberado:
- Deputados: `www.assembleia.pr.leg.br/deputados/conheca` (nome, partido e foto, 54 cartões).
- Presença: `transparencia.assembleia.pr.leg.br/api/presenca/ano?ano=AAAA`, uma lista por
  sessão com as colunas presentes, justificados e ausentes.
- Votos: cada sessão com votação nominal publica um zip de planilhas (uma por item) em
  `api/votacoes/dados-abertos?sessao=ID`, com o nome civil, o partido e o voto de cada um.
  As rotas de busca de votações e a de verba de ressarcimento exigem reCAPTCHA: ficam de
  fora, sem contornar (pedido em docs/pedidos/).
- Proposições: só na API bloqueada acima (a pesquisa legislativa do portal também usa
  reCAPTCHA). Não entram.

Uma requisição por vez, com pausa. O bruto (página, presença e planilhas) vai num zip em
`data/raw/alep/`; `--de-raw` reprocessa sem rede. Grava nas mesmas tabelas das outras casas,
pela gravação do conector SAPL.
"""

import argparse
import html
import io
import json
import re
import time
import zipfile
from datetime import date
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidatura, FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl
from ingestion.identidade import casar_nome

FONTE = "alep"
SITE = "https://www.assembleia.pr.leg.br"
LISTA = SITE + "/deputados/conheca"
TRANSPARENCIA = "https://transparencia.assembleia.pr.leg.br"
BASE_VOTOS = TRANSPARENCIA + "/plenario/controle-de-votacao"
PAUSA = 2.0
MINIMO_DEPUTADOS = 45  # a ALEP tem 54 cadeiras: lista curta é falha da fonte
VOTOS = {"SIM": "Sim", "NAO": "Não", "ABSTER": "Abstenção", "ABSTENCAO": "Abstenção"}


def _limpo(trecho: str | None) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", trecho or "")).split())


def deputados(pagina: str) -> list[dict[str, str | None]]:
    """Os cartões da página 'Conheça os deputados': slug do perfil, nome, partido e foto."""
    vistos, resultado = set(), []
    for cartao in re.split(r'<div class="deputado-card', pagina)[1:]:
        slug = re.search(r"/deputados/perfil/([a-z0-9-]+)\"", cartao)
        nome = re.search(r"<h3[^>]*>(.*?)</h3>", cartao, re.S)
        if not slug or not nome or slug.group(1) in vistos:
            continue
        vistos.add(slug.group(1))
        partido = re.search(r'<p class="text-gray-500[^>]*>(.*?)</p>', cartao, re.S)
        foto = re.search(r'<img[^>]*src="([^"]+)"', cartao)
        resultado.append(
            {
                "slug": slug.group(1),
                "nome": _limpo(nome.group(1)),
                "partido": _limpo(partido.group(1)) if partido else None,
                "foto": foto.group(1) if foto else None,
            }
        )
    return resultado


def _por_nome(nome: str, lista: list[dict]) -> str | None:
    """Slug do deputado que o nome identifica, só se a correspondência for exata e única."""
    achado = casar_nome([nome], [(i, d["nome"]) for i, d in enumerate(lista)])
    return lista[achado]["slug"] if achado is not None else None


def presenca(payload: dict, lista: list[dict]) -> dict[str, tuple[int, int]]:
    """slug -> (sessões em que constava, presenças). Cada sessão traz três colunas de nomes
    (presentes, justificados, ausentes); os justificados contam como falta, como nas outras
    casas. Nome que não casa com um único deputado fica de fora."""
    sessoes: dict[str, int] = {}
    presentes: dict[str, int] = {}
    for sessao in payload.get("sessoes", []):
        linhas = sessao.get("linhas", [])[1:]
        for coluna in (0, 1, 2):
            for linha in linhas:
                nome = (linha[coluna] if len(linha) > coluna else "").strip()
                slug = _por_nome(nome, lista) if nome else None
                if slug:
                    sessoes[slug] = sessoes.get(slug, 0) + 1
                    if coluna == 0:
                        presentes[slug] = presentes.get(slug, 0) + 1
    return {s: (n, presentes.get(s, 0)) for s, n in sessoes.items()}


def ler_xlsx(conteudo: bytes) -> list[list[str]]:
    """Linhas da primeira planilha, só com a biblioteca padrão (as planilhas da ALEP são
    simples: texto e números, sem fórmulas)."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        textos: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            raiz = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
            textos = ["".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")) for si in raiz]
        planilha = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
        raiz = ElementTree.fromstring(z.read(planilha))
    linhas = []
    for linha in raiz.iter(f"{{{ns['m']}}}row"):
        celulas: dict[int, str] = {}
        for c in linha.findall("m:c", ns):
            coluna = 0
            for letra in re.match(r"[A-Z]+", c.get("r", "A"))[0]:
                coluna = coluna * 26 + ord(letra) - 64
            valor = c.find("m:v", ns)
            if c.get("t") == "s" and valor is not None:
                texto = textos[int(valor.text)]
            elif c.get("t") == "inlineStr":
                texto = "".join(t.text or "" for t in c.iter(f"{{{ns['m']}}}t"))
            else:
                texto = valor.text if valor is not None and valor.text else ""
            celulas[coluna - 1] = texto.strip()
        largura = max(celulas, default=-1) + 1
        linhas.append([celulas.get(i, "") for i in range(largura)])
    return linhas


def _numero(texto: str) -> int:
    achado = re.search(r"\d+", texto or "")
    return int(achado.group(0)) if achado else 0


PEQUENAS = {
    "a", "as", "o", "os", "à", "às", "ao", "aos", "e", "de", "da", "das", "do", "dos", "em", "no",
    "na", "nos", "nas", "para", "pelo", "pela", "com", "por", "que", "ou", "um", "uma",
}  # fmt: skip


def ementa_legivel(texto: str) -> str:
    """A ementa vem toda em maiúsculas: cada palavra com inicial maiúscula, menos as pequenas
    ('de', 'da', 'com'...). Siglas viram palavras comuns (ALEP -> Alep)."""
    palavras = texto.lower().split()
    return " ".join(
        p if (i and p in PEQUENAS) else p[:1].upper() + p[1:] for i, p in enumerate(palavras)
    )


def votacao(linhas: list[list[str]]) -> tuple[dict, list[tuple[str, str]]] | None:
    """Uma planilha de item votado -> (dados da votação, [(nome civil, voto)]). Só votação
    nominal; simbólica não tem voto por deputado e devolve None."""
    campos: dict[str, str] = {}
    votos: list[tuple[str, str]] = []
    na_tabela = False
    for linha in linhas:
        rotulo = comum.chave_nome(linha[0]) if linha else ""
        if na_tabela:
            if len(linha) >= 3 and linha[0] and linha[2]:
                votos.append((linha[0], linha[2]))
        elif rotulo == "PARLAMENTAR":
            na_tabela = True
        elif len(linha) > 1 and rotulo:
            campos.setdefault(rotulo, linha[1])
    if "NOMINAL" not in comum.chave_nome(campos.get("TIPO VOTACAO")) or not votos:
        return None
    ementa = " ".join(campos.get("EMENTA", "").split())
    materia = [x for x in linhas[0][1:2] if x] if linhas else []
    titulo = comum.nome_proprio(materia[0]) if materia else "Item de votação"
    data = re.match(r"(\d{2})/(\d{2})/(\d{4})", campos.get("DATA", ""))
    return (
        {
            "materia": f"{titulo}: {ementa_legivel(ementa)}"[:500] if ementa else titulo,
            "resultado": (campos.get("RESULTADO DA VOTACAO") or "").capitalize() or None,
            "sim": _numero(campos.get("VOTOS SIM", "")),
            "nao": _numero(campos.get("VOTO NAO", "")),
            "abstencoes": _numero(campos.get("VOTO ABSTER", "")),
            "data": f"{data[3]}-{data[2]}-{data[1]}" if data else None,
        },
        votos,
    )


def texto_do_voto(voto: str) -> str:
    chave = comum.chave_nome(voto)
    if chave in VOTOS:
        return VOTOS[chave]
    return "Não votou" if chave == "NAO VOTOU" else voto.strip().capitalize()[:30]


def nomes_civis(lista: list[dict], eleitos: list[tuple[int, str | None, str | None]]) -> dict:
    """slug -> chave do nome civil, pela candidatura eleita do TSE (nome de urna casa com o
    do site, o nome civil casa com o da planilha de votos). Quem não casa fica sem voto."""
    pares = [(i, n) for i, urna, civil in eleitos for n in (urna, civil) if n]
    civil_de = {i: civil for i, _, civil in eleitos}
    resultado = {}
    for d in lista:
        achado = casar_nome([d["nome"]], pares)
        if achado is not None and civil_de.get(achado):
            resultado[d["slug"]] = civil_de[achado]
    return resultado


# ---------------------------------------------------------------------------- rede


def _json(client: httpx.Client, caminho: str, **params: Any) -> Any:
    time.sleep(PAUSA)
    return comum._get(client, f"{TRANSPARENCIA}/{caminho}", params, 4).json()


def baixar_sessoes(client: httpx.Client, ano: int) -> list[dict]:
    """As sessões do ano com votação e o zip de dados abertos de cada uma (404 = sem zip)."""
    sessoes = []
    for mes in sorted(_json(client, "api/votacoes/meses", ano=ano).get("meses", {}), key=int):
        for dia in _json(client, "api/votacoes/datas", ano=ano, mes=int(mes)):
            for id_, nome in _json(
                client, "api/votacoes/sessoes", ano=ano, mes=int(mes), data=dia
            ).items():
                try:
                    info = _json(client, "api/votacoes/dados-abertos", sessao=id_)
                except httpx.HTTPStatusError as erro:
                    if erro.response.status_code == 404:
                        continue  # sessão sem votação nominal publicada
                    raise
                sessoes.append({"id": id_, "nome": nome, "ano": ano, "mes": int(mes),
                                "dia": int(dia), "arquivo": info["arquivo"]})  # fmt: skip
    return sessoes


def baixar(client: httpx.Client, anos: list[int]) -> bytes:
    """Todo o necessário num zip só: a página de deputados, a presença de cada ano e as
    planilhas de votação (guardadas já abertas, uma por item)."""
    pacote = io.BytesIO()
    with zipfile.ZipFile(pacote, "w", zipfile.ZIP_DEFLATED) as z:
        time.sleep(PAUSA)
        z.writestr("deputados.html", comum._get(client, LISTA, None, 4).content)
        for ano in anos:
            z.writestr(
                f"presenca_{ano}.json", json.dumps(_json(client, "api/presenca/ano", ano=ano))
            )
        indice = []
        for ano in anos:
            for s in baixar_sessoes(client, ano):
                time.sleep(PAUSA)
                dados = comum._get(client, s["arquivo"], None, 4).content
                with zipfile.ZipFile(io.BytesIO(dados)) as itens:
                    for info in itens.infolist():
                        codigo = re.search(r"ITEM-(\d+)-(\d+)", info.filename)
                        if not info.filename.lower().endswith(".xlsx") or not codigo:
                            continue
                        arquivo = f"votacoes/{s['id']}/{codigo.group(2)}.xlsx"
                        z.writestr(arquivo, itens.read(info))
                        indice.append({**s, "arquivo": arquivo, "item": codigo.group(2)})
        z.writestr("votacoes.json", json.dumps(indice, ensure_ascii=False))
    return pacote.getvalue()


# ---------------------------------------------------------------------------- carga


def montar(pacote: bytes, eleitos: list[tuple[int, str | None, str | None]]) -> dict:
    """Do zip bruto ao formato de `sapl.gravar`."""
    with zipfile.ZipFile(io.BytesIO(pacote)) as z:
        lista = deputados(z.read("deputados.html").decode("utf-8"))
        frequencia: dict[str, tuple[int, int]] = {}
        for nome in z.namelist():
            if nome.startswith("presenca_"):
                for slug, (s, p) in presenca(json.loads(z.read(nome)), lista).items():
                    antes = frequencia.get(slug, (0, 0))
                    frequencia[slug] = (antes[0] + s, antes[1] + p)
        civis = nomes_civis(lista, eleitos)
        por_civil = {comum.chave_nome(civil): slug for slug, civil in civis.items()}
        votacoes, votos = [], []
        for item in json.loads(z.read("votacoes.json")):
            lido = votacao(ler_xlsx(z.read(item["arquivo"])))
            if lido is None:
                continue
            dados, linhas = lido
            id_externo = f"{item['id']}-{item['item']}"[:20]
            votacoes.append({"id_externo": id_externo, **dados, "materia_id": None})
            for civil, voto in linhas:
                slug = por_civil.get(comum.chave_nome(civil))
                if slug:
                    votos.append({"votacao": id_externo, "parlamentar": slug,
                                  "voto": texto_do_voto(voto)})  # fmt: skip
    vereadores = [
        {
            "id_externo": d["slug"][:20],
            "nome": comum.nome_proprio(d["nome"]),
            "nome_completo": comum.nome_proprio(civis[d["slug"]]) if d["slug"] in civis else None,
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
            "sessoes": frequencia.get(d["slug"], (None, None))[0],
            "presencas": frequencia.get(d["slug"], (None, None))[1],
        }
        for d in lista
    ]
    for v in votos:  # o id do deputado na gravação é o slug cortado
        v["parlamentar"] = v["parlamentar"][:20]
    return {"base": BASE_VOTOS, "legislatura": None, "vereadores": vereadores,
            "votacoes": votacoes, "votos": votos}  # fmt: skip


def eleitos_do_tse(session: Session) -> list[tuple[int, str | None, str | None]]:
    """Os deputados estaduais do PR eleitos na última eleição já empossada."""
    filtro = [Candidatura.uf == "PR", Candidatura.cargo == "DEPUTADO ESTADUAL"]
    ultima = session.scalar(
        select(Candidatura.ano_eleicao)
        .where(*filtro, Candidatura.ano_eleicao < date.today().year)
        .order_by(Candidatura.ano_eleicao.desc())
        .limit(1)
    )
    return [
        tuple(linha)
        for linha in session.execute(
            select(Candidatura.id, Candidatura.nome_urna, Candidatura.nome).where(
                *filtro,
                Candidatura.ano_eleicao == ultima,
                Candidatura.situacao_turno.like("ELEITO%"),
            )
        )
    ]


def executar(de_raw: Path | None = None) -> int:
    hoje = date.today()
    anos = [hoje.year - 1, hoje.year]

    def carregar(session: Session, pacote: Any, ingestao: FonteIngestao) -> int:
        casa = montar(pacote, eleitos_do_tse(session))
        if len(casa["vereadores"]) < MINIMO_DEPUTADOS:
            raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALEP; abortando.")
        return sapl.gravar(session, None, casa, uf="PR")

    return comum.executar_ingestao(
        FONTE, LISTA, lambda client: baixar(client, anos), carregar, de_raw=de_raw
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um zip bruto sem baixar")
    total = executar(parser.parse_args().de_raw)
    print(f"ALEP: {total} deputados", flush=True)
