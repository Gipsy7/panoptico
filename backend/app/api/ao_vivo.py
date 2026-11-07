"""O Plenário agora (Câmara e Senado), direto das APIs oficiais, com cache curto."""

from fastapi import APIRouter, Response

from app.services import ao_vivo as servico

router = APIRouter(prefix="/ao-vivo", tags=["ao vivo"])


@router.get("")
def ao_vivo(resposta: Response):
    # Cache curto na CDN e no navegador: a sessão muda em minutos, não em horas.
    resposta.headers["Cache-Control"] = "public, max-age=60, s-maxage=120"
    return servico.ao_vivo()
