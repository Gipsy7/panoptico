"""Representações no Conselho de Ética da Câmara (proposições do tipo REP), como eventos
da linha do tempo do deputado representado.

O representado vem na ementa pelo nome parlamentar, em maiúsculas ("Representação em
desfavor do Senhor Deputado ZÉ TROVÃO por suposto procedimento incompatível com o decoro
parlamentar"). O nome parlamentar é atribuído pela Câmara e único entre os deputados, por
isso a ligação pelo nome parlamentar exato e único, dentro do cadastro da Câmara, é forte
(regra "nome_parlamentar"). Ementa sem nome reconhecível fica de fora (contada).

A ementa é o texto oficial e vai como está, entre aspas; a situação é a da Câmara.
"""

import argparse
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import Candidatura, Evento, FonteIngestao, Parlamentar, PessoaVinculo
from ingestion import comum

FONTE = "camara_etica"
URL_LISTA = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
URL_DETALHE = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}"
URL_FICHA = "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id}"
PAUSA = 0.3
# O trecho depois de "Deputado(a)(s)" até a primeira parte que já não é nome
# ("protocolizada", "por suposto", "em razão", fim da frase). Pode ser uma lista:
# "Deputadas CÉLIA NUNES CORREA, ÉRIKA JUCÁ KOKAY e FERNANDA MELCHIONNA".
TRECHO = re.compile(
    r"Deputad[oa]s?\s+(.+?)(?:,?\s+(?:protocolizad|por\s|em\s+raz|pela\s|para\s|que\s|"
    r"imputa|alega)|\.\s|\.$|$)",
    re.I,
)


def nomes_na_ementa(ementa: str) -> list[str]:
    nomes = []
    for trecho in TRECHO.findall(" ".join((ementa or "").split())):
        for nome in re.split(r",\s*|\s+e\s+", trecho, flags=re.I):
            nome = nome.strip(" .,;'-")
            if len(nome) > 2 and nome not in nomes:
                nomes.append(nome)
    return nomes


def _data(valor: str | None) -> date | None:
    try:
        return datetime.fromisoformat((valor or "")[:16]).date()
    except ValueError:
        return None


def situacao(status: dict | None) -> str | None:
    if not status:
        return None
    partes = [status.get("descricaoSituacao") or ""]
    andamento = status.get("descricaoTramitacao")
    quando = _data(status.get("dataHora"))
    if andamento:
        partes.append(f"último andamento{f' em {quando:%d/%m/%Y}' if quando else ''}: {andamento}")
    return "; ".join(p for p in partes if p)[:80] or None


def eventos(
    representacoes: list[dict], deputados: dict[str, int]
) -> tuple[list[dict[str, Any]], int]:
    """(linhas, sem ligação). `deputados`: chave do nome -> pessoa (só nomes únicos)."""
    linhas, sem = [], 0
    for r in representacoes:
        ligados = {deputados.get(comum.chave_nome(n)) for n in nomes_na_ementa(r["ementa"])}
        ligados.discard(None)
        if not ligados:
            sem += 1
            continue
        for pessoa in sorted(ligados):
            linhas.append(
                {
                    "pessoa_id": pessoa,
                    "id_externo": f"{r['id']}:{pessoa}",
                    "data": _data(r.get("dataApresentacao")),
                    "tipo": "conselho_etica",
                    "descricao": (
                        f"Representação nº {r['numero']}/{r['ano']} no Conselho de Ética da "
                        f'Câmara: "{" ".join(r["ementa"].split())}"'
                    ),
                    "orgao": "Câmara dos Deputados – Conselho de Ética",
                    "numero_processo": f"REP {r['numero']}/{r['ano']}",
                    "situacao": situacao(r.get("statusProposicao")),
                    "fonte_url": URL_FICHA.format(id=r["id"]),
                }
            )
    return linhas, sem


