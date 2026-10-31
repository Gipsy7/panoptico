"""Gera as linhas do .env do painel privado de acessos.

Uso (o dono roda sozinho, no próprio computador):

    python -m app.painel_senha

Pede a senha sem mostrá-la, imprime PAINEL_SENHA_HASH e um PAINEL_SEGREDO novo. A senha em si
nunca é impressa nem gravada. Defina também PAINEL_USUARIO.
"""

import getpass
import secrets
import sys

from app.services.painel_auth import gerar_hash


def main() -> int:
    senha = getpass.getpass("Senha do painel (mínimo 12 caracteres): ")
    if len(senha) < 12:
        print("Senha curta demais: use 12 caracteres ou mais.", file=sys.stderr)
        return 1
    if getpass.getpass("Repita a senha: ") != senha:
        print("As senhas não conferem.", file=sys.stderr)
        return 1
    print("\nCopie estas linhas para o .env (e defina PAINEL_USUARIO):\n")
    print(f"PAINEL_SENHA_HASH={gerar_hash(senha)}")
    print(f"PAINEL_SEGREDO={secrets.token_urlsafe(48)}")
    print("METRICAS_ATIVAS=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
