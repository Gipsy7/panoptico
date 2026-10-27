"""Parte comum da ingestão de emendas estaduais: um adaptador por fonte, uma carga igual.

Cada adaptador (`sc.py`, `mg.py`, ...) só sabe baixar e ler a sua fonte; daqui saem a ligação
do município (código IBGE ou nome dentro da UF), a ligação do autor à pessoa (só nome idêntico
e único entre os deputados estaduais da UF) e a gravação em `emenda_estadual`, apagando e
reinserindo a UF inteira numa transação (a fonte muda retroativamente).

O adaptador é um módulo com:
- `UF`, `FONTE`, `URL` (a da carga), `PAGINA` (a que o cidadão abre), `FONTE_NOME`, `CASA`,
  `RECORTE`, `TERMOS`, `MINIMO` (menos linhas que isso é falha da fonte);
- `VERSAO` (opcional): suba quando a leitura mudar, para a carga incremental reler o
  arquivo mesmo igual;
- `SITUACOES_FORA`: começos de `situacao_proposta` cujo valor previsto não conta (emenda
  cancelada, reprovada, recusada);
- `baixar(client) -> bytes` (bruto como veio; vários arquivos num zip, ver `empacotar`) e
  `normalizar(bruto) -> list[dict]` (puro, testável) com as chaves de `CAMPOS`.
"""

import argparse
import difflib
import io
import re
import zipfile
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import ModuleType
from typing import Any

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.models import (
    Candidatura,
    EmendaEstadual,
    FonteIngestao,
    MandatoLocal,
    Municipio,
    PessoaVinculo,
)
from app.models.pessoa import REGRAS_FORTES
from ingestion import comum
from ingestion.ibge import nomes_anteriores

LOTE = 2000
# Chaves que o adaptador entrega em cada linha (as demais colunas a carga preenche).
CAMPOS = (
    "ano", "codigo", "proposta", "transferencia", "tipo", "autor_nome", "municipio_nome",
    "municipio_ibge", "favorecido_nome", "favorecido_cnpj", "favorecido_natureza", "orgao",
    "instrumento", "objeto", "situacao_proposta", "situacao_transferencia", "valor_previsto",
    "valor_empenhado", "valor_pago",
)  # fmt: skip
# Autores coletivos (bancada, bloco, comissão, mesa): ficam sem pessoa e fora da média.
COLETIVO = re.compile(r"^(BANCADA|BLOCO|COMISSAO|FRENTE|LIDERANCA|MESA|LIDER)\b")
APELIDO = re.compile(r"\(\s*([^)]*?)\s*\)")
TRATAMENTO = re.compile(r"^(DEPUTAD[OA]S?|DEP|DEPS?)\s+(ESTADUAL\s+)?")
CNPJ_TEXTO = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")
CPF_TEXTO = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
SEM_MUNICIPIO = "Não informado pela fonte"


# --------------------------------------------------------------------------- leitura


def valor(texto: Any) -> Decimal | None:
    """'1.234,56', '1234,56', '1234.56', ' 200.000 ', 'R$ 1.000,00', 1234.5 -> Decimal.
    Vazio ou ilegível: None. Ponto sem vírgula com três casas depois é milhar ('200.000')."""
    if texto is None:
        return None
    if isinstance(texto, (int, float, Decimal)):
        return Decimal(str(texto))
    t = re.sub(r"[R$\s\xa0]", "", str(texto))
    if not t or t.lower() in {"-", "none", "null", "nan"}:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def texto(x: Any) -> str | None:
    t = " ".join(str(x if x is not None else "").replace("\xa0", " ").split())
    return t or None


def so_digitos(x: Any) -> str:
    return re.sub(r"\D", "", str(x or ""))


def cnpj(x: Any) -> str | None:
    """CNPJ só com dígitos (14), ou None. CPF (11 dígitos) nunca passa (coleta mínima)."""
    d = so_digitos(x)
    return d if len(d) == 14 else None


def sem_cpf(nome: str | None) -> str | None:
    """Texto livre sem número de CPF (alguns objetos e históricos trazem)."""
    return CPF_TEXTO.sub("[CPF omitido]", nome) if nome else nome


def empacotar(arquivos: dict[str, bytes]) -> bytes:
    """Vários arquivos num zip só (o bruto da carga). Datas fixas nas entradas, para o mesmo
    conteúdo dar o mesmo sha256 (carga incremental)."""
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in sorted(arquivos.items()):
            z.writestr(zipfile.ZipInfo(nome, (2000, 1, 1, 0, 0, 0)), conteudo)
    return saida.getvalue()


def desempacotar(pacote: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(pacote)) as z:
        return {n: z.read(n) for n in z.namelist()}


# --------------------------------------------------------------------------- autor


def coletivo(autor: str | None) -> bool:
    return bool(COLETIVO.match(comum.chave_nome(autor)))


