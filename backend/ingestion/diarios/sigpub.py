"""Atos de nomeação, exoneração e designação no SIGPub (diariomunicipal.com.br).

O SIGPub (Vox Tecnologia) hospeda o diário oficial de associações e federações estaduais de
municípios (AMM-MG, AMUPE-PE, FAMUP-PB, FEMURN-RN, APRECE-CE, AMP-PR, FAMURS-RS, AMM-MT...):
uma edição em PDF com texto por dia, com as matérias de dezenas ou centenas de prefeituras e
câmaras. Cada matéria começa com "ESTADO DE <UF> / <órgão>" e termina em "Código
Identificador:XXXXXXXX", o que permite separar por município (IBGE).

Acesso: aberto. robots.txt do site permite tudo (`Disallow:` vazio, sem Crawl-delay). A "busca
avançada" tem reCAPTCHA e NÃO é usada; só o calendário público de edições anteriores
(POST em /<instância>/materia/calendario, com o token CSRF da própria página) e o PDF.
A lógica de calendário segue o raspador do Querido Diário (okfn-brasil/querido-diario,
gazette/spiders/base/sigpub.py, licença MIT), que cobre só 3 das ~26 instâncias.

REGRA CRÍTICA: nome encontrado em texto nunca é vínculo. O que sai daqui são SUGESTÕES na
tabela `diario_ato` (revisado = falso), para a fila `ingestion.revisar --tipo diario`.
Recorte: edições dos últimos 90 dias na primeira carga, depois incremental; só pessoas que já
acompanhamos com mandato em curso (prefeitos, vice-prefeitos e vereadores eleitos em 2024 e
vereadores em exercício), e só nas matérias do município delas.
"""

import argparse
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import DiarioAto, FonteIngestao
from ingestion import comum
from ingestion.diarios import plataformas as pl
from ingestion.diarios.revisao import aplicar_atos

FONTE = "sigpub_atos"
BASE = "https://www.diariomunicipal.com.br"
DIAS_PRIMEIRA_CARGA = 90
PAUSA = 0.5

# slug da instância -> (nome, UFs dos municípios atendidos)
INSTANCIAS: dict[str, tuple[str, tuple[str, ...]]] = {
    "aam": ("Associação Amazonense de Municípios", ("AM",)),
    "ama": ("Associação dos Municípios Alagoanos", ("AL",)),
    "amurc": ("Municípios do Sul, Extremo Sul e Sudoeste da Bahia", ("BA",)),
    "bahia": ("Associação dos Municípios do Recôncavo Baiano", ("BA",)),
    "aprece": ("Associação dos Municípios do Ceará (APRECE)", ("CE",)),
    "agm": ("Associação Goiana de Municípios", ("GO",)),
    "fgm": ("Federação Goiana de Municípios", ("GO",)),
    "amm-mg": ("Associação Mineira de Municípios", ("MG",)),
    "ms": ("Mato Grosso do Sul", ("MS",)),
    "amm-mt": ("Associação Mato-grossense dos Municípios", ("MT",)),
    "famep": ("Federação das Associações de Municípios do Pará", ("PA",)),
    "famup": ("Federação das Associações de Municípios da Paraíba", ("PB",)),
    "amupe": ("Associação Municipalista de Pernambuco", ("PE",)),
    "appm": ("Associação Piauiense de Municípios", ("PI",)),
    "amp": ("Associação dos Municípios do Paraná", ("PR",)),
    "aemerj": ("Associação de Municípios do Rio de Janeiro", ("RJ",)),
    "femurn": ("Federação dos Municípios do Rio Grande do Norte", ("RN",)),
    "arom": ("Associação Rondoniense de Municípios", ("RO",)),
    "amr": ("Associação dos Municípios de Roraima", ("RR",)),
    "famurs": ("Federação das Associações de Municípios do RS", ("RS",)),
    "sergipe": ("Associação Sergipana de Municípios", ("SE",)),
    "apm": ("Associação Paulista de Municípios", ("SP",)),
    "macatuba": ("Prefeitura de Macatuba", ("SP",)),
    "pmmasp": ("Prefeitura de Monte Alto", ("SP",)),
}

_CODIGO = re.compile(r"C[óo]digo\s+Identificador\s*:\s*([0-9A-Za-z]{6,12})")
_CABECALHO_PAGINA = re.compile(
    r"^.*ANO\s+[IVXLC]+\s*\|\s*N.*$|^www\.diariomunicipal\.com\.br\S*\s+\d+\s*$"
)
_ESTADO = re.compile(r"^\s*ESTADO\s+D[EOA]\s+[A-ZÀ-Ú ]+$|^\s*MUNIC[ÍI]PIO\s+DE\s+.+$", re.I)


# ---- rede -------------------------------------------------------------------------------


