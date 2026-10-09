"""Acervo local: roda as fontes do registro (ingestion/fontes.toml) e mede o volume.

Uso:
    python -m ingestion.acervo rodar --fonte camara_deputados tse_bens
    python -m ingestion.acervo rodar --vencidas     # as que passaram da frequência
    python -m ingestion.acervo relatorio            # volume por fonte e últimas cargas

O acervo é um banco à parte (DATABASE_URL apontando para panoptico_acervo) com os brutos
preservados (PRESERVAR_RAW=true). Ver docs/DECISOES.md, "acervo local".
"""

import argparse
import importlib
import json
import sys
import tomllib
import traceback
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select, text

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum

REGISTRO = Path(__file__).with_name("fontes.toml")
# Total da última execução de cada fonte (todas as anos somados), para a checagem de queda.
HISTORICO = comum.RAW_DIR.parent / "acervo_historico.json"
QUEDA = 0.2  # mais de 20% a menos que a execução anterior: alerta
FREQUENCIAS = {"diaria": 1, "semanal": 7, "mensal": 30, "manual": None}
ACESSOS = {"aberto", "brasil", "lento", "espelho", "pedido", "lai", "indisponivel"}
SITUACOES = {"ativa", "catalogada"}
GUARDAS = {"linhas", "somas"}
BRUTOS = {"completo", "recorte"}


@dataclass
class Fonte:
    nome: str
    modulo: str
    frequencia: str
    anos: str | list[int] | None = None
    args: dict = field(default_factory=dict)
    depende: list[str] = field(default_factory=list)
    acesso: str = "aberto"
    # Coleta mínima (docs/DECISOES.md): só entra com uso declarado; sem uso, fica catalogada.
    situacao: str = "ativa"
    uso: str = ""  # a pergunta do cidadão ou a seção do site que a fonte alimenta
    recorte: str = ""  # quais pessoas, órgãos e período são guardados
    guarda: str = "linhas"  # "linhas" ou "somas"
    bruto: str = "completo"  # "completo" ou "recorte" (recorte em Parquet + manifesto)


def ler_registro(caminho: Path = REGISTRO) -> list[Fonte]:
    with caminho.open("rb") as arquivo:
        fontes = [Fonte(**f) for f in tomllib.load(arquivo)["fonte"]]
    nomes = [f.nome for f in fontes]
    repetidos = {n for n in nomes if nomes.count(n) > 1}
    if repetidos:
        raise ValueError(f"fontes repetidas no registro: {sorted(repetidos)}")
    for f in fontes:
        if f.frequencia not in FREQUENCIAS:
            raise ValueError(f"{f.nome}: frequência desconhecida {f.frequencia!r}")
        if f.acesso not in ACESSOS:
            raise ValueError(f"{f.nome}: acesso desconhecido {f.acesso!r}")
        for campo, valores in (("situacao", SITUACOES), ("guarda", GUARDAS), ("bruto", BRUTOS)):
            if getattr(f, campo) not in valores:
                raise ValueError(f"{f.nome}: {campo} desconhecido {getattr(f, campo)!r}")
        if f.situacao == "ativa" and not f.uso.strip():
            raise ValueError(f"{f.nome}: fonte ativa sem uso declarado (ou marque como catalogada)")
        faltam = [d for d in f.depende if d not in nomes]
        if faltam:
            raise ValueError(f"{f.nome}: depende de fontes fora do registro: {faltam}")
    return fontes


def anos_de(fonte: Fonte, hoje: date) -> list[int] | None:
    """Os anos em que executar(ano) roda, ou None para executar() sem ano."""
    if fonte.anos is None:
        return None
    if isinstance(fonte.anos, list):
        return fonte.anos
    regras = {
        "padrao": [hoje.year - 1, hoje.year],
        "dois_anteriores": [hoje.year - 2, hoje.year - 1],
        "desde_2023": list(range(2023, hoje.year + 1)),
    }
    if fonte.anos not in regras:
        raise ValueError(f"{fonte.nome}: regra de anos desconhecida {fonte.anos!r}")
    return regras[fonte.anos]


