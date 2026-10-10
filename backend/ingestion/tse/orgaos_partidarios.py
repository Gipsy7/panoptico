"""Cargos partidários atuais (presidente, tesoureiro, membro de diretório...) das pessoas
que já acompanhamos, pelo arquivo de órgãos partidários do TSE, como eventos da linha do
tempo.

O arquivo tem o histórico de todos os órgãos desde os anos 1990 (219 MB compactado,
~2 GB aberto). Coleta mínima: é lido de passagem e só ficam os cargos **vigentes**, em
órgãos vigentes, de quem já está na base; a ligação é pelo título de eleitor. O bruto não
é guardado (fica um manifesto): para refazer, baixa-se de novo.
"""

import argparse
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.orm import Session

from app.models import Evento, FonteIngestao, Pessoa, PessoaVinculo
from ingestion import comum
from ingestion.tse import comum_tse

FONTE = "tse_orgaos_partidarios"
URL = f"{comum_tse.BASE}/orgao_partidario/orgao_partidario.zip"
URL_DADOS = "https://dadosabertos.tse.jus.br/dataset/delegados-partidarios"
LOTE = 5000


def _data(valor: str | None) -> date | None:
    """O arquivo tem datas com o ano truncado ("16/03/0208"): ano antes de 1980 vira None."""
    lida = comum_tse.data(valor)
    return lida if lida and lida.year >= 1980 else None


def _texto(valor: str | None) -> str:
    return (comum_tse.texto(valor) or "").strip()


def descricao(linha: dict[str, str]) -> str:
    cargo = _texto(linha.get("DS_CARGO_MEMBRO")).capitalize() or "Membro"
    orgao = _texto(linha.get("NM_TIPO_ORGAO_PARTIDARIO")).lower() or "órgão partidário"
    abrangencia = _texto(linha.get("DS_TIPO_ABRANGENCIA")).lower()
    partido = _texto(linha.get("SG_PARTIDO"))
    uf = _texto(linha.get("SG_UF"))
    lugar = ""
    if abrangencia == "municipal":
        municipio = comum.nome_proprio(_texto(linha.get("NM_MUNICIPIO")))
        lugar = f" em {municipio} ({uf})" if municipio else ""
    elif abrangencia == "estadual" and uf:
        lugar = f" em {uf}"
    return f"{cargo} do {orgao} {abrangencia} do {partido}{lugar}".replace("  ", " ")


def eventos(linhas: Any, por_titulo: dict[str, int]) -> list[dict[str, Any]]:
    """Só cargos vigentes em órgãos vigentes, de pessoas da base (título -> pessoa)."""
    resultado: dict[str, dict[str, Any]] = {}
    for linha in linhas:
        if linha.get("DS_SITU_EXERC_MEMBRO") != "VIGENTE":
            continue
        if linha.get("DS_SITU_EXERC_ORGAO_PARTIDARIO") != "VIGENTE":
            continue
        pessoa = por_titulo.get(comum_tse.titulo(linha.get("NR_TITULO_ELEITORAL_MEMBRO")) or "")
        if pessoa is None:
            continue
        id_externo = f"{linha['SQ_ORGAO_PARTIDARIO']}:{linha['SQ_CARGO_MEMBRO']}"
        gerado = comum_tse.data(linha.get("DT_GERACAO"))
        resultado[id_externo] = {
            "pessoa_id": pessoa,
            "id_externo": id_externo,
            "data": _data(linha.get("DT_INICIO_EXERCICIO_MEMBRO")),
            "tipo": "cargo_partidario",
            "descricao": descricao(linha),
            "orgao": _texto(linha.get("SG_PARTIDO"))[:120] or None,
            "situacao": f"vigente segundo o TSE em {gerado:%d/%m/%Y}" if gerado else "vigente",
            "fonte_url": URL_DADOS,
        }
    return list(resultado.values())


