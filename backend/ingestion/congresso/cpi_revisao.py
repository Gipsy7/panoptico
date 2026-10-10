"""Revisão humana dos pedidos de indiciamento sugeridos pelas CPIs (`cpi_indiciamento_sugestao`).

Nome achado em PDF nunca é vínculo, e pedido de indiciamento em relatório de CPI é proposta da
comissão: não é acusação formal nem condenação (docs/DECISOES.md, "CPIs e CPMIs"). A sugestão
só vira fato publicável depois que uma pessoa confere o trecho e o link do PDF e escolhe, em
`ingestion.revisar --tipo cpi`, a pessoa da base a que o nome se refere. A decisão vai para
data/indiciamentos_revisados.csv (versionado) e é reaplicada a cada carga das CPIs e de pessoas:

- aceito: `cpi_indiciamento_sugestao.revisado = true` e um `Evento` (tipo "cpi_indiciamento")
  na linha do tempo da pessoa escolhida, com o link do PDF como fonte;
- recusado ("não é pessoa da base" ou pessoa privada): a sugestão sai da fila e nunca vira
  evento (e o evento some, se um aceite anterior for revertido).

Só se aceita quem já é pessoa da base; pessoa privada nunca aparece. A sugestão é identificada
no CSV por uma chave estável ("casa:id_externo|página|nome normalizado"), e a pessoa pela
chave de um de seus vínculos (como em atos_revisados.csv), não pelo `pessoa.id`.
"""

import csv
import hashlib
from datetime import date
from pathlib import Path

from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Candidatura, Cpi, CpiIndiciamentoSugestao, Evento, MandatoLocal, Pessoa
from ingestion.comum import chave_nome
from ingestion.diarios.revisao import (
    _publicavel,
    _vinculos_da_pessoa,
    chave_da_pessoa,
    pessoa_da_chave,
)

INDICIAMENTOS_REVISADOS = (
    Path(__file__).resolve().parents[3] / "data" / "indiciamentos_revisados.csv"
)
COLUNAS = ["chave", "pessoa_chave", "decisao", "revisado_por", "revisado_em", "observacao"]
FONTE_EVENTO = "cpi_indiciamentos"
TIPO_EVENTO = "cpi_indiciamento"
MAX_CANDIDATOS = 8
CASA = {"camara": "Câmara dos Deputados", "senado": "Senado Federal", "congresso": "Congresso"}


def chave_da_sugestao(cpi: Cpi, s: CpiIndiciamentoSugestao) -> str:
    return f"{cpi.casa}:{cpi.id_externo}|{s.pagina or 0}|{chave_nome(s.nome_citado)}"


def decisoes(caminho: Path | None = None) -> list[dict[str, str]]:
    caminho = caminho or INDICIAMENTOS_REVISADOS
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [
            {k: (v or "").strip() for k, v in linha.items()}
            for linha in csv.DictReader(arquivo)
            if (linha.get("decisao") or "").strip() in ("aceito", "recusado")
        ]


def _descricao_da_pessoa(session: Session, pessoa_id: int) -> str:
    """Cargo e UF para o revisor distinguir homônimos."""
    for v in _vinculos_da_pessoa(session, pessoa_id):
        if v.fonte == "candidatura":
            ano, _, sq = v.id_externo.partition(":")
            c = session.scalar(
                select(Candidatura).where(
                    Candidatura.ano_eleicao == int(ano), Candidatura.sq_candidato == sq
                )
            )
            if c:
                return f"{c.cargo.lower()} ({ano}), {c.partido or 'sem partido'}, {c.uf}"
        elif v.fonte == "mandato_local":
            casa, uf, _ibge, id_ext = v.id_externo.split(":", 3)
            m = session.scalar(
                select(MandatoLocal).where(
                    MandatoLocal.casa == casa,
                    MandatoLocal.uf == uf,
                    MandatoLocal.id_externo == id_ext,
                )
            )
            if m:
                return f"mandato local ({casa}), {m.partido or 'sem partido'}, {uf}"
        elif v.fonte == "parlamentar":
            return f"parlamentar ({v.id_externo.partition(':')[0]})"
    return "sem cargo identificado"


def candidatos(session: Session, nome: str) -> list[dict]:
    """Pessoas da base com o mesmo nome normalizado; sem nenhuma, as que têm todas as
    palavras do nome (o PDF às vezes abrevia ou parte palavras)."""
    chave = chave_nome(nome)
    achadas = list(session.scalars(select(Pessoa).where(Pessoa.chave_nome == chave)))
    if not achadas:
        palavras = [p for p in chave.split() if len(p) > 2]
        if len(palavras) >= 2:
            achadas = list(
                session.scalars(
                    select(Pessoa)
                    .where(and_(*[Pessoa.chave_nome.like(f"%{p}%") for p in palavras]))
                    .order_by(Pessoa.id)
                    .limit(MAX_CANDIDATOS)
                )
            )
    resultado = []
    for p in achadas[:MAX_CANDIDATOS]:
        chave_p = chave_da_pessoa(session, p.id)
        if chave_p is not None:
            resultado.append(
                {
                    "pessoa_chave": chave_p,
                    "nome": p.nome,
                    "descricao": _descricao_da_pessoa(session, p.id),
                }
            )
    return resultado


