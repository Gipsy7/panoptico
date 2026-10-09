"""Câmara Legislativa do Distrito Federal (CLDF): deputados distritais no cargo hoje e as
proposições de cada um, pela API pública do Processo Legislativo Eletrônico (PLE), sem
autenticação e documentada no catálogo de dados abertos da CLDF.

Grava nas mesmas tabelas das assembleias, com UF "DF", pela gravação do conector SAPL.
- Deputados: autores do tipo PARLAMENTAR com situação ATIVO (24, todas as cadeiras), com
  o nome como o PLE escreve ("Deputado Fábio Felix"); o partido não vem preenchido (o perfil
  mostra o do eleito no TSE).
- Proposições do ano atual e do anterior; a autoria vem em texto ("Deputado X, Deputada
  Y"). Projetos guardam a ementa; indicações, moções e requerimentos viram contagem.
- Gastos do gabinete: verbas indenizatórias do catálogo de dados abertos (um XLSX por
  ano, com o CPF do deputado), somadas por mês e categoria. O deputado é achado pelo CPF
  (candidatura do TSE) e, sem ele, pelo nome.
- Votos e presença não estão na API.
"""

import argparse
import calendar
import io
import re
import time
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from xml.etree import ElementTree

import httpx
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Candidatura, FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "cldf"
API = "https://ple.cl.df.gov.br/pleservico/api/public"
SITE = "https://ple.cl.df.gov.br/#/proposicao/buscar"
POR_PAGINA = 100
PAUSA = 0.3
TITULO = re.compile(r"^Deputad[oa]\s+", re.I)
PROJETO = re.compile(r"^(projeto|proposta de emenda)", re.I)
CATALOGO_VERBAS = "https://dados.cl.df.gov.br/api/3/action/package_show?id=verbas-indenizatorias"
XLSX = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
ROMANO = re.compile(r"^[IVXL]+\s*-\s*")


def _post(client: Any, url: str, params: dict, corpo: dict, tentativas: int = 4) -> dict:
    """POST com novas tentativas: o servidor do PLE às vezes derruba a conexão."""
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = client.post(url, params=params, json=corpo)
            if resposta.status_code < 500:
                return resposta.raise_for_status().json()
        except httpx.TransportError:
            if tentativa == tentativas:
                raise
        time.sleep(3 * tentativa)
    return resposta.raise_for_status().json()


def nome_sem_titulo(nome: str | None) -> str:
    """'Deputado Fábio Felix ' -> 'Fábio Felix'."""
    return TITULO.sub("", (nome or "").strip()).strip()


def autores_de(autoria: str | None) -> list[str]:
    """'Deputado Martins Machado, Deputada Paula Belmonte' -> nomes sem título, sem repetir."""
    nomes = []
    for parte in (autoria or "").split(","):
        nome = nome_sem_titulo(parte)
        if nome and nome not in nomes:
            nomes.append(nome)
    return nomes


def _numero(sigla_numero_ano: str | None) -> int | None:
    """'REQ 3090/2026' -> 3090."""
    achado = re.search(r"(\d+)/\d{4}", sigla_numero_ano or "")
    return int(achado.group(1)) if achado else None


def distribuir(props: list[dict], nomes: set[str]) -> dict[str, dict]:
    chave = {comum.chave_nome(n): n for n in nomes}
    por_deputado: dict[str, dict] = {n: {"contagem": {}, "projetos": []} for n in nomes}
    for p in props:
        tipo = (p.get("tipoProposicao") or "").strip() or "Proposição"
        for ordem, autor in enumerate(autores_de(p.get("autoria"))):
            nome = chave.get(comum.chave_nome(autor))
            if nome is None:
                continue
            dep = por_deputado[nome]
            dep["contagem"][tipo] = dep["contagem"].get(tipo, 0) + 1
            if PROJETO.match(tipo):
                dep["projetos"].append(
                    {
                        "id_externo": str(p["id"]),
                        "tipo": tipo,
                        "numero": _numero(p.get("siglaNumeroAno")),
                        "ano": int(p["dataLeitura"][:4]) if p.get("dataLeitura") else None,
                        "ementa": " ".join((p.get("ementa") or "").split()),
                        "data_apresentacao": p.get("dataLeitura"),
                        "em_tramitacao": None,
                        "primeiro_autor": ordem == 0,
                        "url": f"{API}/proposicao/{p['id']}",
                    }
                )
    return por_deputado


