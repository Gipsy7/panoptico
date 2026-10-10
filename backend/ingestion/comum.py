"""Peças compartilhadas da ingestão: HTTP, arquivo bruto, registro e cargas.

Fluxo de cada fonte: baixar() grava o bruto em data/raw/<fonte>/ e carregar()
transforma o bruto e grava no banco. As duas etapas são separadas para poder
reprocessar o bruto sem rede (--de-raw).
"""

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, func, select, update
from sqlalchemy import insert as sa_insert
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import (
    Candidatura,
    Despesa,
    DownloadCache,
    FonteIngestao,
    Parlamentar,
    Pessoa,
)

RAW_DIR = settings.raw_dir
USER_AGENT = "Panoptico/0.1 (+https://panoptico.social.br)"
# Brutos maiores que isto não são lidos para a memória: carregar_raw devolve o caminho.
LIMITE_EM_MEMORIA = 200_000_000

Baixar = Callable[[httpx.Client], Any]
Normalizar = Callable[[Any], list[dict[str, Any]]]
Carregar = Callable[[Session, Any, FonteIngestao], int]


def criar_cliente() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(30.0, read=120.0),
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        follow_redirects=True,
    )


def _espera(resposta: httpx.Response | None, tentativa: int) -> float:
    """Quanto esperar antes de tentar de novo: o Retry-After da fonte, se houver."""
    if resposta is not None:
        retry_after = resposta.headers.get("Retry-After", "")
        if retry_after.isdigit():
            return min(int(retry_after), 60)
    return float(2**tentativa)


def _get(client: httpx.Client, url: str, params: dict | None, tentativas: int) -> httpx.Response:
    """GET com novas tentativas para falhas de rede, erros 5xx e limite de taxa (429)."""
    resposta = None
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = client.get(url, params=params)
            if resposta.status_code < 500 and resposta.status_code != 429:
                return resposta.raise_for_status()
        except httpx.TransportError:
            if tentativa == tentativas:
                raise
        if tentativa < tentativas:
            time.sleep(_espera(resposta, tentativa))
    return resposta.raise_for_status()


def get_json(client: httpx.Client, url: str, params: dict | None = None, tentativas: int = 3):
    return _get(client, url, params, tentativas).json()


def get_bytes(client: httpx.Client, url: str, tentativas: int = 3) -> bytes:
    return _get(client, url, None, tentativas).content


