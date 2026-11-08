"""Resultado completo das eleições (Frente 5): votos de todos os candidatos e comparecimento.

Duas cargas por ano, cada uma numa transação:

- `tse_comparecimento` (detalhe_votacao_munzona, ~5 MB): aptos, comparecimento, abstenções,
  brancos, nulos e válidos por cargo, município e turno, somados das zonas -> `resultado_totais`.
- `tse_resultados` (votacao_candidato_munzona, até ~580 MB): votos de cada candidato somados das
  zonas -> `resultado_candidato`. Na disputa inteira, todos os candidatos; nas eleições gerais,
  também o recorte por município (presidente, governador e senador: todos; deputados: os 10
  mais votados ali) e, em `resultado_totais.votos_em_eleitos`, quantos votos daqui foram para
  quem se elegeu. Rode o comparecimento antes (o resultado preenche essa coluna nele).

O arquivo de votação é lido em fluxo, um CSV por UF de cada vez (o recorte por município de
deputado é resolvido e descartado ao fim de cada UF, para caber na memória da VPS). O arquivo
"_BRASIL" repete os estados e fica de fora. Votos do exterior (UF "ZZ") contam na disputa de
presidente, mas não têm município: os totais deles ficam numa linha só, município "0000000".
Ver docs/DECISOES.md, "Eleições completas".
"""

import argparse
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import bindparam, delete, insert, update
from sqlalchemy.orm import Session

from app.models import FonteIngestao, ResultadoCandidato, ResultadoTotais
from ingestion import comum
from ingestion.tse import comum_tse
from ingestion.tse.candidaturas import mapa_municipios, situacao_final

FONTE = "tse_resultados"
FONTE_TOTAIS = "tse_comparecimento"
URL = f"{comum_tse.BASE}/votacao_candidato_munzona/votacao_candidato_munzona_{{ano}}.zip"
URL_TOTAIS = f"{comum_tse.BASE}/detalhe_votacao_munzona/detalhe_votacao_munzona_{{ano}}.zip"

MAJORITARIOS_GERAIS = {"PRESIDENTE", "GOVERNADOR", "SENADOR"}
PROPORCIONAIS_GERAIS = {"DEPUTADO FEDERAL", "DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL"}
MAIS_VOTADOS = 10
EXTERIOR = "0000000"


def eleicao_geral(ano: int) -> bool:
    """Eleições gerais em 2018, 2022, 2026...; municipais em 2016, 2020, 2024..."""
    return ano % 4 == 2


def inteiro(valor: str | None) -> int:
    valor = (valor or "").strip()
    return int(valor) if valor.lstrip("-").isdigit() and int(valor) > 0 else 0


def cargo_de(linha: dict[str, str]) -> str:
    return (linha.get("DS_CARGO") or "").strip().upper()


def votos_validos(linha: dict[str, str]) -> int:
    return inteiro(linha.get("QT_VOTOS_NOMINAIS_VALIDOS") or linha.get("QT_VOTOS_NOMINAIS"))


def eleito(situacao: str | None) -> bool:
    return bool(situacao) and situacao.startswith("ELEITO")


# --- Comparecimento -------------------------------------------------------------------------

CAMPOS_TOTAIS = {
    "aptos": "QT_APTOS",
    "comparecimento": "QT_COMPARECIMENTO",
    "abstencoes": "QT_ABSTENCOES",
    "brancos": "QT_VOTOS_BRANCOS",
    "nulos": "QT_TOTAL_VOTOS_NULOS",
    "validos": "QT_TOTAL_VOTOS_VALIDOS",
    "nominais": "QT_VOTOS_NOMINAIS_VALIDOS",
}


def somar_totais(linhas: Iterable[dict[str, str]]) -> tuple[dict[tuple, dict[str, int]], dict]:
    """(turno, cargo, UF, código TSE do município) -> campos somados das zonas, e os nomes dos
    municípios ((UF, código) -> nome) para ligar ao IBGE. Exterior: UF "ZZ"."""
    totais: dict[tuple, dict[str, int]] = defaultdict(lambda: dict.fromkeys(CAMPOS_TOTAIS, 0))
    nomes: dict[tuple[str, str], str] = {}
    for linha in linhas:
        uf = linha["SG_UF"].strip()
        codigo = linha["CD_MUNICIPIO"].strip()
        nomes[(uf, codigo)] = linha["NM_MUNICIPIO"].strip()
        chave = (int(linha.get("NR_TURNO") or 1), cargo_de(linha), uf, codigo)
        alvo = totais[chave]
        for campo, coluna in CAMPOS_TOTAIS.items():
            alvo[campo] += inteiro(linha.get(coluna))
    return totais, nomes


# --- Votação por candidato ------------------------------------------------------------------


@dataclass
class Candidato:
    numero: str | None
    nome_urna: str
    partido: str | None
    situacao: dict[int, str | None] = field(default_factory=dict)


