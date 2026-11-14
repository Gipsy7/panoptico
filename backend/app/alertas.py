"""Alertas de operação por e-mail ao dono, só pela linha de comando.

    python -m app.alertas            # verifica e envia o que for novo na janela
    python -m app.alertas --simular  # mostra o que seria enviado, sem enviar nem gravar
    python -m app.alertas --teste    # envia uma mensagem de teste (confere o SMTP)

Regras e limites em app/services/alertas.py. A saída tem só contagens e assuntos.
"""

import argparse
import logging
import sys
from datetime import UTC, datetime

from app.db import SessionLocal
from app.services import alertas as servico

logger = logging.getLogger("panoptico.alertas")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--simular", action="store_true")
    modo.add_argument("--teste", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    agora = datetime.now(UTC)

    if args.teste:
        if not servico.configurado():
            logger.error("alertas: e-mail não configurado (ver deploy/vps/LEIAME.md)")
            return 1
        servico.enviar_email(
            servico.Alerta(
                "teste",
                agora.isoformat()[:13],
                "Panóptico: teste dos alertas",
                ("Se você recebeu esta mensagem, o envio dos alertas está funcionando.",),
            )
        )
        logger.info("alertas: mensagem de teste enviada")
        return 0

    with SessionLocal() as session:
        if args.simular:
            for alerta in servico.verificar(session, agora):
                repetido = (
                    " (já enviado nesta janela)" if servico.ja_enviado(session, alerta) else ""
                )
                logger.info("%s%s\n%s\n", alerta.assunto, repetido, alerta.texto)
            return 0
        totais = servico.rodar(session, agora)
    logger.info(
        "alertas: %(achados)s achado(s), %(novos)s novo(s), %(enviados)s enviado(s)", totais
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
