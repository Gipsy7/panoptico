from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import FonteItem
from app.services import fontes

router = APIRouter()


@router.get("/fontes", response_model=list[FonteItem])
def listar_fontes(session: Annotated[Session, Depends(get_session)]) -> list[dict]:
    return fontes.listar(session)
