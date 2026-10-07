from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import fontes, municipios, parlamentares, representantes, saude
from app.config import settings

app = FastAPI(
    title="Panóptico API",
    description="Quem te representa, às claras. Dados oficiais de parlamentares federais.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(saude.router)
app.include_router(representantes.router)
app.include_router(parlamentares.router)
app.include_router(municipios.router)
app.include_router(fontes.router)
