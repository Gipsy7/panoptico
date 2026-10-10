"""Atos de nomeação, exoneração, designação e dispensa no Diário Oficial da União (Seção 2),
por nome.

Fonte: base de dados abertos da Imprensa Nacional (in.gov.br, "Base de Dados de Publicações
do DOU"): um ZIP por mês e seção (S02MMAAAA.zip, XML por matéria), de acesso livre, sem
cadastro. (O INLABS, que serve o diário do dia em XML, exige cadastro e senha: não é usado.)
A Seção 2 é a de atos de pessoal dos servidores públicos.

REGRA CRÍTICA: nome encontrado em texto nunca é vínculo. O que sai daqui são SUGESTÕES na
tabela `dou_ato` (revisado = falso), para a fila de revisão humana (`ingestion.revisar
--tipo dou`); nada vira evento publicável. Homônimos são o risco.

Recorte mínimo: só matérias da Seção 2 que citam, no mesmo parágrafo, o nome completo (3+
palavras, único na base) de uma pessoa que já acompanhamos e uma palavra de ato (nomear,
exonerar, designar, dispensar e flexões); janela desde 2025-01-01. O ZIP (16 MB por mês) é
lido em fluxo e não fica: guardamos o trecho de até 500 caracteres, órgão, data, tipo e o
link oficial da página do DOU; o bruto vira recorte + manifesto.
"""

import argparse
import html
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import DouAto, FonteIngestao, Pessoa
from ingestion import comum
from ingestion.diarios.atos import _sem_acento
from ingestion.dou.revisao import aplicar_atos_dou

FONTE = "dou_atos"
URL_BASE = "https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados"
DESDE = (2025, 1)
TAMANHO_TRECHO = 500
JANELA = 230  # caracteres para cada lado do nome
LINHAS_ANTES = 3  # linhas anteriores onde o verbo do ato pode estar (tabelas de nomes)
MIN_PALAVRAS = 3
MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]  # fmt: skip

_VERBOS = (
    r"NOME(?:IA|AR|AM|ADO|ADA|ADOS|ADAS|ACAO)"
    r"|EXONER(?:A|AR|AM|E|ADO|ADA|ADOS|ADAS|ACAO)"
    r"|DESIGN(?:A|AR|AM|E|ADO|ADA|ADOS|ADAS|ACAO)"
    r"|DISPENS(?:A|AR|AM|E|ADO|ADA|ADOS|ADAS)"
)
ATO = re.compile(rf"(?<![A-Z])(?:{_VERBOS})(?![A-Z])")
TIPOS = {"NOME": "nomeacao", "EXON": "exoneracao", "DESI": "designacao", "DISP": "dispensa"}
PALAVRA = re.compile(r"[A-Z0-9]+")
# Assinatura e cargo de quem assina: a autoridade que assina o ato não é o alvo dele.
ASSINATURA = re.compile(r'<p[^>]*class="(?:assina|cargo)"[^>]*>.*?</p>', re.S | re.I)
# Palavras coladas ao nome que não fazem parte dele (títulos e tratamentos).
NAO_E_NOME = {
    "O", "A", "OS", "AS", "SR", "SRA", "SRTA", "SENHOR", "SENHORA", "DR", "DRA", "DOUTOR",
    "DOUTORA", "SERVIDOR", "SERVIDORA", "PROFESSOR", "PROFESSORA", "MILITAR", "CABO", "SOLDADO",
    "SARGENTO", "TENENTE", "CORONEL", "MAJOR", "CAPITAO", "GENERAL", "DELEGADO", "DELEGADA",
    "AGENTE", "JUIZ", "JUIZA", "DESEMBARGADOR", "DESEMBARGADORA", "PROCURADOR", "PROCURADORA",
    "DEFENSOR", "DEFENSORA", "CIDADAO", "CIDADA", "SIAPE", "CPF", "MATRICULA", "PARA", "PELO",
    "PELA", "NO", "NA", "AO", "AOS", "DO", "DA", "DOS", "DAS", "DE", "E", "POR", "COM", "EM",
    "OCUPANTE", "OCUPANTES", "REFERIDO", "REFERIDA", "NOMEADO", "NOMEADA",
}  # fmt: skip


