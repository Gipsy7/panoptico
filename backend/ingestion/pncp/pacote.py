"""Pacote da carga histórica do PNCP na produção.

Reler a API dia a dia leva ~39 h. O acervo local já tem os contratos de 2023 em diante,
conferidos dia a dia contra o total da API. Este módulo gera, a partir do acervo (só SELECT),
exatamente o que `contratos --producao` teria gravado na produção, num arquivo .zip que vai
como anexo de uma release do GitHub; o workflow `pncp-pacote.yml` o carrega no Neon.

    python -m ingestion.pncp.pacote gerar --destino pncp-pacote.zip [--url URL_DO_ACERVO]
    python -m ingestion.pncp.pacote carregar --arquivo pncp-pacote.zip [--manifesto M.json]

Conteúdo (um .jsonl por tabela, mais manifesto.json com contagens e sha256):
- `pncp_anual`: ano anterior e atual, órgãos municipais, por município × fornecedor (CNPJ),
  só os 30 maiores de cada município e ano, dos dias que já saíram da janela (compactados);
- `pncp_dia`: um registro por dia lido desde 1º de janeiro do ano anterior, com `compactado`;
- `pncp_janela`: os últimos 10 dias, por dia × município × fornecedor;
- `pncp_suspeito`: o que ficou de fora das somas por valor suspeito (`suspeito.py`), por dia ×
  órgão × município × fornecedor, do ano anterior em diante;
- `pncp_contrato`: contratos inteiros das empresas sancionadas e dos sócios que acompanhamos
  (o mesmo conjunto-alvo da produção), do ano anterior em diante.

Valor suspeito (digitação errada no PNCP): no acervo só há somas por dia × órgão × fornecedor ×
tipo, então o teste vale para cada linha dessas (igual ao contrato quando `quantidade` é 1); o
que passa do limite sai de `pncp_anual`/`pncp_janela` e vai para `pncp_suspeito`.

Sem pessoa física: só entra fornecedor com CNPJ (PF e estrangeiro nunca têm identificador no
acervo) e todo texto livre passa por `sem_cpf`; a geração para se sobrar padrão de CPF.

Diferenças inevitáveis em relação à leitura direta da API (o acervo guarda somas, não
contratos): o filtro "valor global > 0" não pode ser aplicado a cada contrato, só ao total do
grupo; o nome do fornecedor vem de `pncp_contrato`, `sancao_empresa` e dos pagamentos dos
TCEs (`despesa_fornecedor`, só onde o tribunal publica); os demais ficam sem nome até o diário
vê-los de novo e o site mostra o CNPJ; e `pncp_orgao` não é gravado na produção.
"""

import argparse
import hashlib
import io
import json
import zipfile
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, defer, sessionmaker

from app.models import (
    FonteIngestao,
    PncpAnual,
    PncpContrato,
    PncpDia,
    PncpEntePublico,
    PncpJanela,
    PncpSuspeito,
    SancaoEmpresa,
    SocioPessoa,
)
from ingestion.pncp import anual, suspeito
from ingestion.pncp.contratos import CPF, sem_cpf

VERSAO = 3  # 3 acrescenta pncp_ente_publico; o pacote de versão 2 ainda é aceito na carga
TABELAS = (
    "pncp_anual", "pncp_dia", "pncp_janela", "pncp_suspeito", "pncp_contrato",
    "pncp_ente_publico",
)  # fmt: skip
OPCIONAIS = ("pncp_ente_publico",)  # ausentes nos pacotes de versão 2
CAMPOS_TEXTO_CONTRATO = (
    "orgao_nome", "municipio_nome", "fornecedor_nome", "tipo_contrato", "categoria",
    "objeto", "processo",
)  # fmt: skip
LOTE = 2000
MODELOS = {
    "pncp_anual": PncpAnual, "pncp_dia": PncpDia, "pncp_janela": PncpJanela,
    "pncp_contrato": PncpContrato, "pncp_suspeito": PncpSuspeito,
    "pncp_ente_publico": PncpEntePublico,
}  # fmt: skip


