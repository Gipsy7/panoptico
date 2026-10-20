"""Transferências obrigatórias da União a estados e municípios (Tesouro Transparente).

Repasses constitucionais e legais mês a mês: FPE (estados), FPM (municípios), IPI-Exportação
(parte dos estados) e as demais (CIDE, IOF-Ouro, ITR, LC 176). Entram na tabela
`transferencia_uniao` com `fonte = "tesouro"` e os blocos FPE, FPM, IPI_EXP e OUTRAS_OBRIG.

Fonte: CKAN do Tesouro Transparente, três conjuntos (os arquivos têm nome estável; a URL de
download sai de `package_show`):
- `transferencias-obrigatorias-da-uniao`: um CSV por tributo, linhas = estados, colunas = meses
  (`janeiro/24`...), desde 1991. Usados: `fpe`, `ipi-exp`, `cideest`, `iofest`, `lc176est`
  (valores, bloco por arquivo) e `fpm` (só para conferir a soma dos municípios).
- `transferencias-obrigatorias-da-uniao-por-municipio`: um CSV por tributo, linhas = município x
  mês (`Mês` 1 a 12), colunas = anos. Usados: `fpm`, `cide`, `iof`, `itr`, `lc-176`.
- `lista-de-municipios-do-siafi`: `tabmun.csv`, a tabela oficial código SIAFI x código IBGE.

Armadilhas (conferidas nos arquivos):
- Latin-1 (a leitura tenta UTF-8 e cai para Latin-1), `;`, vários cabeçalhos antes da tabela
  nos arquivos por estado, decimal com vírgula, milhar com ponto, espaços em volta, `-` = vazio.
  Colunas em branco no fim do arquivo.
- O ano vem com 2 dígitos nos arquivos por estado (`janeiro/24`); 51 a 99 = 1951 a 1999.
- Os valores do FPE, FPM e IPI-Exp são líquidos da retenção de 20% do Fundeb: o município
  contabiliza mais (FPM de 2024: R$ 177 bi aqui; ~R$ 214 bi brutos na contabilidade dele).
- O código da cidade é o do SIAFI (4 dígitos, com zero à esquerda), não o do IBGE. A ligação
  usa só a tabela oficial (`tabmun.csv`), nunca o nome. Código fora da tabela ou com UF
  diferente fica com `municipio_ibge` vazio (o valor continua na UF) e entra nos alertas.
- IPI-Exp: só a parte dos estados (a dos municípios é repassada por eles, não pela União).
- FEX e LC 87/96 (Kandir) estão zerados de 2019 em diante e não são lidos. O arquivo
  `fundeb-por-municipio` é o fundo inteiro (impostos de estados e municípios), não repasse da
  União, e também não é lido.
- FPM é guardado só por município (a soma dos municípios de uma UF é o FPM da UF; conferida
  contra `fpm.csv`); FPE e IPI-Exp só por UF. Para o mesmo bloco nunca os dois níveis, para
  que somar por UF não conte em dobro. OUTRAS_OBRIG tem a parte dos estados (linha sem
  município) e a dos municípios (linha com município), sem sobreposição.

Coleta mínima: o bruto é o recorte (só as colunas de 2019 em diante e as linhas de UF e
município), num zip. `carregar` sincroniza por diferença (insere o novo, corrige o que mudou,
apaga o que sumiu): a carga mensal mexe em poucas linhas.
"""

import argparse
import csv
import io
import unicodedata
import zipfile
from collections.abc import Container, Iterator
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import bindparam, delete, insert, select, update
from sqlalchemy.orm import Session

from app.models import FonteIngestao, TransferenciaUniao
from ingestion import comum