def url_do_mes(client: httpx.Client, ano: int, mes: int) -> str | None:
    """Link do ZIP da Seção 2 do mês, lido da página da base de dados (o link tem um
    identificador que muda a cada publicação). None se o mês ainda não foi publicado."""
    resposta = client.get(URL_BASE, params={"ano": ano, "mes": MESES[mes - 1]})
    if resposta.status_code in (400, 404):
        return None
    resposta.raise_for_status()
    padrao = rf'href="(https://www\.in\.gov\.br/documents/[^"]*S02{mes:02d}{ano}\.zip[^"]*)"'
    achado = re.search(padrao, resposta.text)
    return html.unescape(achado.group(1)) if achado else None


def meses_desde(desde: tuple[int, int] = DESDE, hoje: date | None = None) -> list[tuple[int, int]]:
    hoje = hoje or date.today()
    resultado, (ano, mes) = [], desde
    while (ano, mes) <= (hoje.year, hoje.month):
        resultado.append((ano, mes))
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    return resultado


def indice_nomes(session: Session) -> tuple[dict[tuple, list[tuple[int, tuple]]], int]:
    """Índice por as 3 primeiras palavras do nome -> [(pessoa, palavras do nome)]. Nome com
    menos de 3 palavras ou compartilhado por mais de uma pessoa fica de fora (só vale a
    correspondência exata e única). Devolve também quantos nomes ambíguos foram descartados."""
    por_nome: dict[tuple, set[int]] = {}
    for pessoa_id, nome in session.execute(select(Pessoa.id, Pessoa.nome)):
        palavras = tuple(comum.chave_nome(nome).split())
        if len(palavras) >= MIN_PALAVRAS:
            por_nome.setdefault(palavras, set()).add(pessoa_id)
    indice: dict[tuple, list[tuple[int, tuple]]] = {}
    ambiguos = 0
    for palavras, ids in por_nome.items():
        if len(ids) > 1:
            ambiguos += 1
            continue
        indice.setdefault(palavras[:MIN_PALAVRAS], []).append((next(iter(ids)), palavras))
    return indice, ambiguos


def linhas_do_texto(texto_html: str) -> list[str]:
    """Texto da matéria em linhas (parágrafos e linhas de tabela), sem a assinatura."""
    sem_assinatura = ASSINATURA.sub("\n", texto_html)
    quebrado = re.sub(r"</p>|</tr>|<br\s*/?>|</div>|</li>", "\n", sem_assinatura, flags=re.I)
    quebrado = re.sub(r"</t[dh]>", " | ", quebrado, flags=re.I)
    texto = html.unescape(re.sub(r"<[^>]+>", " ", quebrado))
    return [" ".join(linha.split()) for linha in texto.split("\n") if linha.strip()]


PARTICULAS = {"DE", "DA", "DO", "DAS", "DOS"}


def _colado(linha: str, palavras: list, de: int, para: int) -> bool:
    """Só espaço entre a palavra `de` e a palavra `para` (sem vírgula, ponto, parêntese)."""
    ini, fim = sorted((de, para))
    return not linha[palavras[ini][2] : palavras[fim][1]].strip()


def _continua_o_nome(linha: str, palavras: list, i: int, fim_i: int) -> bool:
    """O nome do índice é só um pedaço de um nome maior ("Marcelo de Oliveira" dentro de
    "Augusto Marcelo de Oliveira Santos")? Vê a palavra colada antes e depois (pulando
    "de", "da"...), sem pontuação no meio, escrita no mesmo estilo (CAIXA ALTA ou
    Capitalizada) e que não é título."""
    alta = linha[palavras[i][1] : palavras[i][2]].isupper()
    candidatos = []
    j = i - 1
    while j >= 0 and _colado(linha, palavras, j, j + 1):
        if palavras[j][0] not in PARTICULAS:
            candidatos.append(j)
            break
        j -= 1
    j = fim_i
    while j < len(palavras) and _colado(linha, palavras, j - 1, j):
        if palavras[j][0] not in PARTICULAS:
            candidatos.append(j)
            break
        j += 1
    for j in candidatos:
        palavra, ini, fim = palavras[j]
        original = linha[ini:fim]
        if len(original) < 2 or not original[0].isupper() or original.isupper() != alta:
            continue
        if palavra in NAO_E_NOME or ATO.fullmatch(palavra):
            continue
        return True
    return False