def baixar_para_arquivo(client: httpx.Client, url: str, tentativas: int = 8) -> Path:
    """Baixa em fluxo para um arquivo temporário, sem passar o conteúdo pela memória (para
    arquivos de centenas de MB, como as contas de campanha do TSE). Se a conexão cair no
    meio (visto no TCE-SP, com arquivos de 2 GB), retoma de onde parou com Range."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as destino:
        caminho = Path(destino.name)
    for tentativa in range(tentativas):
        feito = caminho.stat().st_size
        cabecalhos = {"Range": f"bytes={feito}-"} if feito else {}
        try:
            with client.stream("GET", url, timeout=600, headers=cabecalhos) as resposta:
                if resposta.status_code == 416:  # já estava completo
                    return caminho
                resposta.raise_for_status()
                if feito and resposta.status_code != 206:
                    feito = 0  # o servidor ignorou o Range: recomeça do zero
                with caminho.open("r+b" if feito else "wb") as arquivo:
                    arquivo.seek(feito)
                    for bloco in resposta.iter_bytes():  # grava conforme chega
                        arquivo.write(bloco)
            return caminho
        except (httpx.TransportError, httpx.RemoteProtocolError) as erro:
            if tentativa == tentativas - 1:
                raise
            print(f"  download interrompido ({erro.__class__.__name__}); retomando", flush=True)
            time.sleep(5 * (tentativa + 1))
    return caminho


def salvar_raw(fonte: str, payload: Any, prefixo: str = "", extensao: str = ".zip") -> Path:
    """Grava o bruto. Bytes são gravados como vieram (comprimidos com gzip se a extensão
    terminar em .gz); qualquer outro payload vira JSON."""
    destino = RAW_DIR / fonte
    destino.mkdir(parents=True, exist_ok=True)
    nome = f"{prefixo}{datetime.now():%Y-%m-%d_%H%M%S}"
    if isinstance(payload, Path):  # já baixado em disco (baixar_para_arquivo)
        arquivo = destino / f"{nome}{extensao}"
        shutil.move(payload, arquivo)
        return arquivo
    if isinstance(payload, bytes):
        arquivo = destino / f"{nome}{extensao}"
        arquivo.write_bytes(gzip.compress(payload) if extensao.endswith(".gz") else payload)
    else:
        arquivo = destino / f"{nome}.json"
        arquivo.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return arquivo


def trocar_por_manifesto(fonte: str, desde: datetime | None = None) -> list[Path]:
    """Coleta mínima (bruto = "recorte"): troca o bruto das cargas com sucesso da fonte por
    um manifesto (URL, tamanho, sha256, data). Para arquivos grandes que o órgão mantém no
    ar: refazer a carga é baixar de novo. Com `desde`, só as cargas iniciadas a partir
    dali (uma execução de fonte anual grava uma carga por ano); sem, todas."""
    manifestos = []
    with SessionLocal() as session:
        consulta = select(FonteIngestao).where(
            FonteIngestao.fonte == fonte, FonteIngestao.status == "ok"
        )
        if desde is not None:
            consulta = consulta.where(FonteIngestao.iniciado_em >= desde)
        for ingestao in session.scalars(consulta):
            arquivo = Path(ingestao.arquivo_raw)
            if not arquivo.is_file() or arquivo.name.endswith(".manifesto.json"):
                continue
            resumo = hashlib.sha256()
            with arquivo.open("rb") as entrada:
                for bloco in iter(lambda e=entrada: e.read(1 << 20), b""):
                    resumo.update(bloco)
            manifesto = arquivo.with_name(arquivo.name + ".manifesto.json")
            manifesto.write_text(
                json.dumps(
                    {"url": ingestao.url, "tamanho": arquivo.stat().st_size,
                     "sha256": resumo.hexdigest(),
                     "baixado_em": f"{ingestao.iniciado_em:%Y-%m-%d}"},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )  # fmt: skip
            arquivo.unlink()
            ingestao.arquivo_raw = str(manifesto)
            manifestos.append(manifesto)
        session.commit()
    return manifestos


def carregar_raw(arquivo: Path) -> Any:
    arquivo = Path(arquivo)
    if arquivo.suffix == ".json":
        return json.loads(arquivo.read_text(encoding="utf-8"))
    if arquivo.suffix == ".gz":
        return gzip.decompress(arquivo.read_bytes())
    if arquivo.stat().st_size > LIMITE_EM_MEMORIA:
        return arquivo
    return arquivo.read_bytes()


def mapa_parlamentares(session: Session, casa: str) -> dict[str, int]:
    """id_externo -> id interno, para ligar dados de outras fontes ao parlamentar."""
    linhas = session.execute(
        select(Parlamentar.id_externo, Parlamentar.id).where(Parlamentar.casa == casa)
    )
    return {id_externo: id_ for id_externo, id_ in linhas}


def vincular_parlamentares(
    session: Session, casa: str, registros: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Troca o id externo pelo id interno e descarta quem não está na base."""
    mapa = mapa_parlamentares(session, casa)
    linhas = []
    for r in registros:
        parlamentar_id = mapa.get(r["id_externo_parlamentar"])
        if parlamentar_id is not None:
            linha = {k: v for k, v in r.items() if k != "id_externo_parlamentar"}
            linhas.append({**linha, "parlamentar_id": parlamentar_id})
    return linhas


