"""Prestação de contas anual dos partidos (TSE): de onde vem o dinheiro e para onde vai.

O arquivo de cada exercício tem um CSV de receitas e um de despesas por UF, mais o do
diretório nacional (`_BR`) e um `_BRASIL` que junta todos (em 2024: 60 MB compactado, 944 MB
aberto). É lido em fluxo, sem abrir tudo; o `_BRASIL` fica de fora, porque UFs + `_BR` já o
formam (conferido: R$ 8,729 bi de receita e R$ 7,974 bi de despesa nos dois jeitos).

Coleta mínima (docs/DECISOES.md): guardamos só

1. somas por partido, esfera, UF, fonte do recurso e categoria, de receita e de despesa, com
   as transferências internas separadas (`natureza`), para não contar duas vezes o mesmo
   dinheiro que sai de um diretório e entra em outro;
2. a série mensal das cotas do Fundo Partidário e do FEFC que cada partido recebeu do TSE;
3. as linhas de despesa pagas a um fornecedor que já está na base: CNPJ de empresa sancionada
   ou sócia de alguém que acompanhamos, ou pessoa da base (ligada pelo CPF, que não é gravado).

CPF e nome de doador pessoa física nunca saem do arquivo. O bruto não é guardado (fica um
manifesto); para refazer, baixa-se de novo.
"""

import argparse
import functools
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.models import (
    FonteIngestao,
    PartidoContaSoma,
    PartidoCotaMensal,
    PartidoDespesaVinculada,
    Pessoa,
    SancaoEmpresa,
    SocioPessoa,
)
from ingestion import comum
from ingestion.tse import comum_tse

FONTE = "tse_contas_partidarias"
PASTA = "prestacao_contas_anual_partidaria"
URL = f"{comum_tse.BASE}/{PASTA}/{PASTA}_{{ano}}.zip"
LOTE = 5000

FUNDOS = {
    "FUNDO PARTIDARIO": "Fundo Partidário",
    "FUNDO ESPECIAL DE FINANCIAMENTO DE CAMPANHA": "FEFC",
    "RECURSOS PARA CAMPANHA": "Recursos para campanha",
    "OUTROS RECURSOS": "Outros recursos",
}


def _texto(valor: str | None) -> str:
    return comum_tse.texto(valor) or ""


@functools.cache
def fonte_recurso(texto: str | None) -> str:
    """'FUNDO PARTIDÁRIO' e 'Fundo Partidário' são o mesmo rótulo com caixa diferente."""
    chave = comum.chave_nome(_texto(texto))
    if not chave:
        return "Não informado"
    return FUNDOS.get(chave) or comum.limpar_categoria(_texto(texto))


def _fundo_da_cota(origem: str) -> str | None:
    """Origem 'Cotas do Fundo ...' -> 'Fundo Partidário' | 'FEFC' (quem vem do TSE)."""
    chave = comum.chave_nome(origem)
    if not chave.startswith("COTAS DO "):
        return None
    return "Fundo Partidário" if "PARTIDARIO" in chave else "FEFC"


@functools.cache
def natureza_receita(origem: str | None) -> str:
    origem_limpa = _texto(origem)
    if _fundo_da_cota(origem_limpa):
        return "cota_tse"
    chave = comum.chave_nome(origem_limpa)
    if chave == "RECURSOS DE PARTIDOS POLITICOS":
        return "transferencia_partidaria"
    if chave == "RECURSOS DE CANDIDATOS":
        return "recurso_candidato"
    return "outra"


@functools.cache
def natureza_despesa(ds_gasto: str | None) -> str:
    """Transferência é dinheiro que muda de conta (diretório, candidato), não gasto: entra
    como receita lá do outro lado. Fica separada para os totais não contarem em dobro."""
    chave = comum.chave_nome(_texto(ds_gasto))
    if not chave.startswith("TRANSFERENCIAS"):
        return "gasto"
    if "DIRECAO" in chave:
        return "transferencia_diretorio"
    if "CANDIDAT" in chave:
        return "transferencia_candidato"
    return "transferencia_outra"


@functools.cache
def categoria_despesa(ds_gasto: str | None) -> str:
    """O DS_GASTO é 'GRUPO - SUBGRUPO - FINALIDADE' (321 variações em 2024). Fica o grupo,
    que é o que o cidadão entende: 'Pessoal', 'Aluguéis e condomínios'..."""
    return comum.limpar_categoria(_texto(ds_gasto).split(" - ")[0])[:200]


