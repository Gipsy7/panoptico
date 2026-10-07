"""Resolve CEP em UF e município via ViaCEP."""

import re
import time
from dataclasses import dataclass

import httpx

from app.config import settings

CACHE_TTL_SEGUNDOS = 24 * 60 * 60
_cache: dict[str, tuple[float, "Localizacao"]] = {}


class CepInvalido(ValueError):
    pass


class CepNaoEncontrado(LookupError):
    pass


class CepIndisponivel(RuntimeError):
    """O serviço de CEP não respondeu ou respondeu com erro."""


@dataclass(frozen=True)
class Localizacao:
    cep: str
    uf: str
    municipio: str
    codigo_ibge: str


def normalizar_cep(cep: str) -> str:
    digitos = re.sub(r"\D", "", cep or "")
    if len(digitos) != 8:
        raise CepInvalido("O CEP precisa ter 8 dígitos.")
    return digitos


def limpar_cache() -> None:
    _cache.clear()


def buscar_cep(cep: str, client: httpx.Client | None = None) -> Localizacao:
    cep = normalizar_cep(cep)

    em_cache = _cache.get(cep)
    if em_cache and time.monotonic() - em_cache[0] < CACHE_TTL_SEGUNDOS:
        return em_cache[1]

    url = settings.viacep_url.format(cep=cep)
    try:
        if client is None:
            with httpx.Client(timeout=5.0) as c:
                resposta = c.get(url)
        else:
            resposta = client.get(url)
    except httpx.HTTPError as e:
        raise CepIndisponivel("Não foi possível consultar o CEP agora.") from e

    if resposta.status_code == 400:
        raise CepInvalido("CEP inválido.")
    if resposta.status_code != 200:
        raise CepIndisponivel(f"ViaCEP respondeu {resposta.status_code}.")

    dados = resposta.json()
    if str(dados.get("erro", "")).lower() == "true":
        raise CepNaoEncontrado("CEP não encontrado.")

    localizacao = Localizacao(
        cep=cep,
        uf=dados["uf"],
        municipio=dados["localidade"],
        codigo_ibge=dados.get("ibge", ""),
    )
    _cache[cep] = (time.monotonic(), localizacao)
    return localizacao
