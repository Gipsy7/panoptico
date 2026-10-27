"""Assembleia Legislativa do Ceará (ALECE): deputados no cargo hoje e projetos de autoria,
pelas páginas públicas do site (a API do portal da transparência da ALECE só tem
contratos, empenhos, licitações e pagamentos; nada legislativo).

- Lista: `www.al.ce.gov.br/deputados` traz os cartões dos 46 titulares (6 deles licenciados)
  e, numa seção à parte, os suplentes em exercício, com partido e foto.
- Ficha: `www.al.ce.gov.br/deputados/{slug}` dá o e-mail e os telefones do gabinete.
- Projetos: o sistema antigo de proposições (`www2.al.ce.gov.br/legislativo/proposicoes`)
  lista, por tabela (lei, lei complementar, emenda à Constituição, decreto legislativo e
  resolução), 15 por página, com número, autor, data de entrada, ementa e situação (OBS).

Gastos: o portal da transparência publica, por mês, o CSV da "verba de desempenho
parlamentar" (empenhos do gabinete: benefício de alimentação, combustível, consultoria,
telefonia, divulgação, reembolsos indenizatórios). Soma por deputado, mês e tipo de gasto.
O CSV não traz CPF do deputado (o CPF e o CNPJ são do fornecedor e nunca são guardados), só
o nome com erros de digitação; liga-se sozinho só por nome exato (site ou TSE); o aproximado vai
para a fila de revisão humana (`apelidos.py`) e só liga depois de aceito.

Indicações não entram (são milhares de páginas de listagem). Os votos nominais saem em
planilhas de relatório de impressão (uma por matéria), sem estrutura aproveitável.
Uma requisição por vez, com pausa. Grava nas mesmas tabelas das outras casas.
"""

import argparse
import csv
import html
import io
import re
import time
import zipfile
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.assembleias import base
from ingestion.camaras import sapl

FONTE = "alece"
GASTOS = "https://transparencia.al.ce.gov.br/despesas/verba-desempenho-parlamentar/csv"
MOTIVO_SEM_PERIODO = (
    "A linha vem sem mês e ano legíveis na planilha, então não dá para somar por mês"
)
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


# A planilha não tem coluna de tipo de gasto: o tipo está no texto livre do empenho. Regras em
# ordem (a primeira que casa vale); "anulação" e "em substituição" mantêm o assunto do texto,
# então o valor negativo abate o mesmo tipo. O que não casa vai para "Outros".
CATEGORIAS = (
    ("Vale-alimentação e refeição", ("BENEFICIO ALIMENTACAO", "BENEFICIO REFEICAO")),
    ("Combustível (cartão)", ("COMBUSTIV",)),
    ("Divulgação da atividade parlamentar", ("DIVULGACAO",)),
    ("Passagens e hospedagem", ("PASSAGEM", "PASSAGENS", "HOSPEDAGEM", "ESTADIA", "LOCOMOCAO")),
    ("Seguro de vida e plano de saúde", ("SEGURO DE VIDA", "PLANO DE SAUDE")),
    ("Site, software e pesquisa", (" SITE", "SOFTWARE", "PESQUISA DE OPINIAO")),
    (
        "Telefonia, internet e TV",
        ("TELEFON", "INTERNET", "TV POR ASSINATURA", "ASSINATURA DE TV", "MULTIMIDIA"),
    ),
    ("Impressões gráficas", ("IMPRESS", "GRAFIC")),
    ("Locação de veículos e imóveis", ("LOCACAO", "ALUGUEL", "LOCOACAO")),
    ("Consultoria e assessoria", ("CONSULTORIA", "ASSESSORIA", "ACOMPANHAMENTO")),
)
OUTROS = "Outros"


def categoria(descricao: str) -> str:
    texto = " ".join((descricao or "").upper().split())
    for nome, chaves in CATEGORIAS:
        if any(c in texto for c in chaves):
            return nome
    return OUTROS


def nome_do_csv(deputado: str) -> str:
    """'DEP SERGIO AGUIAR.' -> 'SERGIO AGUIAR' (chave de comparação, sem o prefixo DEP)."""
    return comum.chave_nome(re.sub(r"^\s*DEP\b\.?", "", deputado or "", flags=re.I))


def _valor(texto: str) -> Decimal:
    """'-16.000,00' -> Decimal('-16000.00')."""
    t = (texto or "").strip().replace("R$", "").replace(".", "").replace(",", ".")
    return Decimal(t).quantize(Decimal("0.01"))