FONTE = "tesouro_transferencias"
FONTE_TABELA = "tesouro"  # valor de transferencia_uniao.fonte
URL = "https://www.tesourotransparente.gov.br/ckan/dataset/transferencias-obrigatorias-da-uniao"
CKAN = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
PACOTE_UF = "transferencias-obrigatorias-da-uniao"
PACOTE_MUNICIPIO = "transferencias-obrigatorias-da-uniao-por-municipio"
PACOTE_SIAFI = "lista-de-municipios-do-siafi"
ANO_INICIAL = 2019
UFS = frozenset(
    "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
)
ARQUIVOS_ESTADUAIS = {
    "fpe.csv": "FPE",
    "ipi-exp.csv": "IPI_EXP",
    "cideest.csv": "OUTRAS_OBRIG",
    "iofest.csv": "OUTRAS_OBRIG",
    "lc176est.csv": "OUTRAS_OBRIG",
}
ARQUIVOS_MUNICIPAIS = {
    "fpm-por-municipio.csv": "FPM",
    "cide-por-municipio.csv": "OUTRAS_OBRIG",
    "iof-por-municipio.csv": "OUTRAS_OBRIG",
    "itr-por-municipio.csv": "OUTRAS_OBRIG",
    "lc-176-por-municipio.csv": "OUTRAS_OBRIG",
}
ARQUIVO_CONFERENCIA = "fpm.csv"  # FPM por UF, para conferir a soma dos municípios
ARQUIVO_TABELA = "tabmun.csv"
BLOCOS = ("FPE", "FPM", "IPI_EXP", "OUTRAS_OBRIG")
MIN_TABELA = 5000  # a tabela SIAFI x IBGE tem ~5.590 linhas; bem menos é arquivo truncado
MESES = {
    nome: i
    for i, nome in enumerate(
        "janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro"
        " dezembro".split(),
        1,
    )
}
Chave = tuple[int, int, str, str | None, str]  # ano, mês, UF, município (IBGE), bloco


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c))


def decodificar(dados: bytes) -> str:
    """UTF-8 se for, senão Latin-1 (o padrão dos arquivos do Tesouro)."""
    try:
        return dados.decode("utf-8-sig")
    except UnicodeDecodeError:
        return dados.decode("latin-1")


def numero(texto: str | None) -> Decimal | None:
    """' 1.234,56 ' -> 1234.56; vazio e '-' -> None; '(1,50)' e '-1,50' -> negativo."""
    t = (texto or "").replace("R$", "").strip()
    if t in ("", "-"):
        return None
    negativo = t.startswith("(") and t.endswith(")")
    t = t.strip("()").strip()
    if t.startswith("-"):
        negativo, t = True, t[1:].strip()
    try:
        valor = Decimal(t.replace(".", "").replace(",", "."))
    except InvalidOperation as erro:
        raise ValueError(f"Valor inesperado no arquivo do Tesouro: {texto!r}") from erro
    return -valor if negativo else valor


def _coluna_mes(cabecalho: str) -> tuple[int, int] | None:
    """'março/24' -> (2024, 3); outra coisa -> None."""
    nome, barra, ano = _sem_acento(cabecalho.strip().lower()).partition("/")
    if barra and nome in MESES and ano.isdigit() and len(ano) == 2:
        n = int(ano)
        return n + (1900 if n > 50 else 2000), MESES[nome]
    return None


def _linhas(texto: str) -> Iterator[list[str]]:
    return csv.reader(io.StringIO(texto), delimiter=";")


def _cabecalho_estadual(linha: list[str]) -> list[tuple[int, int, int]]:
    """Colunas (posição, ano, mês) se a linha é o cabeçalho do arquivo por estado."""
    if len(linha) > 1 and linha[1].strip().upper() == "UF":
        return [(i, *m) for i, c in enumerate(linha) if (m := _coluna_mes(c))]
    return []


def ler_estadual(
    texto: str, anos: Container[int] | None = None
) -> Iterator[tuple[str, int, int, Decimal]]:
    """Arquivo por estado (linhas = UF, colunas = meses): (uf, ano, mês, valor), sem vazios."""
    colunas: list[tuple[int, int, int]] | None = None
    for linha in _linhas(texto):
        if colunas is None:
            achadas = _cabecalho_estadual(linha)
            if achadas:
                colunas = [(i, a, m) for i, a, m in achadas if anos is None or a in anos]
            continue
        uf = linha[1].strip() if len(linha) > 1 else ""
        if uf not in UFS:
            continue
        for i, ano, mes in colunas:
            valor = numero(linha[i]) if i < len(linha) else None
            if valor is not None:
                yield uf, ano, mes, valor
    if colunas is None:
        raise ValueError("Arquivo por estado do Tesouro sem o cabeçalho (ESTADOS;UF;mês/ano...).")


def anos_estadual(texto: str) -> set[int]:
    """Os anos que o arquivo por estado tem como coluna (mesmo sem valor)."""
    for linha in _linhas(texto):
        if achadas := _cabecalho_estadual(linha):
            return {a for _, a, _ in achadas}
    return set()


def _colunas_ano(cabecalho: list[str], anos: Container[int] | None) -> list[tuple[int, int]]:
    return [
        (i, int(c.strip()))
        for i, c in enumerate(cabecalho)
        if i >= 5 and c.strip().isdigit() and len(c.strip()) == 4
        if anos is None or int(c.strip()) in anos
    ]


