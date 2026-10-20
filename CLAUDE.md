# Panóptico

Site de transparência política: "quem te representa, às claras". O cidadão digita o CEP e vê quem o representa (presidente a vereador), o que cada um faz, gasta, vota e recebe, com dado oficial, link da fonte e data. Público: o grande público brasileiro, no celular, vindo de link de WhatsApp. Critério de pronto: quem não entende de política acha o representante e entende o número em menos de um minuto. Licença AGPL-3.0 (código) e `LICENCA-DADOS.md` (dados).

Responda sempre em português do Brasil (código, commits, docs e relatórios).

## Mapa de pastas

- `backend/app/`: API FastAPI (`api/` rotas, `services/` regras de cálculo, `schemas/`, `config.py`).
- `backend/ingestion/`: coleta e carga por órgão (`camara/`, `senado/`, `tse/`, `camaras/`, `assembleias/`, `tce/`, `pncp/`, `dou/`, `diarios/`...). `fontes.toml` é o registro das fontes do acervo; `run_all.py` é a ingestão diária; `acervo.py`, `revisar.py`, `identidade.py`, `pessoas.py` e `curadoria.py` cuidam do acervo e da identidade.
- `backend/exportar/`: dumps abertos (Parquet e CSV.gz). `backend/analises/`: cruzamentos. `backend/alembic/`: migrações. `backend/tests/`: pytest.
- `backend/data/raw/` (bruto) e `processed/`: fora do git. `data/` na raiz: CSVs versionados (catálogo de canais, curadoria, atos revisados).
- `frontend/`: Next.js 16 (App Router, `cacheComponents`), `app/`, `components/`, `lib/api.ts`, `lib/formato.ts`.
- `docs/`: `DECISOES.md`, `FONTES_DE_DADOS.md`, `DEPLOY.md`, `DEPLOY_GRATUITO.md`, `PLANO_MVP.md`, `DESIGN.md`, `pedidos/`.
- `.github/workflows/`: `ci.yml`, `publicar.yml` e as ingestões (`ingestao*.yml`, `pncp-pacote.yml`, `varredura-canais.yml`). `scripts/`: SQL do acervo e rotinas locais. `.claude/skills/` e `.claude/agents/`.

## Comandos essenciais

Máquina Windows; `uv` não está no PATH: use `python -m uv ...`. Shells: Git Bash e PowerShell.

```bash
# Backend (cd backend). Os testes usam o banco panoptico_test (TEST_DATABASE_URL, padrão em
# app/config.py), nunca o banco de dev nem o acervo. Não exporte DATABASE_URL de produção ou do acervo.
python -m uv run pytest -q
python -m uv run pytest tests/test_x.py -q        # só uma área
# Agentes em paralelo dividem o panoptico_test: erros de conexão em massa = outro agente testando;
# rode só a sua área, espere e repita. O coordenador roda a suíte completa depois do merge.
# Worktree novo: `uv sync --group acervo` (pyarrow do test_exportar).
python -m uv run ruff check . && python -m uv run ruff format --check .
python -m uv run alembic upgrade head              # migrações no banco do DATABASE_URL
python -m uv run uvicorn app.main:app --port 8000  # sem --reload (deixa processo órfão no Windows)

# Frontend (cd frontend)
npm test                                                                   # Vitest (lib/**/*.test.ts, só lógica pura)
npx next typegen && npx tsc --noEmit && npm run lint && npm run build   # pare o `next start` antes do build
# Worktree: copie o node_modules (robocopy); junction quebra o Turbopack, e --webpack sai sem Tailwind.
# Mudou dependência? O npm local (11.6) tira do lock dependências opcionais de outras plataformas e o
# `npm ci` do CI falha. Gere o lock com `npx -y npm@11.21 install --package-lock-only`.
# Screenshot de celular: Edge headless tem janela mínima de ~500 px; use um iframe de 360 px (ver docs/DESIGN.md).

# Acervo local (DATABASE_URL apontando para panoptico_acervo; ver README, "acervo local")
python -m uv run python -m ingestion.acervo rodar --vencidas
python -m uv run python -m ingestion.acervo rodar --fonte tse_bens sapl_assembleias
python -m uv run python -m ingestion.acervo relatorio
# Revisão humana de filas (pergunta no terminal; --exportar grava a fila em CSV)
python -m uv run python -m ingestion.revisar [--tipo vinculo|diario|dou|cpi]
# Exportação aberta (precisa de: uv sync --group acervo)
python -m uv run python -m exportar --listar
python -m uv run python -m exportar --destino saida [--conjunto eventos pessoas_publicas]
```

Para subir tudo, tirar screenshot de 360px e destravar portas, use a skill `rodar-e-verificar`.

## Regras fixas (não se negociam)

