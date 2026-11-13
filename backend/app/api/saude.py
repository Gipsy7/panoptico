from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import Sessao

router = APIRouter()


@router.get("/saude")
def saude(session: Sessao) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
        banco = "ok"
    except SQLAlchemyError:
        banco = "indisponivel"
    return {"status": "ok", "banco": banco}