def proposicoes(client: Any, ano: int, ate: date) -> list[dict]:
    """As proposições lidas no ano, mês a mês (consultas pequenas), parando pelo total de
    páginas que a API informa (o indicador de última página não é confiável)."""
    resultado = []
    for mes in range(1, 13):
        inicio = date(ano, mes, 1)
        if inicio > ate:
            break
        fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
        corpo = {"ano": str(ano), "dataInicio": inicio.isoformat(), "dataFim": fim.isoformat()}
        pagina = 0
        while True:
            time.sleep(PAUSA)
            dados = _post(
                client,
                f"{API}/proposicao/filter",
                {"page": pagina, "size": POR_PAGINA, "sort": "id,ASC"},
                corpo,
            )
            resultado += dados.get("content", [])
            pagina += 1
            if pagina >= dados.get("totalPages", 0):
                break
    return resultado


def ler_xlsx(conteudo: bytes) -> list[dict[str, str]]:
    """Primeira planilha de um XLSX como lista de dicionários, sem dependência nova (o
    XLSX é um zip de XML)."""
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        textos = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ElementTree.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{XLSX}si"):
                textos.append("".join(t.text or "" for t in si.iter(f"{XLSX}t")))
        folha = ElementTree.fromstring(z.read("xl/worksheets/sheet1.xml"))
    linhas = []
    for linha in folha.iter(f"{XLSX}row"):
        valores = {}
        for celula in linha.iter(f"{XLSX}c"):
            coluna = re.sub(r"\d", "", celula.get("r", ""))
            v = celula.find(f"{XLSX}v")
            if v is not None:
                texto = v.text or ""
            else:
                texto = "".join(t.text or "" for t in celula.iter(f"{XLSX}t"))
            if celula.get("t") == "s" and texto:
                texto = textos[int(texto)]
            valores[coluna] = texto.strip()
        linhas.append(valores)
    if not linhas:
        return []
    cabecalho = linhas[0]
    return [{cabecalho[c]: v for c, v in lin.items() if c in cabecalho} for lin in linhas[1:]]


def _data(valor: str, ordem: str) -> date | None:
    """Número de série do Excel (46024 -> 2026-01-02) ou data com barras, na ordem do
    arquivo ("dm" ou "md": o de 2025 usa mês/dia/ano)."""
    valor = (valor or "").strip()
    if re.fullmatch(r"\d+(\.\d+)?", valor):
        return date(1899, 12, 30) + timedelta(days=int(float(valor)))
    partes = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", valor)
    if not partes:
        return None
    a, b, ano = (int(x) for x in partes.groups())
    dia, mes = (a, b) if ordem == "dm" else (b, a)
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def ordem_das_datas(valores: list[str]) -> str:
    """'dm' ou 'md', pelo arquivo inteiro: um primeiro número acima de 12 só pode ser dia;
    um segundo acima de 12, só dia na segunda posição."""
    for valor in valores:
        partes = re.fullmatch(r"(\d{1,2})/(\d{1,2})/\d{4}", (valor or "").strip())
        if partes and int(partes.group(1)) > 12:
            return "dm"
        if partes and int(partes.group(2)) > 12:
            return "md"
    return "dm"


def _sem_plural(palavra: str) -> str:
    return palavra[:-1] if len(palavra) > 3 and palavra.endswith("S") else palavra