@dataclass
class Apuracao:
    """O que a leitura do arquivo de votação produz (antes de ligar os municípios ao IBGE)."""

    candidatos: dict[str, Candidato] = field(default_factory=dict)
    # (turno, cargo, UF da disputa, código TSE do município da disputa ou "") -> sq -> votos
    disputa: dict[tuple, dict[str, int]] = field(default_factory=lambda: defaultdict(dict))
    # (turno, cargo, UF, código TSE do município) -> sq -> votos (recorte, eleições gerais)
    recorte: dict[tuple, dict[str, int]] = field(default_factory=dict)
    # (turno, cargo, UF, código TSE do município) -> votos dados a quem se elegeu (deputados)
    em_eleitos: dict[tuple, int] = field(default_factory=dict)
    nomes: dict[tuple[str, str], str] = field(default_factory=dict)


def blocos_por_arquivo(payload: Any, prefixo: str) -> Iterator[Iterator[dict[str, str]]]:
    """Um bloco de linhas por CSV do zip (um por UF; o "_BRASIL" fica de fora). Não dá para
    agrupar por SG_UF: o arquivo de uma UF traz linhas de presidente de outras (voto em
    trânsito), fora de ordem."""
    with comum_tse.abrir_zip(payload) as z:
        nomes = sorted(
            n.rsplit("/", 1)[-1]
            for n in z.namelist()
            if n.rsplit("/", 1)[-1].startswith(prefixo) and "_BRASIL" not in n
        )
    for nome in nomes:
        yield comum_tse.linhas(payload, nome.removesuffix(".csv"))


