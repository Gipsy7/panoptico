"""Leis ordinárias, leis complementares e emendas constitucionais desde 1985, e o projeto que
virou cada uma.

Duas listas abertas do Senado Federal (JSON, sem token), uma por tipo e ano:
- `/dadosabertos/legislacao/lista?tipo=LEI|LCP|EMC&ano=AAAA`: as normas (código, número, data
  da assinatura, ementa). O tipo volta como "LEI-n" e "EMC-n" (numeradas); a EMC tem números
  repetidos entre a Constituição de 1967 (EC 25 a 27 de 1985) e a de 1988, então a chave é
  tipo + número + ano;
- `/dadosabertos/processo?tipoNorma=LEI|LCP|EMC&anoNorma=AAAA`: os processos do Senado e do
  Congresso com `normaGerada` ("Lei nº 15.240 de 28/10/2025"). Daqui sai o projeto de origem:
  o `codigoMateria` (o mesmo id de `proposicao` do Senado) e a identificação ("PLS 559/2013").
  Vetos, mensagens, substitutivos e emendas da Câmara (VET, MSG, MSF, SCD, ECD) não são o projeto
  de origem e ficam de fora.

Ligação com a Câmara (o Senado não traz o id da Câmara):
- "numero": desde 2019 PL e PLP têm numeração única nas duas Casas; o processo do Senado
  "PL 1087/2025" é o PL 1087/2025 da Câmara. PEC só quando o Senado foi a Casa revisora (o número
  é o da Câmara). Só liga se a proposição estiver na tabela `proposicao`;
- "camara": o despacho da Câmara "Transformado na Lei Ordinária 15123/2025. DOU 25/04/2025"
  na tabela `tramitacao` (já carregada por camara_tramitacoes). Dele sai também a data do
  Diário Oficial (`data_publicacao`).

O texto oficial é o endereço de normas.leg.br pela URN do LexML, o mesmo que o Senado devolve no
detalhe da norma (`urlDocumento`), montado sem pedir o detalhe de cada uma.

Carga diária: ano atual e anterior (6 + 6 pedidos). Carga inicial: `--desde 1985`
(~250 pedidos, ~8.600 normas). Upsert das normas; as ligações dos anos baixados são refeitas.
"""

import argparse
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Norma, NormaProposicao, Proposicao, Tramitacao
from ingestion import comum

FONTE = "congresso_normas"
URL = "https://legis.senado.leg.br/dadosabertos/legislacao/lista"
URL_PROCESSOS = "https://legis.senado.leg.br/dadosabertos/processo"
URL_TEXTO = "https://normas.leg.br/?urn=urn:lex:br:federal:{urn}:{data};{numero}"
TIPOS = ("LEI", "LCP", "EMC")
URN = {"LEI": "lei", "LCP": "lei.complementar", "EMC": "emenda.constitucional"}
NOMES = {"Lei": "LEI", "Lei Complementar": "LCP", "Emenda Constitucional": "EMC"}
PRIMEIRO_ANO = 1985
NUMERACAO_UNICA = 2019  # PL e PLP com o mesmo número nas duas Casas
FORA_DA_ORIGEM = {"VET", "MSG", "MSF", "SCD", "ECD"}
PAUSA = 0.2
LOTE = 3000

_NORMA_GERADA = re.compile(
    r"^(Lei Complementar|Emenda Constitucional|Lei)\s+n\S*\s*([\d.]+)\s+de\s+"
    r"(\d{2})/(\d{2})/(\d{4})"
)
_IDENT = re.compile(r"^([A-Z]+)\s+0*(\d+)/(\d{4})")
_TRANSFORMADO = re.compile(
    r"Transformad[oa]\s+n[ao]\s+(Lei Ordin[áa]ria|Lei Complementar|Emenda Constitucional|Lei)"
    r"\s+(?:n\S*\s*)?([\d.]+)/(\d{4})",
    re.IGNORECASE,
)
_DOU = re.compile(r"DOU\s+(\d{1,2})[/ ](\d{1,2})[/ ](\d{4})")
_TIPO_CAMARA = {
    "lei ordinária": "LEI",
    "lei ordinaria": "LEI",
    "lei": "LEI",
    "lei complementar": "LCP",
    "emenda constitucional": "EMC",
}


