"""Emendas parlamentares (Portal da Transparência, arquivo único em lote).

O arquivo traz todas as emendas desde 2014 (CSV em latin-1, separador `;`), e todas ficam
(desde 18/10/2026; antes, só da legislatura atual). O autor vem com um código do sistema de
orçamento e o nome em maiúsculas. Ligamos o par (código, nome) ao parlamentar pelo nome,
comparando sem acentos e sem pontuação, só com correspondência exata e única; se o nome não
casar, vale o nome mais recente do mesmo código ("AUREO" -> "AUREO RIBEIRO"), exceto quando
o nome traz "(EX-PARLAMENTAR ...)": aí o código passou a outra pessoa (art. 78 da LDO 2025,
ADPF 854) e só o nome antes do parêntese conta.

Do arquivo por favorecido ficam os valores **pagos** de emendas de todos os tipos
(individual, transferência especial/Pix, bancada, comissão e relator) recebidos por
prefeituras, fundos municipais e entidades sem fins lucrativos, que é o que chega de fato a
cada cidade. Bancos intermediários (Caixa, BB) e empresas ficam de fora: estão sediados em
uma cidade e executam em outra. O município vem só por nome e UF e é ligado ao código do
IBGE pelo nome, com correspondência aproximada dentro da UF.

Linhas com código da emenda "Sem informação" (emendas de 2014 a 2020 sem identificação na
base da CGU, pagas de 2015 em diante) trazem o tipo de emenda e o mês do pagamento, mas não o
autor nem o ano da emenda. Vão para `emenda_pagamento_sem_codigo` com o tipo da fonte e o
autor como veio, sem ligação a parlamentar ou pessoa (docs/DECISOES.md, 20/10/2026).

Autor fora do cargo (sem parlamentar em exercício) é ligado a `pessoa` só por nome idêntico
e único entre os eleitos para a Câmara e o Senado (vínculo forte); nome parecido não liga.
"""

import argparse
import csv
import difflib
import io
import zipfile
from collections import Counter
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.models import (
    Candidatura,
    Emenda,
    EmendaConvenio,
    EmendaPagamento,
    EmendaPagamentoSemCodigo,
    FonteIngestao,
    Municipio,
    Parlamentar,
    PessoaVinculo,
)
from app.models.pessoa import REGRAS_FORTES
from ingestion import comum
from ingestion.ibge import nomes_anteriores

FONTE = "transparencia_emendas"
URL = "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO"
ARQUIVO = "EmendasParlamentares.csv"
ARQUIVO_FAVORECIDOS = "EmendasParlamentares_PorFavorecido.csv"
ARQUIVO_CONVENIOS = "EmendasParlamentares_Convenios.csv"
SEM_INFORMACAO = "Sem informação"
GRUPOS = {
    "Município": "prefeitura",
    "Fundo Público da Administração Direta Municipal": "prefeitura",
    "Associação Privada": "entidade",
    "Fundação Privada": "entidade",
}
TIPOS = {
    "Emenda Individual - Transferências com Finalidade Definida": "individual",
    "Emenda Individual - Transferências Especiais": "especial",
    "Emenda de Bancada": "bancada",
    "Emenda de Comissão": "comissao",
    "Emenda de Relator": "relator",
}
# Autor é uma pessoa (deputado ou senador); nos outros tipos é um colegiado.
TIPOS_INDIVIDUAIS = {"individual", "especial"}
CARGOS_AUTORES = ("DEPUTADO FEDERAL", "SENADOR")


def _valor(texto: str) -> Decimal:
    return Decimal((texto or "0").replace(".", "").replace(",", ".") or "0")


def _info(texto: str) -> str | None:
    texto = (texto or "").strip()
    return None if not texto or texto == SEM_INFORMACAO else texto


def tipo_curto(texto: str) -> str | None:
    texto = (texto or "").strip()
    if texto in TIPOS:
        return TIPOS[texto]
    return "individual" if texto.startswith("Emenda Individual") else None


def nome_base(nome: str) -> str:
    """ "TIAGO DIMAS (EX-PARLAMENTAR LAZARO BOTELHO, ...)" -> "TIAGO DIMAS"."""
    return nome.split(" (")[0].strip()