def apurar(blocos: Iterable[Iterable[dict[str, str]]], ano: int) -> Apuracao:
    """Soma as zonas, um arquivo (UF) por vez. O recorte de deputado por município vira os 10
    mais votados (e o total dado a eleitos) ao fim de cada arquivo; o de presidente, governador
    e senador soma entre arquivos (há votos em trânsito de uma UF no arquivo de outra)."""
    geral = eleicao_geral(ano)
    ap = Apuracao()
    majoritario: dict[tuple, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for bloco in blocos:
        proporcional: dict[tuple, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for linha in bloco:
            sq = comum_tse.sq_candidato(linha)
            turno = int(linha.get("NR_TURNO") or 1)
            cargo = cargo_de(linha)
            uf = linha["SG_UF"].strip()
            codigo = linha["CD_MUNICIPIO"].strip()
            ap.nomes[(uf, codigo)] = linha["NM_MUNICIPIO"].strip()
            cand = ap.candidatos.get(sq)
            if cand is None:
                cand = ap.candidatos[sq] = Candidato(
                    comum_tse.texto(linha.get("NR_CANDIDATO")),
                    (linha.get("NM_URNA_CANDIDATO") or "").strip(),
                    comum_tse.texto(linha.get("SG_PARTIDO")),
                )
            situacao = situacao_final(linha)
            if situacao or turno not in cand.situacao:
                cand.situacao[turno] = situacao
            votos = votos_validos(linha)
            if geral:
                uf_disputa = "BR" if cargo == "PRESIDENTE" else comum_tse.uf_da_disputa(linha)
                chave_disputa = (turno, cargo, uf_disputa, "")
            else:
                chave_disputa = (turno, cargo, uf, linha["SG_UE"].strip())
            alvo = ap.disputa[chave_disputa]
            alvo[sq] = alvo.get(sq, 0) + votos
            if geral and cargo in MAJORITARIOS_GERAIS:
                majoritario[(turno, cargo, uf, codigo)][sq] += votos
            elif geral and cargo in PROPORCIONAIS_GERAIS:
                proporcional[(turno, cargo, uf, codigo)][sq] += votos
        for chave, votos_mun in proporcional.items():
            turno = chave[0]
            ap.em_eleitos[chave] = ap.em_eleitos.get(chave, 0) + sum(
                v for sq, v in votos_mun.items() if eleito(ap.candidatos[sq].situacao.get(turno))
            )
            mais = sorted(votos_mun.items(), key=lambda kv: (-kv[1], kv[0]))[:MAIS_VOTADOS]
            ap.recorte[chave] = {sq: v for sq, v in mais if v > 0}
    for chave, votos_mun in majoritario.items():
        ap.recorte[chave] = dict(votos_mun)
    return ap


def linhas_candidatos(ap: Apuracao, ano: int, ibge: dict[tuple[str, str], str]) -> list[dict]:
    """Linhas de `resultado_candidato` (sem ingestao_id)."""
    saida = []

    def linha(turno, cargo, abrangencia, uf, mun, sq, votos):
        c = ap.candidatos[sq]
        return {
            "ano": ano,
            "turno": turno,
            "cargo": cargo,
            "abrangencia": abrangencia,
            "uf": uf,
            "municipio_ibge": mun,
            "sq_candidato": sq,
            "numero": c.numero,
            "nome_urna": c.nome_urna[:120],
            "partido": c.partido,
            "votos": votos,
            "situacao": c.situacao.get(turno),
        }

    for (turno, cargo, uf, codigo), votos_sq in ap.disputa.items():
        mun = ibge.get((uf, codigo)) if codigo else None
        if codigo and mun is None:
            continue
        for sq, votos in votos_sq.items():
            saida.append(linha(turno, cargo, "disputa", uf, mun, sq, votos))
    for (turno, cargo, uf, codigo), votos_sq in ap.recorte.items():
        mun = ibge.get((uf, codigo))
        if mun is None:
            continue
        for sq, votos in votos_sq.items():
            saida.append(linha(turno, cargo, "municipio", uf, mun, sq, votos))
    return saida


# --- Cargas ---------------------------------------------------------------------------------


def _ibge(session: Session, nomes: dict[tuple[str, str], str]) -> dict[tuple[str, str], str]:
    registros = [
        {"uf": uf, "codigo_ue": codigo, "unidade": nome}
        for (uf, codigo), nome in nomes.items()
        if uf != "ZZ"
    ]
    mapa = mapa_municipios(session, registros) if registros else {}
    return {k: v for k, v in mapa.items() if v}


def executar_totais(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, URL_TOTAIS.format(ano=ano))

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        totais, nomes = somar_totais(comum_tse.linhas(payload, f"detalhe_votacao_munzona_{ano}_"))
        if not totais:
            raise ValueError(f"Nenhum total de comparecimento em {ano}; abortando.")
        ibge = _ibge(session, nomes)
        agregado: dict[tuple, dict[str, Any]] = {}
        for (turno, cargo, uf, codigo), campos in totais.items():
            mun = EXTERIOR if uf == "ZZ" else ibge.get((uf, codigo))
            if mun is None:
                continue
            chave = (turno, cargo, mun)
            alvo = agregado.setdefault(
                chave,
                {"ano": ano, "turno": turno, "cargo": cargo, "uf": uf, "municipio_ibge": mun}
                | dict.fromkeys(CAMPOS_TOTAIS, 0),
            )
            for campo, valor in campos.items():
                alvo[campo] += valor
        session.execute(delete(ResultadoTotais).where(ResultadoTotais.ano == ano))
        linhas = [r | {"ingestao_id": ingestao.id} for r in agregado.values()]
        for inicio in range(0, len(linhas), 5000):
            session.execute(insert(ResultadoTotais), linhas[inicio : inicio + 5000])
        return len(linhas)

    return comum.executar_ingestao(
        FONTE_TOTAIS,
        URL_TOTAIS.format(ano=ano),
        baixar,
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{ano}_",
        incremental=comum.Incremental(
            chave=URL_TOTAIS.format(ano=ano), sonda=URL_TOTAIS.format(ano=ano)
        ),
    )


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, URL.format(ano=ano))

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        ap = apurar(blocos_por_arquivo(payload, f"votacao_candidato_munzona_{ano}_"), ano)
        if not ap.disputa:
            raise ValueError(f"Nenhum voto encontrado em {ano}; abortando.")
        ibge = _ibge(session, ap.nomes)
        linhas = [r | {"ingestao_id": ingestao.id} for r in linhas_candidatos(ap, ano, ibge)]
        session.execute(delete(ResultadoCandidato).where(ResultadoCandidato.ano == ano))
        for inicio in range(0, len(linhas), 5000):
            session.execute(insert(ResultadoCandidato), linhas[inicio : inicio + 5000])
        em_eleitos = [
            {"t": turno, "c": cargo, "m": ibge[(uf, codigo)], "v": votos}
            for (turno, cargo, uf, codigo), votos in ap.em_eleitos.items()
            if (uf, codigo) in ibge
        ]
        if em_eleitos:
            stmt = (
                update(ResultadoTotais)
                .where(
                    ResultadoTotais.ano == ano,
                    ResultadoTotais.turno == bindparam("t"),
                    ResultadoTotais.cargo == bindparam("c"),
                    ResultadoTotais.municipio_ibge == bindparam("m"),
                )
                .values(votos_em_eleitos=bindparam("v"))
            )
            for inicio in range(0, len(em_eleitos), 5000):
                session.connection().execute(stmt, em_eleitos[inicio : inicio + 5000])
        return len(linhas)

    return comum.executar_ingestao(
        FONTE,
        URL.format(ano=ano),
        baixar,
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{ano}_",
        incremental=comum.Incremental(chave=URL.format(ano=ano), sonda=URL.format(ano=ano)),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE_TOTAIS} e {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=[2022, 2024, 2026])
    parser.add_argument("--so-totais", action="store_true", help="Só o comparecimento")
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE_TOTAIS} {ano}: {executar_totais(ano)} linhas")
        if not args.so_totais:
            print(f"{FONTE} {ano}: {executar(ano)} linhas")
