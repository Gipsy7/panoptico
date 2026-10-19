from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Municipio
from app.schemas import Localizacao, RepresentantesResposta
from app.services import cep as cep_service
from app.services.representantes import UFS, listar_por_uf

router = APIRouter()


def localizar(
    session: Session, cep: str | None, uf: str | None, municipio: str | None
) -> Localizacao:
    """Onde a pessoa está, pelo município (IBGE), pelo CEP ou pela UF, nessa ordem. Erros
    viram HTTPException com mensagem para o cidadão."""
    if municipio:
        encontrado = session.get(Municipio, municipio)
        if encontrado is None:
            raise HTTPException(404, "Município não encontrado.")
        return Localizacao(
            cep=None,
            uf=encontrado.uf,
            estado=UFS[encontrado.uf],
            municipio=encontrado.nome,
            codigo_ibge=encontrado.ibge,
        )
    if cep:
        try:
            local = cep_service.buscar_cep(cep)
        except cep_service.CepInvalido as e:
            raise HTTPException(422, str(e)) from e
        except cep_service.CepNaoEncontrado as e:
            raise HTTPException(404, str(e)) from e
        except cep_service.CepIndisponivel as e:
            raise HTTPException(502, "O serviço de CEP está fora do ar. Tente pela UF.") from e
        return Localizacao(
            cep=local.cep,
            uf=local.uf,
            estado=UFS[local.uf],
            municipio=local.municipio,
            codigo_ibge=local.codigo_ibge or None,
        )
    if uf:
        sigla = uf.upper()
        if sigla not in UFS:
            raise HTTPException(422, "UF inválida.")
        return Localizacao(cep=None, uf=sigla, estado=UFS[sigla], municipio=None)
    raise HTTPException(422, "Informe o CEP ou a UF.")


@router.get("/representantes", response_model=RepresentantesResposta)
def representantes(
    session: Annotated[Session, Depends(get_session)],
    cep: Annotated[str | None, Query(description="CEP com ou sem hífen")] = None,
    uf: Annotated[str | None, Query(description="Sigla da UF, se não souber o CEP")] = None,
    municipio: Annotated[
        str | None, Query(description="Código IBGE do município, se não souber o CEP")
    ] = None,
) -> RepresentantesResposta:
    localizacao = localizar(session, cep, uf, municipio)
    resultado = listar_por_uf(session, localizacao.uf)
    return RepresentantesResposta.model_validate(
        {
            "localizacao": localizacao,
            "deputados": resultado.deputados,
            "senadores": resultado.senadores,
            "atualizado_em": resultado.atualizado_em,
        },
        from_attributes=True,
    )
