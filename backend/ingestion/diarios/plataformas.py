"""Peças comuns dos conectores de plataformas compartilhadas de diário oficial municipal.

Uma plataforma (SIGPub, DOEM, Instar...) publica o diário de dezenas ou centenas de
municípios. Cada conector baixa as edições, separa o texto em matérias, descobre de qual
município é cada matéria e procura, só nas matérias do município da pessoa, o nome completo
de quem já acompanhamos junto de uma palavra de ato (mesma regra de `diarios/atos.py`).

REGRA CRÍTICA (igual à do Querido Diário): o achado é SUGESTÃO em `diario_ato`
(revisado = falso), para a fila `ingestion.revisar --tipo diario`. Nada vai ao site sem
revisão humana. O texto das edições fica no bruto (`data/raw/<plataforma>/`), não no banco.
"""

import csv
import gzip
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import DiarioAto, Municipio
from ingestion import comum
from ingestion.diarios.atos import _sem_acento, achar_ato, padrao_nome

COBERTURA_CSV = Path(__file__).resolve().parents[3] / "data" / "diarios_plataformas_municipios.csv"
COLUNAS_COBERTURA = ["plataforma", "uf", "municipio_ibge", "municipio", "ultima_edicao", "materias"]

# Palavras que indicam que o cabeçalho de uma matéria é de órgão do município (e não de uma
# associação, consórcio ou do estado): o nome do município só vale depois delas.
_ORGAO_MUNICIPAL = re.compile(
    r"\b(PREFEITURA|CAMARA|MUNICIPIO|MUNICIPAL|FUNDO|SAAE|SAAEE|SAMAE|SERVICO AUTONOMO"
    r"|INSTITUTO|FUNDACAO|SECRETARIA|PREVIDENCIA|RPPS)\b"
)
_LIGACAO = {"DE", "DO", "DA", "DOS", "DAS"}
MAX_PALAVRAS_NOME = 6


def texto_do_pdf(conteudo: bytes, descartar: re.Pattern | None = None) -> str:
    """Texto de um PDF com texto (PyMuPDF; ~100x mais rápido que o pypdf, que levava minutos
    numa edição de 400 páginas). Normaliza ligaduras ("ﬁ" -> "fi") e, com `descartar`,
    tira as linhas que se repetem em cada página (cabeçalho e rodapé)."""
    import pymupdf  # só no grupo "acervo": os conectores de plataformas rodam no acervo

    with pymupdf.open(stream=conteudo, filetype="pdf") as documento:
        paginas = []
        for pagina in documento:
            texto = unicodedata.normalize("NFKC", pagina.get_text())
            if descartar is not None:
                texto = chr(10).join(
                    ln for ln in texto.splitlines() if not descartar.match(ln.strip())
                )
            paginas.append(texto)
    return chr(10).join(paginas)


def indice_municipios(session: Session) -> dict[str, dict[str, str]]:
    """{uf: {nome sem acento em maiúsculas: ibge}}."""
    indice: dict[str, dict[str, str]] = defaultdict(dict)
    for ibge, uf, chave in session.execute(
        select(Municipio.ibge, Municipio.uf, Municipio.nome_chave)
    ):
        indice[uf][chave] = ibge
    return indice


def carregar_alvos(session: Session, indice: dict[str, dict[str, str]]) -> dict[str, list]:
    """{ibge: [(pessoa, nome completo)]} de quem tem mandato em curso (mesmo recorte de
    `diarios/atos.py`), para qualquer município que o conector venha a encontrar."""
    from ingestion.diarios.atos import pessoas_alvo

    todos = {ibge for por_nome in indice.values() for ibge in por_nome.values()}
    alvos: dict[str, list[tuple[int, str]]] = {}
    for pessoa_id, nome, ibge in pessoas_alvo(session, todos):
        alvos.setdefault(ibge, []).append((pessoa_id, nome))
    return alvos


def resolver_municipio(
    cabecalho: str, ufs: list[str] | tuple[str, ...], indice: dict[str, dict[str, str]]
) -> tuple[str, str] | None:
    """(ibge, uf) do município citado no cabeçalho de uma matéria ("PREFEITURA MUNICIPAL DE
    ITAJUBA"), ou None. Pega o maior nome de município que vem depois de "DE/DO/DA" e de uma
    palavra de órgão municipal; órgão sem município (associação, consórcio) fica de fora."""
    palavras = re.findall(r"[A-Z0-9]+", _sem_acento(cabecalho).upper())
    melhor: tuple[int, str, str] | None = None
    for i, palavra in enumerate(palavras):
        if palavra not in _LIGACAO or i + 1 >= len(palavras):
            continue
        if not _ORGAO_MUNICIPAL.search(" ".join(palavras[:i])):
            continue
        for tamanho in range(min(MAX_PALAVRAS_NOME, len(palavras) - i - 1), 0, -1):
            nome = " ".join(palavras[i + 1 : i + 1 + tamanho])
            for uf in ufs:
                ibge = indice.get(uf, {}).get(nome)
                if ibge and (melhor is None or tamanho > melhor[0]):
                    melhor = (tamanho, ibge, uf)
            if melhor and melhor[0] == tamanho:
                break
    return (melhor[1], melhor[2]) if melhor else None


