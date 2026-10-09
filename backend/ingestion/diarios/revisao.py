"""Revisão humana das sugestões de atos nos diários oficiais (tabela `diario_ato`).

Nome achado em texto nunca é vínculo: a sugestão só vira fato publicável depois que uma
pessoa confere o trecho e o link do diário e decide em `ingestion.revisar --tipo diario`.
A decisão vai para data/atos_revisados.csv (versionado) e é reaplicada a cada carga:

- aceito: `diario_ato.revisado = true` e um `Evento` (tipo "ato_pessoal") na linha do tempo,
  com o link do diário como fonte;
- recusado: a sugestão sai da fila e nunca vira evento (e o evento some, se já existia).

A pessoa é identificada no CSV pela chave estável de um de seus vínculos ("fonte:id_externo",
o mesmo formato de `ligado_a` em vinculos_revisados.csv; ex. "candidatura:2024:123"), e não
pelo id de `pessoa`, que muda quando duas pessoas se fundem ou a carga é refeita.
"""

import csv
import hashlib
from datetime import date
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Candidatura, DiarioAto, Evento, MandatoLocal, Municipio, Pessoa
from app.models.pessoa import REGRAS_FORTES, PessoaVinculo

ATOS_REVISADOS = Path(__file__).resolve().parents[3] / "data" / "atos_revisados.csv"
COLUNAS = ["url", "pessoa_chave", "decisao", "revisado_por", "revisado_em", "observacao"]
FONTE_EVENTO = "querido_diario_atos"
TIPO_EVENTO = "ato_pessoal"
ATO_TEXTO = {"nomeacao": "Nomeação", "exoneracao": "Exoneração", "designacao": "Designação"}
_ORDEM_FONTE = {"candidatura": 0, "mandato_local": 1, "parlamentar": 2}


def decisoes(caminho: Path | None = None) -> list[dict[str, str]]:
    caminho = caminho or ATOS_REVISADOS
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [
            {k: (v or "").strip() for k, v in linha.items()}
            for linha in csv.DictReader(arquivo)
            if (linha.get("decisao") or "").strip() in ("aceito", "recusado")
        ]


def _publicavel(v: PessoaVinculo) -> bool:
    return v.regra in REGRAS_FORTES or v.revisado


def _vinculos_da_pessoa(session: Session, pessoa_id: int) -> list[PessoaVinculo]:
    """Vínculos publicáveis primeiro (fortes ou revisados), depois por fonte e chave."""
    lista = session.scalars(select(PessoaVinculo).where(PessoaVinculo.pessoa_id == pessoa_id))
    return sorted(
        lista, key=lambda v: (not _publicavel(v), _ORDEM_FONTE.get(v.fonte, 9), v.id_externo)
    )


def chave_da_pessoa(session: Session, pessoa_id: int) -> str | None:
    vinculos = _vinculos_da_pessoa(session, pessoa_id)
    return f"{vinculos[0].fonte}:{vinculos[0].id_externo}" if vinculos else None


def pessoa_da_chave(session: Session, chave: str) -> int | None:
    fonte, _, id_externo = chave.partition(":")
    return session.scalar(
        select(PessoaVinculo.pessoa_id).where(
            PessoaVinculo.fonte == fonte, PessoaVinculo.id_externo == id_externo
        )
    )


def _cargo(session: Session, pessoa_id: int, ibge: str) -> str:
    """Cargo do mandato no município: prefeito, vice ou vereador (eleição de 2024 ou
    câmara em exercício)."""
    for v in _vinculos_da_pessoa(session, pessoa_id):
        if v.fonte == "candidatura":
            ano, _, sq = v.id_externo.partition(":")
            c = session.scalar(
                select(Candidatura).where(
                    Candidatura.ano_eleicao == int(ano),
                    Candidatura.sq_candidato == sq,
                    Candidatura.municipio_ibge == ibge,
                    Candidatura.situacao_turno.like("ELEITO%"),
                )
            )
            if c:
                return c.cargo.lower()
        elif v.fonte == "mandato_local":
            casa, uf, ibge_m, id_ext = v.id_externo.split(":", 3)
            if casa == "camara" and ibge_m == ibge:
                m = session.scalar(
                    select(MandatoLocal).where(
                        MandatoLocal.casa == casa, MandatoLocal.uf == uf,
                        MandatoLocal.municipio_ibge == ibge, MandatoLocal.id_externo == id_ext,
                    )
                )  # fmt: skip
                if m:
                    return "vereador"
    return "sem mandato identificado"


