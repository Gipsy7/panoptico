"""Gastos do gabinete (verba indenizatória, cota) de assembleias cuja lista de deputados vem de
outro conector (SAPL, PLE, API própria) e cujos gastos só saem num portal de transparência à
parte. Cada casa tem um leitor fino (`gastos_alba.py`, `gastos_alepe.py`...) que baixa o portal e
devolve lançamentos com o nome do deputado como a fonte escreve; daqui vem o resto:

- liga o nome ao deputado em exercício já gravado (`mandato_local` da UF) só por igualdade
  exata ou por decisão humana já registrada (`base.ligar_nomes`, fila de apelidos);
- soma por deputado, ano, mês e categoria e substitui os gastos da UF (`gasto_local`), numa
  transação registrada em `fonte_ingestao`, com o bruto em `data/raw/<fonte>/` (zip);
- se o portal não responder, reprocessa o último bruto e marca a carga com
  `[gastos_mantidos]` (a data mostrada no site continua a da última leitura real).

A carga da casa (lista de deputados) apaga e regrava os mandatos, e com eles os gastos: estes
leitores rodam depois dela na agenda (`deploy/vps/agenda/camaras.sh`). O fornecedor nunca é
guardado (pode ser pessoa física); só deputado, mês, categoria e valor.
"""

import io
import time
import zipfile
from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select

from app.models import FonteIngestao, GastoLocal, GastoLocalFora, MandatoLocal
from ingestion import comum
from ingestion.assembleias import base

MARCA_GASTOS_MANTIDOS = "[gastos_mantidos]"  # lido por app.services.camaras

Arquivos = dict[str, bytes]


def valor_br(texto: str | None) -> Decimal | None:
    """'R$ 4.669,65' -> 4669.65; '13816,6' -> 13816.60; '-' ou vazio -> None."""
    limpo = (texto or "").replace("R$", "").replace("\xa0", " ").strip()
    if not limpo or limpo == "-":
        return None
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        return Decimal(limpo.replace(" ", "")).quantize(Decimal("0.01"))
    except ArithmeticError:
        return None


def empacotar(arquivos: Arquivos) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in sorted(arquivos.items()):
            z.writestr(nome, conteudo)
    return memoria.getvalue()


def desempacotar(payload: bytes) -> Arquivos:
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        return {n: z.read(n) for n in z.namelist()}


def deputados_da_casa(session: Any, uf: str) -> list[dict]:
    """Os deputados em exercício já gravados pela carga da casa, com o nome parlamentar e,
    quando houver, o civil (cada um como uma entrada, para a ligação por nome exato)."""
    resultado = []
    for m in session.scalars(
        select(MandatoLocal).where(
            MandatoLocal.casa == "assembleia", MandatoLocal.uf == uf, MandatoLocal.em_exercicio
        )
    ):
        resultado.append({"id_externo": m.id_externo, "nome": m.nome, "mandato_id": m.id})
        if m.nome_completo and comum.chave_nome(m.nome_completo) != comum.chave_nome(m.nome):
            resultado.append(
                {"id_externo": m.id_externo, "nome": m.nome_completo, "mandato_id": m.id}
            )
    return resultado