def _abrir_municipal(texto: str) -> tuple[Iterator[list[str]], list[str]]:
    leitor = _linhas(texto)
    cabecalho = next(leitor, [])
    if [c.strip().upper() for c in cabecalho[:1]] != ["COD_MUN"]:
        raise ValueError(f"Cabeçalho inesperado no arquivo por município: {cabecalho[:3]}")
    return leitor, cabecalho


def _linha_municipal(linha: list[str]) -> bool:
    return len(linha) >= 5 and linha[0].strip().isdigit() and linha[4].strip().isdigit()


def ler_municipal(
    texto: str, anos: Container[int] | None = None
) -> Iterator[tuple[str, str, str, int, int, Decimal]]:
    """Arquivo por município (linha = município x mês, colunas = anos): (código SIAFI, nome, UF,
    ano, mês, valor), sem vazios."""
    leitor, cabecalho = _abrir_municipal(texto)
    colunas = _colunas_ano(cabecalho, anos)
    for linha in leitor:
        if not _linha_municipal(linha):
            continue
        cod, nome, uf, mes = linha[0].strip(), linha[1].strip(), linha[2].strip(), int(linha[4])
        for i, ano in colunas:
            valor = numero(linha[i]) if i < len(linha) else None
            if valor is not None:
                yield cod, nome, uf, ano, mes, valor


def anos_municipal(texto: str) -> set[int]:
    _, cabecalho = _abrir_municipal(texto)
    return {a for _, a in _colunas_ano(cabecalho, None)}


def ler_tabela_siafi(texto: str) -> dict[str, tuple[str, str]]:
    """tabmun.csv (sem cabeçalho: SIAFI;CNPJ;nome;UF;IBGE) -> {SIAFI: (UF, IBGE)}."""
    tabela = {}
    for linha in _linhas(texto):
        if len(linha) >= 5 and linha[0].strip().isdigit() and linha[4].strip().isdigit():
            tabela[linha[0].strip()] = (linha[3].strip(), linha[4].strip())
    return tabela


# --- recorte (o bruto guardado) ---------------------------------------------------------


def recortar_estadual(texto: str, anos: Container[int]) -> str:
    """Mantém o cabeçalho e só as colunas de mês dos anos pedidos, só as linhas de UF."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\n")
    manter: list[int] | None = None
    for linha in _linhas(texto):
        if manter is None:
            achadas = _cabecalho_estadual(linha)
            if achadas:
                manter = [i for i, a, _ in achadas if a in anos]
                escritor.writerow(linha[:2] + [linha[i] for i in manter])
            continue
        if len(linha) > 1 and linha[1].strip() in UFS:
            escritor.writerow(linha[:2] + [linha[i] if i < len(linha) else "" for i in manter])
    if manter is None:
        raise ValueError("Arquivo por estado do Tesouro sem o cabeçalho (ESTADOS;UF;mês/ano...).")
    return saida.getvalue()


def recortar_municipal(texto: str, anos: Container[int]) -> str:
    """Mantém as 5 primeiras colunas e as colunas dos anos pedidos, só linhas de município."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\n")
    leitor, cabecalho = _abrir_municipal(texto)
    manter = [i for i, _ in _colunas_ano(cabecalho, anos)]
    escritor.writerow(cabecalho[:5] + [cabecalho[i] for i in manter])
    for linha in leitor:
        if _linha_municipal(linha):
            escritor.writerow(linha[:5] + [linha[i] if i < len(linha) else "" for i in manter])
    return saida.getvalue()


def montar_recorte(arquivos: dict[str, bytes]) -> bytes:
    """Zip determinístico (data fixa): o mesmo conteúdo dá os mesmos bytes, e a carga
    incremental reconhece "sem mudança" pelo sha256."""
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for nome in sorted(arquivos):
            info = zipfile.ZipInfo(nome, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, arquivos[nome])
    return saida.getvalue()


# --- download ---------------------------------------------------------------------------


def _urls_do_pacote(client: httpx.Client, pacote: str) -> dict[str, str]:
    """{nome do arquivo: URL de download} dos recursos CSV do conjunto no CKAN."""
    dados = comum.get_json(client, CKAN, {"id": pacote})
    urls = {}
    for recurso in dados["result"]["resources"]:
        url = recurso.get("url") or ""
        if url.lower().endswith(".csv"):
            urls[url.rsplit("/", 1)[-1].lower()] = url
    return urls


def _baixar_csv(client: httpx.Client, urls: dict[str, str], nome: str) -> str:
    if nome not in urls:
        raise ValueError(f"O Tesouro não lista mais o arquivo {nome}; conferir o conjunto no CKAN.")
    return decodificar(comum.get_bytes(client, urls[nome]))


