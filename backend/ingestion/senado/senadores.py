"""Senadores em exercício (API de Dados Abertos do Senado)."""

from typing import Any

import httpx

from ingestion import comum

FONTE = "senado_senadores"
CASA = "senado"
URL = "https://legis.senado.leg.br/dadosabertos/senador/lista/atual"


def _como_lista(valor: Any) -> list:
    """O Senado devolve objeto em vez de lista quando há um só item."""
    if valor is None:
        return []
    return valor if isinstance(valor, list) else [valor]


def _https(url: str | None) -> str | None:
    return url.replace("http://", "https://", 1) if url else url


def _formatar_telefone(numero: str) -> str:
    # O Senado publica só os 8 dígitos; todos os gabinetes ficam em Brasília (61).
    if len(numero) == 8 and numero.isdigit():
        return f"(61) {numero[:4]}-{numero[4:]}"
    return numero


def baixar(client: httpx.Client) -> dict[str, Any]:
    return comum.get_json(client, URL)


def normalizar(payload: dict[str, Any]) -> list[dict[str, Any]]:
    parlamentares = _como_lista(
        payload["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]
    )
    registros = []
    for p in parlamentares:
        ident = p["IdentificacaoParlamentar"]
        telefones = _como_lista((ident.get("Telefones") or {}).get("Telefone"))
        telefones = sorted(telefones, key=lambda t: int(t.get("OrdemPublicacao", 0)))
        codigo = ident["CodigoParlamentar"]
        registros.append(
            {
                "id_externo": codigo,
                "nome_parlamentar": ident["NomeParlamentar"],
                "nome_civil": ident.get("NomeCompletoParlamentar"),
                "partido": ident.get("SiglaPartidoParlamentar"),
                # Suplentes em exercício trazem a UF só no mandato.
                "uf": ident.get("UfParlamentar") or p["Mandato"]["UfParlamentar"],
                "foto_url": _https(ident.get("UrlFotoParlamentar")),
                "email": ident.get("EmailParlamentar"),
                "telefone": _formatar_telefone(telefones[0]["NumeroTelefone"])
                if telefones
                else None,
                "pagina_url": _https(ident.get("UrlPaginaParlamentar")),
                "fonte_url": f"https://legis.senado.leg.br/dadosabertos/senador/{codigo}",
            }
        )
    return registros


def executar(de_raw=None) -> int:
    return comum.executar(FONTE, CASA, URL, baixar, normalizar, de_raw=de_raw)


if __name__ == "__main__":
    comum.main(FONTE, CASA, URL, baixar, normalizar)
