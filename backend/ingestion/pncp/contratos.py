"""Contratos do PNCP (Portal Nacional de Contratações Públicas), em coleta mínima.

Guarda (docs/DECISOES.md, "PNCP"):
- **somas** por dia de publicação × órgão × município × fornecedor × tipo de contrato
  (valor global e quantidade), sem as alienações (`receita`) e com os empenhos separados
  pelo tipo; pessoa física e fornecedor estrangeiro entram sem identificador;
- **linhas inteiras** só dos contratos cujo fornecedor (CNPJ) é sócio que acompanhamos
  (socio_pessoa) ou empresa sancionada (sancao_empresa). Rode depois de cgu_sancoes e
  cnpj_socios;
- do bruto, só o manifesto (por dia: total informado pela API, páginas, bytes, sha256).

Coleta: a API não filtra por fornecedor e recusa páginas profundas (500), então lê um dia de
publicação por vez, 500 contratos por página, uma requisição de cada vez e com pausa. Cada dia
é gravado e confirmado sozinho; a tabela pncp_dia é o cursor e a conferência (total da API
contra o lido). O valor global muda com aditivos, então a coleta seguinte relê os últimos dias
(`--releitura`) e, pela rota de atualização, os dias antigos que tiveram contrato alterado.
"""

import argparse
import hashlib
import json
import re
import time
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    FonteIngestao,
    PncpContrato,
    PncpDia,
    PncpOrgao,
    PncpSoma,
    SancaoEmpresa,
    SocioPessoa,
)
from ingestion import comum

FONTE = "pncp_contratos"
URL = "https://pncp.gov.br/api/consulta/v1/contratos"
URL_ATUALIZACAO = URL + "/atualizacao"
TAMANHO_PAGINA = 500  # o máximo; 501 dá 400
PAUSA = 0.5  # segundos entre requisições
TENTATIVAS = 8  # 429 e 5xx, com espera crescente (comum._get)
JANELA_INICIAL = date(2023, 1, 1)
RELEITURA_DIAS = 7
MAX_RELEITURAS = 20  # dias antigos relidos por coleta, por causa de aditivos
TIPOS_PESSOA = {"PJ", "PF", "PE"}

CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
Chave = tuple[str, str, str, str, str]  # órgão, município, tipo_pessoa, fornecedor, tipo


def sem_cpf(texto: str | None) -> str | None:
    """MEI traz o CPF dentro da razão social ('JOSE DA SILVA 12345678901'): tira."""
    if not texto:
        return None
    return " ".join(CPF.sub(" ", texto).split()) or None


def _digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _valor(valor: Any) -> Decimal | None:
    if valor is None:
        return None
    return Decimal(str(valor)).quantize(Decimal("0.01"))


def _data(valor: str | None) -> date | None:
    try:
        return date.fromisoformat((valor or "")[:10])
    except ValueError:
        return None