def ordenar(fontes: list[Fonte], escolhidas: set[str]) -> list[Fonte]:
    """As escolhidas, cada uma depois das dependências que também foram escolhidas (a
    ordem do registro desempata). Dependência fora da escolha não é puxada junto."""
    por_nome = {f.nome: f for f in fontes}
    ordem: list[Fonte] = []
    visitando: set[str] = set()

    def visitar(nome: str) -> None:
        if nome not in escolhidas or por_nome[nome] in ordem:
            return
        if nome in visitando:
            raise ValueError(f"dependência circular em {nome}")
        visitando.add(nome)
        for dep in por_nome[nome].depende:
            visitar(dep)
        visitando.discard(nome)
        ordem.append(por_nome[nome])

    for f in fontes:
        visitar(f.nome)
    return ordem


def vencidas(fontes: list[Fonte], ultimo_ok: dict[str, datetime], agora: datetime) -> set[str]:
    """Fontes ativas e não manuais cuja última carga com sucesso é mais velha que a
    frequência."""
    resultado = set()
    for f in fontes:
        dias = FREQUENCIAS[f.frequencia]
        if dias is None or f.situacao != "ativa":
            continue
        ultimo = ultimo_ok.get(f.nome)
        # Folga de uma hora: a carga diária das 3h não fica "vencida" às 2h59 do dia seguinte.
        if ultimo is None or agora - ultimo >= timedelta(days=dias) - timedelta(hours=1):
            resultado.add(f.nome)
    return resultado


def _ultimo_ok() -> dict[str, datetime]:
    with SessionLocal() as session:
        linhas = session.execute(
            select(FonteIngestao.fonte, func.max(FonteIngestao.concluido_em))
            .where(FonteIngestao.status == "ok")
            .group_by(FonteIngestao.fonte)
        ).all()
    return {fonte: quando for fonte, quando in linhas if quando}


def _executar(fonte: Fonte, hoje: date) -> int:
    executar = importlib.import_module(fonte.modulo).executar
    anos = anos_de(fonte, hoje)
    if anos is None:
        return executar(**fonte.args)
    return sum(executar(ano, **fonte.args) for ano in anos)


def rodar(nomes: set[str], fontes: list[Fonte]) -> int:
    """Roda as fontes em ordem de dependência. Uma falha não para as outras, mas quem
    depende da fonte que falhou é pulado. Devolve o número de falhas."""
    hoje = date.today()
    falharam: set[str] = set()
    historico = _ler_historico()
    for fonte in ordenar(fontes, nomes):
        if fonte.situacao != "ativa":
            print(
                f"[pulada] {fonte.nome}: catalogada, sem coleta (falta uso declarado)", flush=True
            )
            continue
        bloqueio = [d for d in fonte.depende if d in falharam]
        if bloqueio:
            print(f"[pulada] {fonte.nome}: depende de {', '.join(bloqueio)}", flush=True)
            falharam.add(fonte.nome)
            continue
        inicio = datetime.now(UTC)
        try:
            total = _executar(fonte, hoje)
            segundos = (datetime.now(UTC) - inicio).total_seconds()
            print(f"[ok]     {fonte.nome}: {total} registros em {segundos:.0f}s", flush=True)
            anterior = historico.get(fonte.nome)
            if queda(anterior, total):
                print(
                    f"[alerta] {fonte.nome}: {total} registros, contra {anterior} na execução "
                    f"anterior (queda de mais de {QUEDA:.0%}); conferir a fonte",
                    flush=True,
                )
            historico[fonte.nome] = total
            _gravar_historico(historico)
        except Exception:
            falharam.add(fonte.nome)
            print(f"[erro]   {fonte.nome}", flush=True)
            traceback.print_exc()
    return len(falharam)


def queda(anterior: int | None, atual: int | None, limite: float = QUEDA) -> bool:
    """A carga trouxe muito menos que a anterior? (Visto nas câmaras com SAPL parado: a
    fonte deixa de ser atualizada e a carga encolhe sem dar erro.)"""
    return bool(anterior) and atual is not None and atual < anterior * (1 - limite)