def deputados_por_nome(session: Session) -> dict[str, int]:
    """Nome -> pessoa, num conjunto fechado: o nome parlamentar dos deputados no cadastro
    da Câmara e, entre os deputados federais eleitos (quem já saiu do mandato não está mais
    no cadastro), o nome de urna e o nome civil. Nome que aponta para mais de uma pessoa
    fica de fora."""
    pessoa_do_registro = dict(
        session.execute(
            select(PessoaVinculo.fonte + ":" + PessoaVinculo.id_externo, PessoaVinculo.pessoa_id)
            .where(PessoaVinculo.fonte.in_(("parlamentar", "candidatura")))
        ).all()
    )  # fmt: skip
    candidatos: dict[str, set[int]] = {}

    def anotar(nome: str | None, registro: str) -> None:
        pessoa = pessoa_do_registro.get(registro)
        if nome and pessoa:
            candidatos.setdefault(comum.chave_nome(nome), set()).add(pessoa)

    for id_externo, nome, civil in session.execute(
        select(Parlamentar.id_externo, Parlamentar.nome_parlamentar, Parlamentar.nome_civil).where(
            Parlamentar.casa == "camara"
        )
    ):
        anotar(nome, f"parlamentar:camara:{id_externo}")
        anotar(civil, f"parlamentar:camara:{id_externo}")
    for ano, sq, urna, civil in session.execute(
        select(Candidatura.ano_eleicao, Candidatura.sq_candidato, Candidatura.nome_urna,
               Candidatura.nome)
        .where(Candidatura.cargo == "DEPUTADO FEDERAL",
               Candidatura.situacao_turno.like("ELEITO%"))
    ):  # fmt: skip
        anotar(urna, f"candidatura:{ano}:{sq}")
        anotar(civil, f"candidatura:{ano}:{sq}")
    return {nome: next(iter(p)) for nome, p in candidatos.items() if len(p) == 1}


def gravar(session: Session, representacoes: list[dict], ingestao_id: int | None) -> int:
    linhas, sem = eventos(representacoes, deputados_por_nome(session))
    session.execute(delete(PessoaVinculo).where(PessoaVinculo.fonte == FONTE))
    for linha in linhas:
        vinculo_id = session.scalar(
            insert(PessoaVinculo)
            .values(pessoa_id=linha["pessoa_id"], fonte=FONTE, id_externo=linha["id_externo"],
                    regra="nome_parlamentar")
            .returning(PessoaVinculo.id)
        )  # fmt: skip
        session.execute(
            insert(Evento).values(
                **linha, vinculo_id=vinculo_id, fonte=FONTE, ingestao_id=ingestao_id
            )
        )
    print(f"  {len(representacoes)} representações; {len(linhas)} ligações; {sem} sem deputado")
    return len(linhas)


def baixar(client: httpx.Client, anos: list[int]) -> list[dict]:
    representacoes = []
    for ano in anos:
        pagina = 1
        while True:
            time.sleep(PAUSA)
            dados = comum.get_json(
                client,
                URL_LISTA,
                params={"siglaTipo": "REP", "ano": ano, "itens": 100, "pagina": pagina},
            )
            for item in dados["dados"]:
                time.sleep(PAUSA)
                representacoes.append(
                    comum.get_json(client, URL_DETALHE.format(id=item["id"]))["dados"]
                )
            if not any(link.get("rel") == "next" for link in dados.get("links", [])):
                break
            pagina += 1
    return representacoes


def executar(de_raw: Path | None = None, anos: list[int] | None = None) -> int:
    anos = anos or list(range(2023, date.today().year + 1))

    def carregar(session: Session, payload: list, ingestao: FonteIngestao) -> int:
        return gravar(session, payload, ingestao.id)

    return comum.executar_ingestao(
        FONTE, URL_LISTA + "?siglaTipo=REP", lambda c: baixar(c, anos), carregar, de_raw=de_raw
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument(
        "--ano", type=int, nargs="*", help="Anos de apresentação (padrão: desde 2023)"
    )
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(args.de_raw, args.ano)} representações ligadas")