def _token(client: httpx.Client, slug: str) -> str:
    """Abre a página da instância (cria o cookie de sessão) e devolve o token CSRF do
    formulário do calendário."""
    r = client.get(f"{BASE}/{slug}/", headers={"Accept": "text/html"})
    r.raise_for_status()
    m = re.search(r'id="calendar__token"[^>]*value="([^"]+)"', r.text)
    if not m:
        raise RuntimeError(f"sem token do calendário em {slug}")
    return m.group(1)


def edicoes_do_dia(client: httpx.Client, slug: str, token: str, dia: date) -> list[dict]:
    """Edições regulares e extraordinárias publicadas na data (vazio se não houve)."""
    achadas = []
    for tipo, caminho in (("regular", "materia/calendario"), ("extra", "materia/calendario/extra")):
        time.sleep(PAUSA)
        r = client.post(
            f"{BASE}/{slug}/{caminho}",
            data={
                "calendar[day]": str(dia.day),
                "calendar[month]": str(dia.month),
                "calendar[year]": str(dia.year),
                "calendar[_token]": token,
            },
            headers={"Accept": "application/json"},
        )
        if r.status_code == 429 or r.status_code >= 500:
            r.raise_for_status()  # limite de uso ou servidor com problema: não é "dia sem edição"
        if r.status_code != 200:
            continue
        try:
            corpo = r.json()
        except ValueError:
            continue
        if not isinstance(corpo, dict) or "error" in corpo:
            continue
        for e in corpo.get("edicao") or []:
            achadas.append(
                {
                    "slug": slug,
                    "data": dia.isoformat(),
                    "extra": tipo == "extra",
                    "numero": str(e.get("numero_edicao") or ""),
                    "url": f"{corpo['url_arquivos']}{e['link_diario']}.pdf",
                }
            )
    vistas, unicas = set(), []
    for e in achadas:  # o endpoint "extra" repete a edição regular em alguns dias
        if e["url"] not in vistas:
            vistas.add(e["url"])
            unicas.append(e)
    return unicas


# ---- texto ------------------------------------------------------------------------------


def texto_do_pdf(conteudo: bytes) -> str:
    """Texto do PDF sem o cabeçalho que se repete em cada página."""
    return pl.texto_do_pdf(conteudo, _CABECALHO_PAGINA)


def separar_materias(texto: str) -> list[dict[str, str]]:
    """Cada matéria termina em "Código Identificador:XXXX"; o cabeçalho (ESTADO DE... e o
    órgão) vem logo no começo. Devolve [{codigo, cabecalho, texto}]."""
    materias = []
    inicio = 0
    for m in _CODIGO.finditer(texto):
        corpo = texto[inicio : m.start()].strip()
        inicio = m.end()
        if not corpo:
            continue
        materias.append({"codigo": m.group(1), "cabecalho": cabecalho(corpo), "texto": corpo})
    return materias


def cabecalho(corpo: str) -> str:
    """Primeiras linhas úteis da matéria: o órgão que publica (depois de "ESTADO DE X")."""
    linhas = [ln.strip() for ln in corpo.splitlines() if ln.strip()]
    for i, linha in enumerate(linhas[:60]):
        if _ESTADO.match(linha) and linha.upper().startswith("ESTADO"):
            return " ".join(linhas[i + 1 : i + 4])
    return " ".join(linhas[:3])


# ---- processamento ----------------------------------------------------------------------


def processar_edicao(
    edicao: dict[str, Any],
    indice: dict,
    alvos_por_municipio: dict[str, list[tuple[int, str]]],
    vistos: dict,
) -> list[dict[str, Any]]:
    """Sugestões de uma edição (texto já extraído) e atualização do que foi visto por
    município. Só as matérias do município da pessoa são lidas."""
    _, ufs = INSTANCIAS.get(edicao["slug"], ("", ()))
    dia = date.fromisoformat(edicao["data"])
    resultado = []
    for materia in separar_materias(edicao["texto"]):
        achou = pl.resolver_municipio(materia["cabecalho"], ufs, indice)
        if achou is None:  # sem "ESTADO DE.../órgão" no começo: tenta o início do texto
            achou = pl.resolver_municipio(materia["texto"][:800], ufs, indice)
        if achou is None:
            continue
        ibge, uf = achou
        nome = next((n for n, i in indice[uf].items() if i == ibge), ibge)
        _, ultima, qtd = vistos.get((uf, ibge), (nome, dia, 0))
        vistos[(uf, ibge)] = (nome, max(ultima, dia), qtd + 1)
        for pessoa_id, tipo, trecho in pl.achados_na_materia(
            materia["texto"], alvos_por_municipio.get(ibge, [])
        ):
            resultado.append(
                {
                    "pessoa_id": pessoa_id,
                    "municipio_ibge": ibge,
                    "data": dia,
                    "tipo_ato": tipo,
                    "trecho": trecho,
                    "url": f"{edicao['url']}#{materia['codigo']}",
                }
            )
    return resultado


