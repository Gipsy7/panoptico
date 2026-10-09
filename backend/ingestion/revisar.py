"""Revisão humana dos vínculos por nome aproximado (regra "nome_casa"): o parlamentar da
câmara ou assembleia ligado ao eleito do TSE por um nome parecido, mas não idêntico
("Dr. Valdomiro Lopes" e "Valdomiro Lopes"). Esses vínculos só são publicados depois de
aceitos aqui; a decisão vai para data/vinculos_revisados.csv (versionado) e é reaplicada
a cada carga de pessoas.

Uso:
    python -m ingestion.revisar                    # um por um: [a]ceitar, [r]ecusar, [p]ular
    python -m ingestion.revisar --exportar fila.csv  # para revisar numa planilha e depois
                                                     # colar as linhas decididas no CSV
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Candidatura, MandatoLocal, Municipio, PessoaVinculo
from ingestion.pessoas import COLUNAS_REVISAO, REVISOES, revisoes


def pendentes(session) -> list[dict]:
    """Vínculos "nome_casa" ainda não revisados, com os dois lados para comparar."""
    decididos = {(r["fonte"], r["id_externo"]) for r in revisoes()}
    candidaturas = {
        (c.ano_eleicao, c.sq_candidato): c
        for c in session.scalars(
            select(Candidatura).where(Candidatura.situacao_turno.like("ELEITO%"))
        )
    }
    resultado = []
    for v in session.scalars(
        select(PessoaVinculo).where(
            PessoaVinculo.regra == "nome_casa", PessoaVinculo.revisado.is_(False)
        )
    ):
        if (v.fonte, v.id_externo) in decididos:
            continue
        casa, uf, ibge, id_externo = v.id_externo.split(":", 3)
        mandato = session.scalar(
            select(MandatoLocal).where(
                MandatoLocal.casa == casa, MandatoLocal.uf == uf,
                MandatoLocal.id_externo == id_externo,
                (MandatoLocal.municipio_ibge == ibge) if ibge
                else MandatoLocal.municipio_ibge.is_(None),
            )
        )  # fmt: skip
        if mandato is None or mandato.candidatura_id is None:
            continue
        c = next((x for x in candidaturas.values() if x.id == mandato.candidatura_id), None)
        if c is None:
            continue
        cidade = (
            session.scalar(select(Municipio.nome).where(Municipio.ibge == ibge)) if ibge else None
        )
        resultado.append(
            {
                "fonte": v.fonte,
                "id_externo": v.id_externo,
                "ligado_a": f"candidatura:{c.ano_eleicao}:{c.sq_candidato}",
                "casa": f"{'Câmara de ' + cidade if cidade else 'Assembleia'} ({uf})",
                "na_casa": " / ".join(n for n in (mandato.nome, mandato.nome_completo) if n),
                "no_tse": (
                    f"{c.nome_urna} / {c.nome} "
                    f"({c.cargo.lower()}, {c.partido or 'sem partido'}, {c.ano_eleicao})"
                ),
                "partido_na_casa": mandato.partido or "",
                "fonte_casa": mandato.sapl_url,
            }
        )
    return resultado


def gravar_decisao(item: dict, decisao: str, revisor: str, observacao: str = "") -> None:
    novo = not REVISOES.exists()
    with REVISOES.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_REVISAO)
        if novo:
            escritor.writeheader()
        escritor.writerow(
            {"fonte": item["fonte"], "id_externo": item["id_externo"], "ligado_a": item["ligado_a"],
             "decisao": decisao, "revisado_por": revisor, "revisado_em": date.today().isoformat(),
             "observacao": observacao}
        )  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Revisão de vínculos por nome aproximado")
    parser.add_argument("--exportar", type=Path, help="Grava a fila num CSV, sem perguntar")
    parser.add_argument("--revisor", default="", help="Quem está revisando (vai no CSV)")
    args = parser.parse_args(argv)
    with SessionLocal() as session:
        fila = pendentes(session)
    print(f"{len(fila)} vínculos por nome aproximado esperando revisão", file=sys.stderr)
    if args.exportar:
        with args.exportar.open("w", encoding="utf-8", newline="") as arquivo:
            escritor = csv.DictWriter(
                arquivo, fieldnames=[*fila[0].keys(), "decisao"] if fila else ["decisao"]
            )
            escritor.writeheader()
            escritor.writerows(fila)
        print(f"Fila em {args.exportar}. Preencha 'decisao' (aceito/recusado) e copie as linhas "
              f"decididas para {REVISOES}.", file=sys.stderr)  # fmt: skip
        return 0
    revisor = args.revisor or input("Seu nome (vai no CSV): ").strip()
    for i, item in enumerate(fila, start=1):
        print(f"\n[{i}/{len(fila)}] {item['casa']}")
        print(f"  na casa: {item['na_casa']}  {item['partido_na_casa']}")
        print(f"  no TSE:  {item['no_tse']}")
        print(f"  fonte:   {item['fonte_casa']}")
        resposta = (
            input("  É a mesma pessoa? [a]ceitar, [r]ecusar, [p]ular, [s]air: ").strip().lower()
        )
        if resposta == "s":
            break
        if resposta in ("a", "r"):
            gravar_decisao(item, "aceito" if resposta == "a" else "recusado", revisor)
    print(
        f"\nDecisões em {REVISOES}. Valem na próxima carga de pessoas "
        "(python -m ingestion.pessoas)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
