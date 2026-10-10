"""Revisão humana das sugestões de atos no Diário Oficial da União (tabela `dou_ato`).

Mesma mecânica dos diários municipais (`ingestion/diarios/revisao.py`): nome achado em
texto nunca é vínculo. A sugestão só vira fato publicável depois que uma pessoa confere o
trecho e o link do DOU em `ingestion.revisar --tipo dou`. A decisão vai para
data/dou_revisados.csv (versionado) e é reaplicada a cada carga:

- aceito: `dou_ato.revisado = true` e um `Evento` (tipo "ato_pessoal") na linha do tempo,
  com o link do DOU como fonte;
- recusado: sai da fila e nunca vira evento (e o evento some, se já existia).

A pessoa vai no CSV pela chave estável de um vínculo ("fonte:id_externo"), e a matéria pelo
`id_materia` do XML (várias matérias podem estar na mesma página do DOU, então a URL sozinha
não identifica o ato).
"""

import csv
import hashlib
from datetime import date
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import DouAto, Evento, Pessoa
from ingestion.diarios.revisao import (
    _publicavel,
    _vinculos_da_pessoa,
    chave_da_pessoa,
    pessoa_da_chave,
)

DOU_REVISADOS = Path(__file__).resolve().parents[3] / "data" / "dou_revisados.csv"
COLUNAS = ["id_materia", "pessoa_chave", "decisao", "revisado_por", "revisado_em", "observacao"]
FONTE_EVENTO = "dou_atos"
TIPO_EVENTO = "ato_pessoal"
ATO_TEXTO = {
    "nomeacao": "Nomeação",
    "exoneracao": "Exoneração",
    "designacao": "Designação",
    "dispensa": "Dispensa",
}


def decisoes(caminho: Path | None = None) -> list[dict[str, str]]:
    caminho = caminho or DOU_REVISADOS
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [
            {k: (v or "").strip() for k, v in linha.items()}
            for linha in csv.DictReader(arquivo)
            if (linha.get("decisao") or "").strip() in ("aceito", "recusado")
        ]


def pendentes(session: Session, caminho: Path | None = None) -> list[dict]:
    """Sugestões ainda não decididas, com o contexto para o revisor: quem, órgão, data, tipo
    do ato, trecho e link."""
    decididas = {(d["id_materia"], d["pessoa_chave"]) for d in decisoes(caminho)}
    resultado = []
    consulta = (
        select(DouAto, Pessoa.nome)
        .join(Pessoa, Pessoa.id == DouAto.pessoa_id)
        .where(DouAto.revisado.is_(False))
        .order_by(DouAto.data.desc(), DouAto.id)
    )
    for ato, nome in session.execute(consulta):
        chave = chave_da_pessoa(session, ato.pessoa_id)
        if chave is None or (ato.id_materia, chave) in decididas:
            continue
        resultado.append(
            {
                "id_materia": ato.id_materia,
                "pessoa_chave": chave,
                "pessoa": nome,
                "orgao": ato.orgao,
                "data": ato.data.isoformat(),
                "tipo_ato": ato.tipo_ato,
                "trecho": ato.trecho,
                "url": ato.url,
            }
        )
    return resultado


def gravar_decisao(
    item: dict, decisao: str, revisor: str, observacao: str = "", caminho: Path | None = None
) -> None:
    caminho = caminho or DOU_REVISADOS
    novo = not caminho.exists()
    with caminho.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        if novo:
            escritor.writeheader()
        escritor.writerow(
            {"id_materia": item["id_materia"], "pessoa_chave": item["pessoa_chave"],
             "decisao": decisao, "revisado_por": revisor,
             "revisado_em": date.today().isoformat(), "observacao": observacao}
        )  # fmt: skip


def id_do_evento(pessoa_chave: str, id_materia: str) -> str:
    """Determinístico: o mesmo ato aceito para a mesma pessoa dá sempre o mesmo id."""
    return hashlib.sha1(f"dou|{pessoa_chave}|{id_materia}".encode()).hexdigest()[:24]


def aplicar_atos_dou(session: Session, caminho: Path | None = None) -> dict[str, int]:
    """Reaplica as decisões do CSV (a última de cada matéria e pessoa vale). Decisão que não
    encontra mais a pessoa ou a sugestão é ignorada. Idempotente."""
    contagem = {"aceitos": 0, "recusados": 0}
    ultimas = {(d["id_materia"], d["pessoa_chave"]): d for d in decisoes(caminho)}
    for (id_materia, chave), d in ultimas.items():
        pessoa_id = pessoa_da_chave(session, chave)
        if pessoa_id is None:
            continue
        id_externo = id_do_evento(chave, id_materia)
        ato = session.scalar(
            select(DouAto).where(DouAto.pessoa_id == pessoa_id, DouAto.id_materia == id_materia)
        )
        if d["decisao"] == "recusado":
            session.execute(
                delete(Evento).where(
                    Evento.fonte == FONTE_EVENTO,
                    Evento.id_externo == id_externo,
                    Evento.tipo == TIPO_EVENTO,
                )
            )
            if ato is not None:
                ato.revisado = False
            contagem["recusados"] += 1
            continue
        if ato is None:
            continue
        publicavel = next(
            (v for v in _vinculos_da_pessoa(session, pessoa_id) if _publicavel(v)), None
        )
        if publicavel is None:
            continue  # sem vínculo publicável o evento não apareceria; nada é marcado
        ato.revisado = True
        valores = {
            "pessoa_id": pessoa_id,
            "vinculo_id": publicavel.id,
            "data": ato.data,
            "tipo": TIPO_EVENTO,
            "descricao": f"{ATO_TEXTO.get(ato.tipo_ato, 'Ato')} em ato de pessoal publicado no "
            f"Diário Oficial da União (Seção 2): {ato.orgao}.",
            "orgao": ato.orgao[:120],
            "fonte": FONTE_EVENTO,
            "id_externo": id_externo,
            "fonte_url": ato.url,
        }
        stmt = insert(Evento).values(**valores)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=["fonte", "id_externo", "tipo"],
                set_={k: stmt.excluded[k] for k in valores if k != "id_externo"},
            )
        )
        contagem["aceitos"] += 1
    session.flush()
    return contagem