def chave_categoria(texto: str) -> str:
    """Mesma categoria escrita de jeitos diferentes ("Locação de Veículos", "Locação de
    veículo") -> a mesma chave: sem caixa, acento, partículas nem plural."""
    palavras = comum.chave_nome(ROMANO.sub("", texto or "")).split()
    return " ".join(_sem_plural(p) for p in palavras if p.lower() not in comum.PARTICULAS)


def categoria(texto: str) -> str:
    """'VIII - Divulgação de atividade parlamentar' -> 'Divulgação de atividade parlamentar'."""
    limpo = comum.limpar_categoria(ROMANO.sub("", (texto or "").strip()))
    return limpo[:200] or "Não informada"


# Os arquivos mudam o nome das colunas de um ano para outro.
COLUNAS = {
    "cpf": ("CPF_PARLAMENTAR", "CPF do(a) Deputado(a)"),
    "nome": ("NOME_PARLAMENTAR", "Nome do(a) Deputado(a)"),
    "data": ("DATA_COMPROVANTE", "Data do Recibo/NF"),
    "valor": ("VALOR_DESPESA", "Valor"),
    "classificacao": ("CLASSIFICACAO", "Classificação"),
}


def padronizar(linhas: list[dict]) -> list[dict]:
    """Colunas com nomes únicos e datas já convertidas, conforme o formato do arquivo."""

    def campo(linha: dict, nome: str) -> str:
        return next((linha[c] for c in COLUNAS[nome] if c in linha), "")

    ordem = ordem_das_datas([campo(lin, "data") for lin in linhas])
    return [
        {
            "cpf": re.sub(r"\D", "", campo(lin, "cpf")),
            "nome": campo(lin, "nome"),
            "data": _data(campo(lin, "data"), ordem),
            "valor": campo(lin, "valor"),
            "classificacao": campo(lin, "classificacao"),
        }
        for lin in linhas
    ]


def somar_gastos(linhas: list[dict], anos: set[int]) -> dict[str, list[dict]]:
    """CPF do deputado -> gastos somados por ano, mês e categoria. Categorias com a mesma
    chave são somadas juntas e exibidas com a grafia mais comum."""
    grafias: dict[str, Counter] = defaultdict(Counter)
    for lin in linhas:
        grafias[chave_categoria(lin["classificacao"])][categoria(lin["classificacao"])] += 1
    exibicao = {chave: contagem.most_common(1)[0][0] for chave, contagem in grafias.items()}
    soma: dict[tuple, Decimal] = defaultdict(Decimal)
    for lin in linhas:
        quando = lin["data"]
        if quando is None or quando.year not in anos or len(lin["cpf"]) != 11:
            continue
        try:
            valor = Decimal(lin["valor"] or "0").quantize(Decimal("0.01"))
        except InvalidOperation:
            continue
        cat = exibicao[chave_categoria(lin["classificacao"])]
        soma[(lin["cpf"], quando.year, quando.month, cat)] += valor
    resultado: dict[str, list[dict]] = defaultdict(list)
    for (cpf, ano, mes, cat), valor in soma.items():
        resultado[cpf].append({"ano": ano, "mes": mes, "categoria": cat, "valor": valor})
    return resultado


def baixar_verbas(client: Any, anos: set[int]) -> list[dict]:
    """O XLSX de cada ano do período, pelo catálogo (o nome do recurso traz o ano)."""
    recursos = comum.get_json(client, CATALOGO_VERBAS)["result"]["resources"]
    linhas = []
    for ano in sorted(anos):
        recurso = next(
            (r for r in recursos if str(ano) in r.get("name", "") and r.get("format") == "XLSX"),
            None,
        )
        if recurso:
            linhas += padronizar(ler_xlsx(comum.get_bytes(client, recurso["url"])))
    return linhas