def gravar(
    session: Any,
    *,
    uf: str,
    escopo: str,
    lancamentos: list[dict],
    sigla: str,
) -> tuple[int, list[str]]:
    """Substitui os gastos dos deputados em exercício da UF pelos `lancamentos` (dicts com
    `nome`, `ano`, `mes`, `categoria`, `valor`). Devolve (linhas gravadas, avisos). Aborta sem
    lançamentos, sem deputados na casa ou se nada ligar (falha da fonte, não "sem gastos")."""
    if not lancamentos:
        raise ValueError(f"{sigla}: nenhum lançamento de gasto lido; abortando.")
    deputados = deputados_da_casa(session, uf)
    if not deputados:
        raise ValueError(f"{sigla}: a casa não tem deputados gravados; rode a carga dela antes.")
    totais: dict[str, tuple[int, Decimal]] = {}
    for lan in lancamentos:
        chave = comum.chave_nome(lan["nome"])
        linhas, valor = totais.get(chave, (0, Decimal(0)))
        totais[chave] = (linhas + 1, valor + lan["valor"])
    ligados, sobras = base.ligar_nomes(escopo, totais, deputados, base.nomes_do_tse(session, uf))
    mandato_por_nome: dict[str, set[int]] = defaultdict(set)
    for d in deputados:
        mandato_por_nome[d["nome"]].add(d["mandato_id"])
    soma: dict[tuple, Decimal] = defaultdict(Decimal)
    for lan in lancamentos:
        alvo = mandato_por_nome.get(ligados.get(comum.chave_nome(lan["nome"]), ""), set())
        if len(alvo) != 1:
            continue
        categoria = " ".join(str(lan["categoria"]).split())[:200] or "Sem categoria na fonte"
        soma[(next(iter(alvo)), int(lan["ano"]), int(lan["mes"]), categoria)] += lan["valor"]
    if not soma:
        raise ValueError(f"{sigla}: nenhum gasto ligado a deputado em exercício; abortando.")
    ids = sorted({d["mandato_id"] for d in deputados})
    session.execute(delete(GastoLocal).where(GastoLocal.mandato_id.in_(ids)))
    session.execute(delete(GastoLocalFora).where(GastoLocalFora.mandato_id.in_(ids)))
    linhas = [
        {"mandato_id": m, "ano": a, "mes": mes, "categoria": c, "valor": v}
        for (m, a, mes, c), v in sorted(soma.items())
    ]
    for inicio in range(0, len(linhas), 5000):
        session.execute(insert(GastoLocal), linhas[inicio : inicio + 5000])
    avisos = []
    if sobras:
        valor = sum((totais[s][1] for s in sobras), Decimal(0))
        avisos.append(
            f"Gastos {sigla}: {len(sobras)} nomes da fonte sem deputado em exercício com nome "
            f"igual (ex-deputados, suplentes ou grafia diferente; fila de revisão de apelidos), "
            f"R$ {valor:.2f} fora: " + "; ".join(sobras)
        )
    ligados_ids = {m for (m, *_resto) in soma}
    print(
        f"{sigla}: {len(linhas)} linhas de gasto, {len(ligados_ids)} deputados ligados, "
        f"{len(sobras)} nomes na fila",
        flush=True,
    )
    return len(linhas), avisos


def ultimo_bruto(fonte: str) -> Path | None:
    arquivos = sorted((comum.RAW_DIR / fonte).glob("*.zip"), key=lambda p: p.stat().st_mtime)
    return arquivos[-1] if arquivos else None


def executar(
    *,
    fonte: str,
    uf: str,
    sigla: str,
    url: str,
    baixar: Callable[[httpx.Client], Arquivos],
    ler: Callable[[Arquivos], list[dict]],
    de_raw: Path | None = None,
) -> int:
    """Baixa (ou relê o bruto), liga e grava. Se o portal falhar por rede ou HTTP e houver
    bruto anterior, reprocessa o último com o aviso de gastos mantidos."""
    mantidos: list[str] = []

    def carregar(session: Any, payload: bytes, ingestao: FonteIngestao) -> int:
        total, avisos = gravar(
            session, uf=uf, escopo=fonte, lancamentos=ler(desempacotar(payload)), sigla=sigla
        )
        ingestao.alertas = (mantidos + avisos) or None
        return total

    if de_raw is None:
        try:
            with comum.criar_cliente() as client:
                payload = empacotar(baixar(client))
        except (httpx.HTTPError, ValueError) as erro:
            anterior = ultimo_bruto(fonte)
            if anterior is None:
                raise
            mantidos.append(
                f"{MARCA_GASTOS_MANTIDOS} Gastos {sigla}: o portal não respondeu "
                f"({erro.__class__.__name__}: {str(erro)[:120]}); relido o bruto {anterior.name}"
            )
            print(f"  AVISO {mantidos[0]}", flush=True)
            return comum.executar_ingestao(fonte, url, lambda _c: b"", carregar, de_raw=anterior)
        return comum.executar_ingestao(fonte, url, lambda _c: payload, carregar)
    return comum.executar_ingestao(fonte, url, lambda _c: b"", carregar, de_raw=de_raw)


def pausar(segundos: float) -> None:
    """Uma requisição por vez, com pausa (os portais são das casas)."""
    if segundos:
        time.sleep(segundos)