def normalizar(conteudo_zip: bytes, ano_minimo: int = 0) -> list[dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z:
        texto = z.read(ARQUIVO).decode("latin-1")
    registros = []
    for linha in csv.DictReader(io.StringIO(texto), delimiter=";"):
        ano = int(linha["Ano da Emenda"])
        if ano < ano_minimo:
            continue
        tipo = linha["Tipo de Emenda"].strip()
        registros.append(
            {
                "codigo": linha["Código da Emenda"].strip(),
                "ano": ano,
                "tipo": tipo,
                "individual": tipo.startswith("Emenda Individual"),
                "autor_codigo": linha["Código do Autor da Emenda"].strip(),
                "autor_nome": linha["Nome do Autor da Emenda"].strip()[:200],
                "localidade": linha["Localidade de aplicação do recurso"].strip(),
                "municipio_ibge": _info(linha["Código Município IBGE"]),
                "uf": _info(linha["UF"]),
                "funcao": _info(linha["Nome Função"]),
                "acao": _info(linha["Nome Ação"]),
                "valor_empenhado": _valor(linha["Valor Empenhado"]),
                # Pago no ano + restos a pagar pagos nos anos seguintes.
                "valor_pago": _valor(linha["Valor Pago"])
                + _valor(linha["Valor Restos A Pagar Pagos"]),
            }
        )
    return registros


def normalizar_pagamentos(
    conteudo_zip: bytes,
    ano_minimo: int = 0,
    descartes: Counter | None = None,
    sem_codigo: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Lê o arquivo por favorecido em fluxo (são centenas de MB descomprimidos).

    `descartes` (opcional) conta, para os favorecidos que interessam, as linhas que ficaram
    de fora e o valor delas: sem código de emenda ("Sem informação") e tipo desconhecido.
    `sem_codigo` (opcional) recebe as linhas sem código de emenda: a fonte traz o tipo e o
    mês do pagamento, mas não o autor nem o ano da emenda (vão para
    `emenda_pagamento_sem_codigo`, nunca ligadas a autor)."""
    registros = []
    with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z, z.open(ARQUIVO_FAVORECIDOS) as f:
        for linha in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
            grupo = GRUPOS.get(linha["Natureza Jurídica"].strip())
            if grupo is None:
                continue
            codigo = linha["Código da Emenda"].strip()
            tipo = tipo_curto(linha["Tipo de Emenda"])
            if not codigo[:4].isdigit() or tipo is None:
                motivo = "sem_codigo" if not codigo[:4].isdigit() else "tipo_desconhecido"
                if descartes is not None:
                    descartes[motivo] += 1
                    descartes[f"{motivo}_valor"] += _valor(linha["Valor Recebido"])
                if sem_codigo is not None and motivo == "sem_codigo":
                    sem_codigo.append(
                        {
                            "ano_mes": int(linha["Ano/Mês"]),
                            "tipo": tipo,
                            "autor_codigo": linha["Código do Autor da Emenda"].strip()[:20],
                            "autor_nome": linha["Nome do Autor da Emenda"].strip()[:200],
                            "favorecido": linha["Favorecido"].strip()[:300],
                            "favorecido_codigo": linha["Código do Favorecido"].strip(),
                            "natureza": linha["Natureza Jurídica"].strip(),
                            "grupo": grupo,
                            "uf": linha["UF Favorecido"].strip(),
                            "municipio_nome": linha["Município Favorecido"].strip(),
                            "valor": _valor(linha["Valor Recebido"]),
                        }
                    )
                continue
            if int(codigo[:4]) < ano_minimo:
                continue
            registros.append(
                {
                    "emenda_codigo": codigo,
                    "ano_emenda": int(codigo[:4]),
                    "ano_mes": int(linha["Ano/Mês"]),
                    "autor_codigo": linha["Código do Autor da Emenda"].strip(),
                    "autor_nome": linha["Nome do Autor da Emenda"].strip()[:200],
                    "tipo": tipo,
                    "favorecido": linha["Favorecido"].strip(),
                    "favorecido_codigo": linha["Código do Favorecido"].strip(),
                    "natureza": linha["Natureza Jurídica"].strip(),
                    "grupo": grupo,
                    "uf": linha["UF Favorecido"].strip(),
                    "municipio_nome": linha["Município Favorecido"].strip(),
                    "valor": _valor(linha["Valor Recebido"]),
                }
            )
    return registros


def normalizar_convenios(conteudo_zip: bytes, ano_minimo: int = 0) -> list[dict[str, Any]]:
    """Pares (emenda, convênio) do arquivo de convênios das emendas. Há linhas com código
    "Sem informação": sem emenda identificada, não há a quem ligar."""
    pares: dict[tuple[str, str], dict[str, Any]] = {}
    with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z, z.open(ARQUIVO_CONVENIOS) as f:
        for linha in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
            codigo = linha["Código da Emenda"].strip()
            numero = linha["Número Convênio"].strip()
            if not codigo[:4].isdigit() or int(codigo[:4]) < ano_minimo or not numero:
                continue
            pares[(codigo, numero)] = {"emenda_codigo": codigo, "numero_convenio": numero}
    return list(pares.values())


def resolver_municipios(
    pagamentos: list[dict[str, Any]],
    municipios: list[tuple[str, str, str]],
    descartes: Counter | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Troca (UF, nome) pelo código IBGE. Devolve os resolvidos e quantos ficaram de fora.

    Ordem: nome atual exato; nome anterior registrado pelo IBGE (`data/municipios_nome*.csv`,
    nunca por semelhança); grafia muito parecida (corte 0,88). Quem sobra é contado em
    `descartes` por (UF, nome), com linhas e valor, para a carga registrar no log."""
    exato = {(uf, chave): ibge for ibge, uf, chave in municipios}
    por_uf: dict[str, dict[str, str]] = {}
    for ibge, uf, chave in municipios:
        por_uf.setdefault(uf, {})[chave] = ibge
    anteriores = nomes_anteriores.carregar_apelidos()

    cache: dict[tuple[str, str], tuple[str | None, str]] = {}

    def resolver(uf: str, nome: str) -> tuple[str | None, str]:
        chave = comum.chave_nome(nome)
        if (uf, chave) not in cache:
            ibge, como = exato.get((uf, chave)), "exato"
            if ibge is None and (uf, chave) in anteriores:
                ibge, como = anteriores[(uf, chave)], "nome_anterior"
            if ibge is None:  # grafias antigas: "SANTANA DO LIVRAMENTO", "ITAPAGE"...
                proximos = difflib.get_close_matches(chave, por_uf.get(uf, {}), n=1, cutoff=0.88)
                ibge, como = (por_uf[uf][proximos[0]], "aproximado") if proximos else (None, "sem")
            cache[(uf, chave)] = (ibge, como)
        return cache[(uf, chave)]

    resolvidos, fora = [], 0
    for p in pagamentos:
        ibge, _ = resolver(p["uf"], p["municipio_nome"])
        if ibge is None:
            fora += 1
            if descartes is not None:
                descartes[f"sem_municipio:{p['uf']}/{p['municipio_nome']}"] += 1
                descartes[f"sem_municipio_valor:{p['uf']}/{p['municipio_nome']}"] += p.get(
                    "valor", 0
                )
            continue
        resto = {k: v for k, v in p.items() if k not in ("uf", "municipio_nome")}
        resolvidos.append({**resto, "municipio_ibge": ibge})
    return resolvidos, fora


def resumir_sem_municipio(descartes: Counter, maiores: int = 8) -> str:
    """Texto do log: total de linhas e valor sem município e os maiores nomes."""
    prefixo = "sem_municipio:"
    nomes = [k[len(prefixo) :] for k in descartes if k.startswith(prefixo)]
    valor = {n: descartes[f"sem_municipio_valor:{n}"] for n in nomes}
    linhas = sum(descartes[f"{prefixo}{n}"] for n in nomes)
    topo = sorted(nomes, key=lambda n: valor[n], reverse=True)[:maiores]
    detalhe = "; ".join(f"{n} ({descartes[prefixo + n]}, R$ {valor[n]:,.2f})" for n in topo)
    return f"{linhas} linhas, R$ {sum(valor.values()):,.2f}" + (
        f". Maiores: {detalhe}" if topo else ""
    )


Par = tuple[str, str]  # (código do autor, nome do autor como veio)


def vincular_autores(
    autores: Iterable[tuple[str, str, int]], parlamentares: list[tuple[int, str]]
) -> dict[Par, int]:
    """(código, nome) do autor -> id do parlamentar.

    `autores` são trincas (código, nome, ano) dos autores individuais. Primeiro pelo próprio
    nome (sem o "(EX-PARLAMENTAR ...)"); se não casar, pelo nome mais recente do mesmo
    código, desde que nenhum dos dois traga o parêntese (código que mudou de dono). Nomes
    que batem com mais de um parlamentar ficam sem vínculo."""
    por_nome: dict[str, set[int]] = {}
    for id_, nome in parlamentares:
        por_nome.setdefault(comum.chave_nome(nome), set()).add(id_)

    def unico(nome: str) -> int | None:
        candidatos = por_nome.get(comum.chave_nome(nome_base(nome)), set())
        return next(iter(candidatos)) if len(candidatos) == 1 else None

    pares: set[Par] = set()
    recente: dict[str, tuple[int, str]] = {}
    for codigo, nome, ano in autores:
        pares.add((codigo, nome))
        if "(" in nome:
            continue
        atual = recente.get(codigo)
        if atual is None or ano > atual[0]:
            recente[codigo] = (ano, nome)

    vinculos: dict[Par, int] = {}
    for codigo, nome in pares:
        id_ = unico(nome)
        if id_ is None and "(" not in nome and codigo in recente:
            id_ = unico(recente[codigo][1])
        if id_ is not None:
            vinculos[(codigo, nome)] = id_
    return vinculos


def vincular_pessoas(
    session: Session, pares: Iterable[Par], vinculos: dict[Par, int]
) -> tuple[dict[Par, int], int]:
    """(código, nome) -> pessoa_id, por vínculo forte. Devolve também quantos autores
    individuais ficaram sem pessoa.

    - Autor ligado a parlamentar: a pessoa do parlamentar (vínculo publicável).
    - Os outros: nome idêntico (sem acento e pontuação) ao nome civil ou de urna de um eleito
      para deputado federal ou senador, ligado a uma única pessoa publicável. Nome parecido
      não liga (iria para revisão humana)."""
    publicavel = PessoaVinculo.regra.in_(REGRAS_FORTES) | PessoaVinculo.revisado.is_(True)
    pessoa_do_parlamentar = dict(
        session.execute(
            select(Parlamentar.id, PessoaVinculo.pessoa_id)
            .join(
                PessoaVinculo,
                (PessoaVinculo.fonte == "parlamentar")
                & (
                    PessoaVinculo.id_externo
                    == func.concat(Parlamentar.casa, ":", Parlamentar.id_externo)
                ),
            )
            .where(publicavel)
        ).all()
    )
    por_nome: dict[str, set[int]] = {}
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
            Candidatura.cargo.in_(CARGOS_AUTORES),
            Candidatura.situacao_turno.like("ELEITO%"),
            publicavel,
        )
    ).all()
    for nome, nome_urna, pessoa_id in eleitos:
        for chave in {comum.chave_nome(nome), comum.chave_nome(nome_urna)} - {""}:
            por_nome.setdefault(chave, set()).add(pessoa_id)

    saida: dict[Par, int] = {}
    sem = 0
    for par in set(pares):
        if par in vinculos:
            pessoa_id = pessoa_do_parlamentar.get(vinculos[par])
        else:
            candidatos = por_nome.get(comum.chave_nome(nome_base(par[1])), set())
            pessoa_id = next(iter(candidatos)) if len(candidatos) == 1 else None
        if pessoa_id is None:
            sem += 1
        else:
            saida[par] = pessoa_id
    return saida, sem


