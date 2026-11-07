"""Limite de pedidos por origem, vivendo só na memória do processo: o IP não é gravado em lugar
nenhum. Cada instância conta à parte (com vários workers, cada um conta os seus)."""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


def origem(request: Request) -> str:
    """IP de quem pediu (atrás do Cloudflare vem no cabeçalho), só para contar na memória."""
    return (
        request.headers.get("cf-connecting-ip")
        or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        or (request.client.host if request.client else "?")
    )


class LimitePorOrigem:
    def __init__(
        self,
        por_minuto: int,
        janela: float = 60,
        mensagem: str = "Muitos pedidos. Tente de novo em instantes.",
    ) -> None:
        """Até `por_minuto` pedidos por origem a cada `janela` segundos (padrão: um minuto)."""
        self.por_minuto = por_minuto
        self.janela = janela
        self.mensagem = mensagem
        self.pedidos: dict[str, deque[float]] = defaultdict(deque)

    def __call__(self, request: Request) -> None:
        agora = time.monotonic()
        fila = self.pedidos[origem(request)]
        while fila and agora - fila[0] > self.janela:
            fila.popleft()
        if len(fila) >= self.por_minuto:
            raise HTTPException(429, self.mensagem)
        fila.append(agora)
        if len(self.pedidos) > 5000:  # não cresce sem limite
            for chave in [
                k for k, f in self.pedidos.items() if not f or agora - f[-1] > self.janela
            ]:
                del self.pedidos[chave]