@functools.cache
def categoria_receita(ds_receita: str | None) -> str:
    return comum.limpar_categoria(_texto(ds_receita))[:200]


def _esfera(linha: dict[str, str]) -> str:
    # O arquivo de receitas grafa a coluna "ESPERA" (sic).
    bruto = linha.get("DS_TP_ESFERA_PARTIDARIA") or linha.get("DS_TP_ESPERA_PARTIDARIA")
    return _texto(bruto) or "Não informada"


def _uf(linha: dict[str, str]) -> str:
    return _texto(linha.get("SG_UF"))[:2]


class Resumo:
    """Acumula, linha a linha e sem guardar as linhas, as somas que ficam no banco."""

    def __init__(self, socios: set[str], sancionados: set[str], cpfs: dict[str, int]) -> None:
        self.socios = socios
        self.sancionados = sancionados
        self.cpfs = cpfs
        self.somas: dict[tuple, list] = defaultdict(lambda: [Decimal(0), 0])
        self.cotas: dict[tuple, Decimal] = defaultdict(Decimal)
        self.vinculadas: list[dict[str, Any]] = []
        self.sem_data_cota = 0

    def receita(self, linha: dict[str, str], ano: int) -> None:
        valor = comum_tse.valor(linha.get("VR_RECEITA"))
        if not valor:
            return  # prestador sem movimento: o arquivo traz uma linha zerada
        origem = _texto(linha.get("DS_TP_ORIGEM_DOACAO"))
        partido = _texto(linha.get("SG_PARTIDO"))
        chave = (
            ano, "receita", partido, _esfera(linha), _uf(linha),
            fonte_recurso(linha.get("DS_TP_FONTE_RECURSO")), natureza_receita(origem),
            categoria_receita(linha.get("DS_RECEITA")),
        )  # fmt: skip
        self.somas[chave][0] += valor
        self.somas[chave][1] += 1
        fundo = _fundo_da_cota(origem)
        if fundo and _esfera(linha) == "Nacional":
            recebida = comum_tse.data(linha.get("DT_RECEITA"))
            if recebida is None:
                self.sem_data_cota += 1
            else:
                self.cotas[(ano, recebida.replace(day=1), partido, fundo)] += valor

    def despesa(self, linha: dict[str, str], ano: int) -> None:
        valor = comum_tse.valor(linha.get("VR_PAGAMENTO"))
        if not valor:
            return
        partido = _texto(linha.get("SG_PARTIDO"))
        esfera, uf = _esfera(linha), _uf(linha)
        fonte = fonte_recurso(linha.get("DS_FONTE_DESPESA"))
        gasto = linha.get("DS_GASTO")
        natureza, categoria = natureza_despesa(gasto), categoria_despesa(gasto)
        chave = (ano, "despesa", partido, esfera, uf, fonte, natureza, categoria)
        self.somas[chave][0] += valor
        self.somas[chave][1] += 1

        documento = _texto(linha.get("NR_CPF_CNPJ_FORNECEDOR"))
        cnpj = documento if len(documento) == 14 else None
        pessoa_id = self.cpfs.get(comum_tse.cpf(documento) or "") if len(documento) == 11 else None
        motivos = []
        if cnpj in self.sancionados:
            motivos.append("sancao_empresa")
        if cnpj in self.socios:
            motivos.append("socio_pessoa")
        if pessoa_id is not None:
            motivos.append("pessoa")
        if not motivos:
            return
        motivo = ",".join(motivos)
        self.vinculadas.append({
            "ano": ano, "partido": partido, "esfera": esfera, "uf": uf,
            "municipio": comum.nome_proprio(_texto(linha.get("NM_MUNICIPIO"))) or None,
            "sq_despesa": _texto(linha.get("SQ_DESPESA")) or None,
            "fornecedor_cnpj": cnpj,
            "fornecedor_nome": (_texto(linha.get("NM_FORNECEDOR")) or None) if cnpj else None,
            "pessoa_id": pessoa_id, "motivo": motivo, "categoria": categoria,
            "fonte_recurso": fonte, "natureza": natureza,
            "data": comum_tse.data(linha.get("DT_PAGAMENTO")), "valor": valor,
        })  # fmt: skip

    def linhas_somas(self) -> list[dict[str, Any]]:
        campos = (
            "ano",
            "tipo",
            "partido",
            "esfera",
            "uf",
            "fonte_recurso",
            "natureza",
            "categoria",
        )
        return [
            {**dict(zip(campos, chave, strict=True)), "valor": soma, "lancamentos": n}
            for chave, (soma, n) in self.somas.items()
        ]

    def linhas_cotas(self) -> list[dict[str, Any]]:
        return [
            {"ano": a, "mes": mes, "partido": p, "fundo": f, "valor": v}
            for (a, mes, p, f), v in self.cotas.items()
        ]


