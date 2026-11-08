"""Os temas de "Por dentro do estado" (economia, agro, escolas, internet, saneamento e segurança):
os mesmos serviços das cidades, com o código do estado no lugar do município e sem a comparação do
estado com ele mesmo."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.agro import AgroMunicipio
from app.schemas.emprego import EmpregoMunicipio
from app.schemas.ideb import IdebMunicipio
from app.schemas.internet import InternetMunicipio
from app.schemas.pib import PibMunicipio
from app.schemas.saneamento import SaneamentoMunicipio
from app.schemas.saude_cnes import SaudeMunicipio
from app.schemas.seguranca import SegurancaMunicipio
from app.services import agro, emprego, ideb, internet, pib, saneamento, saude_cnes, seguranca
from app.services.pib import CODIGO_UF

router = APIRouter()
Sessao = Annotated[Session, Depends(get_session)]


def _codigo(uf: str) -> tuple[str, str]:
    uf = uf.upper()
    if uf not in CODIGO_UF:
        raise HTTPException(404, "Estado não encontrado.")
    return uf, CODIGO_UF[uf]


@router.get("/estados/{uf}/pib", response_model=PibMunicipio)
def pib_do_estado(uf: str, session: Sessao) -> dict:
    """PIB do estado (IBGE) e PIB por morador com o do Brasil."""
    uf, codigo = _codigo(uf)
    dados = pib.do_municipio(session, codigo, uf)
    for p in dados["serie"]:
        p["uf_por_habitante"] = None
    return dados


@router.get("/estados/{uf}/emprego", response_model=EmpregoMunicipio)
def emprego_do_estado(uf: str, session: Sessao) -> dict:
    """Empresas, pessoas ocupadas e salário médio do estado (IBGE), com o do Brasil."""
    uf, codigo = _codigo(uf)
    dados = emprego.do_municipio(session, codigo, uf)
    for p in dados["serie"]:
        p["uf_salario_medio"] = None
    return dados


@router.get("/estados/{uf}/agro", response_model=AgroMunicipio)
def agro_do_estado(uf: str, session: Sessao) -> dict:
    """Lavouras e criação do estado (IBGE, PAM e PPM)."""
    uf, codigo = _codigo(uf)
    dados = agro.do_municipio(session, codigo, uf)
    dados["uf_valor_total"] = None
    return dados


@router.get("/estados/{uf}/ideb", response_model=IdebMunicipio)
def ideb_do_estado(uf: str, session: Sessao) -> dict:
    """IDEB do estado por etapa e rede, com o do Brasil (INEP)."""
    uf, _ = _codigo(uf)
    return ideb.do_estado(session, uf)


@router.get("/estados/{uf}/internet", response_model=InternetMunicipio)
def internet_do_estado(uf: str, session: Sessao) -> dict:
    """Banda larga fixa do estado (Anatel) por 100 moradores, com o Brasil."""
    uf, _ = _codigo(uf)
    return internet.do_estado(session, uf)


@router.get("/estados/{uf}/saneamento", response_model=SaneamentoMunicipio)
def saneamento_do_estado(uf: str, session: Sessao) -> dict:
    """Água, esgoto e lixo no estado (Censo 2022), com o Brasil."""
    uf, codigo = _codigo(uf)
    dados = saneamento.do_municipio(session, codigo, uf)
    dados["estado"] = dict.fromkeys(saneamento.CAMPOS)
    return dados


@router.get("/estados/{uf}/saude", response_model=SaudeMunicipio)
def saude_do_estado(uf: str, session: Sessao) -> dict:
    """Leitos, unidades básicas e hospitais do estado (CNES/DATASUS), com o Brasil."""
    uf, codigo = _codigo(uf)
    return saude_cnes.do_lugar(session, codigo, uf, comparar_estado=False)


@router.get("/estados/{uf}/seguranca", response_model=SegurancaMunicipio)
def seguranca_do_estado(uf: str, session: Sessao) -> dict:
    """Homicídios de moradores do estado (SIM/DATASUS), com o Brasil."""
    uf, codigo = _codigo(uf)
    dados = seguranca.do_municipio(session, codigo, uf)
    dados["estado"] = {"serie": [], "media_3_anos_por_100_mil": None}
    return dados