def carregar(session: Session, conteudo: bytes, ingestao: FonteIngestao) -> int:
    registros = normalizar(conteudo)
    if not registros:
        raise ValueError("Nenhuma emenda no arquivo; abortando.")
    municipios = session.execute(select(Municipio.ibge, Municipio.uf, Municipio.nome_chave)).all()
    if not municipios:
        raise ValueError("Tabela de municípios vazia; rode ingestion.ibge.municipios antes.")
    descartes: Counter = Counter()
    brutos_sem_codigo: list[dict[str, Any]] = []
    lista_municipios = [tuple(m) for m in municipios]
    sem_municipio: Counter = Counter()
    pagamentos, fora = resolver_municipios(
        normalizar_pagamentos(conteudo, descartes=descartes, sem_codigo=brutos_sem_codigo),
        lista_municipios,
        sem_municipio,
    )
    if not pagamentos:
        raise ValueError("Nenhum pagamento por favorecido no arquivo; abortando.")
    sem_codigo, fora_sem_codigo = resolver_municipios(
        brutos_sem_codigo, lista_municipios, sem_municipio_sem_codigo := Counter()
    )
    print(f"  com código, sem município: {resumir_sem_municipio(sem_municipio)}")
    print(f"  sem código, sem município: {resumir_sem_municipio(sem_municipio_sem_codigo)}")
    print(
        f"  pagamentos sem código de emenda (tipo da fonte, sem autor nem ano): "
        f"{descartes['sem_codigo']} linhas, R$ {descartes['sem_codigo_valor']:,.2f}; "
        f"gravados {len(sem_codigo)}, sem município identificado {fora_sem_codigo}"
    )
    if descartes["tipo_desconhecido"]:
        print(
            f"  pagamentos com código e tipo desconhecido (fora): "
            f"{descartes['tipo_desconhecido']} linhas, "
            f"R$ {descartes['tipo_desconhecido_valor']:,.2f}"
        )

    autores = [
        (r["autor_codigo"], r["autor_nome"], r["ano"]) for r in registros if r["individual"]
    ] + [
        (p["autor_codigo"], p["autor_nome"], p["ano_emenda"])
        for p in pagamentos
        if p["tipo"] in TIPOS_INDIVIDUAIS
    ]
    parlamentares = session.execute(select(Parlamentar.id, Parlamentar.nome_parlamentar)).all()
    vinculos = vincular_autores(autores, [(p.id, p.nome_parlamentar) for p in parlamentares])
    pessoas, sem_pessoa = vincular_pessoas(session, {(c, n) for c, n, _ in autores}, vinculos)
    print(
        f"  autores individuais: {len({(c, n) for c, n, _ in autores})}; ligados a parlamentar: "
        f"{len(vinculos)}; a pessoa: {len(pessoas)}; sem pessoa (nome sem par exato): "
        f"{sem_pessoa}"
    )

    session.execute(delete(Emenda))
    linhas = [
        {
            **r,
            "parlamentar_id": (
                vinculos.get((r["autor_codigo"], r["autor_nome"])) if r["individual"] else None
            ),
            "ingestao_id": ingestao.id,
        }
        for r in registros
    ]
    for inicio in range(0, len(linhas), 5000):
        session.execute(insert(Emenda), linhas[inicio : inicio + 5000])

    session.execute(delete(EmendaPagamento))
    pagamentos = [
        {
            **p,
            "parlamentar_id": vinculos.get((p["autor_codigo"], p["autor_nome"]))
            if p["tipo"] in TIPOS_INDIVIDUAIS
            else None,
            "pessoa_id": pessoas.get((p["autor_codigo"], p["autor_nome"]))
            if p["tipo"] in TIPOS_INDIVIDUAIS
            else None,
            "ingestao_id": ingestao.id,
        }
        for p in pagamentos
    ]
    for inicio in range(0, len(pagamentos), 5000):
        session.execute(insert(EmendaPagamento), pagamentos[inicio : inicio + 5000])
    session.execute(delete(EmendaPagamentoSemCodigo))
    sem_codigo = [{**p, "ingestao_id": ingestao.id} for p in sem_codigo]
    for inicio in range(0, len(sem_codigo), 5000):
        session.execute(insert(EmendaPagamentoSemCodigo), sem_codigo[inicio : inicio + 5000])
    convenios = normalizar_convenios(conteudo)
    session.execute(delete(EmendaConvenio))
    for inicio in range(0, len(convenios), 5000):
        session.execute(
            insert(EmendaConvenio),
            [{**c, "ingestao_id": ingestao.id} for c in convenios[inicio : inicio + 5000]],
        )
    print(f"  convênios ligados a emendas: {len(convenios)}")
    return len(linhas) + len(pagamentos) + len(sem_codigo)


# Sobe quando a carga passa a gravar algo novo do mesmo arquivo (força uma releitura).
VERSAO_CARGA = "2026-10-20:sem_codigo"


def contexto(session: Session) -> str:
    """Muda quando entram parlamentares ou pessoas novas (religa autores com o arquivo igual)."""
    total, maior = session.execute(
        select(func.count(Parlamentar.id), func.max(Parlamentar.id))
    ).one()
    return f"{VERSAO_CARGA}:parlamentares:{total}:{maior}:{comum.contexto_pessoas(session)}"


def executar(de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> bytes:
        return comum.get_bytes(client, URL)

    return comum.executar_ingestao(
        FONTE,
        URL,
        baixar,
        carregar,
        de_raw=de_raw,
        # O arquivo da CGU muda poucas vezes por semana: com o mesmo sha256 (e os mesmos
        # parlamentares e pessoas), não regrava as ~400 mil linhas.
        incremental=comum.Incremental(chave=FONTE, contexto=contexto),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} registros (emendas + pagamentos)")