def nomes_do_autor(autor: str | None) -> list[str]:
    """Chaves de nome do autor, na ordem de tentativa: o nome sem tratamento ('Dep. ',
    'Deputado ') nem apelido entre parênteses e, se houver, o apelido
    ('MARCOS JOSÉ ABREU ( MARQUITO)')."""
    apelido = APELIDO.search(autor or "")
    base = TRATAMENTO.sub("", comum.chave_nome(APELIDO.sub(" ", autor or "")))
    chaves = [base]
    if apelido:
        chaves.append(TRATAMENTO.sub("", comum.chave_nome(apelido.group(1))))
    return [c for c in dict.fromkeys(chaves) if c]


def mapa_pessoas(session: Session, uf: str) -> dict[str, set[int]]:
    """Chave de nome -> pessoas publicáveis com esse nome entre os deputados estaduais (ou
    distritais) da UF: eleitos pelo TSE (nome civil e de urna) e os que a Casa lista."""
    publicavel = PessoaVinculo.regra.in_(REGRAS_FORTES) | PessoaVinculo.revisado.is_(True)
    eleitos = session.execute(
        select(Candidatura.nome, Candidatura.nome_urna, PessoaVinculo.pessoa_id)
        .join(
            PessoaVinculo,
            (PessoaVinculo.fonte == "candidatura")
            & (
                PessoaVinculo.id_externo
                == func.concat(Candidatura.ano_eleicao, ":", Candidatura.sq_candidato)
            ),
        )
        .where(
            Candidatura.cargo.in_(("DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL")),
            Candidatura.uf == uf,
            Candidatura.situacao_turno.like("ELEITO%"),
            publicavel,
        )
    ).all()
    no_cargo = session.execute(
        select(MandatoLocal.nome, MandatoLocal.nome_completo, PessoaVinculo.pessoa_id)
        .join(
            PessoaVinculo,
            (PessoaVinculo.fonte == "mandato_local")
            & (
                PessoaVinculo.id_externo
                == func.concat(
                    MandatoLocal.casa, ":", MandatoLocal.uf, "::", MandatoLocal.id_externo
                )
            ),
        )
        .where(MandatoLocal.casa == "assembleia", MandatoLocal.uf == uf, publicavel)
    ).all()
    por_nome: dict[str, set[int]] = {}
    for nome, outro, pessoa_id in [*eleitos, *no_cargo]:
        for chave in {comum.chave_nome(nome), comum.chave_nome(outro)} - {""}:
            por_nome.setdefault(chave, set()).add(pessoa_id)
    return por_nome


def vincular_pessoa(autor: str, por_nome: dict[str, set[int]]) -> int | None:
    """Pessoa do autor por nome idêntico e único na Casa; coletivos e ambíguos: None."""
    if coletivo(autor):
        return None
    for chave in nomes_do_autor(autor):
        candidatos = por_nome.get(chave, set())
        if len(candidatos) == 1:
            return next(iter(candidatos))
    return None


# --------------------------------------------------------------------------- município


def resolver_municipios(
    uf: str, linhas: list[dict[str, Any]], municipios: list[tuple[str, str]]
) -> dict[tuple[str | None, str], str | None]:
    """(código como veio, nome como veio) -> código IBGE de 7 dígitos dentro da UF.

    Código de 7 dígitos que existe vale; de 6 (sem o dígito verificador, como no ES) vale se
    só um município da UF começa com ele. Sem código: nome igual sem acento, nome anterior do
    IBGE e, por último, a grafia mais próxima (corte 0,88, como nas federais)."""
    por_chave = {chave: ibge for ibge, chave in municipios}
    codigos = {ibge for ibge, _ in municipios}
    apelidos = nomes_anteriores.carregar_apelidos()
    saida: dict[tuple[str | None, str], str | None] = {}
    for codigo, nome in {(x.get("municipio_ibge"), x["municipio_nome"]) for x in linhas}:
        ibge = None
        d = so_digitos(codigo)
        if len(d) == 7 and d in codigos:
            ibge = d
        elif len(d) == 6:
            achados = [c for c in codigos if c.startswith(d)]
            ibge = achados[0] if len(achados) == 1 else None
        if ibge is None and nome and nome != SEM_MUNICIPIO:
            chave = comum.chave_nome(nome)
            ibge = por_chave.get(chave) or apelidos.get((uf, chave))
            if ibge is None and chave:
                proximo = difflib.get_close_matches(chave, list(por_chave), n=1, cutoff=0.88)
                ibge = por_chave[proximo[0]] if proximo else None
        saida[(codigo, nome)] = ibge
    return saida


# --------------------------------------------------------------------------- carga


def _limites() -> dict[str, int]:
    """Tamanho das colunas de texto, para cortar o que a fonte manda maior."""
    return {
        c.name: c.type.length
        for c in EmendaEstadual.__table__.columns
        if getattr(c.type, "length", None)
    }