def deputado_por_cpf(session: Any, nomes: set[str]) -> dict[str, str]:
    """CPF -> nome do deputado ativo, pela candidatura a deputado distrital no TSE (nome de
    urna ou civil igual ao nome no PLE)."""
    chave = {comum.chave_nome(n): n for n in nomes}
    resultado = {}
    for cpf, urna, civil in session.execute(
        select(Candidatura.cpf, Candidatura.nome_urna, Candidatura.nome).where(
            Candidatura.cargo == "DEPUTADO DISTRITAL", Candidatura.cpf.is_not(None)
        )
    ):
        nome = chave.get(comum.chave_nome(urna)) or chave.get(comum.chave_nome(civil))
        if nome:
            resultado[cpf] = nome
    return resultado


def anexar_gastos(session: Any, casa: dict) -> int:
    """Põe os gastos em cada deputado: pelo CPF (via TSE) e, sem ele, pelo nome sem título
    da planilha. Devolve quantos CPFs da planilha ficaram sem deputado."""
    nomes = {v["nome"] for v in casa["vereadores"]}
    por_cpf = deputado_por_cpf(session, nomes)
    chave = {comum.chave_nome(n): n for n in nomes}
    verbas = casa.pop("verbas")
    nome_do_cpf = {lin["cpf"]: nome_sem_titulo(lin["nome"]) for lin in verbas}
    por_nome: dict[str, list] = defaultdict(list)
    sem = 0
    for cpf, lista in somar_gastos(verbas, casa.pop("anos")).items():
        nome = por_cpf.get(cpf) or chave.get(comum.chave_nome(nome_do_cpf.get(cpf)))
        if nome is None:
            sem += 1
            continue
        por_nome[nome] += lista
    for v in casa["vereadores"]:
        v["gastos"] = por_nome.get(v["nome"], [])
    return sem


def coletar(hoje: date) -> dict:
    with comum.criar_cliente() as client:
        autores = comum.get_json(client, f"{API}/autor/listar")
        props = proposicoes(client, hoje.year - 1, hoje) + proposicoes(client, hoje.year, hoje)
        verbas = baixar_verbas(client, {hoje.year - 1, hoje.year})
    ativos = [
        a for a in autores if a.get("tipoAutor") == "PARLAMENTAR" and a.get("situacao") == "ATIVO"
    ]
    nomes = {nome_sem_titulo(a["nome"]) for a in ativos}
    autoria = distribuir(props, nomes)
    vereadores = [
        {
            "id_externo": str(a["id"]),
            "nome": nome_sem_titulo(a["nome"]),
            "nome_completo": None,
            "partido": a.get("partidoPoliticoSigla") or None,
            "foto_url": None,  # a foto vem do TSE, pela ligação ao eleito
            "email": a.get("email") or None,
            "telefone": None,
            "titular": True,
            "em_exercicio": True,
            "inicio": None,
            "fim": None,
            "proposicoes_por_tipo": autoria[nome_sem_titulo(a["nome"])]["contagem"],
            "projetos": autoria[nome_sem_titulo(a["nome"])]["projetos"],
            "sessoes": None,
            "presencas": None,
        }
        for a in ativos
    ]
    return {
        "base": SITE,
        "legislatura": None,
        "vereadores": vereadores,
        "votacoes": [],
        "votos": [],
        "verbas": verbas,
        "anos": {hoje.year - 1, hoje.year},
    }


def executar() -> int:
    casa = coletar(date.today())
    if len(casa["vereadores"]) < 20:  # a CLDF tem 24 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na CLDF; abortando.")
    with SessionLocal() as session:
        sem = anexar_gastos(session, casa)
        if sem:
            print(f"  {sem} CPFs das verbas sem deputado ativo correspondente", flush=True)
        total = sapl.gravar(session, None, casa, uf="DF")
        session.add(
            FonteIngestao(fonte=FONTE, url=API, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(f"CLDF: {total} deputados distritais", flush=True)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
