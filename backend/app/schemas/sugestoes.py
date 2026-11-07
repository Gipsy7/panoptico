"""Avisar erro, direito de resposta e correções públicas (Frente 7)."""

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

TipoPerfilSite = Literal["parlamentar", "deputado-estadual", "vereador", "eleito"]

TEXTO_MIN = 10
TEXTO_MAX_ERRO = 2000
TEXTO_MAX_RESPOSTA = 3000


def _vazio_vira_none(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


class SugestaoEntrada(BaseModel):
    tipo: Literal["erro", "resposta"]
    categoria: Literal["numero", "cadastro", "foto", "link", "outro"] | None = None
    texto: str = Field(max_length=TEXTO_MAX_RESPOSTA)
    pagina: str = Field(min_length=1, max_length=300)
    secao: str | None = Field(default=None, max_length=120)
    perfil_tipo: TipoPerfilSite | None = None
    perfil_id: str | None = Field(default=None, max_length=40)
    contato: str | None = Field(default=None, max_length=200)
    confirmacao: Literal["email_funcional", "oficio"] | None = None

    @field_validator("texto")
    @classmethod
    def _texto(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < TEXTO_MIN:
            raise ValueError(f"O texto precisa ter pelo menos {TEXTO_MIN} caracteres.")
        return valor

    @field_validator("pagina")
    @classmethod
    def _pagina(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor.startswith("/") or valor.startswith("//"):
            raise ValueError("A página é o caminho do site, começando por /.")
        return valor

    @field_validator("secao", "perfil_id", "contato")
    @classmethod
    def _opcional(cls, valor: str | None) -> str | None:
        return _vazio_vira_none(valor)

    @field_validator("contato")
    @classmethod
    def _contato(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        e_email = re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", valor) is not None
        e_telefone = re.fullmatch(r"[\d\s()+.-]+", valor) is not None and (
            8 <= len(re.sub(r"\D", "", valor)) <= 15
        )
        if not (e_email or e_telefone):
            raise ValueError("O contato precisa ser um e-mail ou um telefone.")
        return valor

    @model_validator(mode="after")
    def _por_tipo(self) -> "SugestaoEntrada":
        if self.tipo == "erro":
            if self.categoria is None:
                raise ValueError("Escolha o tipo de erro (categoria).")
            if len(self.texto) > TEXTO_MAX_ERRO:
                raise ValueError(f"O texto pode ter até {TEXTO_MAX_ERRO} caracteres.")
            self.confirmacao = None
        else:
            if self.confirmacao is None:
                raise ValueError("Diga por qual canal oficial a identidade será confirmada.")
            self.categoria = None
        if (self.perfil_tipo is None) != (self.perfil_id is None):
            raise ValueError("perfil_tipo e perfil_id vão juntos.")
        return self


class Protocolo(BaseModel):
    protocolo: str


class RespostaPublicada(BaseModel):
    id: int
    texto: str
    secao: str | None
    recebida_em: date
    publicada_em: date | None


class CorrecaoPublica(BaseModel):
    id: int
    data: date
    dado: str
    antes: str
    depois: str
    motivo: str
    fonte: str
    perfil_tipo: str | None
    perfil_id: str | None
    perfil_nome: str | None


class Correcoes(BaseModel):
    itens: list[CorrecaoPublica]
    total: int