def _datahora(valor: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(valor) if valor else None
    except ValueError:
        return None


def fornecedor_de(contrato: dict[str, Any]) -> tuple[str, str]:
    """(tipo de pessoa, CNPJ). O CNPJ só existe para PJ com 14 dígitos; para PF e estrangeiro
    é vazio: o CPF não é lido para lugar nenhum."""
    tipo = (contrato.get("tipoPessoa") or "").upper()
    if tipo not in TIPOS_PESSOA:
        return "XX", ""
    if tipo == "PJ" and len(_digitos(contrato.get("niFornecedor"))) == 14:
        return tipo, _digitos(contrato["niFornecedor"])
    return tipo, ""


def _nome(campo: Any) -> str:
    return ((campo or {}).get("nome") or "Não informado").strip()[:60]


@dataclass
class Dia:
    """O que um dia de publicação trouxe, já reduzido ao que guardamos."""

    dia: date
    total_api: int = 0
    lidos: int = 0
    repetidos: int = 0
    receitas: int = 0
    empenhos: int = 0
    pessoas_fisicas: int = 0
    paginas: int = 0
    bytes: int = 0
    somas: dict[Chave, list] = field(default_factory=lambda: defaultdict(lambda: [0, Decimal(0)]))
    orgaos: dict[str, dict] = field(default_factory=dict)
    alvo: dict[str, dict] = field(default_factory=dict)
    sha256: Any = field(default_factory=hashlib.sha256)


def contrato_inteiro(c: dict[str, Any], cnpj: str) -> dict[str, Any]:
    orgao, unidade = c.get("orgaoEntidade") or {}, c.get("unidadeOrgao") or {}
    objeto = sem_cpf(c.get("objetoContrato"))
    return {
        "numero_controle": c["numeroControlePNCP"],
        "orgao_cnpj": _digitos(orgao.get("cnpj"))[:14],
        "orgao_nome": (orgao.get("razaoSocial") or "")[:300] or None,
        "esfera": orgao.get("esferaId"),
        "uf": unidade.get("ufSigla"),
        "municipio_ibge": _digitos(unidade.get("codigoIbge"))[:7] or None,
        "municipio_nome": (unidade.get("municipioNome") or "")[:120] or None,
        "fornecedor_cnpj": cnpj,
        "fornecedor_nome": (sem_cpf(c.get("nomeRazaoSocialFornecedor")) or "")[:300] or None,
        "tipo_contrato": _nome(c.get("tipoContrato")),
        "categoria": _nome(c.get("categoriaProcesso")),
        "receita": bool(c.get("receita")),
        "objeto": objeto[:2000] if objeto else None,
        "valor_inicial": _valor(c.get("valorInicial")),
        "valor_global": _valor(c.get("valorGlobal")),
        "valor_acumulado": _valor(c.get("valorAcumulado")),
        "data_assinatura": _data(c.get("dataAssinatura")),
        "vigencia_inicio": _data(c.get("dataVigenciaInicio")),
        "vigencia_fim": _data(c.get("dataVigenciaFim")),
        "publicado_em": _data(c.get("dataPublicacaoPncp")),
        "atualizado_em": _datahora(c.get("dataAtualizacaoGlobal")),
        "compra_pncp": c.get("numeroControlePncpCompra"),
        "processo": (c.get("processo") or "")[:100] or None,
    }


def somar(d: Dia, contratos: list[dict[str, Any]], alvo: set[str]) -> None:
    """Acumula os contratos de uma página nas somas do dia (puro, sem rede nem banco)."""
    for c in contratos:
        d.lidos += 1
        tipo_pessoa, cnpj = fornecedor_de(c)
        if cnpj and cnpj in alvo and c.get("numeroControlePNCP"):
            d.alvo[c["numeroControlePNCP"]] = contrato_inteiro(c, cnpj)  # com a flag receita
        if c.get("receita"):  # alienação: não é gasto
            d.receitas += 1
            continue
        tipo = _nome(c.get("tipoContrato"))
        if tipo.lower() == "empenho":
            d.empenhos += 1
        if tipo_pessoa == "PF":
            d.pessoas_fisicas += 1
        orgao, unidade = c.get("orgaoEntidade") or {}, c.get("unidadeOrgao") or {}
        orgao_cnpj = _digitos(orgao.get("cnpj"))[:14]
        ibge = _digitos(unidade.get("codigoIbge"))[:7]
        soma = d.somas[(orgao_cnpj, ibge, tipo_pessoa, cnpj, tipo)]
        soma[0] += 1
        soma[1] += _valor(c.get("valorGlobal")) or Decimal(0)
        if orgao_cnpj and orgao_cnpj not in d.orgaos:
            d.orgaos[orgao_cnpj] = {
                "cnpj": orgao_cnpj,
                "nome": (orgao.get("razaoSocial") or "Não informado")[:300],
                "esfera": orgao.get("esferaId"),
                "poder": orgao.get("poderId"),
                "uf": unidade.get("ufSigla"),
            }


def paginas(
    client: httpx.Client, url: str, dia: date, pausa: float = PAUSA
) -> Iterator[tuple[dict[str, Any], bytes]]:
    """As páginas de um dia, uma requisição por vez. Dia sem registros responde 204."""
    pagina = 1
    while True:
        params = {
            "dataInicial": f"{dia:%Y%m%d}",
            "dataFinal": f"{dia:%Y%m%d}",
            "pagina": pagina,
            "tamanhoPagina": TAMANHO_PAGINA,
        }
        resposta = comum._get(client, url, params, TENTATIVAS)
        corpo = resposta.json() if resposta.content else {}
        yield corpo, resposta.content
        if pagina >= (corpo.get("totalPaginas") or 0):
            return
        pagina += 1
        time.sleep(pausa)


def ler_dia(client: httpx.Client, dia: date, alvo: set[str], pausa: float = PAUSA) -> Dia:
    d = Dia(dia)
    vistos: set[str] = set()
    for corpo, bruto in paginas(client, URL, dia, pausa):
        d.paginas += 1
        d.bytes += len(bruto)
        d.sha256.update(bruto)
        d.total_api = corpo.get("totalRegistros") or 0
        novos = []
        for c in corpo.get("data") or []:
            numero = c.get("numeroControlePNCP")
            if numero in vistos:  # a lista andou durante a leitura: conta uma vez
                d.repetidos += 1
                continue
            vistos.add(numero)
            novos.append(c)
        somar(d, novos, alvo)
    return d


def ler_atualizacoes(
    client: httpx.Client, dia: date, alvo: set[str], pausa: float = PAUSA
) -> tuple[set[date], dict[str, dict]]:
    """Contratos alterados num dia (aditivos...): os dias de publicação a reler e, já
    completos, os que são do conjunto-alvo."""
    publicados: set[date] = set()
    linhas: dict[str, dict] = {}
    for corpo, _ in paginas(client, URL_ATUALIZACAO, dia, pausa):
        for c in corpo.get("data") or []:
            publicado = _data(c.get("dataPublicacaoPncp"))
            if publicado:
                publicados.add(publicado)
            _, cnpj = fornecedor_de(c)
            if cnpj in alvo and c.get("numeroControlePNCP") and publicado:
                linhas[c["numeroControlePNCP"]] = contrato_inteiro(c, cnpj)
    return publicados, linhas


def _em_lotes(itens: list, tamanho: int) -> Iterator[list]:
    for i in range(0, len(itens), tamanho):
        yield itens[i : i + tamanho]


def upsert_contratos(session: Session, linhas: list[dict[str, Any]]) -> None:
    for lote in _em_lotes(linhas, 500):
        stmt = insert(PncpContrato).values(lote)
        atualizar = {c: stmt.excluded[c] for c in lote[0] if c != "numero_controle"}
        session.execute(
            stmt.on_conflict_do_update(index_elements=["numero_controle"], set_=atualizar)
        )


def gravar_dia(session: Session, d: Dia) -> None:
    """Troca o dia inteiro numa transação (idempotente: reler o dia não soma duas vezes)."""
    session.execute(delete(PncpSoma).where(PncpSoma.dia == d.dia))
    somas = [
        {
            "dia": d.dia, "orgao_cnpj": o, "municipio_ibge": m, "tipo_pessoa": p,
            "fornecedor_cnpj": f, "tipo_contrato": t, "quantidade": q, "valor_global": v,
        }
        for (o, m, p, f, t), (q, v) in d.somas.items()
    ]  # fmt: skip
    for lote in _em_lotes(somas, 2000):
        session.execute(insert(PncpSoma).values(lote))
    for lote in _em_lotes(list(d.orgaos.values()), 2000):
        stmt = insert(PncpOrgao).values(lote)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=["cnpj"],
                set_={c: stmt.excluded[c] for c in ("nome", "esfera", "poder", "uf")},
            )
        )
    upsert_contratos(session, list(d.alvo.values()))
    valores = {
        "total_api": d.total_api, "lidos": d.lidos, "receitas": d.receitas,
        "empenhos": d.empenhos, "pessoas_fisicas": d.pessoas_fisicas,
        "linhas_alvo": len(d.alvo), "lido_em": datetime.now(UTC),
    }  # fmt: skip
    stmt = insert(PncpDia).values(dia=d.dia, **valores)
    session.execute(stmt.on_conflict_do_update(index_elements=["dia"], set_=valores))
    session.commit()


