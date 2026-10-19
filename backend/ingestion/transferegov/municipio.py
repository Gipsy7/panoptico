"""CNPJ do beneficiário -> código IBGE do município, para planos e convênios das emendas.

Três fontes, na ordem:
1. entes do SICONFI (Tesouro): CNPJ e código IBGE de cada prefeitura e de cada estado;
   CNPJ de estado não vira município (o dinheiro é do estado, não de uma cidade);
2. o próprio arquivo de emendas por favorecido (CGU), já ligado ao município: cobre fundos
   municipais (saúde, assistência...) e entidades; CNPJ que aparece em mais de um
   município fica de fora;
3. conferência por nome: "MUNICIPIO DE GASPAR" + UF, pelo mesmo critério de nome do arquivo
   por favorecido (exato e, se não houver, aproximado dentro da UF).

CNPJ sem mapa fica sem município e é contado à parte.
"""

import re
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EmendaPagamento, Municipio
from ingestion import comum
from ingestion.transparencia.emendas import resolver_municipios

URL_ENTES = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes"
PREFIXOS_PREFEITURA = re.compile(
    r"^(MUNICIPIO DE |MUNICIPIO DO |MUNICIPIO DA |PREFEITURA MUNICIPAL DE |"
    r"PREFEITURA MUNICIPAL DO |PREFEITURA MUNICIPAL DA |PREFEITURA DE |MUNICIPIO )"
)


def baixar_entes(client: httpx.Client) -> list[dict[str, Any]]:
    """Os ~5.600 entes (municípios, estados, DF, União) numa chamada só."""
    payload = comum.get_json(client, URL_ENTES)
    return [
        {"cnpj": e.get("cnpj"), "ibge": str(e["cod_ibge"]), "uf": e.get("uf"),
         "esfera": e.get("esfera")}
        for e in payload.get("items", [])
    ]  # fmt: skip


def _cnpj(texto: str | None) -> str:
    return re.sub(r"\D", "", texto or "")


def favorecidos(session: Session) -> dict[str, str]:
    """CNPJ -> IBGE pelo arquivo por favorecido; CNPJ em mais de um município fica de fora."""
    linhas = session.execute(
        select(EmendaPagamento.favorecido_codigo, func.min(EmendaPagamento.municipio_ibge))
        .group_by(EmendaPagamento.favorecido_codigo)
        .having(func.count(func.distinct(EmendaPagamento.municipio_ibge)) == 1)
    ).all()
    return {_cnpj(c): ibge for c, ibge in linhas if len(_cnpj(c)) == 14}


class Mapa:
    def __init__(
        self,
        entes: list[dict[str, Any]],
        por_favorecido: dict[str, str],
        municipios: list[tuple[str, str, str]],
    ) -> None:
        self.prefeituras: dict[str, str] = {}
        self.estados: set[str] = set()
        for e in entes:
            cnpj = _cnpj(e.get("cnpj"))
            if len(cnpj) != 14:
                continue
            if e.get("esfera") == "M":
                self.prefeituras[cnpj] = e["ibge"]
            elif e.get("esfera") in ("E", "D"):
                self.estados.add(cnpj)
        self.por_favorecido = por_favorecido
        self.municipios = municipios
        self._cache_nome: dict[tuple[str, str], str | None] = {}

    def _por_nome(self, uf: str | None, nome: str | None) -> str | None:
        if not uf or not nome:
            return None
        chave = (uf, nome)
        if chave not in self._cache_nome:
            resolvidos, _ = resolver_municipios(
                [{"uf": uf, "municipio_nome": nome}], self.municipios
            )
            self._cache_nome[chave] = resolvidos[0]["municipio_ibge"] if resolvidos else None
        return self._cache_nome[chave]

    def resolver(
        self,
        cnpj: str | None,
        uf: str | None = None,
        beneficiario: str | None = None,
        municipio_nome: str | None = None,
    ) -> tuple[str | None, str]:
        """(IBGE ou None, como foi resolvido): siconfi | favorecido | nome | estado | sem."""
        cnpj = _cnpj(cnpj)
        if cnpj in self.prefeituras:
            return self.prefeituras[cnpj], "siconfi"
        if cnpj in self.estados:
            return None, "estado"
        if cnpj in self.por_favorecido:
            return self.por_favorecido[cnpj], "favorecido"
        nome = comum.chave_nome(beneficiario)
        if PREFIXOS_PREFEITURA.match(nome):
            ibge = self._por_nome(uf, PREFIXOS_PREFEITURA.sub("", nome))
            if ibge:
                return ibge, "nome"
        if municipio_nome:  # convênio: município do convenente informado pela CGU
            ibge = self._por_nome(uf, municipio_nome)
            if ibge:
                return ibge, "nome"
        return None, "sem"


def montar(session: Session, entes: list[dict[str, Any]]) -> Mapa:
    municipios = [
        tuple(m)
        for m in session.execute(select(Municipio.ibge, Municipio.uf, Municipio.nome_chave))
    ]
    return Mapa(entes, favorecidos(session), municipios)  # type: ignore[arg-type]


def contexto(session: Session) -> str:
    """Muda quando o mapa de favorecidos muda (recarrega com o bruto da API igual)."""
    total, distintos = session.execute(
        select(func.count(), func.count(func.distinct(EmendaPagamento.favorecido_codigo)))
    ).one()
    return f"favorecidos:{total}:{distintos}"