def pendentes(session: Session, caminho: Path | None = None) -> list[dict]:
    """Sugestões ainda não decididas no CSV (pessoa jurídica fica de fora), com a CPI, o
    trecho, a página, o link do PDF e os candidatos a pessoa da base."""
    decididas = {d["chave"] for d in decisoes(caminho)}
    consulta = (
        select(CpiIndiciamentoSugestao, Cpi)
        .join(Cpi, Cpi.id == CpiIndiciamentoSugestao.cpi_id)
        .where(CpiIndiciamentoSugestao.pessoa_juridica.is_(False))
        .order_by(Cpi.id, CpiIndiciamentoSugestao.pagina, CpiIndiciamentoSugestao.id)
    )
    resultado = []
    for s, cpi in session.execute(consulta):
        chave = chave_da_sugestao(cpi, s)
        if chave in decididas:
            continue
        resultado.append(
            {
                "chave": chave,
                "cpi": cpi.nome,
                "casa": CASA.get(cpi.casa, cpi.casa),
                "data_relatorio": cpi.data_fim.isoformat() if cpi.data_fim else "",
                "nome_citado": s.nome_citado,
                "trecho": s.trecho,
                "pagina": s.pagina,
                "url": s.url,
                "candidatos": candidatos(session, s.nome_citado),
            }
        )
    return resultado


def gravar_decisao(
    item: dict,
    decisao: str,
    revisor: str,
    pessoa_chave: str = "",
    observacao: str = "",
    caminho: Path | None = None,
) -> None:
    caminho = caminho or INDICIAMENTOS_REVISADOS
    novo = not caminho.exists()
    with caminho.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        if novo:
            escritor.writeheader()
        escritor.writerow(
            {"chave": item["chave"], "pessoa_chave": pessoa_chave if decisao == "aceito" else "",
             "decisao": decisao, "revisado_por": revisor, "revisado_em": date.today().isoformat(),
             "observacao": observacao}
        )  # fmt: skip


def id_do_evento(pessoa_chave: str, chave: str) -> str:
    """Determinístico: o mesmo pedido aceito para a mesma pessoa dá sempre o mesmo id."""
    return hashlib.sha1(f"{pessoa_chave}|{chave}".encode()).hexdigest()[:24]


def _descricao_evento(cpi: Cpi) -> str:
    return (
        f"Relatório final da {cpi.nome} ({CASA.get(cpi.casa, cpi.casa)}), adotado pela "
        "comissão, propõe o indiciamento desta pessoa. Pedido de indiciamento de CPI é "
        "proposta da comissão: não é acusação formal nem condenação, e cabe ao Ministério "
        "Público decidir se denuncia."
    )


def aplicar_indiciamentos(session: Session, caminho: Path | None = None) -> dict[str, int]:
    """Reaplica as decisões do CSV (a última de cada sugestão vale). Decisão que não encontra
    mais a pessoa ou a sugestão é ignorada. Idempotente."""
    contagem = {"aceitos": 0, "recusados": 0}
    todas = decisoes(caminho)
    if not todas:
        return contagem
    ultimas = {d["chave"]: d for d in todas}
    antigos: dict[str, set[str]] = {}  # ids de eventos de aceites (inclusive anteriores)
    for d in todas:
        if d["decisao"] == "aceito" and d["pessoa_chave"]:
            antigos.setdefault(d["chave"], set()).add(id_do_evento(d["pessoa_chave"], d["chave"]))
    sugestoes = {
        chave_da_sugestao(cpi, s): (s, cpi)
        for s, cpi in session.execute(
            select(CpiIndiciamentoSugestao, Cpi).join(Cpi, Cpi.id == CpiIndiciamentoSugestao.cpi_id)
        )
    }
    for chave, d in ultimas.items():
        aceito = d["decisao"] == "aceito" and bool(d["pessoa_chave"])
        vigente = id_do_evento(d["pessoa_chave"], chave) if aceito else None
        obsoletos = antigos.get(chave, set()) - {vigente}
        if obsoletos:
            session.execute(
                delete(Evento).where(
                    Evento.fonte == FONTE_EVENTO,
                    Evento.tipo == TIPO_EVENTO,
                    Evento.id_externo.in_(obsoletos),
                )
            )
        achada = sugestoes.get(chave)
        if achada is None:
            continue
        sugestao, cpi = achada
        if not aceito:
            if d["decisao"] == "recusado":
                sugestao.revisado = True
                contagem["recusados"] += 1
            continue
        pessoa_id = pessoa_da_chave(session, d["pessoa_chave"])
        if pessoa_id is None:
            continue
        publicavel = next(
            (v for v in _vinculos_da_pessoa(session, pessoa_id) if _publicavel(v)), None
        )
        if publicavel is None:
            continue  # sem vínculo publicável o evento não apareceria
        sugestao.revisado = True
        valores = {
            "pessoa_id": pessoa_id,
            "vinculo_id": publicavel.id,
            "data": cpi.data_fim,
            "tipo": TIPO_EVENTO,
            "descricao": _descricao_evento(cpi),
            "orgao": cpi.nome[:120],
            "fonte": FONTE_EVENTO,
            "id_externo": vigente,
            "fonte_url": sugestao.url,
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
