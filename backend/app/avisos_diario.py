"""Resumo diário dos avisos por Web Push, só pela linha de comando.

    python -m app.avisos_diario            # detecta, envia e avança o cursor
    python -m app.avisos_diario --semear   # obrigatório na 1ª vez: grava o que existe, sem enviar
    python -m app.avisos_diario --simular  # conta quem receberia, sem enviar nem gravar

Sai sem fazer nada com avisos desligados. A saída tem só contagens, nunca endpoint.
"""

import argparse
import logging
import sys
import zlib

from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal, engine
from app.services import avisos as servico

logger = logging.getLogger("panoptico.avisos")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--semear", action="store_true")
    modo.add_argument("--simular", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not servico.ligado():
        logger.info("avisos desligados: nada a fazer")
        return 0

    # Duas rodadas ao mesmo tempo mandariam o mesmo resumo duas vezes. A trava fica numa conexão
    # própria porque a sessão devolve a dela ao pool a cada commit.
    chave = zlib.crc32(f"avisos:{settings.ambiente}".encode())
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as trava:
        if not trava.scalar(select(func.pg_try_advisory_lock(chave))):
            logger.info("avisos: outra rodada em andamento")
            return 0
        try:
            with SessionLocal() as session:
                if args.semear:
                    logger.info("avisos semeados: %s fatos", servico.semear(session))
                    return 0
                relatorio = servico.executar(session, simular=args.simular)
                if args.simular:
                    logger.info("simulação: %s", relatorio)
                return 0
        except servico.SemSemente:
            logger.error("ambiente sem semente: rode --semear uma vez antes de enviar")
            return 1
        finally:
            trava.scalar(select(func.pg_advisory_unlock(chave)))


if __name__ == "__main__":
    sys.exit(main())
