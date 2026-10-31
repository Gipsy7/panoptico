"""Senha e token do painel privado de acessos. Só biblioteca padrão.

A senha vira "scrypt:N:r:p:sal:hash" (base64 sem "$", para o .env do compose não interpretar).
O token é "validade.assinatura": a validade em segundos desde 1970 e um HMAC-SHA256 dela com
PAINEL_SEGREDO. Não há sessão no servidor nem cookie; o navegador guarda o token na aba.
"""

import base64
import hashlib
import hmac
import os
import time

N, R, P = 2**14, 8, 1
VALIDADE_S = 12 * 3600


def _b64(dado: bytes) -> str:
    return base64.urlsafe_b64encode(dado).decode().rstrip("=")


def _desb64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _scrypt(senha: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(senha.encode(), salt=sal, n=n, r=r, p=p, dklen=32, maxmem=128 * n * r * 2)


def gerar_hash(senha: str) -> str:
    sal = os.urandom(16)
    return f"scrypt:{N}:{R}:{P}:{_b64(sal)}:{_b64(_scrypt(senha, sal, N, R, P))}"


def conferir_senha(senha: str, armazenado: str) -> bool:
    """Comparação em tempo constante. Hash mal formado nunca confere."""
    try:
        nome, n, r, p, sal, esperado = armazenado.split(":")
        if nome != "scrypt":
            return False
        calculado = _scrypt(senha, _desb64(sal), int(n), int(r), int(p))
        return hmac.compare_digest(calculado, _desb64(esperado))
    except (ValueError, TypeError):
        return False


def _assinar(segredo: str, validade: int) -> str:
    return _b64(hmac.new(segredo.encode(), str(validade).encode(), hashlib.sha256).digest())


def emitir_token(segredo: str, agora: float | None = None) -> str:
    validade = int((agora if agora is not None else time.time()) + VALIDADE_S)
    return f"{validade}.{_assinar(segredo, validade)}"


def token_valido(token: str, segredo: str, agora: float | None = None) -> bool:
    if not segredo:
        return False
    try:
        texto, assinatura = token.split(".", 1)
        validade = int(texto)
    except ValueError:
        return False
    if not hmac.compare_digest(_assinar(segredo, validade).encode(), assinatura.encode()):
        return False
    return validade > (agora if agora is not None else time.time())