def baixar(client: httpx.Client, anos: Container[int]) -> bytes:
    """Baixa os arquivos usados e devolve o recorte (zip). Os arquivos grandes (30 MB) são
    reduzidos um a um, para não ficarem todos na memória."""
    client.headers["Accept"] = "*/*"  # o padrão do cliente comum é JSON; aqui são CSVs
    recorte: dict[str, bytes] = {}
    estaduais = _urls_do_pacote(client, PACOTE_UF)
    for nome in [*ARQUIVOS_ESTADUAIS, ARQUIVO_CONFERENCIA]:
        recorte[nome] = recortar_estadual(_baixar_csv(client, estaduais, nome), anos).encode()
    municipais = _urls_do_pacote(client, PACOTE_MUNICIPIO)
    for nome in ARQUIVOS_MUNICIPAIS:
        recorte[nome] = recortar_municipal(_baixar_csv(client, municipais, nome), anos).encode()
    tabela = _urls_do_pacote(client, PACOTE_SIAFI)
    recorte[ARQUIVO_TABELA] = _baixar_csv(client, tabela, ARQUIVO_TABELA).encode()
    return montar_recorte(recorte)


# --- leitura do recorte -----------------------------------------------------------------


def ler_recorte(payload: bytes) -> tuple[dict[Chave, Decimal], set[int], list[str]]:
    """Do zip de recorte para as linhas da tabela: {(ano, mês, UF, IBGE, bloco): valor},
    os anos cobertos (têm coluna no arquivo, mesmo sem valor) e os alertas."""
    avisos: list[str] = []
    soma: dict[Chave, Decimal] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        textos = {n: decodificar(z.read(n)) for n in z.namelist()}
    esperados = [*ARQUIVOS_ESTADUAIS, ARQUIVO_CONFERENCIA, *ARQUIVOS_MUNICIPAIS, ARQUIVO_TABELA]
    if faltam := [n for n in esperados if n not in textos]:
        raise ValueError(f"Recorte do Tesouro sem os arquivos: {', '.join(faltam)}")
    tabela = ler_tabela_siafi(textos[ARQUIVO_TABELA])
    if len(tabela) < MIN_TABELA:
        raise ValueError(f"Tabela SIAFI x IBGE com só {len(tabela)} municípios; abortando.")

    anos: set[int] = set()
    for nome, bloco in ARQUIVOS_ESTADUAIS.items():
        anos |= anos_estadual(textos[nome])
        for uf, ano, mes, valor in ler_estadual(textos[nome]):
            chave = (ano, mes, uf, None, bloco)
            soma[chave] = soma.get(chave, Decimal(0)) + valor

    nao_casados: dict[tuple[str, str, str], Decimal] = {}
    fpm_municipios: dict[int, Decimal] = {}
    for nome, bloco in ARQUIVOS_MUNICIPAIS.items():
        anos |= anos_municipal(textos[nome])
        for cod, cidade, uf, ano, mes, valor in ler_municipal(textos[nome]):
            achado = tabela.get(cod)
            ibge = achado[1] if achado and achado[0] == uf else None
            if ibge is None:
                par = (cod, uf, cidade)
                nao_casados[par] = nao_casados.get(par, Decimal(0)) + valor
            chave = (ano, mes, uf, ibge, bloco)
            soma[chave] = soma.get(chave, Decimal(0)) + valor
            if bloco == "FPM":
                fpm_municipios[ano] = fpm_municipios.get(ano, Decimal(0)) + valor
    if nao_casados:
        total = sum(nao_casados.values())
        nomes = "; ".join(f"{c}/{u} {n}" for (c, u, n) in sorted(nao_casados))
        avisos.append(
            f"{len(nao_casados)} município(s) do Tesouro fora da tabela SIAFI x IBGE"
            f" (R$ {total:,.2f}"
            f" ficam só na UF, sem município): {nomes}"
        )

    fpm_uf: dict[int, Decimal] = {}
    for _, ano, _, valor in ler_estadual(textos[ARQUIVO_CONFERENCIA]):
        fpm_uf[ano] = fpm_uf.get(ano, Decimal(0)) + valor
    for ano in sorted(fpm_uf):
        dif = fpm_municipios.get(ano, Decimal(0)) - fpm_uf[ano]
        if abs(dif) > Decimal("1.00"):
            avisos.append(
                f"FPM {ano}: soma dos municípios difere do total das UFs em R$ {dif:,.2f}"
            )
    linhas = {k: v.quantize(Decimal("0.01")) for k, v in soma.items() if v != 0}
    return linhas, anos, avisos


