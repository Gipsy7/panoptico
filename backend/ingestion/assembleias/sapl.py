"""Assembleias legislativas que usam o SAPL (Interlegis): deputados estaduais no cargo hoje
e os projetos de cada um.

É o mesmo conector das câmaras municipais (`ingestion.camaras.sapl`), porque a API do SAPL
é a mesma. A lista das assembleias com SAPL saiu de um levantamento das 27 casas (ver
docs/FONTES_DE_DADOS.md); as demais publicam em sistemas próprios e ganham conectores
próprios, uma a uma.
"""

import argparse
from datetime import UTC, date, datetime

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion.camaras import sapl

FONTE = "sapl_assembleias"
ASSEMBLEIAS = {
    "AC": "https://sapl.al.ac.leg.br/",
    "AL": "https://sapl.al.al.leg.br/",
    "AM": "https://sapl.al.am.leg.br/",
    "MT": "https://sapl.al.mt.leg.br/",
    "PB": "https://sapl.al.pb.leg.br/",
    "PI": "https://sapl.al.pi.leg.br/",
    "RO": "https://sapl.al.ro.leg.br/",
    "RR": "https://sapl.al.rr.leg.br/",
    "TO": "https://sapl.al.to.leg.br/",
}


def executar(ufs: list[str] | None = None) -> int:
    hoje = date.today()
    total, falhas = 0, 0
    for uf, base in ASSEMBLEIAS.items():
        if ufs and uf not in ufs:
            continue
        try:
            casa = sapl.coletar(base, hoje)
            if not casa:
                continue
            with SessionLocal() as session:
                quantos = sapl.gravar(session, None, casa, uf=uf)
                session.commit()
            print(f"  {uf}: {quantos} deputados", flush=True)
            total += quantos
        except Exception as erro:  # uma assembleia fora do ar não derruba as outras
            print(f"  {uf} ({base}): {erro.__class__.__name__}: {str(erro)[:120]}", flush=True)
            falhas += 1
    with SessionLocal() as session:
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url="SAPL das assembleias legislativas",
                arquivo_raw="(não guardado)",
                registros=total,
                status="ok",
                concluido_em=datetime.now(UTC),
            )
        )
        session.commit()
    print(f"{falhas} assembleias com falha, {total} deputados")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--uf", nargs="*", help="Só estas assembleias")
    args = parser.parse_args()
    executar([u.upper() for u in args.uf] if args.uf else None)
