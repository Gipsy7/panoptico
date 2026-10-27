"""Pauta do Plenário do Senado: sessões de hoje a +14 dias e as matérias de cada uma.

API: `/plenario/agenda/mes/{AAAAMMDD}` (da data até o fim do mês; a janela pode cruzar o mês,
então pode levar duas chamadas). `Sessoes.Sessao[]` → `Materias.Materia[]` (uma matéria só
vem como objeto, e sessão sem pauta não tem `Materias`). `CodigoMateria` é o mesmo
`proposicao_id_externo` das votações.
"""

import argparse
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import FonteIngestao
from ingestion import comum
from ingestion import pauta_comum as pc

CASA = "senado"
FONTE = "senado_pauta"
URL = "https://legis.senado.leg.br/dadosabertos/plenario/agenda/mes/{data}"
URL_PAGINA = "https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigo}"


def _lista(valor: Any) -> list[dict[str, Any]]:
    """O Senado devolve objeto quando há um item só."""
    if not valor:
        return []
    return valor if isinstance(valor, list) else [valor]


def _datas_de_consulta(hoje: date) -> list[date]:
    inicio, fim = pc.janela(hoje)
    datas = [inicio]
    if (fim.year, fim.month) != (inicio.year, inicio.month):
        datas.append(fim.replace(day=1))
    return datas


def baixar(client: httpx.Client, hoje: date) -> dict[str, Any]:
    meses = []
    for data in _datas_de_consulta(hoje):
        pc.pausa()
        meses.append(
            {
                "consulta": data.isoformat(),
                "agenda": comum.get_json(client, URL.format(data=f"{data:%Y%m%d}")),
            }
        )
    return {"hoje": hoje.isoformat(), "meses": meses}


def normalizar(payload: dict[str, Any]) -> list[dict[str, Any]]:
    inicio, fim = pc.janela(date.fromisoformat(payload["hoje"]))
    itens: dict[tuple[str, str], dict[str, Any]] = {}
    for mes in payload["meses"]:
        sessoes = _lista(
            ((mes["agenda"].get("AgendaPlenario") or {}).get("Sessoes") or {}).get("Sessao")
        )
        for sessao in sessoes:
            dia = date.fromisoformat(sessao["Data"][:10])
            situacao = (sessao.get("SituacaoSessao") or "").strip()
            if not inicio <= dia <= fim or situacao.startswith("Cancelad"):
                continue
            codigo_sessao = str(sessao["CodigoSessao"])
            materias = _lista((sessao.get("Materias") or {}).get("Materia"))
            for posicao, materia in enumerate(materias, start=1):
                codigo = str(materia["CodigoMateria"])
                if (codigo_sessao, codigo) in itens:
                    continue
                sequencia = str(materia.get("SequenciaOrdem") or "")
                itens[(codigo_sessao, codigo)] = {
                    "data": dia,
                    "sessao": codigo_sessao,
                    "ordem": int(sequencia) if sequencia.isdigit() else posicao,
                    "proposicao": pc.limpar_texto(materia.get("DescricaoIdentificacaoMateria"))
                    or None,
                    "proposicao_id_externo": codigo,
                    "ementa": pc.limpar_texto(materia.get("Ementa")) or None,
                    "url": URL_PAGINA.format(codigo=codigo),
                }
    return sorted(itens.values(), key=lambda i: (i["data"], i["sessao"], i["ordem"]))


def carregar(session: Session, payload: dict[str, Any], ingestao: FonteIngestao) -> int:
    return pc.substituir_pauta(session, CASA, normalizar(payload), ingestao)


def executar(de_raw: Path | None = None, hoje: date | None = None) -> int:
    hoje = hoje or date.today()
    return comum.executar_ingestao(
        FONTE, URL.format(data=f"{hoje:%Y%m%d}"), lambda client: baixar(client, hoje), carregar,
        de_raw=de_raw,
    )  # fmt: skip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} itens")
