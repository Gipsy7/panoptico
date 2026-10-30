"""Leitura dos registros do Argos para análise, só pela linha de comando.

    python -m app.argos_relatorio                  # resumo no terminal
    python -m app.argos_relatorio --exportar saida # grava CSVs em saida/
    python -m app.argos_relatorio --apagar-antigos # apaga o que passou de 180 dias

Nenhuma rota da API lê esses dados e eles não entram na exportação aberta.
"""

import argparse
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.argos import ArgosAvaliacao, ArgosConversa, ArgosFraseNaoEntendida
from app.services import argos as servico


def frases_mais_frequentes(session: Session, limite: int = 50) -> list[tuple[str, int, date]]:
    q = (
        select(
            ArgosFraseNaoEntendida.texto,
            func.count().label("vezes"),
            func.max(ArgosFraseNaoEntendida.dia),
        )
        .group_by(ArgosFraseNaoEntendida.texto)
        .order_by(func.count().desc(), ArgosFraseNaoEntendida.texto)
        .limit(limite)
    )
    return [(t, n, d) for t, n, d in session.execute(q)]


def util_por_assunto(session: Session) -> list[tuple[str, int, int]]:
    """(assunto, total, quantos acharam útil)."""
    q = (
        select(
            ArgosAvaliacao.assunto,
            func.count(),
            func.sum(case((ArgosAvaliacao.util.is_(True), 1), else_=0)),
        )
        .group_by(ArgosAvaliacao.assunto)
        .order_by(func.count().desc())
    )
    return [(a, n, int(u or 0)) for a, n, u in session.execute(q)]


def conversas(session: Session) -> list[ArgosConversa]:
    return list(session.scalars(select(ArgosConversa).order_by(ArgosConversa.dia.desc())))


def exportar(session: Session, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    with (destino / "argos_frases.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["texto", "vezes", "ultimo_dia"])
        w.writerows(frases_mais_frequentes(session, 100000))
    with (destino / "argos_avaliacoes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["assunto", "total", "uteis"])
        w.writerows(util_por_assunto(session))
    with (destino / "argos_conversas.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dia", "autor", "texto"])
        for c in conversas(session):
            for m in c.mensagens:
                w.writerow([c.dia, m["autor"], m["texto"]])


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--exportar", type=Path, metavar="PASTA", help="grava CSVs na pasta")
    ap.add_argument("--apagar-antigos", action="store_true", help="apaga o que passou de 180 dias")
    args = ap.parse_args(argv)
    with SessionLocal() as session:
        if args.apagar_antigos:
            n = servico.apagar_antigos(session)
            session.commit()
            print(f"Apagados {n} registros com mais de {servico.DIAS_DE_GUARDA} dias.")
            return
        if args.exportar:
            exportar(session, args.exportar)
            print(f"CSVs em {args.exportar}")
            return
        print("Frases não entendidas mais frequentes")
        for texto, vezes, dia in frases_mais_frequentes(session, 30):
            print(f"  {vezes:>4}x  {texto}  (último: {dia})")
        print("\nUtilidade por assunto (úteis/total)")
        for assunto, total, uteis in util_por_assunto(session):
            print(f"  {assunto:<18} {uteis}/{total}  ({100 * uteis // total}%)")
        guardadas = conversas(session)
        print(f"\nConversas guardadas: {len(guardadas)}")
        for c in guardadas:
            print(f"\n--- {c.dia} ---")
            for m in c.mensagens:
                print(f"  [{m['autor']}] {m['texto']}")


if __name__ == "__main__":
    main()
