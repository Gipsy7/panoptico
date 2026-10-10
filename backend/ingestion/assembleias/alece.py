"""Assembleia Legislativa do Ceará (ALECE): deputados no cargo hoje e projetos de autoria,
pelas páginas públicas do site (a API do portal da transparência da ALECE só tem
contratos, empenhos, licitações e pagamentos; nada legislativo).

- Lista: `www.al.ce.gov.br/deputados` traz os cartões dos 46 titulares (6 deles licenciados)
  e, numa seção à parte, os suplentes em exercício, com partido e foto.
- Ficha: `www.al.ce.gov.br/deputados/{slug}` dá o e-mail e os telefones do gabinete.
- Projetos: o sistema antigo de proposições (`www2.al.ce.gov.br/legislativo/proposicoes`)
  lista, por tabela (lei, lei complementar, emenda à Constituição, decreto legislativo e
  resolução), 15 por página, com número, autor, data de entrada, ementa e situação (OBS).

Indicações não entram (são milhares de páginas de listagem). Os votos nominais saem em
planilhas de relatório de impressão (uma por matéria), sem estrutura aproveitável. Há uma
verba de desempenho parlamentar no portal da transparência, mas só como PDF por deputado.
Uma requisição por vez, com pausa. Grava nas mesmas tabelas das outras casas.
"""

import argparse
import html
import re
import time
from datetime import UTC, date, datetime
from typing import Any

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "alece"
SITE = "https://www.al.ce.gov.br"
LISTA = SITE + "/deputados"
LEGADO = "https://www2.al.ce.gov.br/legislativo/proposicoes/"
PAUSA = 1.0
TABELAS = {
    "projeto_lei": ("PL", "Projeto de Lei"),
    "projeto_compl": ("PLC", "Projeto de Lei Complementar"),
    "projeto_emen": ("PEC", "Proposta de Emenda à Constituição"),
    "projeto_decre": ("PDL", "Projeto de Decreto Legislativo"),
    "projeto_reso": ("PRS", "Projeto de Resolução"),
}
LEGISLATURA = "31_legislatura"
CARTAO = re.compile(
    r'<div\s+class="deputado_card(?P<estado>[^"]*)"[^>]*>\s*'
    r'<img[^>]*src="(?P<foto>[^"]*)"[^>]*>\s*'
    r'<p class="deputado_card--nome[^"]*"><a href="[^"]*/deputados/(?P<slug>[^"/]+)">\s*'
    r"(?P<nome>.*?)\s*</a></p>\s*"
    r'<p class="deputado_card--partido[^"]*">\s*(?P<partido>.*?)\s*</p>',
    re.S,
)


def _limpo(trecho: str | None) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", trecho or "")).split())


def deputados(pagina: str) -> list[dict[str, Any]]:
    """Os cartões da lista. `licenciado`: titular afastado; `suplente`: está na seção dos
    suplentes em exercício. Quem está em exercício é o titular não licenciado e o suplente."""
    corte = pagina.find("Suplentes em Exerc")
    resultado, vistos = [], set()
    for c in CARTAO.finditer(pagina):
        if c.group("slug") in vistos:
            continue
        vistos.add(c.group("slug"))
        suplente = corte >= 0 and c.start() > corte
        licenciado = "licenciado" in c.group("estado")
        resultado.append(
            {
                "slug": c.group("slug"),
                "nome": _limpo(c.group("nome")),
                "partido": _limpo(c.group("partido")) or None,
                "foto": c.group("foto") or None,
                "suplente": suplente,
                "licenciado": licenciado,
            }
        )
    return resultado


def ficha(pagina: str) -> dict[str, str | None]:
    """E-mail e telefones do gabinete, da página do deputado."""

    def campo(rotulo: str) -> str | None:
        m = re.search(
            rf'font-weight-bold">\s*{rotulo}\s*</span>\s*<span[^>]*>\s*(.*?)\s*</span>',
            pagina,
            re.S,
        )
        return _limpo(m.group(1)) or None if m else None

    email = campo("E-mails")
    return {
        "email": email.split()[0].lower() if email else None,
        "telefone": campo("Telefones"),
    }


def _autores(texto: str) -> list[str]:
    """'AUTORIA: DEPUTADA EMILIA PESSOA.' -> ['EMILIA PESSOA']; vários autores separados por
    vírgula ou 'e'. Pode vir só o nome ('LARISSA GASPAR')."""
    limpo = re.sub(r"^\s*autoria\s*:?", "", _limpo(texto), flags=re.I).strip(" .")
    limpo = re.sub(r"\b(deputad[oa]s?|dep\.?)\s+", "", limpo, flags=re.I)
    return [a.strip() for a in re.split(r"\s*(?:,|;|\be\b)\s*", limpo, flags=re.I) if a.strip()]


def _data(valor: str) -> str | None:
    for formato in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(valor.strip(), formato).date().isoformat()
        except ValueError:
            continue
    return None


def _celula(bloco: str, rotulo: str) -> str:
    m = re.search(rf"<b>{rotulo}[^<]*</b></font><br><font[^>]*>(.*?)</font>", bloco, re.S)
    return _limpo(m.group(1)) if m else ""


