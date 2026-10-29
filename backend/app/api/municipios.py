from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import CanalOficial, Municipio
from app.schemas import (
    CanaisResposta,
    ContasMunicipioResposta,
    FornecedoresPncpResposta,
    FornecedoresResposta,
    MunicipioInfo,
)
from app.schemas.emendas_municipio import EmendasMunicipioCompleta
from app.schemas.repasses_estaduais import RepassesEstaduaisResposta
from app.services import contas, contratos_pncp, emendas, fornecedores, repasses_estaduais

router = APIRouter()


@router.get("/municipios/{ibge}/emendas", response_model=EmendasMunicipioCompleta)
def emendas_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Emendas pagas à cidade por tipo e autor, previsto nos planos Pix e convênios."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return emendas.resumo_municipio(session, municipio)


@router.get("/municipios/{ibge}/contas", response_model=ContasMunicipioResposta)
def contas_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Contas anuais da prefeitura no SICONFI: receita, despesa e áreas."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    resultado = contas.resumo(session, ibge)
    if resultado is None:
        raise HTTPException(404, "Sem contas entregues ao Tesouro para este município.")
    return resultado


@router.get("/municipios/{ibge}/repasses-estaduais", response_model=RepassesEstaduaisResposta)
def repasses_estaduais_do_municipio(
    ibge: str, session: Annotated[Session, Depends(get_session)]
) -> dict:
    """Quanto o governo do estado repassou à prefeitura, por tipo (SICONFI, DCA)."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return repasses_estaduais.resumo(session, municipio)


@router.get("/municipios/{ibge}/fornecedores", response_model=FornecedoresResposta)
def fornecedores_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Para quem a prefeitura e a câmara pagaram (onde o Tribunal de Contas publica)."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    resultado = fornecedores.resumo(session, ibge)
    if resultado is None:
        raise HTTPException(404, "Sem dados de fornecedores para este município.")
    return resultado


ORDEM_CANAIS = [
    "prefeitura",
    "camara",
    "sapl",
    "sistema_legislativo",
    "transparencia_prefeitura",
    "transparencia_camara",
]


@router.get("/municipios/{ibge}/canais", response_model=CanaisResposta)
def canais_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Sites oficiais da cidade, do catálogo revisado (data/canais_oficiais.csv)."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    canais = session.scalars(select(CanalOficial).where(CanalOficial.municipio_ibge == ibge)).all()
    canais = sorted(
        canais, key=lambda c: ORDEM_CANAIS.index(c.tipo) if c.tipo in ORDEM_CANAIS else 99
    )
    return {"itens": canais}


@router.get("/municipios", response_model=list[MunicipioInfo])
def municipios_da_uf(
    uf: Annotated[str, Query(min_length=2, max_length=2)],
    session: Annotated[Session, Depends(get_session)],
) -> list[Municipio]:
    return list(
        session.scalars(
            select(Municipio).where(Municipio.uf == uf.upper()).order_by(Municipio.nome_chave)
        )
    )


@router.get("/municipios/{ibge}/fornecedores-pncp", response_model=FornecedoresPncpResposta)
def fornecedores_pncp_do_municipio(
    ibge: str, session: Annotated[Session, Depends(get_session)]
) -> dict:
    """Maiores fornecedores dos órgãos municipais no PNCP, no ano mais recente."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    resultado = contratos_pncp.maiores_do_municipio(session, ibge)
    if resultado is None:
        raise HTTPException(404, "Sem contratos do PNCP para este município.")
    return resultado