def pendentes(session: Session, caminho: Path | None = None) -> list[dict]:
    """Sugestões ainda não decididas (nem aceitas, nem recusadas no CSV), com o contexto
    para o revisor: quem, cargo e município do mandato, data, tipo, trecho e link."""
    decididas = {(d["url"], d["pessoa_chave"]) for d in decisoes(caminho)}
    resultado = []
    consulta = (
        select(DiarioAto, Pessoa.nome, Municipio.nome, Municipio.uf)
        .join(Pessoa, Pessoa.id == DiarioAto.pessoa_id)
        .outerjoin(Municipio, Municipio.ibge == DiarioAto.municipio_ibge)
        .where(DiarioAto.revisado.is_(False))
        .order_by(DiarioAto.data.desc(), DiarioAto.id)
    )
    for ato, nome, cidade, uf in session.execute(consulta):
        chave = chave_da_pessoa(session, ato.pessoa_id)
        if chave is None or (ato.url, chave) in decididas:
            continue
        resultado.append(
            {
                "url": ato.url,
                "pessoa_chave": chave,
                "pessoa": nome,
                "cargo": _cargo(session, ato.pessoa_id, ato.municipio_ibge),
                "municipio": (cidade or ato.municipio_ibge) + (f" ({uf})" if uf else ""),
                "data": ato.data.isoformat(),
                "tipo_ato": ato.tipo_ato,
                "trecho": ato.trecho,
            }
        )
    return resultado


def gravar_decisao(
    item: dict, decisao: str, revisor: str, observacao: str = "", caminho: Path | None = None
) -> None:
    caminho = caminho or ATOS_REVISADOS
    novo = not caminho.exists()
    with caminho.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        if novo:
            escritor.writeheader()
        escritor.writerow(
            {"url": item["url"], "pessoa_chave": item["pessoa_chave"], "decisao": decisao,
             "revisado_por": revisor, "revisado_em": date.today().isoformat(),
             "observacao": observacao}
        )  # fmt: skip


def id_do_evento(pessoa_chave: str, url: str) -> str:
    """Determinístico: o mesmo ato aceito para a mesma pessoa dá sempre o mesmo id."""
    return hashlib.sha1(f"{pessoa_chave}|{url}".encode()).hexdigest()[:24]


def aplicar_atos(session: Session, caminho: Path | None = None) -> dict[str, int]:
    """Reaplica as decisões do CSV (a última de cada url e pessoa vale). Decisão que não
    encontra mais a pessoa ou a sugestão é ignorada. Idempotente."""
    contagem = {"aceitos": 0, "recusados": 0}
    ultimas = {(d["url"], d["pessoa_chave"]): d for d in decisoes(caminho)}
    for (url, chave), d in ultimas.items():
        pessoa_id = pessoa_da_chave(session, chave)
        if pessoa_id is None:
            continue
        id_externo = id_do_evento(chave, url)
        ato = session.scalar(
            select(DiarioAto).where(DiarioAto.pessoa_id == pessoa_id, DiarioAto.url == url)
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
        cidade = session.scalar(select(Municipio.nome).where(Municipio.ibge == ato.municipio_ibge))
        local = f"de {cidade}" if cidade else f"do município {ato.municipio_ibge}"
        valores = {
            "pessoa_id": pessoa_id,
            "vinculo_id": publicavel.id,
            "data": ato.data,
            "tipo": TIPO_EVENTO,
            "descricao": f"{ATO_TEXTO.get(ato.tipo_ato, 'Ato')} em ato publicado no diário "
            f"oficial {local}.",
            "orgao": f"Diário Oficial {local}"[:120],
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
