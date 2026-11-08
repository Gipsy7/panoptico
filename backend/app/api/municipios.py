from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, select
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
from app.schemas.ideb import IdebMunicipio
from app.schemas.obras import ObrasMunicipio, ObrasPorUf
from app.schemas.pib import PibMunicipio
from app.schemas.repasses_estaduais import RepassesEstaduaisResposta
from app.services import (
    contas,
    contratos_pncp,
    emendas,
    fornecedores,
    ideb,
    obras,
    pib,
    repasses_estaduais,
)
from app.services.texto_busca import normalizar

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


@router.get("/municipios/{ibge}/obras", response_model=ObrasMunicipio)
def obras_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Obras federais do Obrasgov.br na cidade, por situação, com o percentual executado."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    return obras.do_municipio(session, ibge)


@router.get("/municipios/{ibge}/ideb", response_model=IdebMunicipio)
def ideb_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """IDEB da cidade por etapa e rede, com o do estado e o do Brasil na mesma rede (INEP)."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return ideb.do_municipio(session, ibge, municipio.uf)


@router.get("/municipios/{ibge}/pib", response_model=PibMunicipio)
def pib_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """PIB da cidade (IBGE), com o PIB por morador do estado e do Brasil no mesmo ano."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return pib.do_municipio(session, ibge, municipio.uf)


@router.get("/obras/estados", response_model=ObrasPorUf)
def obras_por_estado(session: Annotated[Session, Depends(get_session)]) -> dict:
    """Obras federais por estado e situação (Obrasgov.br)."""
    return obras.resumo_ufs(session)


@router.get("/municipios/busca", response_model=list[MunicipioInfo])
def buscar_municipio(
    q: Annotated[str, Query(min_length=2, max_length=80)],
    session: Annotated[Session, Depends(get_session)],
) -> list[Municipio]:
    """Cidades pelo nome, sem acento nem caixa (a busca da home): primeiro as que começam com o
    texto, depois as que o contêm; no máximo 8."""
    termo = " ".join(normalizar(q).upper().split())
    if len(termo) < 2:
        return []
    comeca = Municipio.nome_chave.startswith(termo, autoescape=True)
    return list(
        session.scalars(
            select(Municipio)
            .where(Municipio.nome_chave.contains(termo, autoescape=True))
            .order_by(case((comeca, 0), else_=1), Municipio.nome_chave, Municipio.uf)
            .limit(8)
        )
    )


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
