"""Assembleia Legislativa de Mato Grosso do Sul (ALEMS): deputados em exercício e gastos da
cota (CEAP), pelo site e pelo portal da transparência da Casa.

- Deputados: `al.ms.gov.br/Partidos/Lista`, os 24 agrupados por partido, com o código do perfil
  e a foto.
- Gastos: `transparencia2.al.ms.gov.br/ceap/notas/exportar-csv?ano=AAAA`, o CSV que o próprio
  portal oferece ("Exportar todos os lançamentos"): um lançamento por nota, com deputado
  ("DEP. HASHIOKA"), mês, categoria e valor ("R$ 4.669,65"). O arquivo começa com quatro linhas
  de identificação antes do cabeçalho. Somamos por deputado, mês e categoria, nos anos atual e
  anterior; o deputado é ligado pelo nome exato (sem o "DEP.").

Não entram proposições, votos nem presença: o sistema de proposições (sgpl.consulta.al.ms.gov.br)
é protegido por um desafio de prova de trabalho ("Validando acesso...") contra automação, que não
contornamos. Ver docs/DECISOES.md. Uma requisição por vez, com pausa.
"""

import argparse
import csv
import io
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal

from ingestion import comum
from ingestion.assembleias import base

FONTE = "alems"
SITE = "https://al.ms.gov.br"
LISTA = SITE + "/Partidos/Lista"
CEAP = "https://transparencia2.al.ms.gov.br/ceap/notas/exportar-csv"
MESES = {
    m: i
    for i, m in enumerate(
        "janeiro fevereiro março abril maio junho julho agosto".split()
        + "setembro outubro novembro dezembro".split(),
        1,
    )
}
# O CEAP escreve alguns nomes de outro jeito que a lista de partidos (abreviação, nome civil
# parcial); conferidos um a um contra a lista de deputados, que não tem outro com o mesmo nome.
APELIDOS = {
    "CEL DAVID": "Coronel David",
    "GLEICE JANE BARBOSA": "Gleice Jane",
    "PEDRO ARLEI CARAVINA": "Caravina",
    "PROFESSOR RINALDO": "Professor Rinaldo Modesto",
    "JOAO HENRIQUE MIRANDA SOARES CATAN": "João Henrique",
}
PARTIDO = re.compile(r'<div class="party-name"[^>]*>(?P<sigla>[^<]*)</div>')
CARTAO = re.compile(
    r'href="/Deputados/Visualizar/(?P<id>\d+)">\s*(?:<img src="(?P<foto>[^"]*)"[^>]*/>)?\s*'
    r'<div class="">(?P<nome>[^<]*)</div>'
)


def deputados(pagina: str) -> list[dict]:
    resultado = []
    for bloco in pagina.split('<div class="party" >')[1:]:
        sigla = base.limpo(PARTIDO.search(bloco).group("sigla"))  # type: ignore[union-attr]
        for c in CARTAO.finditer(bloco):
            resultado.append(
                {
                    "id": c["id"],
                    "nome": base.limpo(c["nome"]),
                    "partido": sigla.upper() if sigla.lower() == "união" else sigla,
                    "foto": SITE + c["foto"] if c["foto"] else None,
                    "url": f"{SITE}/Deputados/Visualizar/{c['id']}",
                }
            )
    return resultado


def lancamentos(texto: str) -> list[dict]:
    """Linhas do CSV do CEAP: pula as linhas de identificação antes do cabeçalho."""
    linhas = texto.lstrip("\ufeff").splitlines()
    inicio = next(i for i, linha in enumerate(linhas) if linha.startswith("Deputado;"))
    return list(csv.DictReader(io.StringIO("\n".join(linhas[inicio:])), delimiter=";"))


def _valor(texto: str) -> Decimal:
    return Decimal(texto.replace("R$", "").strip().replace(".", "").replace(",", "."))


def gastos(texto: str, por_nome: dict[str, str]) -> tuple[dict[str, list[dict]], int]:
    """Id do deputado -> gastos por ano, mês e categoria; e quantos lançamentos ficaram sem
    deputado ligado."""
    soma: dict[tuple, Decimal] = defaultdict(Decimal)
    sem_dono = 0
    for linha in lancamentos(texto):
        nome = re.sub(r"^(DEP\.|DEPUTAD[OA])\s*", "", linha["Deputado"].strip(), flags=re.I)
        chave = comum.chave_nome(nome)
        dono = por_nome.get(chave) or por_nome.get(comum.chave_nome(APELIDOS.get(chave)))
        mes = MESES.get(comum.chave_nome(linha["Mês"]).lower().replace("marco", "março"))
        if dono is None or mes is None:
            sem_dono += 1
            continue
        categoria = " ".join(linha["Categoria"].split())[:200]
        soma[(dono, int(linha["Ano"]), mes, categoria)] += _valor(linha["Valor (R$)"])
    resultado: dict[str, list[dict]] = defaultdict(list)
    for (dono, ano, mes, categoria), valor in soma.items():
        resultado[dono].append({"ano": ano, "mes": mes, "categoria": categoria, "valor": valor})
    return resultado, sem_dono


def coletar(hoje: date) -> dict:
    with comum.criar_cliente() as client:
        lista = deputados(comum._get(client, LISTA, None, 4).content.decode("utf-8", "replace"))
        por_nome = {comum.chave_nome(d["nome"]): d["id"] for d in lista}
        todos: dict[str, list[dict]] = defaultdict(list)
        for ano in (hoje.year - 1, hoje.year):
            texto = comum._get(client, CEAP, {"ano": ano}, 4).content.decode("utf-8-sig", "replace")
            por_deputado, sem_dono = gastos(texto, por_nome)
            for k, v in por_deputado.items():
                todos[k] += v
            print(f"  CEAP {ano}: {sem_dono} lançamentos sem deputado ligado", flush=True)
    return base.casa(LISTA, [base.registro(d, gastos=todos.get(d["id"])) for d in lista])


def executar() -> int:
    # A ALEMS tem 24 cadeiras: lista curta é falha da fonte.
    return base.gravar(
        coletar(date.today()), fonte=FONTE, uf="MS", sigla="ALEMS", url=LISTA, minimo=20
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
