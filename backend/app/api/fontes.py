from fastapi import APIRouter

from app.db import Sessao
from app.schemas import FonteItem
from app.services import fontes

router = APIRouter()


@router.get("/fontes", response_model=list[FonteItem])
def listar_fontes(session: Sessao) -> list[dict]:
    return fontes.listar(session)