# O nome de parlamentar como lotação ("no gabinete do(a) Deputado(a) Fulano") não é o alvo.
ANTES_TITULO = re.compile(
    r"(?:DEPUTAD[OA]S?|SENADOR(?:A|ES)?|VEREADOR(?:A|ES)?|GABINETE|LIDERANCA|BANCADA)"
    r"[\s()A-Z]{0,12}$"
)
# Atos que não são o ato de pessoal em si (afastamento, penalidade, pensão, prorrogação...):
# se aparecem entre o verbo e o nome, o nome não é o alvo da nomeação/exoneração.
OUTRO_ATO = re.compile(
    r"AUTORIZ|AFASTAMENTO|PENALIDADE|NOTIFIC|FERIAS|PENSAO|APOSENTADORIA|PRORROG|RENOV"
    r"|CONVALID|DECORRENTE|TORNAR SEM|TORNA SEM|RETIFIC|CESSAO|REMOVER|REMOCAO"
    r"|SUBSTITU|CONCEDER|LICENCA"
)
DISTANCIA_VERBO = 150  # caracteres entre o verbo do ato e o nome
DISTANCIA_VERBO_DEPOIS = 60  # "Fulano, nomeado ..."


def _verbo_do_ato(alvo: str, inicio: int, fim: int) -> str | None:
    """Palavra de ato que governa o nome: a última antes dele (até DISTANCIA_VERBO caracteres,
    sem outro tipo de ato no meio) ou, na falta, a primeira logo depois."""
    antes = alvo[max(0, inicio - DISTANCIA_VERBO) : inicio]
    verbos = list(ATO.finditer(antes))
    if verbos:
        ultimo = verbos[-1]
        if OUTRO_ATO.search(antes[max(0, ultimo.start() - 30) :]):  # "prorrogar a designação"
            return None
        return ultimo.group()
    depois = ATO.search(alvo[fim : fim + DISTANCIA_VERBO_DEPOIS])
    if depois and not OUTRO_ATO.search(alvo[fim : fim + depois.start()]):
        return depois.group()
    return None


def achar_nomes(
    linhas: list[str], indice: dict[tuple, list[tuple[int, tuple]]]
) -> list[tuple[int, str, str]]:
    """(pessoa, tipo do ato, trecho curto) de cada pessoa do índice citada pelo nome
    completo numa linha que tem (ou cujas linhas anteriores têm) uma palavra de ato.
    Uma por pessoa."""
    achados: dict[int, tuple[int, str, str]] = {}
    for n, linha in enumerate(linhas):
        dobrada = _sem_acento(linha).upper()
        palavras = [(m.group(), m.start(), m.end()) for m in PALAVRA.finditer(dobrada)]
        if len(palavras) < MIN_PALAVRAS:
            continue
        for i in range(len(palavras) - MIN_PALAVRAS + 1):
            chave = tuple(p[0] for p in palavras[i : i + MIN_PALAVRAS])
            for pessoa_id, nome in indice.get(chave, ()):
                fim_i = i + len(nome)
                if pessoa_id in achados or tuple(p[0] for p in palavras[i:fim_i]) != nome:
                    continue
                if len(palavras) == len(nome):
                    continue  # linha só com o nome: assinatura ou lista, não o ato
                if _continua_o_nome(linha, palavras, i, fim_i):
                    continue
                antes = "\n".join(linhas[max(0, n - LINHAS_ANTES) : n])
                contexto = (antes + "\n" if antes else "") + linha
                base = len(antes) + 1 if antes else 0
                inicio, fim = base + palavras[i][1], base + palavras[fim_i - 1][2]
                alvo = _sem_acento(contexto).upper()
                if ANTES_TITULO.search(alvo[max(0, inicio - 30) : inicio]):
                    continue
                verbo = _verbo_do_ato(alvo, inicio, fim)
                if verbo is None:
                    continue
                ini, fin = max(0, inicio - JANELA), min(len(contexto), fim + JANELA)
                trecho = " ".join(contexto[ini:fin].split())[:TAMANHO_TRECHO]
                achados[pessoa_id] = (pessoa_id, TIPOS[verbo[:4]], trecho)
    return list(achados.values())


def _data(texto: str) -> date | None:
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        return None


