"""Resultado do 2º turno de presidente e governador pela divulgação de resultados do TSE.

Os dados abertos (consulta_cand e votacao_candidato_munzona) só trazem o resultado dias
depois da eleição. Na noite da votação, o sistema de divulgação (resultados.tse.jus.br,
o mesmo do site e do app "Resultados" do TSE) publica um JSON por disputa:

  config:  /oficial/comum/config/ele-c.json (lista as eleições do ciclo e as UFs de cada uma)
  disputa: /oficial/ele<ano>/<cd_eleicao>/dados/<uf>/<uf>-c<cargo:04>-e<cd_eleicao:06>-u.json
           (br-c0001 presidente; <uf>-c0003 governador)

Só atualizamos candidaturas já guardadas (por sequencial do TSE, `sqcand`, igual ao
SQ_CANDIDATO dos dados abertos; sem ele, por número + cargo + UF): situação final, votos do
2º turno e data da eleição. Nunca criamos candidaturas. Só gravamos disputa TOTALIZADA (100%
das seções e andamento "f"); sem isso, nada é gravado.

Convivência com os dados abertos: quando consulta_cand/votação trouxerem o resultado, a carga
normal grava os mesmos valores por cima. Enquanto trouxerem a versão de antes da apuração
("2º TURNO", votos do 1º turno), essas cargas não desfazem este resultado (ver
`candidaturas.carregar_registros` e `votos.executar`).
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Candidatura, FonteIngestao
from ingestion import comum

FONTE = "tse_resultado_2_turno"
BASE = "https://resultados.tse.jus.br/oficial"
URL_CONFIG = f"{BASE}/comum/config/ele-c.json"
URL_DISPUTA = BASE + "/ele{ano}/{eleicao}/dados/{uf}/{uf}-c{cargo:04d}-e{eleicao:06d}-u.json"
# Página pública do TSE com o resultado (o que o cidadão confere).
URL_PAGINA = "https://resultados.tse.jus.br/"
# Cargo no site do TSE -> (titular, vice) como guardados em `candidatura`.
CARGOS = {
    "Presidente": ("PRESIDENTE", "VICE-PRESIDENTE"),
    "Governador": ("GOVERNADOR", "VICE-GOVERNADOR"),
}
VICE_DE = {titular: vice for titular, vice in CARGOS.values()}
SITUACAO = {"s": "ELEITO", "n": "NÃO ELEITO"}
FUSO = ZoneInfo("America/Sao_Paulo")


class NaoTotalizado(Exception):
    """Nenhuma disputa de 2º turno está totalizada ainda: nada a gravar."""


def disputas_do_ciclo(config: dict, ano: int) -> list[dict[str, Any]]:
    """Disputas de 2º turno de presidente e governador do ciclo: eleição, cargo e UF."""
    achadas = []
    for pleito in config.get("pl", []):
        if pleito.get("c") != f"ele{ano}":
            continue
        for eleicao in pleito.get("e", []):
            if str(eleicao.get("t")) != "2":
                continue
            for abrangencia in eleicao.get("abr", []):
                for cargo in abrangencia.get("cp", []):
                    if cargo.get("ds") in CARGOS:
                        achadas.append(
                            {
                                "eleicao": int(eleicao["cd"]),
                                "cargo_codigo": int(cargo["cd"]),
                                "cargo": CARGOS[cargo["ds"]][0],
                                "uf": abrangencia["cd"].lower(),
                            }
                        )
    return achadas


def _percentual(valor: Any) -> float:
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return 0.0


def totalizacao(dados: dict) -> datetime | None:
    """Momento da totalização informado pelo próprio JSON (dt e ht, horário de Brasília)."""
    try:
        return datetime.strptime(f"{dados['dt']} {dados['ht']}", "%d/%m/%Y %H:%M:%S").replace(
            tzinfo=FUSO
        )
    except (KeyError, ValueError):
        return None


def candidatos(dados: dict) -> list[dict]:
    return [
        cand
        for cargo in dados.get("carg", [])
        for agrupamento in cargo.get("agr", [])
        for partido in agrupamento.get("par", [])
        for cand in partido.get("cand", [])
    ]


def totalizada(dados: dict) -> bool:
    """100% das seções totalizadas, andamento finalizado e todos os candidatos com resultado
    (e = "s" eleito ou "n" não eleito; qualquer outro valor é apuração em curso)."""
    lista = candidatos(dados)
    return bool(
        lista
        and dados.get("and") == "f"
        and _percentual(dados.get("s", {}).get("pstn")) >= 100
        and all(c.get("e") in SITUACAO for c in lista)
        and any(c["e"] == "s" for c in lista)
        and totalizacao(dados) is not None
    )


def normalizar(payload: dict) -> tuple[list[dict[str, Any]], list[str]]:
    """(resultados das disputas totalizadas, avisos das que ficaram de fora).
    Um resultado por candidato e por vice (o vice herda a situação do titular, sem votos
    próprios: a chapa é votada pelo titular)."""
    resultados: list[dict[str, Any]] = []
    avisos: list[str] = []
    for chave, dados in payload["arquivos"].items():
        cargo, uf = chave.split(":")
        if not totalizada(dados):
            avisos.append(f"{cargo} {uf.upper()}: ainda não totalizado (não gravado)")
            continue
        momento = totalizacao(dados)
        data = datetime.strptime(dados["dt"], "%d/%m/%Y").date()
        base = {
            "uf": "BR" if cargo == "PRESIDENTE" else uf.upper(),
            "data_eleicao": data,
            "totalizado_em": momento,
        }
        for cand in candidatos(dados):
            situacao = SITUACAO[cand["e"]]
            resultados.append(
                {
                    **base,
                    "cargo": cargo,
                    "sq_candidato": cand["sqcand"],
                    "numero": cand.get("n"),
                    "situacao_turno": situacao,
                    "votos": int(cand["vap"]),
                    "titular": True,
                }
            )
            for v in cand.get("vs", []):
                if v.get("tp") == "v" and v.get("sqcand"):
                    resultados.append(
                        {
                            **base,
                            "cargo": VICE_DE[cargo],
                            "sq_candidato": v["sqcand"],
                            "numero": cand.get("n"),
                            "situacao_turno": situacao,
                            "votos": None,
                            "titular": False,
                        }
                    )
    return resultados, avisos


def aplicar(session: Session, resultados: list[dict[str, Any]], ano: int) -> tuple[int, list[str]]:
    """Atualiza as candidaturas já guardadas. Devolve (atualizadas, avisos do que não casou)."""
    avisos: list[str] = []
    atualizadas = 0
    guardadas = session.execute(
        select(
            Candidatura.id,
            Candidatura.sq_candidato,
            Candidatura.cargo,
            Candidatura.uf,
            Candidatura.numero,
        ).where(Candidatura.ano_eleicao == ano)
    ).all()
    por_sq = {g.sq_candidato: g.id for g in guardadas}
    por_numero: dict[tuple[str, str, str], list[int]] = {}
    for g in guardadas:
        por_numero.setdefault((g.cargo, g.uf, g.numero or ""), []).append(g.id)
    for r in resultados:
        id_ = por_sq.get(r["sq_candidato"])
        if id_ is None and r["titular"]:
            # Sem o sequencial: número + cargo + UF, só se houver uma única candidatura.
            achadas = por_numero.get((r["cargo"], r["uf"], r["numero"] or ""), [])
            id_ = achadas[0] if len(achadas) == 1 else None
        if id_ is None:
            if r["titular"]:
                avisos.append(f"{r['cargo']} {r['uf']} nº {r['numero']}: candidatura não guardada")
            continue
        valores = {"situacao_turno": r["situacao_turno"], "data_eleicao": r["data_eleicao"]}
        if r["votos"] is not None:
            valores["votos"] = r["votos"]
        session.execute(update(Candidatura).where(Candidatura.id == id_).values(**valores))
        atualizadas += 1
    return atualizadas, avisos


def executar(ano: int = 2026, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> dict:
        config = comum.get_json(client, URL_CONFIG)
        arquivos = {}
        for d in disputas_do_ciclo(config, ano):
            url = URL_DISPUTA.format(
                ano=ano, eleicao=d["eleicao"], uf=d["uf"], cargo=d["cargo_codigo"]
            )
            arquivos[f"{d['cargo']}:{d['uf']}"] = comum.get_json(client, url)
        if not arquivos:
            raise NaoTotalizado(f"O TSE não lista disputa de 2º turno de {ano}.")
        resultados, avisos = normalizar({"arquivos": arquivos})
        for aviso in avisos:
            print(f"{FONTE}: {aviso}")
        if not resultados:
            # Antes de qualquer registro: não suja fonte_ingestao com carga que não gravou.
            raise NaoTotalizado("Nenhuma disputa de 2º turno totalizada ainda; nada gravado.")
        return {"ano": ano, "arquivos": arquivos}

    def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
        resultados, avisos = normalizar(payload)
        if not resultados:
            raise NaoTotalizado("Nenhuma disputa de 2º turno totalizada; nada gravado.")
        atualizadas, sem_casar = aplicar(session, resultados, int(payload.get("ano", ano)))
        # A data da carga é a da totalização do próprio JSON (a mais recente das disputas
        # gravadas): é a que o site mostra como "atualizado em".
        ingestao.concluido_em = max(r["totalizado_em"] for r in resultados)
        ingestao.total_fonte = sum(1 for r in resultados if r["titular"])
        if avisos or sem_casar:
            ingestao.alertas = avisos + sem_casar
        return atualizadas

    return comum.executar_ingestao(
        FONTE, URL_CONFIG, baixar, carregar, de_raw=de_raw, prefixo_raw=f"{ano}_"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem rede")
    args = parser.parse_args()
    try:
        total = executar(args.ano, de_raw=args.de_raw)
    except NaoTotalizado as erro:
        print(f"{FONTE}: {erro}")
        raise SystemExit(3) from erro
    print(f"{FONTE} {args.ano}: {total} candidaturas atualizadas")