def upsert_parlamentares(
    session: Session, casa: str, registros: list[dict[str, Any]], ingestao: FonteIngestao
) -> int:
    """Faz upsert da lista e marca os demais parlamentares da casa como fora de exercício."""
    if not registros:
        raise ValueError(f"Nenhum registro para {casa}; abortando para não zerar a casa.")

    agora = datetime.now(UTC)
    linhas = [
        {
            **r,
            "casa": casa,
            "em_exercicio": True,
            "atualizado_em": agora,
            "ingestao_id": ingestao.id,
        }
        for r in registros
    ]
    stmt = insert(Parlamentar).values(linhas)
    colunas_atualizaveis = {
        c: stmt.excluded[c] for c in linhas[0] if c not in ("casa", "id_externo")
    }
    session.execute(
        stmt.on_conflict_do_update(
            constraint="uq_parlamentar_casa_id_externo", set_=colunas_atualizaveis
        )
    )

    ids = [r["id_externo"] for r in registros]
    session.execute(
        update(Parlamentar)
        .where(Parlamentar.casa == casa, Parlamentar.id_externo.not_in(ids))
        .values(em_exercicio=False, atualizado_em=agora)
    )
    return len(linhas)


def chave_nome(nome: str | None) -> str:
    """Chave para comparar nomes: 'Dr. Flávio' -> 'DR FLAVIO'."""
    sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^A-Z ]", " ", sem_acento.upper()).split())


PARTICULAS = {"da", "das", "de", "do", "dos", "e"}


def nome_proprio(nome: str | None) -> str | None:
    """'MARIA DA SILVA' -> 'Maria da Silva'. Nomes já em caixa mista ficam como estão."""
    if not nome or not nome.isupper():
        return nome
    palavras = nome.lower().split()
    return " ".join(
        p if i > 0 and p in PARTICULAS else p[:1].upper() + p[1:] for i, p in enumerate(palavras)
    )


def limpar_categoria(texto: str | None) -> str:
    """Padroniza o nome da categoria de gasto (a Câmara publica tudo em maiúsculas)."""
    t = re.sub(r"\s*,\s*", ", ", " ".join((texto or "").split())).rstrip(".").strip()
    if not t:
        return "Não informado"
    return t[0].upper() + t[1:].lower() if t.isupper() else t


def recarregar_despesas(
    session: Session, casa: str, ano: int, linhas: list[dict[str, Any]], ingestao: FonteIngestao
) -> int:
    """Substitui as despesas de uma casa num ano. Os arquivos oficiais são anuais e mudam
    retroativamente (glosas, restituições), então recarregar o ano inteiro é o mais seguro."""
    if not linhas:
        raise ValueError(f"Nenhuma despesa de {casa} em {ano}; abortando para não zerar o ano.")
    session.execute(delete(Despesa).where(Despesa.casa == casa, Despesa.ano == ano))
    base = {"casa": casa, "ano": ano, "ingestao_id": ingestao.id}
    for inicio in range(0, len(linhas), 5000):
        lote = [{**base, **linha} for linha in linhas[inicio : inicio + 5000]]
        session.execute(sa_insert(Despesa), lote)
    return len(linhas)


def anos_padrao() -> list[int]:
    ano = datetime.now().year
    return [ano - 1, ano]


# --- Carga incremental: não baixa nem recarrega o que não mudou -------------------------

SEM_MUDANCA = "sem_mudanca"
# Status que contam como carga bem-sucedida (o acervo e o --vencidas tratam igual).
STATUS_SUCESSO = ("ok", SEM_MUDANCA)
# Quantas cargas terminaram sem mudança nesta execução (o acervo lê para o relatório).
cargas_sem_mudanca = 0
# Ignora o cache e carrega de qualquer jeito (acervo --forcar ou PANOPTICO_FORCAR=1).
forcar = os.environ.get("PANOPTICO_FORCAR", "") in ("1", "true", "sim")