def resumir(
    receitas: Iterable[dict[str, str]],
    despesas: Iterable[dict[str, str]],
    ano: int,
    socios: set[str] | None = None,
    sancionados: set[str] | None = None,
    cpfs: dict[str, int] | None = None,
) -> Resumo:
    resumo = Resumo(socios or set(), sancionados or set(), cpfs or {})
    for linha in receitas:
        resumo.receita(linha, ano)
    for linha in despesas:
        resumo.despesa(linha, ano)
    return resumo


def _gravar(session: Session, modelo: type, linhas: list[dict[str, Any]]) -> None:
    for inicio in range(0, len(linhas), LOTE):
        session.execute(insert(modelo), linhas[inicio : inicio + LOTE])


def carregar(session: Session, payload: Any, ano: int) -> int:
    sancionados = set(session.scalars(select(SancaoEmpresa.cnpj).distinct()))
    socios = set(session.scalars(select(SocioPessoa.cnpj).distinct()))
    cpfs = {
        cpf: id_
        for cpf, id_ in session.execute(
            select(Pessoa.cpf, Pessoa.id).where(Pessoa.cpf.is_not(None))
        )
    }
    resumo = resumir(
        comum_tse.linhas(payload, "receita_anual_"),
        comum_tse.linhas(payload, "despesa_anual_"),
        ano,
        socios,
        sancionados,
        cpfs,
    )
    somas = resumo.linhas_somas()
    if not somas:
        raise RuntimeError(f"Nenhuma conta partidária em {ano}: nada alterado.")
    for modelo in (PartidoContaSoma, PartidoCotaMensal, PartidoDespesaVinculada):
        session.execute(delete(modelo).where(modelo.ano == ano))
    cotas = resumo.linhas_cotas()
    _gravar(session, PartidoContaSoma, somas)
    _gravar(session, PartidoCotaMensal, cotas)
    _gravar(session, PartidoDespesaVinculada, resumo.vinculadas)
    print(
        f"  {len(somas)} somas, {len(cotas)} cotas mensais, "
        f"{len(resumo.vinculadas)} despesas com fornecedor da base"
        + (f"; {resumo.sem_data_cota} cotas sem data" if resumo.sem_data_cota else "")
    )
    return len(somas) + len(cotas) + len(resumo.vinculadas)


def _contexto(session: Session) -> str:
    """Pessoas e os cadastros de sancionadas e sócios, de que a carga depende."""
    sancoes = session.scalar(select(func.count()).select_from(SancaoEmpresa))
    socios = session.scalar(select(func.count()).select_from(SocioPessoa))
    return f"{comum.contexto_pessoas(session)};sancoes:{sancoes};socios:{socios}"


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, URL.format(ano=ano))

    def gravar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        return carregar(session, payload, ano)

    try:
        return comum.executar_ingestao(
            FONTE,
            URL.format(ano=ano),
            baixar,
            gravar,
            de_raw=de_raw,
            prefixo_raw=f"{ano}_",
            incremental=comum.Incremental(sonda=URL.format(ano=ano), contexto=_contexto),
        )
    except httpx.HTTPStatusError as erro:
        if erro.response.status_code != 404:
            raise
        print(f"  {FONTE}: o TSE ainda não publicou o exercício {ano}")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="+", default=[date.today().year - 1])
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um só ano)")
    parser.add_argument("--manter-bruto", action="store_true", help="Não troca o zip por manifesto")
    args = parser.parse_args()
    inicio = datetime.now(UTC)
    for ano_ in args.ano:
        print(f"{FONTE} {ano_}: {executar(ano_, de_raw=args.de_raw)} registros")
    if args.de_raw is None and not args.manter_bruto:
        comum.trocar_por_manifesto(FONTE, desde=inicio)