def gravar(session: Session, linhas: list[dict[str, Any]], ingestao_id: int | None) -> int:
    """Grava só o que mudou (cargo novo, alterado ou encerrado), para a recarga de 18 mil
    cargos não reescrever o banco inteiro. A data "vigente segundo o TSE em ..." não conta
    como mudança: ela muda em todas as linhas a cada arquivo novo."""
    campos = ("pessoa_id", "data", "descricao", "orgao", "fonte_url")
    atuais = {
        e.id_externo: e
        for e in session.execute(
            select(
                Evento.id, Evento.id_externo, Evento.vinculo_id,
                *(getattr(Evento, c) for c in campos),
            ).where(Evento.fonte == FONTE)
        )
    }  # fmt: skip
    novos = {linha["id_externo"]: linha for linha in linhas}
    sumiram = [e.vinculo_id for k, e in atuais.items() if k not in novos]
    for inicio in range(0, len(sumiram), LOTE):  # o evento cai junto (cascata do vínculo)
        lote = sumiram[inicio : inicio + LOTE]
        session.execute(delete(PessoaVinculo).where(PessoaVinculo.id.in_(lote)))

    mudaram = [
        (atuais[k], linha) for k, linha in novos.items()
        if k in atuais and any(getattr(atuais[k], c) != linha[c] for c in campos)
    ]  # fmt: skip
    for velho, linha in mudaram:
        session.execute(
            update(PessoaVinculo).where(PessoaVinculo.id == velho.vinculo_id)
            .values(pessoa_id=linha["pessoa_id"])
        )  # fmt: skip
        session.execute(
            update(Evento).where(Evento.id == velho.id).values(**linha, ingestao_id=ingestao_id)
        )

    acrescentar = [linha for k, linha in novos.items() if k not in atuais]
    for inicio in range(0, len(acrescentar), LOTE):
        lote = acrescentar[inicio : inicio + LOTE]
        ids = session.scalars(
            insert(PessoaVinculo).returning(PessoaVinculo.id, sort_by_parameter_order=True),
            [{"pessoa_id": x["pessoa_id"], "fonte": FONTE, "id_externo": x["id_externo"],
              "regra": "titulo"} for x in lote],
        ).all()  # fmt: skip
        session.execute(
            insert(Evento),
            [{**x, "vinculo_id": v, "fonte": FONTE, "ingestao_id": ingestao_id}
             for x, v in zip(lote, ids, strict=True)],
        )  # fmt: skip
    print(f"  {len(acrescentar)} cargos novos, {len(mudaram)} alterados, {len(sumiram)} encerrados")
    return len(linhas)


def contexto_titulos(session: Session) -> str:
    """Muda quando entram pessoas com título de eleitor (as que o arquivo pode ligar)."""
    total, maior = session.execute(
        select(func.count(Pessoa.id), func.max(Pessoa.id)).where(Pessoa.titulo.is_not(None))
    ).one()
    return f"titulos:{total}:{maior}"


def executar(de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, URL)

    def carregar(session: Session, payload: Path, ingestao: FonteIngestao) -> int:
        por_titulo = dict(
            session.execute(
                select(Pessoa.titulo, Pessoa.id).where(Pessoa.titulo.is_not(None))
            ).all()
        )
        linhas = eventos(comum_tse.linhas(payload, "orgao_partidario_"), por_titulo)
        if not linhas:
            raise RuntimeError("Nenhum cargo partidário de pessoas da base: nada alterado.")
        total = gravar(session, linhas, ingestao.id)
        print(f"  {total} cargos partidários vigentes de pessoas da base")
        return total

    # O arquivo tem 219 MB: a sonda (ETag) evita baixar de novo enquanto o TSE não o republica.
    total = comum.executar_ingestao(
        FONTE, URL, baixar, carregar, de_raw=de_raw,
        incremental=comum.Incremental(sonda=URL, contexto=contexto_titulos),
    )  # fmt: skip
    if de_raw is None:
        comum.trocar_por_manifesto(FONTE)
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} cargos")