def _data_br(valor: str | None) -> date | None:
    try:
        return datetime.strptime((valor or "").strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def url_texto(tipo: str, data: date, numero: int) -> str:
    return URL_TEXTO.format(urn=URN[tipo], data=data.isoformat(), numero=numero)


def _documentos(resposta: Any) -> list[dict]:
    """A lista do Senado: `documentos` some quando o ano não tem norma e `documento` vira
    objeto quando há uma só."""
    docs = ((resposta or {}).get("ListaDocumento") or {}).get("documentos") or {}
    docs = docs.get("documento") or [] if isinstance(docs, dict) else []
    return [docs] if isinstance(docs, dict) else list(docs)


def normalizar_normas(payload: dict) -> list[dict[str, Any]]:
    """Normas do bruto -> linhas de `norma` (sem repetidas)."""
    linhas: dict[tuple, dict[str, Any]] = {}
    for tipo, por_ano in payload.get("normas", {}).items():
        if tipo not in TIPOS:
            continue
        for docs in por_ano.values():
            for d in _documentos(docs):
                data = _data_br(d.get("dataassinatura"))
                numero = str(d.get("numero") or "").replace(".", "").strip()
                if data is None or not numero.isdigit() or not d.get("id"):
                    continue
                chave = (tipo, int(numero), data.year)
                linhas[chave] = {
                    "id_externo": str(d["id"]),
                    "tipo": tipo,
                    "numero": int(numero),
                    "ano": data.year,
                    "data": data,
                    "ementa": (d.get("ementa") or "").strip(),
                    "url": url_texto(tipo, data, int(numero)),
                }
    return list(linhas.values())


def norma_gerada(texto: str | None) -> tuple[str, int, date] | None:
    """ "Lei Complementar nº 214 de 16/01/2025" -> ("LCP", 214, date(2025, 1, 16))."""
    achou = _NORMA_GERADA.match((texto or "").strip())
    if not achou:
        return None
    nome, numero, dia, mes, ano = achou.groups()
    try:
        return NOMES[nome], int(numero.replace(".", "")), date(int(ano), int(mes), int(dia))
    except ValueError:
        return None


def identificacao(texto: str | None) -> tuple[str, int, int] | None:
    """ "PL 4253/2020 (Substitutivo-CD)" -> ("PL", 4253, 2020)."""
    achou = _IDENT.match((texto or "").strip())
    return (achou[1], int(achou[2]), int(achou[3])) if achou else None


def normalizar_processos(payload: dict) -> list[dict[str, Any]]:
    """Processos do Senado com norma gerada -> (norma, codigoMateria, identificação, sigla...)."""
    saida: dict[tuple, dict[str, Any]] = {}
    for p in payload.get("processos", []):
        norma = norma_gerada(p.get("normaGerada"))
        ident = (p.get("identificacao") or "").strip()
        partes = identificacao(ident)
        codigo = str(p.get("codigoMateria") or "")
        if norma is None or partes is None or not codigo or partes[0] in FORA_DA_ORIGEM:
            continue
        saida[(norma, codigo)] = {
            "norma": norma,
            "codigo": codigo,
            "identificacao": ident[:60],
            "sigla": partes[0],
            "numero": partes[1],
            "ano": partes[2],
            "revisora": p.get("objetivo") == "Revisora",
        }
    return list(saida.values())


def transformado_em(despacho: str | None) -> tuple[str, int, int, date | None] | None:
    """Despacho da Câmara "Transformado na Lei Ordinária 15123/2025. DOU 25/04/2025 PÁG 03"
    -> ("LEI", 15123, 2025, date(2025, 4, 25)). Decreto legislativo e resolução: None."""
    achou = _TRANSFORMADO.search(despacho or "")
    if not achou:
        return None
    tipo = _TIPO_CAMARA[achou[1].lower()]
    dou = _DOU.search(despacho or "", achou.end())
    publicada = None
    if dou:
        try:
            publicada = date(int(dou[3]), int(dou[2]), int(dou[1]))
        except ValueError:
            publicada = None
    return tipo, int(achou[2].replace(".", "")), int(achou[3]), publicada


def anos_da_carga(desde: int | None = None, hoje: date | None = None) -> list[int]:
    hoje = hoje or date.today()
    inicio = max(PRIMEIRO_ANO, desde if desde else hoje.year - 1)
    return list(range(inicio, hoje.year + 1))


def baixar(client: httpx.Client, anos: list[int]) -> dict[str, Any]:
    normas: dict[str, dict[str, Any]] = {t: {} for t in TIPOS}
    processos: list[dict] = []
    for ano in anos:
        for tipo in TIPOS:
            normas[tipo][str(ano)] = comum.get_json(client, URL, params={"tipo": tipo, "ano": ano})
            time.sleep(PAUSA)
            lista = comum.get_json(
                client, URL_PROCESSOS, params={"tipoNorma": tipo, "anoNorma": ano}
            )
            processos.extend(lista if isinstance(lista, list) else [])
            time.sleep(PAUSA)
    return {"anos": anos, "normas": normas, "processos": processos}


def _upsert_normas(session: Session, linhas: list[dict], ingestao_id: int) -> None:
    for i in range(0, len(linhas), LOTE):
        lote = [{**r, "ingestao_id": ingestao_id} for r in linhas[i : i + LOTE]]
        stmt = insert(Norma).values(lote)
        session.execute(
            stmt.on_conflict_do_update(
                constraint="uq_norma_tipo_numero_ano",
                set_={
                    c: stmt.excluded[c]
                    for c in ("id_externo", "data", "ementa", "url", "ingestao_id")
                },
            )
        )


def ligacoes_do_senado(
    processos: list[dict], ids_norma: dict[tuple, int], camara: dict[tuple, str]
) -> list[dict[str, Any]]:
    """Ligações "senado" (codigoMateria) e "numero" (mesmo número na Câmara)."""
    linhas: dict[tuple, dict[str, Any]] = {}
    for p in processos:
        tipo, numero, data = p["norma"]
        norma_id = ids_norma.get((tipo, numero, data.year))
        if norma_id is None:
            continue
        linhas[(norma_id, "senado", p["codigo"])] = {
            "norma_id": norma_id,
            "casa": "senado",
            "proposicao_id_externo": p["codigo"],
            "identificacao": p["identificacao"],
            "origem": "senado",
        }
        mesmo_numero = (p["sigla"] in ("PL", "PLP") and p["ano"] >= NUMERACAO_UNICA) or (
            p["sigla"] == "PEC" and p["revisora"]
        )
        id_camara = camara.get((p["sigla"], p["numero"], p["ano"])) if mesmo_numero else None
        if id_camara:
            linhas.setdefault(
                (norma_id, "camara", id_camara),
                {
                    "norma_id": norma_id,
                    "casa": "camara",
                    "proposicao_id_externo": id_camara,
                    "identificacao": f"{p['sigla']} {p['numero']}/{p['ano']}",
                    "origem": "numero",
                },
            )
    return list(linhas.values())


def ligacoes_da_camara(
    session: Session, ids_norma: dict[tuple, int]
) -> tuple[list[dict[str, Any]], dict[int, date]]:
    """Ligações "camara" pelo despacho "Transformado na Lei..." e a data do Diário Oficial."""
    rotulos = {
        i: f"{s} {n}/{a}"
        for i, s, n, a in session.execute(
            select(Proposicao.id_externo, Proposicao.sigla_tipo, Proposicao.numero, Proposicao.ano)
            .where(Proposicao.casa == "camara")
        )
    }  # fmt: skip
    linhas: dict[tuple, dict[str, Any]] = {}
    publicacao: dict[int, date] = {}
    consulta = select(Tramitacao.proposicao_id_externo, Tramitacao.descricao).where(
        Tramitacao.casa == "camara", Tramitacao.descricao.ilike("%Transformad%")
    )
    for pid, despacho in session.execute(consulta):
        achou = transformado_em(despacho)
        if achou is None:
            continue
        tipo, numero, ano, publicada = achou
        norma_id = ids_norma.get((tipo, numero, ano))
        if norma_id is None:
            continue
        linhas[(norma_id, "camara", pid)] = {
            "norma_id": norma_id,
            "casa": "camara",
            "proposicao_id_externo": pid,
            "identificacao": rotulos.get(pid),
            "origem": "camara",
        }
        if publicada:
            publicacao.setdefault(norma_id, publicada)
    return list(linhas.values()), publicacao


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    normas = normalizar_normas(payload)
    if not normas:
        raise RuntimeError("Senado sem normas nos anos pedidos: nada alterado.")
    anos = sorted({int(a) for a in payload.get("anos", [])} | {r["ano"] for r in normas})
    total = sum(
        len(_documentos(d)) for por_ano in payload.get("normas", {}).values()
        for d in por_ano.values()
    )  # fmt: skip
    comum.conferir_carga(
        ingestao, normas, total_fonte=total, unica=["tipo", "numero", "ano"],
        nao_nulos=["ementa", "data"],
    )  # fmt: skip
    _upsert_normas(session, normas, ingestao.id)

    ids_norma = {
        (t, n, a): i for i, t, n, a in session.execute(
            select(Norma.id, Norma.tipo, Norma.numero, Norma.ano)
        )
    }  # fmt: skip
    camara = {
        (s, n, a): i
        for i, s, n, a in session.execute(
            select(Proposicao.id_externo, Proposicao.sigla_tipo, Proposicao.numero, Proposicao.ano)
            .where(Proposicao.casa == "camara")
        )
    }  # fmt: skip
    do_senado = ligacoes_do_senado(normalizar_processos(payload), ids_norma, camara)
    da_camara, publicacao = ligacoes_da_camara(session, ids_norma)

    # Refaz as ligações vindas do Senado nos anos baixados e todas as do despacho da Câmara.
    normas_dos_anos = select(Norma.id).where(Norma.ano.in_(anos))
    session.execute(
        delete(NormaProposicao).where(
            NormaProposicao.origem.in_(("senado", "numero")),
            NormaProposicao.norma_id.in_(normas_dos_anos),
        )
    )
    session.execute(delete(NormaProposicao).where(NormaProposicao.origem == "camara"))
    np = NormaProposicao
    existentes = set(session.execute(select(np.norma_id, np.casa, np.proposicao_id_externo)).all())
    novas: dict[tuple, dict[str, Any]] = {}
    for r in do_senado + da_camara:  # a ligação do Senado vem antes: fica com ela se repetir
        chave = (r["norma_id"], r["casa"], r["proposicao_id_externo"])
        if chave not in existentes:
            novas.setdefault(chave, {**r, "ingestao_id": ingestao.id})
    lista = list(novas.values())
    for i in range(0, len(lista), LOTE):
        session.execute(insert(NormaProposicao).values(lista[i : i + LOTE]))

    for norma_id, publicada in publicacao.items():
        session.execute(
            Norma.__table__.update()
            .where(Norma.id == norma_id)
            .values(data_publicacao=publicada)
        )  # fmt: skip

    por_tipo = {t: sum(1 for r in normas if r["tipo"] == t) for t in TIPOS}
    ligadas = len({r["norma_id"] for r in lista})
    print(
        f"  {por_tipo['LEI']} leis, {por_tipo['LCP']} leis complementares e {por_tipo['EMC']}"
        f" emendas constitucionais de {anos[0]} a {anos[-1]}; {len(lista)} ligações a projetos"
        f" ({ligadas} normas); {len(publicacao)} com data do Diário Oficial pela Câmara"
    )
    return len(normas)


def executar(de_raw: Path | None = None, desde: int | None = None) -> int:
    anos = anos_da_carga(desde)
    return comum.executar_ingestao(
        FONTE,
        URL,
        lambda client: baixar(client, anos),
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{anos[0]}-{anos[-1]}_",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um JSON bruto sem baixar")
    parser.add_argument(
        "--desde",
        type=int,
        help=f"Primeiro ano (carga inicial: {PRIMEIRO_ANO}); padrão: o anterior",
    )
    args = parser.parse_args()
    print(f"{FONTE}: {executar(args.de_raw, args.desde)} normas")
