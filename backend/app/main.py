from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    busca,
    comparar,
    eleitos,
    fontes,
    municipios,
    parlamentares,
    representantes,
    saude,
)
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

# Os dados mudam uma vez por dia (ingestão diária). Deixar a CDN guardar as respostas
# poupa o banco: a mesma consulta só chega ao Postgres uma vez por hora, e enquanto a
# cópia é renovada em segundo plano o visitante recebe a anterior. /saude fica de fora
# para continuar refletindo o estado real do banco.
CACHE_CDN = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"


@app.middleware("http")
async def cache_na_cdn(request: Request, call_next):
    resposta = await call_next(request)
    if (
        request.method == "GET"
        and resposta.status_code == 200
        and request.url.path != "/saude"
        and "cache-control" not in resposta.headers
    ):
        resposta.headers["Cache-Control"] = CACHE_CDN
    return resposta


app.include_router(saude.router)
app.include_router(representantes.router)
app.include_router(parlamentares.router)
app.include_router(municipios.router)
app.include_router(fontes.router)
app.include_router(comparar.router)
app.include_router(eleitos.router)
app.include_router(busca.router)