@dataclass
class Incremental:
    """Liga a carga incremental numa fonte (opt-in).

    chave: identifica o arquivo no download_cache (padrão: a URL da carga).
    sonda: URL consultada com requisição condicional antes de baixar (None: não sonda e
        compara só o sha256 depois de baixar, para URLs que mudam de nome ou APIs).
    contexto: texto que muda quando algo de que a carga depende mudou no banco (ex.: novas
        pessoas a ligar). Se mudou, recarrega mesmo com o arquivo igual.
    """

    chave: str | None = None
    sonda: str | None = None
    contexto: Callable[[Session], str] | None = None


def contexto_pessoas(session: Session) -> str:
    """Muda quando entram pessoas novas: fontes que só gravam "as pessoas que já temos"
    precisam reler o arquivo igual para ligar quem chegou depois."""
    total, maior = session.execute(select(func.count(Pessoa.id), func.max(Pessoa.id))).one()
    return f"pessoas:{total}:{maior}"


def contexto_candidaturas(ano: int) -> Callable[[Session], str]:
    """Pessoas + as candidaturas do ano (para fontes que se penduram nelas)."""

    def contexto(session: Session) -> str:
        total, maior = session.execute(
            select(func.count(Candidatura.id), func.max(Candidatura.id)).where(
                Candidatura.ano_eleicao == ano
            )
        ).one()
        return f"{contexto_pessoas(session)};candidaturas:{total}:{maior}"

    return contexto


def sha256_de(payload: Any) -> str:
    """sha256 do arquivo, dos bytes ou, para JSON já lido (dict/list), do JSON canônico."""
    resumo = hashlib.sha256()
    if not isinstance(payload, bytes | Path):
        payload = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    if isinstance(payload, Path):
        with payload.open("rb") as entrada:
            for bloco in iter(lambda e=entrada: e.read(1 << 20), b""):
                resumo.update(bloco)
    else:
        resumo.update(payload)
    return resumo.hexdigest()


def sondar(client: httpx.Client, url: str, cache: DownloadCache | None) -> dict[str, Any]:
    """Pergunta ao servidor se o arquivo mudou, sem baixar. Devolve {"igual": True|False|None,
    "etag", "last_modified", "tamanho"}; igual None = não deu para saber (baixa e compara o
    sha256). Usa HEAD condicional (If-None-Match / If-Modified-Since); 304 ou validadores
    iguais ao do último download significam que nada mudou."""
    resultado: dict[str, Any] = {"igual": None, "etag": None, "last_modified": None,
                                 "tamanho": None}  # fmt: skip
    cabecalhos = {}
    if cache is not None and cache.etag:
        cabecalhos["If-None-Match"] = cache.etag
    if cache is not None and cache.last_modified:
        cabecalhos["If-Modified-Since"] = cache.last_modified
    try:
        resposta = client.head(url, headers=cabecalhos, timeout=30)
    except httpx.HTTPError:
        return resultado
    if resposta.status_code == 304:
        resultado["igual"] = True
        return resultado
    if resposta.status_code != 200:  # HEAD não suportado, bloqueado ou erro: baixa
        return resultado
    etag = resposta.headers.get("ETag")
    modificado = resposta.headers.get("Last-Modified")
    tamanho = resposta.headers.get("Content-Length")
    resultado.update(etag=etag, last_modified=modificado, tamanho=int(tamanho) if tamanho else None)
    if cache is not None:
        if etag:
            resultado["igual"] = etag == cache.etag
        elif modificado and tamanho:
            resultado["igual"] = modificado == cache.last_modified and int(tamanho) == cache.tamanho
    return resultado