def gravar(
    session: Session,
    adaptador: ModuleType,
    linhas: list[dict[str, Any]],
    ingestao: FonteIngestao,
) -> int:
    """Liga município e autor e regrava a UF inteira. Aborta se vier pouco (falha da fonte)
    ou se a chave da linha (proposta) se repetir."""
    uf = adaptador.UF
    if len(linhas) < adaptador.MINIMO:
        raise ValueError(f"Só {len(linhas)} emendas em {adaptador.FONTE}; abortando.")
    chaves = [x["proposta"] for x in linhas]
    if len(set(chaves)) != len(chaves):
        repetidas = sorted({c for c in chaves if chaves.count(c) > 1})[:5]
        raise ValueError(f"{adaptador.FONTE}: chave de linha repetida ({repetidas}).")
    municipios = session.execute(
        select(Municipio.ibge, Municipio.nome_chave).where(Municipio.uf == uf)
    ).all()
    ibge = resolver_municipios(uf, linhas, [tuple(m) for m in municipios])
    por_nome = mapa_pessoas(session, uf)
    pessoas = {a: vincular_pessoa(a, por_nome) for a in {x["autor_nome"] for x in linhas}}
    limites = _limites()
    for coluna in ("proposta", "codigo"):  # chaves não se cortam
        longas = [x[coluna] for x in linhas if len(x[coluna] or "") > limites[coluna]]
        if longas or any(not x[coluna] for x in linhas):
            raise ValueError(f"{adaptador.FONTE}: {coluna} vazio ou longo demais ({longas[:3]}).")
    registros = []
    for x in linhas:
        r = {c: x.get(c) for c in CAMPOS}
        r["uf"] = uf
        r["tipo"] = r["tipo"] or ("bancada" if coletivo(r["autor_nome"]) else "individual")
        r["autor_chave"] = comum.chave_nome(r["autor_nome"])
        r["municipio_nome"] = r["municipio_nome"] or SEM_MUNICIPIO
        r["municipio_ibge"] = ibge.get((x.get("municipio_ibge"), x["municipio_nome"]))
        r["pessoa_id"] = pessoas[x["autor_nome"]] if r["tipo"] == "individual" else None
        r["valor_previsto"] = r["valor_previsto"] or Decimal(0)
        r["valor_pago"] = r["valor_pago"] or Decimal(0)
        r["fonte"] = adaptador.FONTE
        r["ingestao_id"] = ingestao.id
        for coluna, tamanho in limites.items():
            if (
                coluna not in ("proposta", "codigo")
                and isinstance(r.get(coluna), str)
                and len(r[coluna]) > tamanho
            ):
                r[coluna] = r[coluna][: tamanho - 1] + "…"
        registros.append(r)
    session.execute(delete(EmendaEstadual).where(EmendaEstadual.uf == uf))
    for i in range(0, len(registros), LOTE):
        session.execute(insert(EmendaEstadual), registros[i : i + LOTE])
    individuais = {x["autor_nome"] for x in registros if x["tipo"] == "individual"}
    ligados = {a for a in individuais if pessoas[a]}
    sem_municipio = {x["municipio_nome"] for x in registros if not x["municipio_ibge"]}
    print(
        f"{adaptador.FONTE}: {len(registros)} linhas, "
        f"{len({x['codigo'] for x in registros})} emendas; autores individuais ligados a "
        f"pessoa: {len(ligados)} de {len(individuais)}; sem pessoa: "
        f"{sorted(individuais - ligados)[:20]}; linhas sem município: "
        f"{sum(1 for x in registros if not x['municipio_ibge'])} "
        f"({sorted(sem_municipio)[:10]})",
        flush=True,
    )
    return len(registros)


def contexto(adaptador: ModuleType) -> Callable[[Session], str]:
    """Religa os autores quando entram pessoas ou mudam os deputados no cargo, e relê o
    arquivo igual quando a leitura do adaptador muda (`VERSAO`)."""
    uf = adaptador.UF
    versao = getattr(adaptador, "VERSAO", 1)

    def _contexto(session: Session) -> str:
        total = session.scalar(
            select(func.count(MandatoLocal.id)).where(
                MandatoLocal.casa == "assembleia", MandatoLocal.uf == uf
            )
        )
        return f"{comum.contexto_pessoas(session)};assembleia_{uf}:{total};v{versao}"

    return _contexto


def executar(adaptador: ModuleType, de_raw: Path | None = None) -> int:
    def carregar(session: Session, bruto: Any, ingestao: FonteIngestao) -> int:
        return gravar(session, adaptador, adaptador.normalizar(bruto), ingestao)

    return comum.executar_ingestao(
        adaptador.FONTE,
        adaptador.URL,
        adaptador.baixar,
        carregar,
        de_raw=de_raw,
        extensao_raw=getattr(adaptador, "EXTENSAO_RAW", ".zip"),
        # As fontes mudam pouco de um dia para o outro: com o mesmo conteúdo (e as mesmas
        # pessoas), não regrava nem acumula bruto.
        incremental=comum.Incremental(chave=adaptador.FONTE, contexto=contexto(adaptador)),
    )


def main(adaptador: ModuleType) -> None:
    parser = argparse.ArgumentParser(description=f"Ingestão: {adaptador.FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    total = executar(adaptador, de_raw=args.de_raw)
    print(f"{adaptador.FONTE}: {total} linhas de emendas estaduais ({adaptador.UF})")
