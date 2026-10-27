"""Assembleia Legislativa de Santa Catarina (ALESC): deputados no cargo hoje e as
proposições de cada um, pelas páginas públicas da ALESC (não há API nem exportação).

- Deputados: a página oficial de deputados (www.alesc.sc.gov.br/deputados), com nome,
  partido e foto de cada um (40).
- Proposições: o e-Legis (portalelegis.alesc.sc.gov.br) lista as do "processo legislativo"
  (projetos, guardados com ementa) e as da "atividade parlamentar" (requerimentos,
  indicações, moções e pedidos de informação, só como contagem), 10 por página, filtradas
  por data de entrada. A autoria vem como "Deputado Altair Silva".
- Gastos de gabinete: a Transparência da ALESC publica um CSV por ano
  (transparencia.alesc.sc.gov.br/gabinetes-parlamentares/csv/AAAA; o endereço antigo
  `gabinetes_csv.php?ano=` redireciona para ele). Uma linha por pagamento (verba, descrição,
  "conta" = nome do deputado, favorecido, trecho, data, valor); entra só a soma por deputado,
  mês e descrição. Favorecido e trecho (diárias de funcionários) não são guardados.
- Presença: o e-Legis lista as sessões plenárias (`/sessoes-plenarias`, mais recentes
  primeiro) e cada uma tem a página `/presenca` com "Presente" ou "Ausência justificada" por
  deputado.
- Votos: a "Ordem do Dia" de cada sessão (`/sessoes-plenarias/{id}/ordem-do-dia`) marca cada
  item como "Votação nominal" ou simbólica; nos nominais o botão "Extrato de votação" carrega
  `/extrato-votacao/{código}`, que lista deputado e voto. Essa rota responde 405 a um GET
  comum e 200 à mesma chamada AJAX que o botão faz (cabeçalho `X-Requested-With`, posto pelo
  script do site); não há captcha, login nem robots que vede (o `/robots.txt` é 404). Os votos
  só vão ao deputado de nome igual ao do site (ou do TSE); os totais contam o extrato todo.

Uma requisição por vez, com pausa. Grava nas mesmas tabelas das outras casas, pela
gravação do conector SAPL.
"""

import argparse
import csv
import html
import io
import json
import re
import time
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.assembleias import base
from ingestion.camaras import sapl
from ingestion.identidade import casar_nome

FONTE = "alesc"
FONTE_VOTOS = "alesc_votos"  # escopo da fila de apelidos dos nomes nos extratos de votos
GASTOS = "https://transparencia.alesc.sc.gov.br/gabinetes-parlamentares/csv/{ano}"
DEPUTADOS = "https://www.alesc.sc.gov.br/deputados"
ELEGIS = "https://portalelegis.alesc.sc.gov.br"
LISTAS = ("processo-legislativo", "atividade-parlamentar")
PAUSA = 0.5
TIPOS = {
    "PL.": "Projeto de Lei",
    "PLC": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PRS": "Projeto de Resolução",
    "PDL": "Projeto de Decreto Legislativo",
    "RQS": "Requerimento",
    "IND": "Indicação",
    "MOC": "Moção",
    "PIC": "Pedido de Informação",
    "OFL": "Ofício Legislativo",
    "RCC": "Requerimento de Comissões",
    "RQC": "Requerimento de Frente, Fórum, CPI ou Comissão Mista",
    "PSA": "Proposta de Sustação de Ato",
}
CARTAO = re.compile(
    r'<a href="/proposicoes/(?P<id>[A-Za-z0-9]+)">(?P<sigla>[^<]+)</a>\s*</h4>'
    r'(?P<corpo>.*?)(?=<div class="card card-alesc|<nav|$)',
    re.S,
)
CAMPO = r'fw-bold[^>]*>\s*{rotulo}\s*</div>\s*<div class="col-lg-10">(?P<valor>.*?)</div>'
TITULO = re.compile(r"^Deputad[oa]\s+", re.I)


