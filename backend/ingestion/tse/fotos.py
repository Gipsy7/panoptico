"""Fotos dos eleitos que só existem no TSE (vereadores, prefeitos, deputados estaduais,
governadores, presidente), a partir dos zips de fotos por UF.

Os zips trazem todos os candidatos (552 MB só SC em 2024; 2,2 GB SP): cada um é baixado
para o disco, só as fotos das candidaturas guardadas são lidas, reduzidas para WebP e
gravadas no banco, e o zip é apagado antes do próximo. Parlamentares federais já têm a
foto oficial da Câmara e do Senado e ficam de fora.
"""

import argparse
import io
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models import Candidatura, FonteIngestao, Foto
from app.services.representantes import UFS
from ingestion import comum

FONTE = "tse_fotos"
URL = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes{ano}/fotos/foto_cand{ano}_{uf}_div.zip"
LARGURA = 240
NOME = re.compile(r"F[A-Z]{2}(\d+)_div\.(jpe?g|png)$", re.IGNORECASE)


def reduzir(conteudo: bytes) -> bytes | None:
    """Foto 3x4 reduzida para WebP de 240 px de largura (uns 10 KB)."""
    try:
        with Image.open(io.BytesIO(conteudo)) as imagem:
            imagem = imagem.convert("RGB")
            altura = round(imagem.height * LARGURA / imagem.width)
            imagem = imagem.resize((LARGURA, altura), Image.Resampling.LANCZOS)
            saida = io.BytesIO()
            imagem.save(saida, format="WEBP", quality=72, method=6)
            return saida.getvalue()
    except (UnidentifiedImageError, OSError, ZeroDivisionError):
        return None


def extrair(zip_: zipfile.ZipFile, candidaturas: dict[str, int]) -> list[dict]:
    fotos = []
    for nome in zip_.namelist():
        achado = NOME.search(nome.rsplit("/", 1)[-1])
        if not achado or achado.group(1) not in candidaturas:
            continue
        webp = reduzir(zip_.read(nome))
        if webp:
            fotos.append({"candidatura_id": candidaturas[achado.group(1)], "webp": webp})
    return fotos


def gravar(fotos: list[dict]) -> None:
    with SessionLocal() as session:
        for inicio in range(0, len(fotos), 500):
            stmt = insert(Foto).values(fotos[inicio : inicio + 500])
            session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["candidatura_id"], set_={"webp": stmt.excluded.webp}
                )
            )
        session.commit()


def executar(ano: int, ufs: list[str] | None = None) -> int:
    with SessionLocal() as session:
        candidaturas = dict(
            session.execute(
                select(Candidatura.sq_candidato, Candidatura.id).where(
                    Candidatura.ano_eleicao == ano,
                    Candidatura.parlamentar_id.is_(None),
                    Candidatura.situacao_turno.like("ELEITO%"),
                )
            ).all()
        )
    if not candidaturas:
        return 0
    total = 0
    with comum.criar_cliente() as client:
        for uf in ufs or [*UFS, "BR"]:
            try:
                arquivo = comum.baixar_para_arquivo(client, URL.format(ano=ano, uf=uf))
            except Exception as erro:  # um UF sem arquivo (ex.: BR em eleição municipal)
                print(f"  {uf}: sem arquivo ({erro.__class__.__name__})")
                continue
            try:
                with zipfile.ZipFile(arquivo) as z:
                    fotos = extrair(z, candidaturas)
                gravar(fotos)
                total += len(fotos)
                print(f"  {uf}: {len(fotos)} fotos")
            finally:
                Path(arquivo).unlink(missing_ok=True)
    with SessionLocal() as session:
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url=URL.format(ano=ano, uf="{UF}"),
                arquivo_raw="(não guardado: zips de centenas de MB)",
                registros=total,
                status="ok",
                concluido_em=datetime.now(UTC),
            )
        )
        session.commit()
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=[2022, 2024])
    parser.add_argument("--uf", nargs="*", help="Só estes UFs (padrão: todos e BR)")
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano, args.uf)} fotos")