def conjunto_alvo(session: Session) -> set[str]:
    """CNPJs de sócios que acompanhamos e de empresas sancionadas."""
    return set(session.scalars(select(SocioPessoa.cnpj).distinct())) | set(
        session.scalars(select(SancaoEmpresa.cnpj).distinct())
    )


def dias_da_janela(inicio: date, fim: date) -> list[date]:
    return [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]


def planejar(
    de: date | None, ate: date | None, ultimo: date | None, hoje: date, releitura: int
) -> tuple[date, date, bool]:
    """(início, fim, incremental). Sem --de/--ate e com cursor: relê os últimos `releitura`
    dias a partir do cursor; sem cursor: da janela inicial até hoje."""
    fim = ate or hoje
    if de is not None:
        return de, fim, False
    if ultimo is not None:
        return max(JANELA_INICIAL, ultimo - timedelta(days=releitura - 1)), fim, ate is None
    return JANELA_INICIAL, fim, False


def escrever_manifesto(caminho: Path, dados: dict[str, Any]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def executar(
    de: date | None = None,
    ate: date | None = None,
    releitura: int = RELEITURA_DIAS,
    max_releituras: int = MAX_RELEITURAS,
    pausa: float = PAUSA,
) -> int:
    """Lê os dias de publicação de `de` a `ate` (padrão: do cursor, ou de 2023, até hoje).
    Devolve quantos contratos foram lidos."""
    hoje = date.today()
    with SessionLocal() as session:
        alvo = conjunto_alvo(session)
        ultimo = session.scalar(select(func.max(PncpDia.dia)))
        carregados = set(session.scalars(select(PncpDia.dia)))
        inicio, fim, incremental = planejar(de, ate, ultimo, hoje, releitura)
        manifesto = comum.RAW_DIR / FONTE / f"{datetime.now():%Y-%m-%d_%H%M%S}.manifesto.json"
        ingestao = FonteIngestao(fonte=FONTE, url=URL, arquivo_raw=str(manifesto))
        session.add(ingestao)
        session.commit()

        dados: dict[str, Any] = {
            "url": URL, "de": inicio.isoformat(), "ate": fim.isoformat(),
            "alvo": len(alvo), "incremental": incremental, "dias": [],
        }  # fmt: skip
        total = 0
        try:
            with comum.criar_cliente() as client:
                dias = dias_da_janela(inicio, fim)
                if incremental:
                    dias += _dias_alterados(
                        client, session, inicio, fim, carregados, alvo, max_releituras, pausa
                    )
                print(f"  {len(dias)} dias a ler ({inicio} a {fim}); {len(alvo)} CNPJs-alvo")
                for dia in dias:
                    d = ler_dia(client, dia, alvo, pausa)
                    gravar_dia(session, d)
                    total += d.lidos
                    dados["dias"].append(
                        {"dia": dia.isoformat(), "total_api": d.total_api, "lidos": d.lidos,
                         "paginas": d.paginas, "bytes": d.bytes, "sha256": d.sha256.hexdigest()}
                    )  # fmt: skip
                    aviso = "" if d.lidos == d.total_api else "  <-- difere do total da API"
                    print(
                        f"  {dia}: {d.lidos}/{d.total_api} contratos, {len(d.alvo)} do alvo{aviso}"
                    )
            ingestao.status = "ok"
        except Exception:
            session.rollback()
            ingestao.status = "erro"
            raise
        finally:
            ingestao.registros = total
            ingestao.concluido_em = datetime.now(UTC)
            session.add(ingestao)
            session.commit()
            escrever_manifesto(manifesto, dados)
    return total


def _dias_alterados(
    client: httpx.Client,
    session: Session,
    inicio: date,
    fim: date,
    carregados: set[date],
    alvo: set[str],
    maximo: int,
    pausa: float,
) -> list[date]:
    """Pela rota de atualização: dias de publicação já carregados, anteriores à releitura,
    que tiveram contrato alterado (aditivo). Os mais recentes primeiro, até `maximo`."""
    antigos: set[date] = set()
    for dia in dias_da_janela(inicio, fim):
        publicados, linhas = ler_atualizacoes(client, dia, alvo, pausa)
        upsert_contratos(session, list(linhas.values()))
        session.commit()
        antigos |= {p for p in publicados if p < inicio and p in carregados}
    escolhidos = sorted(antigos, reverse=True)[:maximo]
    if len(antigos) > maximo:
        print(f"  {len(antigos) - maximo} dias antigos com contrato alterado ficam p/ a próxima")
    return sorted(escolhidos)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de", type=date.fromisoformat, help="Primeiro dia (AAAA-MM-DD)")
    parser.add_argument("--ate", type=date.fromisoformat, help="Último dia (AAAA-MM-DD)")
    parser.add_argument("--releitura", type=int, default=RELEITURA_DIAS)
    parser.add_argument("--max-releituras", type=int, default=MAX_RELEITURAS)
    args = parser.parse_args()
    lidos = executar(args.de, args.ate, args.releitura, args.max_releituras)
    print(f"{FONTE}: {lidos} contratos lidos")
