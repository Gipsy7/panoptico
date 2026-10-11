"""LEIAME.md e dicionario.json: o que cada arquivo tem, de onde veio e quando foi a carga."""

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Connection, text

from exportar.conjuntos import Conjunto

VERSAO_ESQUEMA = 1
REPOSITORIO = "https://github.com/Gipsy7/Panoptico"
LICENCA = {
    "nome": "Creative Commons Atribuição 4.0 Internacional (CC BY 4.0)",
    "url": "https://creativecommons.org/licenses/by/4.0/deed.pt-br",
}


def ultimas_cargas(conn: Connection, fontes: tuple[str, ...]) -> list[dict]:
    """Dia/hora da última carga bem-sucedida de cada fonte (fonte_ingestao)."""
    linhas = conn.execute(
        text(
            """SELECT fonte, max(coalesce(concluido_em, iniciado_em)) AS ultima
               FROM fonte_ingestao
               WHERE fonte = ANY(:fontes) AND status IN ('ok', 'sem_mudanca')
               GROUP BY fonte"""
        ),
        {"fontes": list(fontes)},
    ).all()
    por_fonte = {f: u for f, u in linhas}
    return [
        {"fonte": f, "ultima_carga": por_fonte[f].isoformat() if f in por_fonte else None}
        for f in fontes
    ]


def montar_dicionario(
    conn: Connection, conjuntos: tuple[Conjunto, ...], resultados: dict[str, dict]
) -> dict:
    return {
        "versao_esquema": VERSAO_ESQUEMA,
        "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "projeto": REPOSITORIO,
        "licenca": LICENCA,
        "conjuntos": [
            {
                "nome": c.nome,
                "titulo": c.titulo,
                "descricao": c.descricao,
                "fonte_oficial": {"orgao": c.orgao, "url": c.url},
                "cargas": ultimas_cargas(conn, c.fontes),
                "o_que_fica_de_fora": c.filtros,
                "linhas": resultados[c.nome]["linhas"],
                "arquivos": {
                    "parquet": resultados[c.nome]["parquet"],
                    "csv_gz": resultados[c.nome]["csv_gz"],
                },
                "colunas": [
                    {"nome": k.nome, "tipo": k.tipo, "descricao": k.descricao} for k in c.colunas
                ],
            }
            for c in conjuntos
        ],
    }


def _kb(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB" if n >= 1024 * 1024 else f"{n / 1024:.0f} kB"


def _licenca_leiame(dicionario: dict) -> str:
    data = dicionario["gerado_em"][:10]
    orgaos = sorted({c["fonte_oficial"]["orgao"] for c in dicionario["conjuntos"]})
    return f"""## Licença

Estes dados abertos estão sob a **{LICENCA["nome"]}**
({LICENCA["url"]}). Você pode copiar, redistribuir, adaptar e usar para qualquer fim,
inclusive comercial, desde que dê o crédito.

Forma sugerida de citação:

> Panóptico (panoptico.social.br), a partir de {" / ".join(orgaos)}, dados de {data}.

Os dados de origem são públicos e oficiais; a fonte de cada conjunto está no `dicionario.json`.
A licença cobre a seleção, a organização e as ligações feitas pelo Panóptico. O código do
projeto segue a sua própria licença (ver `LICENCA-DADOS.md` no repositório).
"""


def montar_leiame(dicionario: dict) -> str:
    linhas_tabela = "\n".join(
        f"| `{c['nome']}` | {c['titulo']} | {c['linhas']:,} | "
        f"{_kb(c['arquivos']['parquet']['bytes'])} | {_kb(c['arquivos']['csv_gz']['bytes'])} |"
        for c in dicionario["conjuntos"]
    ).replace(",", ".")
    return f"""# Panóptico: dados abertos do acervo

Gerado em {dicionario["gerado_em"]} (UTC) a partir do acervo do Panóptico ({REPOSITORIO}).
Cada conjunto vem em dois formatos equivalentes: `<nome>.parquet` (zstd, com tipos) e
`<nome>.csv.gz` (UTF-8, vírgula, cabeçalho, datas em ISO 8601, decimais com ponto).
`dicionario.json` descreve cada coluna, a fonte oficial, a data da última carga de cada fonte,
o tamanho e o SHA-256 de cada arquivo.

## Conjuntos

| Conjunto | O que é | Linhas | Parquet | CSV.gz |
|---|---|---:|---:|---:|
{linhas_tabela}

## O que nunca está aqui

- CPF, título de eleitor e data de nascimento de ninguém. Sequências com cara de CPF são
  removidas dos textos (`[CPF omitido]`); fornecedor pessoa física sai sem nome e sem documento.
- Pessoas privadas, e pessoas sem ao menos um vínculo forte ou revisado à mão com um registro
  oficial (a mesma regra do site, `publicavel()`).
- Sugestões não revisadas: atos achados por nome nos diários oficiais e no DOU, e pedidos de
  indiciamento extraídos de relatórios de CPI. Achado em texto não é vínculo.
- Casos em rascunho.
- Nomes de doadores de campanha (só totais).

## Como ler

```python
import pandas as pd
eventos = pd.read_parquet("eventos.parquet")
pessoas = pd.read_parquet("pessoas_publicas.parquet")
eventos.merge(pessoas, left_on="pessoa_id", right_on="id", suffixes=("", "_pessoa"))
```

```sql
-- DuckDB
SELECT ano, sum(valor_global) FROM 'pncp_anual.parquet' GROUP BY ano;
```

Os `id` são deste retrato do banco: servem para ligar os arquivos entre si, mas **não são
estáveis entre gerações**. Para acompanhar um registro ao longo do tempo, use as chaves das
fontes (`casa` + `id_externo`, `ano_eleicao` + `sq_candidato`, `numero_controle`...).

## Cuidados

- Os dados são cópias de fontes oficiais, com a data da última carga de cada uma no
  dicionário. Em caso de dúvida, vale o que está na fonte (`fonte_url`, `sapl_url`).
- Ser citado num evento não é culpa: leia o `tipo`, a `situacao` e abra o documento oficial.
- Ligações por nome são conservadoras; homônimos existem. A coluna `regra` e `revisado` mostram
  como cada ligação foi feita.

{_licenca_leiame(dicionario)}"""


def escrever_documentacao(
    conn: Connection, conjuntos: tuple[Conjunto, ...], resultados: dict[str, dict], destino: Path
) -> None:
    dicionario = montar_dicionario(conn, conjuntos, resultados)
    (destino / "dicionario.json").write_text(
        json.dumps(dicionario, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (destino / "LEIAME.md").write_text(montar_leiame(dicionario), encoding="utf-8")