def _limpo(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", trecho or "")).split())


def deputados(pagina: str) -> list[dict[str, str]]:
    """Os cartões da página oficial: slug, nome, partido e foto."""
    vistos, resultado = set(), []
    for bloco in re.finditer(
        r'<a href="https://www\.alesc\.sc\.gov\.br/deputado/(?P<slug>[a-z0-9-]+)/">\s*'
        r'<div class="row align-items-center gx-3">(?P<corpo>.*?)</a>',
        pagina,
        re.S,
    ):
        slug, corpo = bloco.group("slug"), bloco.group("corpo")
        if slug in vistos:
            continue
        vistos.add(slug)
        nome = re.search(r'<h3 class="lab-title-news">(.*?)</h3>', corpo, re.S)
        partido = re.search(r'<span class="lab-button[^"]*"[^>]*>(.*?)</span>', corpo, re.S)
        foto = re.search(r'<img src="([^"]+)"', corpo)
        if nome:
            resultado.append({"slug": slug, "nome": _limpo(nome.group(1)),
                              "partido": _limpo(partido.group(1)) if partido else None,
                              "foto": foto.group(1) if foto else None})  # fmt: skip
    return resultado


def proposicoes(pagina: str) -> list[dict[str, Any]]:
    """Os cartões de uma página do e-Legis."""
    resultado = []
    for cartao in CARTAO.finditer(pagina):
        corpo = cartao.group("corpo")
        ementa = re.search(r'<p class="mb-1[^"]*"[^>]*>(.*?)</p>', corpo, re.S)
        entrada = re.search(CAMPO.format(rotulo="Entrada"), corpo, re.S)
        autoria = re.search(CAMPO.format(rotulo="Autoria"), corpo, re.S)
        itens = re.findall(r"<li>(.*?)</li>", autoria.group("valor"), re.S) if autoria else []
        autores = [_limpo(a) for a in itens]
        sigla = _limpo(cartao.group("sigla"))
        resultado.append(
            {
                "id": cartao.group("id"),
                "sigla": sigla,
                "ementa": _limpo(ementa.group(1)) if ementa else "",
                "entrada": _limpo(entrada.group("valor")) if entrada else "",
                "autores": [TITULO.sub("", a).strip() for a in autores],
            }
        )
    return resultado


def tipo_e_numero(sigla: str) -> tuple[str, int | None, int | None]:
    """'PL./0640/2026' -> ('Projeto de Lei', 640, 2026)."""
    achado = re.match(r"([A-Z]+\.?)\s*/?\s*(\d+)/(\d{4})", sigla.replace(" ", ""))
    if not achado:
        return sigla, None, None
    prefixo = achado.group(1)
    return TIPOS.get(prefixo, prefixo.rstrip(".")), int(achado.group(2)), int(achado.group(3))


def _data(valor: str) -> str | None:
    try:
        return datetime.strptime(valor.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def distribuir(props: list[dict], nomes: set[str]) -> dict[str, dict]:
    chave = {comum.chave_nome(n): n for n in nomes}
    por_deputado: dict[str, dict] = {n: {"contagem": {}, "projetos": []} for n in nomes}
    for p in props:
        tipo, numero, ano = tipo_e_numero(p["sigla"])
        for ordem, autor in enumerate(p["autores"]):
            nome = chave.get(comum.chave_nome(autor))
            if nome is None:
                continue
            dep = por_deputado[nome]
            dep["contagem"][tipo] = dep["contagem"].get(tipo, 0) + 1
            if p["lista"] == "processo-legislativo":
                dep["projetos"].append(
                    {
                        "id_externo": p["id"],
                        "tipo": tipo,
                        "numero": numero,
                        "ano": ano,
                        "ementa": p["ementa"],
                        "data_apresentacao": _data(p["entrada"]),
                        "em_tramitacao": None,
                        "primeiro_autor": ordem == 0,
                        "url": f"{ELEGIS}/proposicoes/{p['id']}",
                    }
                )
    return por_deputado


def _valor(texto: str) -> Decimal:
    """'1.018,80' -> Decimal('1018.80')."""
    return Decimal(texto.strip().replace(".", "").replace(",", ".") or "0")


def gastos_do_csv(conteudo: bytes) -> dict[str, dict[tuple[int, int, str], Decimal]]:
    """O CSV anual (UTF-8 com BOM, separado por ponto e vírgula) -> conta -> {(ano, mês,
    descrição): soma}. Devolução de diária vem com valor negativo e entra na soma."""
    texto = conteudo.decode("utf-8-sig")
    resultado: dict[str, dict[tuple[int, int, str], Decimal]] = {}
    for linha in csv.DictReader(io.StringIO(texto, newline=""), delimiter=";"):
        data = re.match(r"(\d{2})/(\d{2})/(\d{4})", (linha.get("Data de Referência") or "").strip())
        conta = " ".join((linha.get("Conta") or "").split())
        if not data or not conta:
            continue
        categoria = " ".join((linha.get("Descrição") or linha.get("Verba") or "Outros").split())
        chave = (int(data[3]), int(data[2]), categoria[:200])
        por_conta = resultado.setdefault(conta, {})
        por_conta[chave] = por_conta.get(chave, Decimal(0)) + _valor(linha.get("Valor") or "")
    return resultado


def distribuir_gastos(
    contas: dict[str, dict[tuple[int, int, str], Decimal]], nomes: list[str]
) -> tuple[dict[str, list[dict]], list[str]]:
    """Liga cada conta ao deputado pelo nome (exato e único, ver `casar_nome`). Devolve os
    gastos por nome de deputado e as contas que não casaram (ex-deputados e suplentes)."""
    pares = list(enumerate(nomes))
    por_deputado: dict[str, list[dict]] = {}
    sobras = []
    for conta, itens in contas.items():
        apelido = re.findall(r"\(([^)]+)\)", conta)  # "Ana Paula da Silva (Paulinha)"
        achado = casar_nome([conta, *apelido], pares)
        if achado is None:
            sobras.append(conta)
            continue
        lista = por_deputado.setdefault(nomes[achado], [])
        lista += [
            {"ano": a, "mes": m, "categoria": c, "valor": v}
            for (a, m, c), v in sorted(itens.items())
        ]
    return por_deputado, sobras


def baixar_gastos(client: Any, anos: list[int]) -> dict[int, bytes]:
    """Um CSV por ano, gravado no bruto (`data/raw/alesc/`) antes de processar."""
    arquivos = {}
    for ano in anos:
        time.sleep(PAUSA)
        conteudo = comum.get_bytes(client, GASTOS.format(ano=ano), 4)
        comum.salvar_raw(FONTE, conteudo, f"gastos_{ano}_", ".csv.gz")
        arquivos[ano] = conteudo
    return arquivos


def sessoes_realizadas(pagina: str) -> list[dict]:
    """Os cartões da lista de sessões plenárias do e-Legis: id, nome, data e situação."""
    resultado = []
    for cartao in re.split(r'<div class="card card-alesc', pagina)[1:]:
        id_ = re.search(r"/sessoes-plenarias/(\w+)/presenca", cartao)
        if not id_:
            continue
        nome = re.search(r'<h4 class="mb-1">(.*?)</h4>', cartao, re.S)
        quando = re.search(r"(\d{2})/(\d{2})/(\d{4})", cartao)
        situacao = re.search(r"badge rounded-pill[^>]*>(.*?)</span>", cartao, re.S)
        resultado.append(
            {
                "id": id_.group(1),
                "nome": _limpo(nome.group(1)) if nome else "",
                "data": f"{quando[3]}-{quando[2]}-{quando[1]}" if quando else None,
                "situacao": _limpo(situacao.group(1)) if situacao else "",
            }
        )
    return resultado


def presenca_da_sessao(pagina: str) -> list[tuple[str, str]]:
    """(deputado, situação) de cada linha da lista de presença: 'Presente' ou 'Ausência
    justificada'. Sessão que ainda não aconteceu vem sem linhas."""
    return [
        (_limpo(n), _limpo(s))
        for n, s in re.findall(r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>", pagina, re.S)
    ]


def contar_presenca(sessoes: list[dict], nomes: list[str]) -> dict[str, tuple[int, int]]:
    """nome -> (sessões em que constava na lista, presenças) nas sessões realizadas. Um nome da
    lista só conta se casar com um único deputado (ver `casar_nome`)."""
    pares = list(enumerate(nomes))
    ligacao: dict[str, str | None] = {}
    total: dict[str, int] = {}
    presentes: dict[str, int] = {}
    for sessao in sessoes:
        if sessao["situacao"] != "Realizada":
            continue
        for nome, situacao in sessao["linhas"]:
            if nome not in ligacao:
                achado = casar_nome([nome], pares)
                ligacao[nome] = nomes[achado] if achado is not None else None
            deputado = ligacao[nome]
            if deputado:
                total[deputado] = total.get(deputado, 0) + 1
                presentes[deputado] = presentes.get(deputado, 0) + (situacao == "Presente")
    return {n: (total[n], presentes.get(n, 0)) for n in total}


def baixar_presenca(client: Any, anos: list[int]) -> list[dict]:
    """Sessões desde 1º de janeiro do primeiro ano, com a lista de presença das realizadas
    (a lista de sessões vem da mais recente para a mais antiga)."""
    inicio = f"{min(anos)}-01-01"
    sessoes, pagina = [], 1
    while True:
        time.sleep(PAUSA)
        itens = sessoes_realizadas(
            comum._get(client, f"{ELEGIS}/sessoes-plenarias", {"page": pagina}, 4).text
        )
        if not itens:
            break
        sessoes += [s for s in itens if s["data"] and s["data"] >= inicio]
        if max(s["data"] or "" for s in itens) < inicio:
            break
        pagina += 1
    for s in sessoes:
        s["linhas"] = []
        if s["situacao"] == "Realizada":
            time.sleep(PAUSA)
            url = f"{ELEGIS}/sessoes-plenarias/{s['id']}/presenca"
            s["linhas"] = presenca_da_sessao(comum._get(client, url, None, 4).text)
    comum.salvar_raw(FONTE, sessoes, "presenca_")
    return sessoes


VOTOS = {"SIM": "Sim", "NAO": "Não", "ABSTENCAO": "Abstenção", "ABSTER": "Abstenção"}


def votacoes_nominais(pagina: str) -> list[dict]:
    """Os itens da 'Ordem do Dia' de uma sessão que tiveram votação nominal e têm extrato:
    proposição, resultado ('Aprovado', 'Rejeitado'...), ementa e o código do extrato. Itens
    em votação simbólica, retirados de pauta ou sem extrato ficam de fora."""
    resultado = []
    for cartao in re.split(r'<div class="border-bottom mb-3">', pagina)[1:]:
        extrato = re.search(r'hx-get="/extrato-votacao/(\w+)"', cartao)
        badges = [_limpo(b) for b in re.findall(r'<span class="badge[^>]*>(.*?)</span>', cartao)]
        if not extrato or not any(b.lower() == "votação nominal" for b in badges):
            continue
        proposicao = re.search(r'<a href="/proposicoes/(\w+)">([^<]+)</a>', cartao)
        veredito = next((b for b in badges if "nominal" not in b.lower()), None)
        ementa = re.search(r'<p class="fst-italic[^>]*>(.*?)</p>', cartao, re.S)
        resultado.append(
            {
                "extrato": extrato.group(1),
                "proposicao": _limpo(proposicao.group(2)) if proposicao else "",
                "proposicao_id": proposicao.group(1) if proposicao else None,
                "resultado": veredito,
                "ementa": _limpo(ementa.group(1)) if ementa else "",
            }
        )
    return resultado


def votos_do_extrato(fragmento: str) -> list[tuple[str, str]]:
    """(deputado, voto) de cada cartão do extrato de votação (o nome e o voto, só)."""
    pares = re.findall(
        r"<div>([^<]+)</div>\s*<div><span class=\"badge[^>]*>([^<]+)</span></div>", fragmento
    )
    return [
        (" ".join(html.unescape(n).split()), " ".join(html.unescape(v).split())) for n, v in pares
    ]


def texto_do_voto(voto: str) -> str:
    return VOTOS.get(comum.chave_nome(voto)) or voto.strip().capitalize()[:30]


def baixar_votacoes(client: Any, sessoes: list[dict]) -> dict[str, bytes]:
    """Para cada sessão realizada, a 'Ordem do Dia' e, de cada item com votação nominal, o
    extrato de votos. O extrato do e-Legis só responde à chamada AJAX que a própria página faz
    (cabeçalho `X-Requested-With`, como o script do site); sem ele a rota devolve 405. Não há
    captcha, login nem bloqueio: é a mesma requisição que o botão 'Extrato de votação' faz."""
    arquivos: dict[str, bytes] = {}
    indice = []
    for s in sessoes:
        if s.get("situacao") != "Realizada":
            continue
        time.sleep(PAUSA)
        pagina = comum._get(client, f"{ELEGIS}/sessoes-plenarias/{s['id']}/ordem-do-dia", None, 4)
        arquivos[f"od_{s['id']}.html"] = pagina.content
        indice.append({"sessao": s["id"], "data": s["data"], "nome": s.get("nome", "")})
        for item in votacoes_nominais(pagina.content.decode("utf-8", "replace")):
            time.sleep(PAUSA)
            resposta = client.get(
                f"{ELEGIS}/extrato-votacao/{item['extrato']}",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            arquivos[f"ex_{item['extrato']}.html"] = resposta.raise_for_status().content
    arquivos["indice.json"] = json.dumps(indice, ensure_ascii=False).encode("utf-8")
    return arquivos


def empacotar(arquivos: dict[str, bytes]) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in sorted(arquivos.items()):
            z.writestr(nome, conteudo)
    return memoria.getvalue()


def montar_votacoes(
    arquivos: dict[str, bytes], deputados_da_casa: list[dict], tse: list[tuple[str, str]]
) -> tuple[list[dict], list[dict]]:
    """Do bruto (ordens do dia e extratos) às votações e votos de `sapl.gravar`. O voto só vai
    para o deputado cujo nome no extrato é igual (sem acento nem caixa) ao do site ou ao nome
    de urna/civil do TSE da mesma candidatura; os totais da votação contam todo o extrato."""
    indice = json.loads(arquivos["indice.json"])
    por_nome = {comum.chave_nome(d["nome"]): d["slug"][:20] for d in deputados_da_casa}
    totais: dict[str, tuple[int, Decimal]] = {}
    for n, _ in _todos_os_nomes(arquivos):  # votos por nome; sem valor em reais
        votos_n, _zero = totais.get(comum.chave_nome(n), (0, Decimal(0)))
        totais[comum.chave_nome(n)] = (votos_n + 1, Decimal(0))
    ligados, _ = base.ligar_nomes(FONTE_VOTOS, totais, deputados_da_casa, tse)
    votacoes, votos, vistos = [], [], set()
    for sessao in indice:
        pagina = arquivos[f"od_{sessao['sessao']}.html"].decode("utf-8", "replace")
        for item in votacoes_nominais(pagina):
            nome_arq = f"ex_{item['extrato']}.html"
            if item["extrato"] in vistos or nome_arq not in arquivos:
                continue
            vistos.add(item["extrato"])
            linhas = votos_do_extrato(arquivos[nome_arq].decode("utf-8", "replace"))
            if not linhas:
                continue
            textos = [texto_do_voto(v) for _, v in linhas]
            materia = (
                f"{item['proposicao']}: {item['ementa']}"[:500]
                if item["ementa"]
                else item["proposicao"]
            )
            votacoes.append(
                {
                    "id_externo": item["extrato"][:20],
                    "materia": materia,
                    "resultado": item["resultado"],
                    "sim": textos.count("Sim"),
                    "nao": textos.count("Não"),
                    "abstencoes": textos.count("Abstenção"),
                    "data": sessao["data"],
                    "materia_id": None,
                    # O código da proposição no e-Legis é o mesmo `id_externo` do projeto.
                    "materia_id_externo": item["proposicao_id"],
                    "materia_ementa": item["ementa"] or None,
                    "url": f"{ELEGIS}/sessoes-plenarias/{sessao['sessao']}/ordem-do-dia",
                }
            )
            for (nome, _), texto in zip(linhas, textos, strict=True):
                chave = comum.chave_nome(nome)
                alvo = ligados.get(chave)
                slug = por_nome.get(comum.chave_nome(alvo)) if alvo else None
                if slug:
                    votos.append(
                        {"votacao": item["extrato"][:20], "parlamentar": slug, "voto": texto}
                    )
    return votacoes, votos


def _todos_os_nomes(arquivos: dict[str, bytes]) -> list[tuple[str, str]]:
    achados = []
    for nome_arq, conteudo in arquivos.items():
        if nome_arq.startswith("ex_"):
            achados += votos_do_extrato(conteudo.decode("utf-8", "replace"))
    return achados


def baixar_lista(client: Any, lista: str, ano: int) -> list[dict]:
    """Todas as páginas de uma lista do e-Legis num ano, uma requisição por vez."""
    params = {"inicio": f"{ano}-01-01", "fim": f"{ano}-12-31"}
    resultado, pagina = [], 1
    while True:
        time.sleep(PAUSA)
        resposta = comum._get(
            client, f"{ELEGIS}/proposicoes/{lista}", {**params, "page": pagina}, 4
        )
        itens = proposicoes(resposta.text)
        for item in itens:
            item["lista"] = lista
        resultado += itens
        total = re.search(r"Exibindo [\d.]+ - ([\d.]+) de ([\d.]+)", resposta.text)
        if not itens or not total or total.group(1) == total.group(2):
            return resultado
        pagina += 1


def coletar(
    hoje: date,
    gastos_raw: list[Path] | None = None,
    presenca_raw: Path | None = None,
    votos_raw: Path | None = None,
) -> dict:
    with comum.criar_cliente() as client:
        lista = deputados(comum._get(client, DEPUTADOS, None, 4).text)
        anos = [hoje.year - 1, hoje.year]
        if gastos_raw:  # --gastos-de-raw: reprocessa os CSVs já guardados
            csvs = [comum.carregar_raw(Path(a)) for a in gastos_raw]
        else:
            csvs = list(baixar_gastos(client, anos).values())
        if presenca_raw:
            sessoes = comum.carregar_raw(presenca_raw)
        else:
            sessoes = baixar_presenca(client, anos)
        if votos_raw:  # --votos-de-raw: reprocessa o zip de ordens do dia e extratos
            with zipfile.ZipFile(votos_raw) as z:
                extratos = {n: z.read(n) for n in z.namelist()}
        else:
            extratos = baixar_votacoes(client, sessoes)
            raw = comum.salvar_raw(FONTE, empacotar(extratos), "votacoes_", ".zip")
            print(f"  bruto das votações: {raw}", flush=True)
        props = []
        for ano in (hoje.year - 1, hoje.year):
            for nome_lista in LISTAS:
                props += baixar_lista(client, nome_lista, ano)
    autoria = distribuir(props, {d["nome"] for d in lista})
    contas: dict[str, dict[tuple[int, int, str], Decimal]] = {}
    for conteudo in csvs:
        for conta, itens in gastos_do_csv(conteudo).items():
            contas.setdefault(conta, {}).update(itens)
    with SessionLocal() as session:
        tse = base.nomes_do_tse(session, "SC")
    votacoes, votos = montar_votacoes(extratos, lista, tse)
    print(f"  votações nominais: {len(votacoes)}; votos de deputados da lista: {len(votos)}")
    frequencia = contar_presenca(sessoes, [d["nome"] for d in lista])
    gastos, sobras = distribuir_gastos(contas, [d["nome"] for d in lista])
    print(f"  gastos: {len(gastos)} deputados; contas sem deputado: {sobras}", flush=True)
    vereadores = [
        {
            "id_externo": d["slug"][:20],
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
            "proposicoes_por_tipo": autoria[d["nome"]]["contagem"],
            "projetos": autoria[d["nome"]]["projetos"],
            "gastos": gastos.get(d["nome"], []),
            "sessoes": frequencia.get(d["nome"], (None, None))[0],
            "presencas": frequencia.get(d["nome"], (None, None))[1],
        }
        for d in lista
    ]
    return {
        "base": ELEGIS,
        "legislatura": None,
        "vereadores": vereadores,
        "votacoes": votacoes,
        "votos": votos,
    }


def executar(
    gastos_raw: list[Path] | None = None,
    presenca_raw: Path | None = None,
    votos_raw: Path | None = None,
) -> int:
    casa = coletar(date.today(), gastos_raw, presenca_raw, votos_raw)
    if len(casa["vereadores"]) < 30:  # a ALESC tem 40 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALESC; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="SC")
        session.add(
            FonteIngestao(fonte=FONTE, url=ELEGIS, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(f"ALESC: {total} deputados", flush=True)
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument(
        "--gastos-de-raw",
        type=Path,
        nargs="+",
        help="CSVs de gastos já guardados em data/raw/alesc",
    )
    parser.add_argument("--presenca-de-raw", type=Path, help="JSON de presença já guardado")
    parser.add_argument("--votos-de-raw", type=Path, help="zip de votações já guardado")
    args = parser.parse_args()
    executar(args.gastos_de_raw, args.presenca_de_raw, args.votos_de_raw)