- **Linguagem factual, sem juízo.** Sem nota, ranking, selo, adjetivo nem cor de "bom/ruim". Número literal ("votou em 31 de 59") e contexto da fonte.
- **Fonte e data visíveis** em toda seção (`FonteRodape`); a data vem da última carga `ok` em `fonte_ingestao`.
- **Comparação com a média da Casa** ao lado do número (parlamentares em exercício; quem não tem nada entra com zero).
- **Linguagem do dia a dia**; o termo oficial aparece em letra menor. Diga o que ficou de fora quando houver recorte.
- **Coleta mínima** (LGPD): só o necessário; nada de CPF, título de eleitor ou data de nascimento em API, site ou exportação. Doadores pessoas físicas não têm nome exibido.
- **Bloqueio deliberado nunca é contornado**: captcha, reCAPTCHA, 403 proposital, geobloqueio ou `robots.txt` que veda. Sem proxy, VPN, navegador disfarçado ou outro truque. Vira pedido (acesso ou LAI) em `docs/pedidos/` (e `acesso` em `fontes.toml`), e o site diz o que falta.
- **Dado bruto separado do tratado**: o bruto vai para `data/raw/<fonte>/` antes de processar; `--de-raw` reprocessa sem rede. Uma transação por carga, registrada em `fonte_ingestao`.
- Migrações só acrescentam (tabela nova, coluna opcional); remoção em duas publicações. Número que não bate com a fonte é bug: investigue, não ajuste.
- Cores só pelos tokens do tema; evite vermelho, azul e verde-amarelo como cor principal (associação partidária). Contraste AA.

## Git e publicação

- Trabalhe no `dev` (ou em branch de worktree a partir dele). Nunca push direto no `main`, nunca `--force`.
- `git push origin dev` dispara o workflow **Publicar**: testa, migra a produção, recarrega dados federais só se uma migração declarar `RECARREGAR_DADOS = True`, e então avança o `main`.
- **Só o `main` faz deploy na Vercel**, e o limite é de 100 deploys por dia (Hobby): junte commits e faça pushes em lote, não um por ajuste.
- Commits em pt-BR, mensagem curta e factual. No `dev` o CI roda dentro do Publicar; em outros branches e PRs roda o `ci.yml`.
- `ACOMPANHAMENTO.md` é arquivo local de acompanhamento, **nunca vai para o git** (não use `git add -A` às cegas). Atualize ao fim de cada tarefa.
- Atualize o `README.md` a cada entrega relevante.

## Dois bancos

- **Acervo local** (`panoptico_acervo`, Postgres 18 nativo): sem limites, com todos os brutos, fontes de Justiça e controle, PNCP completo, eleições antigas. Aqui se carrega e se testa o novo.
- **Produção** (Neon, plano Launch, pago por uso): recorte enxuto, ingestão pelo GitHub Actions (EUA, por isso fontes só-Brasil ficam no acervo). Travas de custo já decididas (CDN 1h, firewall 120 req/min, 0,25 CU, spending limit); não as reestime. **Nada de recarga completa na produção**; carga é incremental, e mudança que pesa no banco precisa ser pensada antes. Segredos (`DATABASE_URL`, chaves) nunca são lidos nem impressos.

## Identidade e revisão humana

Pessoa pública única (`pessoa`, `pessoa_vinculo`): ligação por CPF, título de eleitor ou revisão manual; nome idêntico é vínculo forte, aproximado vai para fila. Só aparece no site o que é "publicável" (`publicavel()`). Filas de revisão humana, nunca automáticas: vínculos por nome (`revisar`), atos de diários (`--tipo diario`), atos de pessoal do DOU (`--tipo dou`) e indiciamentos sugeridos por CPI (`--tipo cpi`). Sugestão não revisada nunca vai ao site nem à exportação; casos em rascunho também não.

## Onde fica cada coisa

- `docs/DECISOES.md`: o porquê de cada decisão, por data, com índice no topo. **Leia só a seção relevante**, não o arquivo inteiro (800+ linhas); acrescente uma seção ao decidir algo novo.
- `docs/FONTES_DE_DADOS.md`: URL, formato, campos, armadilhas e frequência de cada fonte.
- `docs/DESIGN.md`: padrões visuais e de interface do site.
- `docs/DEPLOY_GRATUITO.md` (produção, filas, travas) e `docs/DEPLOY.md` (alternativa em VPS).
- `docs/pedidos/`: pedidos de acesso/LAI a fontes bloqueadas.
- `ACOMPANHAMENTO.md` (local): estado das tarefas. **Leia só a seção relevante.**

## Skills (não duplicadas aqui) e agentes

- `nova-fonte-de-dados`: qualquer coisa em `backend/ingestion`, tabela alimentada por ingestão, número que não bate com a fonte.
- `nova-secao-no-perfil`: o que o cidadão vê (rota da API, componente, página); Next.js 16 tem particularidades (`params` são Promises).
- `rodar-e-verificar`: subir API e site no Windows, screenshots de celular, depurar "não mostra dados".
- `operar-producao`: Vercel, Neon, Actions, domínios, ingestão e CI.
- Agentes em `.claude/agents/`: `conector` (fontes), `tela` (interface), `mecanico` (docs e ajustes pequenos), `verificador` (checagem sem editar código), `operador` (produção).