def varrer(
    arquivo: Path | bytes, indice: dict[tuple, list[tuple[int, tuple]]], estatisticas: Counter
) -> list[dict[str, Any]]:
    """Lê o ZIP em fluxo (um XML por vez) e devolve só as matérias que citam alguém do índice
    num ato. Os XML sem esse recorte são descartados na hora."""
    achados = []
    origem = io.BytesIO(arquivo) if isinstance(arquivo, bytes) else arquivo
    with zipfile.ZipFile(origem) as zip_:
        for nome in zip_.namelist():
            if not nome.endswith(".xml"):
                continue
            estatisticas["materias"] += 1
            try:
                raiz = ET.fromstring(zip_.read(nome).decode("utf-8-sig"))
            except ET.ParseError:
                estatisticas["xml_invalido"] += 1
                continue
            artigo = raiz if raiz.tag == "article" else raiz.find("article")
            texto = artigo.findtext("body/Texto") if artigo is not None else None
            if artigo is None or not texto:
                continue
            atributos = artigo.attrib
            if atributos.get("pubName") not in (None, "DO2"):
                continue
            data = _data(atributos.get("pubDate", ""))
            id_materia = atributos.get("idMateria") or atributos.get("id")
            link = atributos.get("pdfPage", "").replace("http://", "https://")
            if not (data and id_materia and link):
                estatisticas["sem_data_ou_link"] += 1
                continue
            for pessoa_id, tipo, trecho in achar_nomes(linhas_do_texto(texto), indice):
                achados.append(
                    {
                        "pessoa_id": pessoa_id,
                        "id_materia": id_materia[:20],
                        "data": data,
                        "tipo_ato": tipo,
                        "orgao": atributos.get("artCategory", "").strip() or "DOU",
                        "tipo_materia": (atributos.get("artType") or "")[:100] or None,
                        "trecho": trecho,
                        "url": link,
                    }
                )
    estatisticas["achados"] += len(achados)
    return achados


def gravar(session: Session, achados: list[dict[str, Any]], ano: int, mes: int) -> int:
    """Troca as sugestões ainda não revisadas do mês pelas desta leitura (o que já foi
    revisado fica); idempotente."""
    inicio = date(ano, mes, 1)
    fim = date(ano + (mes == 12), mes % 12 + 1, 1)
    session.execute(
        delete(DouAto).where(DouAto.data >= inicio, DouAto.data < fim, DouAto.revisado.is_(False))
    )
    for lote in range(0, len(achados), 1000):
        session.execute(
            insert(DouAto)
            .values(achados[lote : lote + 1000])
            .on_conflict_do_nothing(index_elements=["pessoa_id", "id_materia"])
        )
    session.flush()
    aplicar_atos_dou(session)  # decisões já registradas valem para sugestões recarregadas
    return len(achados)


def executar(ano: int, mes: int, de_raw: Path | None = None) -> int:
    url = None
    if de_raw is None:
        with comum.criar_cliente() as client:
            url = url_do_mes(client, ano, mes)
        if url is None:
            print(f"  {ano}-{mes:02d}: ZIP da Seção 2 ainda não publicado", flush=True)
            return 0

    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, url)

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        indice, ambiguos = indice_nomes(session)
        estatisticas: Counter = Counter()
        achados = varrer(payload, indice, estatisticas)
        print(
            f"  {ano}-{mes:02d}: {estatisticas['materias']} matérias lidas, "
            f"{len(achados)} sugestões ({ambiguos} nomes ambíguos fora do índice)",
            flush=True,
        )
        if estatisticas["materias"] == 0:
            raise ValueError(f"ZIP de {ano}-{mes:02d} sem matérias; abortando.")
        comum.salvar_raw(
            FONTE, [{**a, "data": a["data"].isoformat()} for a in achados], f"{ano}-{mes:02d}_"
        )  # recorte: só as sugestões
        return gravar(session, achados, ano, mes)

    inicio = datetime.now()
    total = comum.executar_ingestao(
        FONTE,
        url or str(de_raw),
        baixar,
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"S02_{ano}-{mes:02d}_",
        incremental=comum.Incremental(
            chave=f"{FONTE}:{ano}-{mes:02d}", sonda=url, contexto=comum.contexto_pessoas
        ),
    )
    comum.trocar_por_manifesto(FONTE, desde=inicio)  # o ZIP de 16 MB não fica: só o manifesto
    return total


def executar_tudo(desde: tuple[int, int] = DESDE) -> int:
    total = 0
    for ano, mes in meses_desde(desde):
        total += executar(ano, mes)
    with SessionLocal() as session:
        aplicar_atos_dou(session)
        session.commit()
    return total


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    p.add_argument("--mes", help="só este mês (AAAA-MM)")
    p.add_argument("--desde", default="2025-01", help="primeiro mês (AAAA-MM; padrão 2025-01)")
    p.add_argument("--de-raw", type=Path, help="reprocessa um ZIP já baixado (exige --mes)")
    a = p.parse_args()
    if a.mes:
        y, m = (int(x) for x in a.mes.split("-"))
        print(f"{FONTE}: {executar(y, m, a.de_raw)} sugestões")
    else:
        y, m = (int(x) for x in a.desde.split("-"))
        print(f"{FONTE}: {executar_tudo((y, m))} sugestões")