def proposicoes(pagina: str) -> list[dict[str, Any]]:
    """Os registros de uma página de listagem do sistema antigo."""
    blocos = re.split(r"N&ordm; do Proj\.:", pagina)[1:]
    resultado = []
    for bloco in blocos:
        bloco = "<b>N&ordm; do Proj.:" + bloco
        numero = re.match(r"(\d+)\s*/\s*(\d{2})\b", _celula(bloco, "N&ordm; do Proj."))
        if not numero:
            continue
        ementa = re.search(r"<b>Ementa:</b></font><br><font[^>]*>(.*?)</font></td>", bloco, re.S)
        link = re.search(r"href='([^']+)'", ementa.group(1)) if ementa else None
        resultado.append(
            {
                "numero": int(numero.group(1)),
                "ano": 2000 + int(numero.group(2)),
                "autores": _autores(_celula(bloco, "Autor")),
                "entrada": _data(_celula(bloco, "Entrada")),
                "ementa": _limpo(ementa.group(1)) if ementa else "",
                "situacao": _celula(bloco, "OBS"),
                "url": link.group(1) if link else None,
            }
        )
    return resultado


def _ultima_pagina(pagina: str) -> int:
    return max((int(n) for n in re.findall(r"absolutepage=(\d+)", pagina)), default=1)


def baixar_projetos(client: Any, tabela: str, ano_minimo: int) -> list[dict]:
    """Percorre a listagem de trás para a frente (a mais recente está no fim) até uma página
    sem nada do `ano_minimo` em diante."""
    url = f"{LEGADO}ano.php"
    params = {"nome": LEGISLATURA, "tabela": tabela, "opcao": "T"}
    time.sleep(PAUSA)
    primeira = comum._get(client, url, params, 4).content.decode("utf-8", errors="replace")
    ultima = _ultima_pagina(primeira)
    resultado: list[dict] = []
    for n in range(ultima, 0, -1):
        if n == 1:
            pagina = primeira
        else:
            time.sleep(PAUSA)
            pagina = comum._get(client, url, {**params, "absolutepage": n}, 4).content.decode(
                "utf-8", errors="replace"
            )
        achados = proposicoes(pagina)
        recentes = [p for p in achados if p["ano"] >= ano_minimo]
        resultado += recentes
        if not recentes:
            break
    return resultado


def distribuir(props: list[tuple[str, str, dict]], lista: list[dict]) -> dict[str, list[dict]]:
    """slug do deputado -> projetos (o primeiro autor listado é o primeiro autor)."""
    por_nome = {comum.chave_nome(d["nome"]): d["slug"] for d in lista}
    resultado: dict[str, list[dict]] = {d["slug"]: [] for d in lista}
    for sigla, tipo, p in props:
        for i, autor in enumerate(p["autores"]):
            slug = por_nome.get(comum.chave_nome(autor))
            if slug is None:
                continue
            situacao = p["situacao"].upper()
            resultado[slug].append(
                {
                    "id_externo": f"{sigla}-{p['numero']}-{p['ano']}"[:20],
                    "tipo": tipo,
                    "numero": p["numero"],
                    "ano": p["ano"],
                    "ementa": p["ementa"],
                    "data_apresentacao": p["entrada"],
                    "em_tramitacao": situacao.startswith("TRAMIT") if situacao else None,
                    "primeiro_autor": i == 0,
                    "url": p["url"],
                }
            )
    return resultado


def coletar(hoje: date) -> dict:
    ano_minimo = hoje.year - 1
    with comum.criar_cliente() as client:
        lista = deputados(comum._get(client, LISTA, None, 4).content.decode("utf-8", "replace"))
        for d in lista:
            time.sleep(PAUSA / 2)
            try:
                d.update(
                    ficha(
                        comum._get(client, f"{LISTA}/{d['slug']}", None, 3).content.decode(
                            "utf-8", "replace"
                        )
                    )
                )
            except Exception as erro:  # uma ficha fora do ar não derruba a lista
                print(f"  ficha {d['slug']}: {erro.__class__.__name__}", flush=True)
        props: list[tuple[str, str, dict]] = []
        for tabela, (sigla, tipo) in TABELAS.items():
            # Sem o texto do projeto publicado, o endereço é o da listagem da tabela.
            listagem = f"{LEGADO}numero.php?nome={LEGISLATURA}&tabela={tabela}&opcao=T"
            for p in baixar_projetos(client, tabela, ano_minimo):
                props.append((sigla, tipo, {**p, "url": p["url"] or listagem}))
    autoria = distribuir(props, lista)
    vereadores = []
    for d in lista:
        projetos = autoria[d["slug"]]
        contagem: dict[str, int] = {}
        for p in projetos:
            contagem[p["tipo"]] = contagem.get(p["tipo"], 0) + 1
        vereadores.append(
            {
                "id_externo": d["slug"],
                "nome": d["nome"],
                "nome_completo": None,
                "partido": d["partido"],
                "foto_url": d["foto"],
                "email": d.get("email"),
                "telefone": d.get("telefone"),
                "titular": not d["suplente"],
                "em_exercicio": not d["licenciado"],
                "inicio": None,
                "fim": None,
                "proposicoes_por_tipo": contagem,
                "projetos": projetos,
                "sessoes": None,
                "presencas": None,
            }
        )
    return {
        "base": LISTA,
        "legislatura": None,
        "vereadores": vereadores,
        "votacoes": [],
        "votos": [],
    }


def executar() -> int:
    casa = coletar(date.today())
    exercicio = sum(1 for v in casa["vereadores"] if v["em_exercicio"])
    if exercicio < 40:  # a ALECE tem 46 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {exercicio} deputados em exercício na ALECE; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="CE")
        session.add(
            FonteIngestao(fonte=FONTE, url=LISTA, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(f"ALECE: {total} deputados", flush=True)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
