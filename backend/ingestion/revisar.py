"""Revisão humana dos vínculos por nome aproximado (regra "nome_casa"): o parlamentar da
câmara ou assembleia ligado ao eleito do TSE por um nome parecido, mas não idêntico
("Dr. Valdomiro Lopes" e "Valdomiro Lopes"). Esses vínculos só são publicados depois de
aceitos aqui; a decisão vai para data/vinculos_revisados.csv (versionado) e é reaplicada
a cada carga de pessoas.

Os atos de nomeação e exoneração sugeridos pelos diários oficiais (tabela diario_ato) têm a
mesma revisão, com --tipo diario; a decisão vai para data/atos_revisados.csv. Os pedidos de
indiciamento dos relatórios de CPI (tabela cpi_indiciamento_sugestao) também, com --tipo cpi:
o revisor liga o nome a uma pessoa da base ou recusa; a decisão vai para
data/indiciamentos_revisados.csv.

Uso:
    python -m ingestion.revisar                    # um por um: [a]ceitar, [r]ecusar, [p]ular
    python -m ingestion.revisar --exportar fila.csv  # para revisar numa planilha e depois
                                                     # colar as linhas decididas no CSV
    python -m ingestion.revisar --tipo diario      # atos dos diários (também com --exportar)
    python -m ingestion.revisar --tipo cpi         # indiciamentos sugeridos pelas CPIs
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Candidatura, MandatoLocal, Municipio, PessoaVinculo
from ingestion.congresso.cpi_revisao import INDICIAMENTOS_REVISADOS
from ingestion.congresso.cpi_revisao import gravar_decisao as gravar_indiciamento
from ingestion.congresso.cpi_revisao import pendentes as pendentes_indiciamentos
from ingestion.diarios.revisao import ATOS_REVISADOS
from ingestion.diarios.revisao import gravar_decisao as gravar_ato
from ingestion.diarios.revisao import pendentes as pendentes_atos
from ingestion.pessoas import COLUNAS_REVISAO, REVISOES, revisoes


def pendentes(session) -> list[dict]:
    """Vínculos "nome_casa" ainda não revisados, com os dois lados para comparar."""
    decididos = {(r["fonte"], r["id_externo"]) for r in revisoes()}
    candidaturas = {
        (c.ano_eleicao, c.sq_candidato): c
        for c in session.scalars(
            select(Candidatura).where(Candidatura.situacao_turno.like("ELEITO%"))
        )
    }
    resultado = []
    for v in session.scalars(
        select(PessoaVinculo).where(
            PessoaVinculo.regra == "nome_casa", PessoaVinculo.revisado.is_(False)
        )
    ):
        if (v.fonte, v.id_externo) in decididos:
            continue
        casa, uf, ibge, id_externo = v.id_externo.split(":", 3)
        mandato = session.scalar(
            select(MandatoLocal).where(
                MandatoLocal.casa == casa, MandatoLocal.uf == uf,
                MandatoLocal.id_externo == id_externo,
                (MandatoLocal.municipio_ibge == ibge) if ibge
                else MandatoLocal.municipio_ibge.is_(None),
            )
        )  # fmt: skip
        if mandato is None or mandato.candidatura_id is None:
            continue
        c = next((x for x in candidaturas.values() if x.id == mandato.candidatura_id), None)
        if c is None:
            continue
        cidade = (
            session.scalar(select(Municipio.nome).where(Municipio.ibge == ibge)) if ibge else None
        )
        resultado.append(
            {
                "fonte": v.fonte,
                "id_externo": v.id_externo,
                "ligado_a": f"candidatura:{c.ano_eleicao}:{c.sq_candidato}",
                "casa": f"{'Câmara de ' + cidade if cidade else 'Assembleia'} ({uf})",
                "na_casa": " / ".join(n for n in (mandato.nome, mandato.nome_completo) if n),
                "no_tse": (
                    f"{c.nome_urna} / {c.nome} "
                    f"({c.cargo.lower()}, {c.partido or 'sem partido'}, {c.ano_eleicao})"
                ),
                "partido_na_casa": mandato.partido or "",
                "fonte_casa": mandato.sapl_url,
            }
        )
    return resultado


def gravar_decisao(item: dict, decisao: str, revisor: str, observacao: str = "") -> None:
    novo = not REVISOES.exists()
    with REVISOES.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_REVISAO)
        if novo:
            escritor.writeheader()
        escritor.writerow(
            {"fonte": item["fonte"], "id_externo": item["id_externo"], "ligado_a": item["ligado_a"],
             "decisao": decisao, "revisado_por": revisor, "revisado_em": date.today().isoformat(),
             "observacao": observacao}
        )  # fmt: skip


def _exportar(fila: list[dict], destino: Path, onde: Path) -> None:
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo, fieldnames=[*fila[0].keys(), "decisao"] if fila else ["decisao"]
        )
        escritor.writeheader()
        escritor.writerows(fila)
    print(f"Fila em {destino}. Preencha 'decisao' (aceito/recusado) e copie as linhas "
          f"decididas para {onde}.", file=sys.stderr)  # fmt: skip


def _revisar_vinculos(fila: list[dict], revisor: str) -> None:
    for i, item in enumerate(fila, start=1):
        print(f"\n[{i}/{len(fila)}] {item['casa']}")
        print(f"  na casa: {item['na_casa']}  {item['partido_na_casa']}")
        print(f"  no TSE:  {item['no_tse']}")
        print(f"  fonte:   {item['fonte_casa']}")
        resposta = (
            input("  É a mesma pessoa? [a]ceitar, [r]ecusar, [p]ular, [s]air: ").strip().lower()
        )
        if resposta == "s":
            break
        if resposta in ("a", "r"):
            gravar_decisao(item, "aceito" if resposta == "a" else "recusado", revisor)


def _revisar_diarios(fila: list[dict], revisor: str) -> None:
    for i, item in enumerate(fila, start=1):
        print(f"\n[{i}/{len(fila)}] {item['pessoa']}, {item['cargo']} em {item['municipio']}")
        print(f"  {item['data']}  ato: {item['tipo_ato']}")
        print(f"  trecho:  {item['trecho']}")
        print(f"  diário:  {item['url']}")
        resposta = (
            input("  O ato é desta pessoa? [a]ceitar, [r]ecusar, [p]ular, [s]air: ").strip().lower()
        )
        if resposta == "s":
            break
        if resposta in ("a", "r"):
            gravar_ato(item, "aceito" if resposta == "a" else "recusado", revisor)


def _candidatos_em_texto(candidatos: list[dict]) -> str:
    return " | ".join(f"{c['pessoa_chave']} = {c['nome']}, {c['descricao']}" for c in candidatos)


def _revisar_cpis(fila: list[dict], revisor: str) -> None:
    for i, item in enumerate(fila, start=1):
        encerrada = item["data_relatorio"] or "data não informada"
        print(f"\n[{i}/{len(fila)}] {item['cpi']} ({item['casa']}, encerrada em {encerrada})")
        print(f"  nome no PDF: {item['nome_citado']}  (página {item['pagina']})")
        print(f"  trecho: {item['trecho']}")
        print(f"  PDF:    {item['url']}")
        candidatos = item["candidatos"]
        for n, c in enumerate(candidatos, start=1):
            print(f"  [{n}] {c['nome']}: {c['descricao']}")
        if not candidatos:
            print("  (nenhuma pessoa da base com esse nome)")
        pergunta = (
            "  Número da pessoa (aceitar), [n] não é pessoa da base (recusar), [p]ular, [s]air: "
        )
        resposta = input(pergunta).strip().lower()
        if resposta == "s":
            break
        if resposta == "n":
            gravar_indiciamento(item, "recusado", revisor)
        elif resposta.isdigit() and 1 <= int(resposta) <= len(candidatos):
            escolhida = candidatos[int(resposta) - 1]
            gravar_indiciamento(item, "aceito", revisor, pessoa_chave=escolhida["pessoa_chave"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Revisão humana de vínculos e de atos")
    parser.add_argument(
        "--tipo", choices=["vinculo", "diario", "cpi"], default="vinculo",
        help="vinculo: nomes aproximados (padrão); diario: atos de nomeação/exoneração "
        "sugeridos pelos diários oficiais; cpi: pedidos de indiciamento dos relatórios de CPI",
    )  # fmt: skip
    parser.add_argument("--exportar", type=Path, help="Grava a fila num CSV, sem perguntar")
    parser.add_argument("--revisor", default="", help="Quem está revisando (vai no CSV)")
    args = parser.parse_args(argv)
    diario, cpi = args.tipo == "diario", args.tipo == "cpi"
    busca = pendentes_indiciamentos if cpi else pendentes_atos if diario else pendentes
    with SessionLocal() as session:
        fila = busca(session)
    destino = INDICIAMENTOS_REVISADOS if cpi else ATOS_REVISADOS if diario else REVISOES
    rotulo = (
        "pedidos de indiciamento de CPI"
        if cpi
        else "atos de diários oficiais"
        if diario
        else "vínculos por nome aproximado"
    )
    print(f"{len(fila)} {rotulo} esperando revisão", file=sys.stderr)
    if args.exportar:
        if cpi:  # a lista de candidatos vira texto numa coluna
            fila = [{**f, "candidatos": _candidatos_em_texto(f["candidatos"])} for f in fila]
        _exportar(fila, args.exportar, destino)
        return 0
    revisor = args.revisor or input("Seu nome (vai no CSV): ").strip()
    (_revisar_cpis if cpi else _revisar_diarios if diario else _revisar_vinculos)(fila, revisor)
    proxima = "a próxima carga de pessoas (python -m ingestion.pessoas)"
    print(f"\nDecisões em {destino}. Valem na {proxima}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