# --- banco ------------------------------------------------------------------------------


def sincronizar(
    session: Session,
    fonte: str,
    escopo: list[Any],
    novas: dict[Chave, Decimal],
    ingestao_id: int | None,
) -> tuple[int, int, int]:
    """Deixa as linhas do `escopo` (condições SQL sobre TransferenciaUniao, da `fonte`) iguais a
    `novas`: insere o que falta, corrige o valor que mudou, apaga o que sumiu. Devolve
    (inseridas, corrigidas, apagadas). Carga repetida não mexe em nada."""
    t = TransferenciaUniao
    existentes: dict[Chave, list[tuple[int, Decimal]]] = {}
    consulta = select(t.id, t.ano, t.mes, t.uf, t.municipio_ibge, t.bloco, t.valor).where(
        t.fonte == fonte, *escopo
    )
    for id_, ano, mes, uf, ibge, bloco, valor in session.execute(consulta):
        existentes.setdefault((ano, mes, uf, ibge, bloco), []).append((id_, valor))

    apagar: list[int] = []
    corrigir: list[dict[str, Any]] = []
    for chave, itens in existentes.items():
        novo = novas.get(chave)
        if novo is None:
            apagar.extend(i for i, _ in itens)
            continue
        apagar.extend(i for i, _ in itens[1:])  # duplicata da mesma chave
        if itens[0][1] != novo:
            corrigir.append({"b_id": itens[0][0], "b_valor": novo, "b_ingestao": ingestao_id})
    inserir = [
        {
            "ano": ano, "mes": mes, "uf": uf, "municipio_ibge": ibge, "bloco": bloco,
            "fonte": fonte, "valor": valor, "ingestao_id": ingestao_id,
        }
        for (ano, mes, uf, ibge, bloco), valor in novas.items()
        if (ano, mes, uf, ibge, bloco) not in existentes
    ]  # fmt: skip
    for inicio in range(0, len(apagar), 5000):
        session.execute(delete(t).where(t.id.in_(apagar[inicio : inicio + 5000])))
    if corrigir:
        atualizar = (
            update(t)
            .where(t.id == bindparam("b_id"))
            .values(valor=bindparam("b_valor"), ingestao_id=bindparam("b_ingestao"))
        )
        for inicio in range(0, len(corrigir), 5000):
            session.connection().execute(atualizar, corrigir[inicio : inicio + 5000])
    for inicio in range(0, len(inserir), 5000):
        session.execute(insert(t), inserir[inicio : inicio + 5000])
    return len(inserir), len(corrigir), len(apagar)


def carregar(session: Session, payload: bytes, ingestao: FonteIngestao) -> int:
    linhas, anos, avisos = ler_recorte(payload)
    ufs_fpe = {k[2] for k in linhas if k[4] == "FPE"}
    if len(ufs_fpe) != 27 or not any(k[4] == "FPM" for k in linhas):
        raise ValueError(f"Recorte do Tesouro sem FPE de 27 UFs ou sem FPM ({len(ufs_fpe)} UFs).")
    t = TransferenciaUniao
    inseridas, corrigidas, apagadas = sincronizar(
        session, FONTE_TABELA, [t.ano.in_(sorted(anos)), t.bloco.in_(BLOCOS)], linhas, ingestao.id
    )
    print(
        f"  Tesouro {min(anos)}-{max(anos)}: {len(linhas)} linhas ({inseridas} novas, "
        f"{corrigidas} corrigidas, {apagadas} apagadas)",
        flush=True,
    )
    ingestao.alertas = avisos or None
    ingestao.total_fonte = len(linhas)
    return len(linhas)


def executar(anos: list[int] | int | None = None, de_raw: Path | None = None) -> int:
    """Sem `anos`: o ano anterior e o atual (o Tesouro corrige pouco para trás). A carga inicial
    passa todos: `--ano 2019 2020 ...`."""
    hoje = date.today().year
    if isinstance(anos, int):
        anos = [anos]
    pedidos = set(anos) if anos else {hoje - 1, hoje}
    if min(pedidos) < ANO_INICIAL:
        raise ValueError(f"Antes de {ANO_INICIAL} não se guarda (recorte da fonte).")
    faixa = f"{min(pedidos)}-{max(pedidos)}"
    return comum.executar_ingestao(
        FONTE,
        URL,
        lambda client: baixar(client, pedidos),
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{faixa}_",
        incremental=comum.Incremental(chave=f"{FONTE}:{faixa}"),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", help="Anos (padrão: o anterior e o atual)")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um recorte bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(args.ano, de_raw=args.de_raw)} linhas")