def _ler_historico() -> dict[str, int]:
    try:
        return json.loads(HISTORICO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _gravar_historico(historico: dict[str, int]) -> None:
    HISTORICO.parent.mkdir(parents=True, exist_ok=True)
    HISTORICO.write_text(json.dumps(historico, indent=1, sort_keys=True), encoding="utf-8")


def _tamanho_dir(caminho: Path) -> int:
    return sum(a.stat().st_size for a in caminho.rglob("*") if a.is_file())


def _mb(n: int) -> str:
    return f"{n / 1_000_000:,.1f}".replace(",", "_").replace(".", ",").replace("_", ".")


def relatorio(fontes: list[Fonte]) -> None:
    """Volume por fonte (bruto em disco) e por tabela (banco), e a última carga de cada
    fonte. É a base para decidir a infraestrutura de produção."""
    with SessionLocal() as session:
        ultimas = {
            fonte: (status, quando, registros)
            for fonte, status, quando, registros in session.execute(
                select(
                    FonteIngestao.fonte,
                    FonteIngestao.status,
                    FonteIngestao.concluido_em,
                    FonteIngestao.registros,
                )
                .distinct(FonteIngestao.fonte)
                .order_by(FonteIngestao.fonte, FonteIngestao.iniciado_em.desc())
            ).all()
        }
        banco = session.scalar(text("select pg_database_size(current_database())"))
        tabelas = session.execute(
            text(
                "select schemaname || '.' || relname, pg_total_relation_size(relid), n_live_tup"
                " from pg_stat_user_tables order by 2 desc limit 15"
            )
        ).all()
    print(f"Banco: {_mb(banco)} MB    Brutos em {comum.RAW_DIR}")
    print(f"\n{'fonte':28} {'situação':10} {'freq.':8} {'acesso':8} {'guarda':6} "
          f"{'última carga':17} {'status':7} {'registros':>10} {'bruto MB':>10}")  # fmt: skip
    total_bruto = 0
    for f in fontes:
        status, quando, registros = ultimas.get(f.nome, ("-", None, None))
        bruto = _tamanho_dir(comum.RAW_DIR / f.nome) if (comum.RAW_DIR / f.nome).exists() else 0
        total_bruto += bruto
        print(
            f"{f.nome:28} {f.situacao:10} {f.frequencia:8} {f.acesso:8} {f.guarda:6} "
            f"{quando.strftime('%d/%m/%Y %H:%M') if quando else '-':17} {status:7} "
            f"{registros if registros is not None else '-':>10} {_mb(bruto):>10}"
        )
    print(f"\nBrutos no total: {_mb(total_bruto)} MB")
    print("\nMaiores tabelas:")
    for nome, tamanho, linhas in tabelas:
        print(f"  {nome:45} {_mb(tamanho):>10} MB {linhas:>12} linhas")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acervo local do Panóptico")
    sub = parser.add_subparsers(dest="comando", required=True)
    p_rodar = sub.add_parser("rodar", help="Roda fontes do registro")
    grupo = p_rodar.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--fonte", nargs="+", help="Estas fontes (nomes do registro)")
    grupo.add_argument("--vencidas", action="store_true", help="As que passaram da frequência")
    sub.add_parser("relatorio", help="Volume e última carga de cada fonte")
    args = parser.parse_args(argv)

    fontes = ler_registro()
    if args.comando == "relatorio":
        relatorio(fontes)
        return 0
    if args.vencidas:
        nomes = vencidas(fontes, _ultimo_ok(), datetime.now(UTC))
    else:
        desconhecidas = set(args.fonte) - {f.nome for f in fontes}
        if desconhecidas:
            parser.error(f"fontes fora do registro: {sorted(desconhecidas)}")
        nomes = set(args.fonte)
    if not nomes:
        print("Nenhuma fonte a rodar.")
        return 0
    return 1 if rodar(nomes, fontes) else 0


if __name__ == "__main__":
    sys.exit(main())