class PacoteInvalido(SystemExit):
    pass


# --- geração -------------------------------------------------------------------------------


def _json(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, date | datetime):
        return valor.isoformat()
    raise TypeError(type(valor))


def _linhas(session: Session, sql: str, **params: Any) -> list[dict[str, Any]]:
    return [dict(r) for r in session.execute(text(sql), params).mappings()]


def _nomes(session: Session) -> dict[str, str]:
    """Nome por CNPJ: pagamentos dos TCEs (despesa_fornecedor), por cima sancao_empresa e, por
    cima, o que o PNCP informou (pncp_contrato)."""
    nomes: dict[str, str] = {}
    for cnpj, nome in session.execute(
        text(
            """
            SELECT regexp_replace(documento, '[^0-9]', '', 'g') AS cnpj, max(fornecedor)
            FROM despesa_fornecedor
            WHERE length(regexp_replace(documento, '[^0-9]', '', 'g')) = 14
            GROUP BY 1
            """
        )
    ):
        nomes[cnpj] = nome
    for cnpj, nome in session.execute(select(SancaoEmpresa.cnpj, SancaoEmpresa.nome)):
        nomes.setdefault(cnpj, nome)
    for cnpj, nome in session.execute(
        select(PncpContrato.fornecedor_cnpj, PncpContrato.fornecedor_nome).where(
            PncpContrato.fornecedor_nome.is_not(None)
        )
    ):
        nomes[cnpj] = nome
    return nomes


def _nome_limpo(nomes: dict[str, str], cnpj: str) -> str | None:
    return (sem_cpf(nomes.get(cnpj)) or "")[:120] or None


