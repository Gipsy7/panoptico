"""Discursos em Plenário do Senado (pronunciamentos por período).

`GET /plenario/lista/discursos/{AAAAMMDD}/{AAAAMMDD}` lista as sessões do período com os
pronunciamentos de cada uma: id, tipo de uso da palavra, resumo oficial, indexação, link do
texto integral e o código do senador (as falas de autoridades e convidados vêm sem código e
ficam de fora). O `CodigoSessao` é o mesmo da API de votações. O resumo das falas de votação é
descritivo ("Orientação à bancada, pelo Partido PT, sobre o PLP nº 14, de 2026"): não traz o
argumento, que só está no texto integral (o link).

O Senado publica com cerca de 1 semana de atraso: a carga incremental recobre as últimas 3
semanas desde a última carga `ok`; a primeira vai do início do ano anterior. Só sessões do
Senado (`SF`; as do Congresso ficam de fora). O bruto guarda a janela, então `--de-raw` repete a
mesma carga sem rede. Apaga e reinsere os discursos da janela.
"""

import argparse
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import FonteIngestao
from ingestion import comum
from ingestion import discursos_comum as dc

FONTE = "senado_discursos"
CASA = "senado"
URL = "https://legis.senado.leg.br/dadosabertos/plenario/lista/discursos/{ini}/{fim}"
MARGEM_DIAS = 21
# Um mês do calendário por chamada: a API recusa (400) período maior que um mês (01/02 a 02/03
# dá 400; 01/02 a 01/03 e 01/01 a 31/01 passam).
PAUSA = 0.3


def _lista(valor: Any) -> list:
    """A API devolve objeto quando há um item só e lista quando há vários."""
    if valor is None:
        return []
    return valor if isinstance(valor, list) else [valor]


def baixar(client: httpx.Client, inicio: date, fim: date, completa: bool) -> dict[str, Any]:
    respostas, de = [], inicio
    while de <= fim:
        proximo = date(de.year + de.month // 12, de.month % 12 + 1, 1)
        ate = min(proximo - timedelta(days=1), fim)
        respostas.append(
            comum.get_json(client, URL.format(ini=f"{de:%Y%m%d}", fim=f"{ate:%Y%m%d}"))
        )
        de = ate + timedelta(days=1)
        time.sleep(PAUSA)
    return {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "completa": completa,
        "respostas": respostas,
    }


def normalizar(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Bruto -> pronunciamentos de senadores em sessões do Senado, com as matérias citadas
    (resumo + indexação)."""
    registros = []
    for resposta in payload["respostas"]:
        sessoes = _lista(
            ((resposta.get("DiscursosSessao") or {}).get("Sessoes") or {}).get("Sessao")
        )
        for sessao in sessoes:
            if sessao.get("SiglaCasa") != "SF":
                continue
            for p in _lista((sessao.get("Pronunciamentos") or {}).get("Pronunciamento")):
                codigo = p.get("CodigoParlamentar")
                dia = p.get("Data") or sessao.get("DataSessao")
                if not codigo or not dia:
                    continue
                resumo = dc.limpar_texto(p.get("Resumo"))
                registros.append(
                    {
                        "id_externo": str(p["CodigoPronunciamento"]),
                        "id_externo_parlamentar": str(codigo),
                        "data": date.fromisoformat(dia[:10]),
                        "data_hora": None,  # a fonte só informa o dia
                        "sessao_id_externo": str(sessao["CodigoSessao"]),
                        "fase": sessao.get("DescricaoSessao"),
                        "tipo": (p.get("TipoUsoPalavra") or {}).get("Descricao"),
                        "sumario": resumo,
                        "url_texto": p.get("TextoIntegral") or None,
                        "url_video": None,
                        "citadas": dc.citacoes(f"{resumo or ''} {p.get('Indexacao') or ''}"),
                    }
                )
    return registros


def carregar(session: Session, payload: dict[str, Any], ingestao: FonteIngestao) -> int:
    linhas = comum.vincular_parlamentares(session, CASA, normalizar(payload))
    return dc.recarregar_discursos(
        session,
        CASA,
        date.fromisoformat(payload["inicio"]),
        date.fromisoformat(payload["fim"]),
        linhas,
        ingestao,
        completa=payload.get("completa", False),
    )


def executar(de_raw: Path | None = None, desde: date | None = None) -> int:
    """Incremental por padrão; `desde` força o início da janela."""
    hoje = date.today()
    piso = date(comum.anos_padrao()[0], 1, 1)
    estado: dict[str, Any] = {}
    if de_raw is None:
        with comum.SessionLocal() as session:
            if desde is not None:
                inicio, completa = max(desde, piso), desde <= piso
            else:
                inicio, completa = dc.inicio_incremental(session, FONTE, MARGEM_DIAS, piso, hoje)
            estado = {"inicio": inicio, "completa": completa}

    def baixar_janela(client: httpx.Client) -> dict[str, Any]:
        return baixar(client, estado["inicio"], hoje, estado["completa"])

    return comum.executar_ingestao(
        FONTE, URL.format(ini="AAAAMMDD", fim="AAAAMMDD"), baixar_janela, carregar, de_raw=de_raw
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    parser.add_argument(
        "--desde",
        type=date.fromisoformat,
        help="Início da janela (AAAA-MM-DD); padrão: incremental",
    )
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw, desde=args.desde)} discursos")
