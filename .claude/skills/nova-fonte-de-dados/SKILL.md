---
name: nova-fonte-de-dados
description: Como adicionar ou alterar uma fonte de dados na ingestão do Panóptico (backend/ingestion), do reconhecimento do formato real até o banco, testes e documentação. Use sempre que a tarefa envolver baixar dados de um órgão público (Câmara, Senado, Portal da Transparência, TSE, IBGE, Assembleias, Câmaras Municipais), criar ou mudar uma tabela alimentada por ingestão, mudar o run_all, reprocessar dados brutos, ou investigar por que um número carregado não bate com a fonte — mesmo que o pedido não diga "ingestão".
---

# Nova fonte de dados

O Panóptico só mostra o que consegue provar: cada número vem de uma fonte oficial, com link e data. A ingestão é onde isso se garante. Siga as etapas na ordem; a primeira é a que mais evita retrabalho.

## 1. Reconheça a fonte antes de escrever código

Baixe uma amostra real e olhe com os próprios olhos. As fontes oficiais têm armadilhas que só aparecem nos dados, e já custaram caro neste projeto:

- **Identificadores diferentes entre formatos.** O JSON de gastos da Câmara usa `numeroDeputadoID`, que não é o id da API; só o CSV traz `ideCadastro` (o id certo). Antes de ligar uma fonte ao `parlamentar`, meça quantos registros casam (ex.: "509 de 513").
- **Chave que não é única.** No arquivo de emendas, o código da emenda se repete (uma linha por emenda × localidade × ação). Não crie `UNIQUE` sem conferir.
- **Valores "Sem informação"**, campos nulos, lista que vira objeto quando tem um item só (Senado), números com vírgula decimal, CSV em latin-1, BOM no início.
- **Semântica enganosa.** "Transformado em nova proposição" não é lei; "Sociedade de Economia Mista" no favorecido de emenda é a Caixa/BB intermediando, não a cidade recebendo.
- **Tamanho.** Arquivos de 50–180 MB: leia em fluxo (`csv` + `io.TextIOWrapper` sobre `zipfile.open`), nunca carregue tudo com `json.load`.

Prefira arquivos em lote a APIs paginadas quando existirem (menos requisições, sem limite de taxa). Registre o que encontrou em `docs/FONTES_DE_DADOS.md` (URL, formato, campos usados, armadilhas, frequência).

## 2. Estrutura do módulo

Crie `backend/ingestion/<orgao>/<assunto>.py` seguindo os módulos existentes (`camara/despesas.py`, `senado/votacoes.py`, `transparencia/emendas.py` são bons modelos). O padrão:

```python
FONTE = "camara_despesas"          # nome em fonte_ingestao e pasta em data/raw/
URL = "https://..."

def normalizar(payload) -> list[dict]:      # puro: bruto -> registros; fácil de testar
    ...

def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client):                       # só rede; devolve o bruto como veio
        return comum.get_bytes(client, URL.format(ano=ano))
    def carregar(session, payload, ingestao): # normaliza, liga ao parlamentar, grava
        linhas = comum.vincular_parlamentares(session, CASA, normalizar(payload))
        return comum.recarregar_despesas(session, CASA, ano, linhas, ingestao)
    return comum.executar_ingestao(FONTE, URL.format(ano=ano), baixar, carregar,
                                   de_raw=de_raw, prefixo_raw=f"{ano}_")
```

Por que assim:
- **Bruto separado do tratado** (princípio do projeto): `executar_ingestao` grava o bruto em `data/raw/<fonte>/` antes de processar, e `--de-raw <arquivo>` reprocessa sem rede. Bytes viram `.zip` ou, com `extensao_raw=".csv.gz"`, são comprimidos; o resto vira `.json`. Se a fonte tem dois arquivos que precisam entrar juntos, empacote-os num zip em memória (veja `camara/votacoes.py`).
- **Uma transação por carga, registrada em `fonte_ingestao`**: se falhar, nada fica pela metade e fica um registro `status="erro"`. A página "Sobre as fontes" lê a data da última carga `ok` daqui.
- **Recarga idempotente**: arquivos oficiais mudam retroativamente. Para dados anuais, apague o ano e reinsira (como `recarregar_despesas`); para entidades, upsert com `on_conflict_do_update`. Sempre aborte se a lista vier vazia, para não zerar a base por uma falha da fonte.
- **Ligação ao parlamentar** por `comum.mapa_parlamentares` / `vincular_parlamentares` (id externo → id interno). Sem id, compare nomes com `comum.chave_nome` e **só aceite correspondência exata e única** — aproximação errou em todos os casos testados ("Camilo Santana" → "Alex Santana").
- Inserções em lotes (2.000–5.000 linhas) e consultas `IN` com listas grandes divididas, por causa do limite de parâmetros do Postgres.

Helpers úteis em `ingestion/comum.py`: `get_json`/`get_bytes` (com retry), `limpar_categoria`, `nome_proprio`, `chave_nome`, `anos_padrao`.

Inclua um `if __name__ == "__main__":` com `argparse` (`--ano`, `--de-raw`) como nos outros módulos.

## 3. Banco

Modelo em `backend/app/models/<nome>.py`, exportado em `app/models/__init__.py`, e migração **escrita à mão** em `backend/alembic/versions/000N_<nome>.py` (siga a numeração e o estilo das anteriores, com `op.f(...)` e a naming convention de `models/base.py`). Aplique com `python -m uv run alembic upgrade head`.

Lembre do limite do Neon gratuito (0,5 GB): guarde só o período útil (ex.: ano anterior e atual, ou desde 2023) e confira o tamanho com `pg_total_relation_size` depois de carregar.

## 4. Testes

Em `backend/tests/`, com dados **reais** recortados da fonte (salve uma amostra pequena em `tests/fixtures/` ou monte o CSV/zip no próprio teste). Cubra:
- a normalização, incluindo cada armadilha encontrada na etapa 1;
- a carga no banco (idempotência, abortar com lista vazia);
- a rota da API que expõe o dado, se houver.

Use os helpers de `tests/test_api.py` (`_popular`, `_ingestao`) e as fixtures de `tests/conftest.py` (`session`, `client`). HTTP externo é simulado com `respx`.

## 5. Ligar ao resto

- Adicione ao `ingestion/run_all.py` (`_tarefas`), respeitando dependências: parlamentares primeiro, municípios antes de emendas.
- Adicione ao catálogo em `app/services/fontes.py` (página "Sobre as fontes").
- Decisões de metodologia (o que entra, o que fica de fora e por quê) em `docs/DECISOES.md`.
- Se a carga inicial precisar de anos extras, documente em `docs/DEPLOY_GRATUITO.md` e no workflow `.github/workflows/ingestao.yml` (passo da carga inicial).

## 6. Verificar

```bash
cd backend
python -m uv run ruff format . && python -m uv run ruff check --fix .
python -m uv run pytest -q
python -m uv run python -m ingestion.<orgao>.<assunto>          # carga real
python -m uv run python -m ingestion.<orgao>.<assunto> --de-raw "$(ls -t data/raw/<fonte>/* | head -1)"
```

Depois da carga, confira contagens e somas no banco contra a fonte (ex.: total de um parlamentar conhecido) e diga explicitamente o que casou e o que ficou de fora (ex.: "209 pagamentos sem município identificado"). Números que ficaram de fora sem explicação são o tipo de erro que destrói a confiança no site.