def _nome_raw(edicao: dict[str, Any]) -> str:
    return f"{edicao['data']}_{edicao['numero'] or 'sn'}{'_extra' if edicao['extra'] else ''}"


def _inicio(slug: str, hoje: date, dias: int) -> date:
    """Primeira carga: últimos `dias`; depois, a partir da data da última varredura completa da
    instância (arquivo `.ate` na pasta do bruto), com 3 dias de folga para edições publicadas
    com atraso. Uma varredura interrompida ou com falha não grava a data."""
    inicio = hoje - timedelta(days=dias)
    marca = comum.RAW_DIR / FONTE / slug / ".ate"
    if marca.exists():
        try:
            inicio = max(inicio, date.fromisoformat(marca.read_text().strip()) - timedelta(days=3))
        except ValueError:
            pass
    return inicio


def _marcar_varredura(slug: str, hoje: date) -> None:
    pasta = comum.RAW_DIR / FONTE / slug
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / ".ate").write_text(hoje.isoformat())


def executar(
    instancias: list[str] | None = None,
    dias: int = DIAS_PRIMEIRA_CARGA,
    de_raw: Path | None = None,
) -> int:
    hoje = date.today()
    novos = edicoes_lidas = 0
    vistos: dict = {}
    with SessionLocal() as session:
        ingestao = FonteIngestao(fonte=FONTE, url=BASE, arquivo_raw="(por edição)")
        session.add(ingestao)
        session.flush()
        indice = pl.indice_municipios(session)
        alvos = pl.carregar_alvos(session, indice)
        session.commit()
        print(f"  {sum(map(len, alvos.values()))} pessoas em {len(alvos)} municípios", flush=True)

        def tratar(edicao: dict[str, Any]) -> None:
            nonlocal novos, edicoes_lidas
            sugestoes = processar_edicao(edicao, indice, alvos, vistos)
            novos += pl.gravar_sugestoes(session, sugestoes)
            session.commit()
            edicoes_lidas += 1

        if de_raw:
            arquivos = [de_raw] if de_raw.is_file() else sorted(de_raw.rglob("*.json.gz"))
            for arquivo in arquivos:
                tratar(pl.ler_raw_edicao(arquivo))
        else:
            alvo_slugs = instancias or list(INSTANCIAS)
            with comum.criar_cliente() as client:
                for slug in alvo_slugs:
                    try:
                        token = _token(client, slug)
                    except (httpx.HTTPError, RuntimeError) as erro:
                        print(f"  {slug}: sem acesso ({erro})", flush=True)
                        continue
                    dia = _inicio(slug, hoje, dias)
                    falhou = False
                    while dia <= hoje:
                        try:
                            edicoes = edicoes_do_dia(client, slug, token, dia)
                        except httpx.HTTPError:
                            edicoes, falhou = [], True
                        for e in edicoes:
                            pasta = comum.RAW_DIR / FONTE / slug / f"{_nome_raw(e)}.json.gz"
                            if pasta.exists():
                                continue
                            try:
                                pdf = comum.get_bytes(client, e["url"])
                                e["texto"] = texto_do_pdf(pdf)
                            except Exception as erro:  # noqa: BLE001
                                print(f"  {slug} {e['data']}: edição não lida ({erro})", flush=True)
                                continue
                            pl.gravar_raw_edicao(FONTE, slug, _nome_raw(e), e)
                            tratar(e)
                        dia += timedelta(days=1)
                    if not falhou:
                        _marcar_varredura(slug, hoje)
                    situacao = "com falhas" if falhou else "ok"
                    print(
                        f"  {slug}: {situacao} ({edicoes_lidas} edições, {novos} sug.)", flush=True
                    )
        pl.registrar_cobertura(FONTE, vistos)
        ingestao = session.merge(ingestao)
        aplicar_atos(session)  # decisões já registradas valem para sugestões recarregadas
        ingestao.registros = session.scalar(select(func.count()).select_from(DiarioAto))
        ingestao.status = "ok"
        ingestao.concluido_em = datetime.now()
        session.commit()
    print(f"  {edicoes_lidas} edições; {len(vistos)} municípios vistos; {novos} sugestões")
    return novos


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    p.add_argument("--instancias", nargs="+", help=f"só estas ({', '.join(INSTANCIAS)})")
    p.add_argument("--dias", type=int, default=DIAS_PRIMEIRA_CARGA)
    p.add_argument("--de-raw", type=Path, help="pasta (ou arquivo .json.gz) de bruto, sem rede")
    a = p.parse_args()
    print(f"{FONTE}: {executar(a.instancias, a.dias, a.de_raw)} sugestões")