def _registrar_sem_mudanca(
    session: Session, fonte: str, url: str, motivo: str, info: dict[str, Any], cache
) -> int:
    """Grava a verificação (status "sem_mudanca") e devolve o total da última carga, para o
    acervo não ler a ausência de carga como queda."""
    global cargas_sem_mudanca
    anterior = session.scalars(
        select(FonteIngestao)
        .where(
            FonteIngestao.fonte == fonte,
            FonteIngestao.url == url,
            FonteIngestao.status.in_(STATUS_SUCESSO),
        )
        .order_by(FonteIngestao.iniciado_em.desc(), FonteIngestao.id.desc())
        .limit(1)
    ).first()
    total = anterior.registros if anterior and anterior.registros is not None else 0
    agora = datetime.now(UTC)
    session.add(
        FonteIngestao(
            fonte=fonte,
            url=url,
            arquivo_raw=anterior.arquivo_raw if anterior else "",
            status=SEM_MUDANCA,
            registros=total,
            total_fonte=anterior.total_fonte if anterior else None,
            concluido_em=agora,
        )
    )
    if cache is not None:
        cache.etag = info.get("etag") or cache.etag
        cache.last_modified = info.get("last_modified") or cache.last_modified
        cache.baixado_em = agora
    session.commit()
    cargas_sem_mudanca += 1
    print(f"  {fonte}: sem mudança ({motivo}); nada baixado/carregado de novo", flush=True)
    return total


def _guardar_cache(
    session: Session, chave: str, url: str, sha: str, tamanho: int, info: dict, contexto
) -> None:
    linha = {
        "chave": chave, "url": url, "etag": info.get("etag"),
        "last_modified": info.get("last_modified"), "sha256": sha,
        "tamanho": info.get("tamanho") or tamanho, "contexto": contexto,
        "baixado_em": datetime.now(UTC),
    }  # fmt: skip
    stmt = insert(DownloadCache).values(linha)
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["chave"], set_={k: v for k, v in linha.items() if k != "chave"}
        )
    )


class ContaLinhas:
    """Conta as linhas de um iterador à medida que passam (para o total do arquivo sem
    guardar tudo na memória): `linhas = ContaLinhas(it)`; depois de consumir, `linhas.total`."""

    def __init__(self, iterador: Iterable[Any]) -> None:
        self.iterador = iterador
        self.total = 0

    def __iter__(self):
        for linha in self.iterador:
            self.total += 1
            yield linha


def conferir_carga(
    ingestao: FonteIngestao,
    linhas: Iterable[dict[str, Any]] | None = None,
    *,
    total_fonte: int | None = None,
    nao_nulos: Iterable[str] = (),
    unica: Iterable[str] | None = None,
    total_carregado: int | None = None,
) -> list[str]:
    """Checagens de qualidade da carga, gravadas em fonte_ingestao.alertas.

    total_fonte: o total que a fonte informa (ou as linhas do arquivo); só informativo,
    a menos que total_carregado também venha (aí diferença vira alerta).
    nao_nulos: campos-chave que não podem estar vazios nas linhas carregadas.
    unica: campos que juntos identificam a linha; repetidos viram alerta."""
    alertas: list[str] = []
    if total_fonte is not None:
        ingestao.total_fonte = total_fonte
        if total_carregado is not None and total_carregado != total_fonte:
            alertas.append(f"carregou {total_carregado} de {total_fonte} informados pela fonte")
    if linhas is not None:
        linhas = list(linhas)
        for campo in nao_nulos:
            nulos = sum(1 for r in linhas if r.get(campo) in (None, ""))
            if nulos:
                alertas.append(f"campo-chave {campo} vazio em {nulos} de {len(linhas)} linhas")
        if unica:
            chaves = [tuple(r.get(c) for c in unica) for r in linhas]
            repetidas = len(chaves) - len(set(chaves))
            if repetidas:
                alertas.append(f"{repetidas} linhas repetidas na chave ({', '.join(unica)})")
    ingestao.alertas = alertas or None
    return alertas