def montar(session: Session, hoje: date) -> dict[str, list[dict[str, Any]]]:
    """As quatro tabelas, como `contratos --producao` as deixaria em `hoje`."""
    inicio = date(anual.ano_minimo(hoje), 1, 1)
    corte = hoje - timedelta(days=anual.JANELA_DIAS)  # antes dele: compactado
    nomes = _nomes(session)
    # limite de cada linha: o menor entre a despesa paga anual do município e o teto absoluto
    base = """
        FROM pncp_soma p JOIN pncp_orgao o ON o.cnpj = p.orgao_cnpj AND o.esfera = 'M'
        LEFT JOIN (
            SELECT DISTINCT ON (municipio_ibge) municipio_ibge, despesa_paga
            FROM contas_municipio WHERE despesa_paga > 0 ORDER BY municipio_ibge, ano DESC
        ) c ON c.municipio_ibge = p.municipio_ibge
        WHERE p.fornecedor_cnpj <> '' AND p.municipio_ibge <> ''
    """
    limite = "LEAST(CAST(:teto AS numeric), COALESCE(c.despesa_paga, CAST(:teto AS numeric)))"
    municipal = f"{base} AND p.valor_global <= {limite}"
    teto = suspeito.TETO_ABSOLUTO

    soma_anual = _linhas(
        session,
        f"""
        SELECT ano, municipio_ibge, fornecedor_cnpj, quantidade, valor_global FROM (
            SELECT ano, municipio_ibge, fornecedor_cnpj, quantidade, valor_global,
                   row_number() OVER (PARTITION BY ano, municipio_ibge
                                      ORDER BY valor_global DESC, fornecedor_cnpj) AS posicao
            FROM (
                SELECT EXTRACT(YEAR FROM p.dia)::int AS ano, p.municipio_ibge,
                       p.fornecedor_cnpj, sum(p.quantidade)::int AS quantidade,
                       sum(p.valor_global) AS valor_global
                {municipal} AND p.dia >= :inicio AND p.dia < :corte
                GROUP BY 1, 2, 3 HAVING sum(p.valor_global) > 0
            ) s
        ) r WHERE posicao <= :maiores
        ORDER BY ano, municipio_ibge, fornecedor_cnpj
        """,
        inicio=inicio, corte=corte, maiores=anual.MAIORES_POR_MUNICIPIO, teto=teto,
    )  # fmt: skip
    for linha in soma_anual:
        linha["fornecedor_nome"] = _nome_limpo(nomes, linha["fornecedor_cnpj"])

    janela = _linhas(
        session,
        f"""
        SELECT p.dia, p.municipio_ibge, p.fornecedor_cnpj,
               sum(p.quantidade)::int AS quantidade, sum(p.valor_global) AS valor_global
        {municipal} AND p.dia >= :corte
        GROUP BY 1, 2, 3 HAVING sum(p.valor_global) > 0
        ORDER BY 1, 2, 3
        """,
        corte=corte, teto=teto,
    )  # fmt: skip
    for linha in janela:
        linha["fornecedor_nome"] = _nome_limpo(nomes, linha["fornecedor_cnpj"])

    suspeitos = _linhas(
        session,
        f"""
        SELECT p.dia, p.municipio_ibge, p.orgao_cnpj, p.fornecedor_cnpj, '' AS referencia,
               sum(p.quantidade)::int AS quantidade, sum(p.valor_global) AS valor_global,
               max({limite}) AS limite
        {base} AND p.valor_global > {limite} AND p.dia >= :inicio
        GROUP BY 1, 2, 3, 4 ORDER BY 1, 2, 3, 4
        """,
        inicio=inicio, teto=teto,
    )  # fmt: skip
    for linha in suspeitos:
        linha["fornecedor_nome"] = _nome_limpo(nomes, linha["fornecedor_cnpj"])

    dias = _linhas(
        session,
        """
        SELECT dia, total_api, lidos, receitas, empenhos, pessoas_fisicas, linhas_alvo,
               lido_em, (dia < :corte) AS compactado
        FROM pncp_dia WHERE dia >= :inicio ORDER BY dia
        """,
        inicio=inicio, corte=corte,
    )  # fmt: skip

    alvo = set(session.scalars(select(SancaoEmpresa.cnpj).distinct())) | set(
        session.scalars(select(SocioPessoa.cnpj).distinct())
    )
    limites = suspeito.carregar_limites(session)
    contratos: list[dict[str, Any]] = []
    colunas = [c.name for c in PncpContrato.__table__.columns]
    for c in session.scalars(
        select(PncpContrato)
        .options(defer(PncpContrato.valor_suspeito))  # o acervo pode não ter a coluna ainda
        .where(PncpContrato.publicado_em >= inicio)
        .order_by(PncpContrato.numero_controle)
    ):
        if c.fornecedor_cnpj not in alvo:
            continue
        linha = {k: getattr(c, k) for k in colunas if k != "valor_suspeito"}
        linha["valor_suspeito"] = suspeito.eh_suspeito(
            c.valor_global, c.esfera, c.municipio_ibge, limites
        )
        for k in CAMPOS_TEXTO_CONTRATO:
            if linha[k]:
                linha[k] = sem_cpf(linha[k])
        contratos.append(linha)
    entes = _linhas(session, "SELECT cnpj FROM pncp_orgao ORDER BY cnpj")
    return {
        "pncp_anual": soma_anual, "pncp_dia": dias, "pncp_janela": janela,
        "pncp_suspeito": suspeitos, "pncp_contrato": contratos, "pncp_ente_publico": entes,
    }  # fmt: skip