# Quem assina o ato ("O PREFEITO MUNICIPAL DE X, Fulano de Tal, no uso das atribuições...") é
# quem decide, não o alvo do ato: essas ocorrências do nome são apagadas antes da busca.
_ASSINA = re.compile(r"^\W{0,3}(?:NO USO|USANDO|NO EXERCICIO|NO EXERCÍCIO|NA FORMA|CONSIDERANDO)")


def _sem_quem_assina(texto: str, maiusculo: str, padrao: re.Pattern) -> str:
    apagado = texto
    for m in padrao.finditer(maiusculo):
        if _ASSINA.match(maiusculo[m.end() : m.end() + 24]):
            apagado = apagado[: m.start()] + " " * (m.end() - m.start()) + apagado[m.end() :]
    return apagado


def achados_na_materia(texto: str, alvos: list[tuple[int, str]]) -> list[tuple[int, str, str]]:
    """(pessoa, tipo do ato, trecho) para cada pessoa do município citada com ato na matéria."""
    maiusculo = _sem_acento(texto).upper()
    resultado = []
    for pessoa_id, nome in alvos:
        padrao = padrao_nome(nome)
        if padrao is None or not padrao.search(maiusculo):
            continue
        achado = achar_ato(nome, _sem_quem_assina(texto, maiusculo, padrao))
        if achado:
            resultado.append((pessoa_id, achado[0], achado[1]))
    return resultado


def gravar_sugestoes(session: Session, sugestoes: list[dict[str, Any]]) -> int:
    """Insere em `diario_ato` (revisado = falso); a chave (pessoa, url) evita duplicar."""
    novos = 0
    for s in sugestoes:
        resultado = session.execute(
            insert(DiarioAto)
            .values(
                pessoa_id=s["pessoa_id"],
                municipio_ibge=s["municipio_ibge"],
                data=s["data"],
                tipo_ato=s["tipo_ato"],
                trecho=s["trecho"],
                url=s["url"],
            )
            .on_conflict_do_nothing(index_elements=["pessoa_id", "url"])
            .returning(DiarioAto.id)
        )
        novos += 1 if resultado.scalar_one_or_none() is not None else 0
    return novos


def gravar_raw_edicao(fonte: str, subpasta: str, nome: str, edicao: dict[str, Any]) -> Path:
    """Bruto de uma edição (metadados + texto extraído), em JSON comprimido."""
    destino = comum.RAW_DIR / fonte / subpasta
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"{nome}.json.gz"
    caminho.write_bytes(gzip.compress(json.dumps(edicao, ensure_ascii=False).encode("utf-8")))
    return caminho


def ler_raw_edicao(caminho: Path) -> dict[str, Any]:
    return json.loads(gzip.decompress(caminho.read_bytes()).decode("utf-8"))


def registrar_cobertura(
    plataforma: str, observados: dict[tuple[str, str], tuple[str, date, int]]
) -> None:
    """Atualiza data/diarios_plataformas_municipios.csv (evidência de cobertura): uma linha
    por plataforma × município visto nas edições, com a última edição e o nº de matérias vistas
    na última carga (rodar de novo com --de-raw sobre todo o bruto refaz a evidência inteira).
    `observados`: {(uf, ibge): (nome, última edição, matérias)}."""
    linhas: dict[tuple[str, str], dict[str, str]] = {}
    if COBERTURA_CSV.exists():
        with COBERTURA_CSV.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                linhas[(r["plataforma"], r["municipio_ibge"])] = r
    for (uf, ibge), (nome, ultima, materias) in observados.items():
        antiga = linhas.get((plataforma, ibge))
        data_final = max(ultima.isoformat(), antiga["ultima_edicao"]) if antiga else ultima
        linhas[(plataforma, ibge)] = {
            "plataforma": plataforma,
            "uf": uf,
            "municipio_ibge": ibge,
            "municipio": nome,
            "ultima_edicao": str(data_final),
            "materias": str(materias),
        }
    COBERTURA_CSV.parent.mkdir(parents=True, exist_ok=True)
    with COBERTURA_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_COBERTURA)
        w.writeheader()
        for chave in sorted(linhas):
            w.writerow(linhas[chave])