def ler_mes(conteudo: bytes) -> list[dict[str, str]]:
    """O CSV de um mês (UTF-8 com BOM, ';'): a primeira linha é só ';;;' e o cabeçalho vem na
    segunda. Mês sem lançamentos traz só o cabeçalho."""
    texto = conteudo.decode("utf-8-sig", errors="replace")
    if texto.lstrip()[:1] == "<":
        raise ValueError("o endereço devolveu HTML, não o CSV")
    linhas = texto.splitlines()
    while linhas and not linhas[0].upper().startswith("DEPUTADO"):
        linhas.pop(0)
    if not linhas:
        raise ValueError("CSV sem o cabeçalho DEPUTADO;PERIODO;...")
    leitor = csv.DictReader(io.StringIO("\n".join(linhas)), delimiter=";")
    return [{(k or "").strip(): (v or "").strip() for k, v in lin.items()} for lin in leitor]


def somar_gastos(
    linhas: list[dict[str, str]],
) -> tuple[dict[str, dict[tuple[int, int, str], Decimal]], dict[str, dict[int, dict]]]:
    """Nome (chave) -> {(ano, mês, tipo): soma} e, do que não entra na soma por mês (período
    ou valor ilegível), nome -> ano -> {linhas, valor, linhas_valor_ilegivel}. Só as colunas
    de nome, período, descrição e valor são usadas; CNPJ/CPF e credor são descartados."""
    soma: dict[str, dict[tuple[int, int, str], Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    fora: dict[str, dict[int, dict]] = defaultdict(dict)
    for lin in linhas:
        nome = nome_do_csv(lin.get("DEPUTADO", ""))
        if not nome:
            continue
        periodo = re.fullmatch(r"(\d{2})/(\d{4})", lin.get("PERIODO", ""))
        try:
            valor = _valor(lin.get("VALOR", ""))
        except InvalidOperation:
            valor = None
        if periodo is None or not 1 <= int(periodo[1]) <= 12 or valor is None:
            ano = int(periodo[2]) if periodo else 0
            acc = fora[nome].setdefault(
                ano, {"linhas": 0, "valor": Decimal(0), "linhas_valor_ilegivel": 0}
            )
            acc["linhas"] += 1
            if valor is None:
                acc["linhas_valor_ilegivel"] += 1
            else:
                acc["valor"] += valor
            continue
        soma[nome][(int(periodo[2]), int(periodo[1]), categoria(lin.get("DESCRICAO", "")))] += valor
    return soma, fora


def meses_do_periodo(hoje: date) -> list[tuple[int, int]]:
    """Janeiro do ano anterior até o mês atual (a Casa publica o empenho no mês)."""
    return [
        (a, m)
        for a in (hoje.year - 1, hoje.year)
        for m in range(1, 13)
        if (a, m) <= (hoje.year, hoje.month)
    ]


def empacotar(arquivos: dict[str, bytes]) -> bytes:
    """Os CSVs mensais num zip (o bruto de uma carga), um por AAAA-MM."""
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in sorted(arquivos.items()):
            z.writestr(nome, conteudo)
    return memoria.getvalue()


def baixar_gastos(client: Any, meses: list[tuple[int, int]]) -> dict[str, bytes]:
    arquivos = {}
    for ano, mes in meses:
        time.sleep(PAUSA)
        arquivos[f"{ano}-{mes:02d}.csv"] = comum._get(
            client, GASTOS, {"mes": f"{mes:02d}", "ano": str(ano)}, 4
        ).content
    return arquivos


def linhas_dos_arquivos(arquivos: dict[str, bytes]) -> list[dict[str, str]]:
    linhas = []
    for conteudo in arquivos.values():
        linhas += ler_mes(conteudo)
    if not linhas:
        raise ValueError("ALECE: nenhum lançamento de gasto nos meses lidos; abortando.")
    return linhas


def totais_por_nome(linhas: list[dict[str, str]]) -> dict[str, tuple[int, Decimal]]:
    """Chave de nome -> (lançamentos, valor líquido) de toda a planilha, para dimensionar a
    fila de apelidos (nomes sem deputado)."""
    totais: dict[str, tuple[int, Decimal]] = {}
    for lin in linhas:
        nome = nome_do_csv(lin.get("DEPUTADO", ""))
        if not nome:
            continue
        try:
            valor = _valor(lin.get("VALOR", ""))
        except InvalidOperation:
            valor = Decimal(0)
        n, total = totais.get(nome, (0, Decimal(0)))
        totais[nome] = (n + 1, total + valor)
    return totais


def anexar_gastos(session: Any, casa: dict, linhas: list[dict[str, str]]) -> list[str]:
    """Põe os gastos em cada deputado (e o que não entra na soma em `gastos_fora`). Devolve
    os nomes do CSV que não casaram com nenhum deputado da lista (ex-deputados, erros de
    digitação)."""
    deputados = casa["vereadores"]
    soma, fora = somar_gastos(linhas)
    ligados, sobras = base.ligar_nomes(
        FONTE, totais_por_nome(linhas), deputados, base.nomes_do_tse(session, "CE")
    )
    por_nome: dict[str, list[dict]] = defaultdict(list)
    fora_por_nome: dict[str, list[dict]] = defaultdict(list)
    for chave, itens in soma.items():
        if chave in ligados:
            por_nome[ligados[chave]] += [
                {"ano": a, "mes": m, "categoria": c, "valor": v}
                for (a, m, c), v in sorted(itens.items())
            ]
    for chave, anos in fora.items():
        if chave in ligados:
            fora_por_nome[ligados[chave]] += [
                {"ano": ano, "motivo": MOTIVO_SEM_PERIODO, **dados} for ano, dados in anos.items()
            ]
    for d in deputados:
        agrupado: dict[tuple, Decimal] = defaultdict(Decimal)  # duas grafias do mesmo deputado
        for g in por_nome.get(d["nome"], []):
            agrupado[(g["ano"], g["mes"], g["categoria"])] += g["valor"]
        d["gastos"] = [
            {"ano": a, "mes": m, "categoria": c, "valor": v}
            for (a, m, c), v in sorted(agrupado.items())
        ]
        d["gastos_fora"] = fora_por_nome.get(d["nome"], [])
    return sobras


def coletar(hoje: date, gastos_raw: Path | None = None) -> dict:
    ano_minimo = hoje.year - 1
    with comum.criar_cliente() as client:
        if gastos_raw:  # --gastos-de-raw: reprocessa o zip já guardado, sem rede
            with zipfile.ZipFile(gastos_raw) as z:
                arquivos = {n: z.read(n) for n in z.namelist()}
        else:
            arquivos = baixar_gastos(client, meses_do_periodo(hoje))
            raw = comum.salvar_raw(FONTE, empacotar(arquivos), "gastos_", ".zip")
            print(f"  bruto dos gastos: {raw}", flush=True)
        linhas = linhas_dos_arquivos(arquivos)
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
        "linhas_gastos": linhas,
    }


def alerta_sem_deputado(linhas: list[dict[str, str]], sobras: list[str]) -> list[str]:
    """Quanto da planilha ficou sem deputado (ex-deputados e nomes com erro de digitação)."""
    if not sobras:
        return []
    conjunto = set(sobras)
    total, n = Decimal(0), 0
    for lin in linhas:
        if nome_do_csv(lin.get("DEPUTADO", "")) in conjunto:
            n += 1
            try:
                total += _valor(lin.get("VALOR", ""))
            except InvalidOperation:
                pass
    valor = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return [
        f"Gastos ALECE: {n} lançamentos (R$ {valor}) de {len(conjunto)} nomes da planilha não "
        "casaram com um deputado da lista (ex-deputados ou nome com erro de digitação, que "
        "não ligamos por aproximação): " + "; ".join(sorted(conjunto))
    ]


def executar(gastos_raw: Path | None = None) -> int:
    casa = coletar(date.today(), gastos_raw)
    linhas = casa.pop("linhas_gastos")
    exercicio = sum(1 for v in casa["vereadores"] if v["em_exercicio"])
    if exercicio < 40:  # a ALECE tem 46 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {exercicio} deputados em exercício na ALECE; abortando.")
    with SessionLocal() as session:
        sobras = anexar_gastos(session, casa, linhas)
        alertas = alerta_sem_deputado(linhas, sobras)
        for a in alertas:
            print(f"  AVISO {a}", flush=True)
        total = sapl.gravar(session, None, casa, uf="CE")
        session.add(
            FonteIngestao(fonte=FONTE, url=LISTA, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC), alertas=alertas or None)
        )  # fmt: skip
        session.commit()
    com_gasto = sum(1 for v in casa["vereadores"] if v["gastos"])
    print(f"ALECE: {total} deputados, {com_gasto} com gastos", flush=True)
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    ap.add_argument("--de-raw", type=Path, help="zip de gastos de data/raw/alece (sem rede)")
    executar(ap.parse_args().de_raw)