def varrer_cpf(tabelas: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Achados de padrão de CPF em qualquer texto do pacote (CNPJ de 14 dígitos não casa)."""
    achados = []
    for nome, linhas in tabelas.items():
        for linha in linhas:
            for campo, valor in linha.items():
                if isinstance(valor, str) and CPF.search(valor):
                    achados.append(f"{nome}.{campo}")
    return achados


def _jsonl(linhas: list[dict[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(l, ensure_ascii=False, default=_json, sort_keys=True).encode() + b"\n"
        for l in linhas  # noqa: E741
    )


def gerar(session: Session, destino: Path, hoje: date | None = None) -> dict[str, Any]:
    """Escreve o .zip em `destino` e o manifesto externo ao lado; devolve o manifesto."""
    hoje = hoje or date.today()
    tabelas = montar(session, hoje)
    achados = varrer_cpf(tabelas)
    if achados:
        raise PacoteInvalido(f"padrão de CPF no pacote: {sorted(set(achados))}")
    dias = [d["dia"] for d in tabelas["pncp_dia"]]
    manifesto: dict[str, Any] = {
        "versao": VERSAO,
        "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "referencia": hoje.isoformat(),
        "periodo": {
            "de": min(dias).isoformat() if dias else None,
            "ate": max(dias).isoformat() if dias else None,
            "janela_dias": anual.JANELA_DIAS,
            "maiores_por_municipio": anual.MAIORES_POR_MUNICIPIO,
        },
        "tabelas": {},
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for nome in TABELAS:
            dados = _jsonl(tabelas[nome])
            manifesto["tabelas"][nome] = {
                "arquivo": f"{nome}.jsonl",
                "linhas": len(tabelas[nome]),
                "bytes": len(dados),
                "sha256": hashlib.sha256(dados).hexdigest(),
            }
            z.writestr(f"{nome}.jsonl", dados)
        z.writestr("manifesto.json", json.dumps(manifesto, ensure_ascii=False, indent=1))
    externo = {
        **manifesto,
        "arquivo": destino.name,
        "arquivo_bytes": destino.stat().st_size,
        "arquivo_sha256": hashlib.sha256(destino.read_bytes()).hexdigest(),
    }
    destino.with_suffix(".manifesto.json").write_text(
        json.dumps(externo, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return externo


# --- carga ---------------------------------------------------------------------------------


def ler(arquivo: Path, manifesto_externo: Path | None = None) -> tuple[dict, dict[str, list]]:
    """Lê e confere o pacote (sha256 do arquivo, se houver manifesto externo, e de cada tabela)."""
    if manifesto_externo is not None:
        esperado = json.loads(manifesto_externo.read_text(encoding="utf-8"))["arquivo_sha256"]
        real = hashlib.sha256(arquivo.read_bytes()).hexdigest()
        if real != esperado:
            raise PacoteInvalido(f"sha256 do arquivo difere do manifesto: {real} != {esperado}")
    with zipfile.ZipFile(arquivo) as z:
        manifesto = json.loads(z.read("manifesto.json"))
        if manifesto.get("versao") not in (2, VERSAO):
            raise PacoteInvalido(f"versão de pacote não suportada: {manifesto.get('versao')}")
        tabelas: dict[str, list] = {}
        for nome in TABELAS:
            if nome in OPCIONAIS and nome not in manifesto["tabelas"]:
                tabelas[nome] = []
                continue
            info = manifesto["tabelas"][nome]
            dados = z.read(info["arquivo"])
            if hashlib.sha256(dados).hexdigest() != info["sha256"]:
                raise PacoteInvalido(f"sha256 de {nome} não confere")
            linhas = [json.loads(l) for l in io.BytesIO(dados).read().splitlines() if l]  # noqa: E741
            if len(linhas) != info["linhas"]:
                raise PacoteInvalido(
                    f"{nome}: {len(linhas)} linhas, manifesto diz {info['linhas']}"
                )
            tabelas[nome] = linhas
    return manifesto, tabelas


def _converter(nome: str, linha: dict[str, Any]) -> dict[str, Any]:
    saida = {}
    for coluna in MODELOS[nome].__table__.columns:
        valor = linha.get(coluna.name)
        if valor is not None:
            tipo = coluna.type.python_type
            if tipo is Decimal:
                valor = Decimal(valor)
            elif tipo is datetime:
                valor = datetime.fromisoformat(valor)
            elif tipo is date:
                valor = date.fromisoformat(valor)
        saida[coluna.name] = valor
    return saida


def _inserir(session: Session, nome: str, linhas: list[dict[str, Any]]) -> None:
    modelo = MODELOS[nome]
    convertidas = [_converter(nome, l) for l in linhas]  # noqa: E741
    for i in range(0, len(convertidas), LOTE):
        lote = convertidas[i : i + LOTE]
        stmt = insert(modelo).values(lote)
        if nome == "pncp_ente_publico":
            stmt = stmt.on_conflict_do_nothing()
        elif nome == "pncp_contrato":
            atualizar = {c: stmt.excluded[c] for c in lote[0] if c != "numero_controle"}
            stmt = stmt.on_conflict_do_update(index_elements=["numero_controle"], set_=atualizar)
        session.execute(stmt)


def carregar(session: Session, manifesto: dict, tabelas: dict[str, list], forcar: bool = False):
    """Troca o período do pacote numa transação só (idempotente): pncp_anual dos anos dele,
    pncp_dia e pncp_janela dos dias dele, e upsert dos contratos. Os dias que o diário já
    leu depois do pacote ficam como estão. Recusa se o diário já somou, em pncp_anual, um dia
    posterior ao pacote (trocar o ano apagaria essa soma), a menos que `forcar`."""
    de = date.fromisoformat(manifesto["periodo"]["de"])
    ate = date.fromisoformat(manifesto["periodo"]["ate"])
    if not forcar:
        depois = session.scalar(
            select(PncpDia.dia).where(PncpDia.dia > ate, PncpDia.compactado.is_(True)).limit(1)
        )
        if depois is not None:
            raise PacoteInvalido(
                f"o diário já somou {depois}, posterior ao pacote ({ate}); "
                "carregar de novo apagaria essa soma (use --forcar se for isso mesmo)"
            )
    anos = sorted({l["ano"] for l in tabelas["pncp_anual"]})  # noqa: E741
    session.execute(delete(PncpAnual).where(PncpAnual.ano.in_(anos)))
    session.execute(delete(PncpJanela).where(PncpJanela.dia.between(de, ate)))
    session.execute(delete(PncpDia).where(PncpDia.dia.between(de, ate)))
    session.execute(delete(PncpSuspeito).where(PncpSuspeito.dia.between(de, ate)))
    for nome in TABELAS:
        _inserir(session, nome, tabelas[nome])
    # a carga também vale como "última atualização" que o site mostra (o diário faz o mesmo)
    agora = datetime.now(UTC)
    session.add(
        FonteIngestao(
            fonte="pncp_contratos", url="pacote histórico do PNCP",
            arquivo_raw=f"pncp-pacote {manifesto.get('gerado_em', '')}",
            iniciado_em=agora, concluido_em=agora, status="ok",
            registros=sum(len(tabelas[n]) for n in TABELAS if n != "pncp_ente_publico"),
            alertas=[f"pacote histórico até {ate}"],
        )
    )  # fmt: skip
    session.commit()


def resumo(session: Session) -> dict[str, int]:
    return {
        n: session.scalar(text(f"SELECT count(*) FROM {n}")) or 0  # noqa: S608
        for n in TABELAS
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Pacote da carga histórica do PNCP")
    sub = parser.add_subparsers(dest="comando", required=True)
    g = sub.add_parser("gerar", help="gera o pacote a partir do acervo (só SELECT)")
    g.add_argument("--destino", type=Path, required=True)
    g.add_argument("--url", help="URL do acervo (padrão: DATABASE_URL)")
    g.add_argument("--hoje", type=date.fromisoformat, help="data de referência (padrão: hoje)")
    c = sub.add_parser("carregar", help="grava o pacote no banco de DATABASE_URL")
    c.add_argument("--arquivo", type=Path, required=True)
    c.add_argument("--manifesto", type=Path, help="manifesto externo (sha256 do arquivo)")
    c.add_argument("--forcar", action="store_true")
    args = parser.parse_args()

    if args.comando == "gerar":
        if args.url:
            sessao = sessionmaker(bind=create_engine(args.url))
        else:
            from app.db import SessionLocal as sessao
        with sessao() as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            m = gerar(session, args.destino, args.hoje)
        print(json.dumps(m, ensure_ascii=False, indent=1))
    else:
        from app.db import SessionLocal

        manifesto, tabelas = ler(args.arquivo, args.manifesto)
        with SessionLocal() as session:
            carregar(session, manifesto, tabelas, args.forcar)
            print("carregado:", json.dumps(resumo(session)))


if __name__ == "__main__":
    main()