def executar_ingestao(
    fonte: str,
    url: str,
    baixar: Baixar,
    carregar: Carregar,
    de_raw: Path | None = None,
    prefixo_raw: str = "",
    extensao_raw: str = ".zip",
    incremental: Incremental | bool = False,
) -> int:
    """Baixa (ou lê o bruto), grava o bruto e roda a carga numa transação registrada.

    Com `incremental` (True: pela URL da carga), antes de baixar sonda o servidor
    (ETag/Last-Modified) e, depois de baixar, compara o sha256 com o do último download:
    se nada mudou, não grava o bruto, não recarrega e registra status "sem_mudanca"."""
    if incremental is True:
        incremental = Incremental(chave=url, sonda=url)
    usar_cache = bool(incremental) and de_raw is None and not forcar
    chave = (incremental.chave or url) if incremental else url
    info: dict[str, Any] = {}
    contexto = None
    sha = None
    tamanho = 0
    if de_raw is None:
        cache = None
        if incremental:
            with SessionLocal() as session:
                cache = session.get(DownloadCache, chave)
                if cache is not None:
                    session.expunge(cache)
                if incremental.contexto is not None:
                    contexto = incremental.contexto(session)
            if cache is not None and cache.contexto != contexto:
                cache = None  # algo de que a carga depende mudou: relê mesmo se igual
        with criar_cliente() as client:
            if incremental and incremental.sonda:
                info = sondar(client, incremental.sonda, cache if usar_cache else None)
                if usar_cache and cache is not None and info["igual"]:
                    with SessionLocal() as session:
                        return _registrar_sem_mudanca(
                            session, fonte, url, "servidor informa o mesmo arquivo", info,
                            session.get(DownloadCache, chave),
                        )  # fmt: skip
            payload = baixar(client)
        if incremental:
            sha = sha256_de(payload)
            if usar_cache and cache is not None and cache.sha256 == sha:
                if isinstance(payload, Path):
                    payload.unlink(missing_ok=True)  # versão igual não se acumula no bruto
                with SessionLocal() as session:
                    return _registrar_sem_mudanca(
                        session, fonte, url, "sha256 igual ao do último download", info,
                        session.get(DownloadCache, chave),
                    )  # fmt: skip
        if isinstance(payload, Path):
            tamanho = payload.stat().st_size
        elif isinstance(payload, bytes):
            tamanho = len(payload)
        else:  # JSON já lido (dict/list)
            tamanho = len(json.dumps(payload, ensure_ascii=False))
        arquivo = salvar_raw(fonte, payload, prefixo_raw, extensao_raw)
        if isinstance(payload, Path):  # o arquivo foi movido para o raw
            payload = arquivo
    else:
        arquivo = Path(de_raw)
        payload = carregar_raw(arquivo)

    with SessionLocal() as session:
        ingestao = FonteIngestao(fonte=fonte, url=url, arquivo_raw=str(arquivo))
        session.add(ingestao)
        session.flush()
        try:
            total = carregar(session, payload, ingestao)
            ingestao.registros = total
            ingestao.status = "ok"
            ingestao.concluido_em = datetime.now(UTC)
            if sha is not None:  # só vale como "último download" se a carga deu certo
                _guardar_cache(session, chave, url, sha, tamanho, info, contexto)
            session.commit()
        except Exception:
            session.rollback()
            session.add(
                FonteIngestao(
                    fonte=fonte,
                    url=url,
                    arquivo_raw=str(arquivo),
                    status="erro",
                    concluido_em=datetime.now(UTC),
                )
            )
            session.commit()
            raise
    return total


def executar(
    fonte: str,
    casa: str,
    url: str,
    baixar: Baixar,
    normalizar: Normalizar,
    de_raw: Path | None = None,
) -> int:
    """Ingestão da lista de parlamentares de uma casa."""

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        return upsert_parlamentares(session, casa, normalizar(payload), ingestao)

    return executar_ingestao(fonte, url, baixar, carregar, de_raw=de_raw)


def main(fonte: str, casa: str, url: str, baixar: Baixar, normalizar: Normalizar) -> None:
    parser = argparse.ArgumentParser(description=f"Ingestão: {fonte}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    total = executar(fonte, casa, url, baixar, normalizar, de_raw=args.de_raw)
    print(f"{fonte}: {total} registros")
