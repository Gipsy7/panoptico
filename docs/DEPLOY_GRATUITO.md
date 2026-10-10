# Publicação gratuita (Vercel + Neon + GitHub Actions)

| Parte | Onde | Endereço |
|---|---|---|
| Site (Next.js) | Vercel, projeto `panoptico` | https://panoptico.social.br |
| API (FastAPI) | Vercel, projeto `panoptico-api` | https://api.panoptico.social.br |
| Banco | Neon (plano Launch, pago por uso, desde outubro de 2026) | — |
| Atualização diária dos dados | GitHub Actions (`.github/workflows/ingestao.yml`) | 6h de Brasília |
| Câmaras municipais (SAPL) | `.github/workflows/ingestao-camaras.yml`, um estado por máquina | domingo, 8h |
| Justiça e identidade (pessoas, cassações, sanções, TCU, DataJud, Conselhos de Ética, CPIs, cargos partidários, curadoria) | `.github/workflows/ingestao-justica.yml` | terça, 10h |
| Contas dos municípios (SICONFI) | `.github/workflows/ingestao-mensal.yml` | dia 15, 7h |
| TSE (eleitos, bens, contas, votos, fotos) | `.github/workflows/ingestao-tse.yml` | manual, uma vez por eleição |
| Varredura dos canais oficiais | `.github/workflows/varredura-canais.yml` | manual |

Nenhum segredo fica no repositório. A URL do banco vai só para o **secret do GitHub** e para a **variável de ambiente da Vercel**.

Para migrar para uma VPS no futuro, veja [DEPLOY.md](DEPLOY.md).

## 1. Neon (banco)

1. Crie um projeto (região **AWS São Paulo** se houver; senão a mais próxima, como US East).
2. Em **Connection Details**, copie duas strings de conexão:
   - **com pooling** (o host tem `-pooler`): para a API na Vercel;
   - **sem pooling** (direta): para as migrações e a ingestão no GitHub Actions.
3. Pode colar como o Neon entrega (`postgresql://...?sslmode=require`); o código ajusta o driver.

## 2. GitHub (ingestão)

No repositório, em **Settings → Secrets and variables → Actions → New repository secret**:

| Nome | Valor |
|---|---|
| `DATABASE_URL` | string do Neon **sem pooling** |

Depois, em **Actions → Ingestão diária → Run workflow**, marque **Carga inicial** e rode. Leva de 10 a 20 minutos: cria as tabelas e carrega tudo. Daí em diante roda sozinho todo dia.

## 3. Vercel: API

**Add New → Project →** importe `panoptico` e configure:

| Campo | Valor |
|---|---|
| Project Name | `panoptico-api` |
| Root Directory | `backend` |
| Framework Preset | FastAPI (detectado sozinho) |

**Environment Variables:**

| Nome | Valor |
|---|---|
| `DATABASE_URL` | string do Neon **com pooling** |
| `CORS_ORIGINS` | `["https://panoptico.social.br"]` |

Depois do deploy, em **Settings → Domains**, adicione `api.panoptico.social.br`.

Teste: `https://<endereço>.vercel.app/saude` deve responder `{"status":"ok","banco":"ok"}`.

## 4. Vercel: site

**Add New → Project →** importe `panoptico` de novo:

| Campo | Valor |
|---|---|
| Project Name | `panoptico` |
| Root Directory | `frontend` |
| Framework Preset | Next.js |

**Environment Variables:**

| Nome | Valor |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://api.panoptico.social.br` |
| `NEXT_PUBLIC_SITE_URL` | `https://panoptico.social.br` |
| `NEXT_PUBLIC_CONTATO_EMAIL` | (opcional) |

Em **Settings → Domains**, adicione `panoptico.social.br` e `www.panoptico.social.br` (marque o `www` para redirecionar).

Mudou alguma variável `NEXT_PUBLIC_*`? Faça **Redeploy**, porque elas entram no build.

## 5. DNS (Registro.br)

Na zona DNS do domínio, crie os registros que a Vercel mostrar em **Settings → Domains** de cada projeto. Em geral:

| Nome | Tipo | Valor |
|---|---|---|
| `panoptico.social.br` (raiz) | A | o IP que a Vercel indicar |
| `www` | CNAME | o valor que a Vercel indicar |
| `api` | CNAME | o valor que a Vercel indicar |

Use os valores exatos da tela da Vercel. A propagação leva de minutos a algumas horas, e o HTTPS é emitido sozinho.

## Como publicar uma mudança

Trabalhe no branch **`dev`** e envie (`git push origin dev`). O workflow **Publicar** (`.github/workflows/publicar.yml`) faz o resto:

1. roda os testes;
2. aplica as migrações no Neon;
3. recarrega os dados federais (cerca de 20 minutos) **só se uma das migrações aplicadas declarar `RECARREGAR_DADOS = True`**, isto é, se mexer em tabelas que a ingestão diária preenche. Tabelas novas com carga própria (TSE, SICONFI, SAPL) não pedem recarga, e a publicação fica em poucos minutos;
4. avança o `main`, e a Vercel publica.

Assim o código novo nunca entra no ar antes de o banco estar pronto para ele, e o site não fica sem dados. Para forçar a recarga sem migração nova: **Actions → Publicar → Run workflow → recarregar**.

Regras:
- **Não envie direto para o `main`.** O Publicar só avança o `main` se for "fast-forward"; se o `main` tiver commits que o `dev` não tem, ele falha em vez de apagar trabalho.
- **Migrações só acrescentam** (tabelas e colunas opcionais). Remover ou renomear coluna exige duas publicações: primeiro o código para de usar, depois a migração remove.
- A ingestão diária e a recarga do Publicar não rodam ao mesmo tempo (mesmo grupo de concorrência), e cada fonte é trocada numa transação: durante a carga o site continua com os dados anteriores.

## Limites do plano gratuito

- **Neon (histórico: o banco saiu do plano gratuito em outubro de 2026; hoje vale o Launch, ver "Travas contra consumo excessivo"):** 0,5 GB. O banco tinha ~260 MB; os gastos do gabinete são a maior tabela e só guardamos o ano anterior e o atual.
- **Cold start:** depois de um tempo sem acesso, o banco e a API "acordam" e o primeiro acesso leva 1 a 3 segundos a mais.
- **Vercel Hobby:** uso não comercial.
- **Vercel Hobby, 100 deploys por dia** (somando os dois projetos): em 09/10/2026 o limite estourou (`api-deployments-free-per-day`) e a API ficou presa num deploy antigo. Por isso `frontend/vercel.json` e `backend/vercel.json` desligam o deploy de qualquer branch que não seja o `main` (sem prévias do `dev`), e os merges são enviados em lote.
- **GitHub Actions:** em repositório público, os workflows agendados são **desativados depois de 60 dias sem commits**. O GitHub avisa por e-mail; basta reativar em **Actions** ou fazer um commit.
- **Arquivos brutos:** ficam 7 dias como artefato de cada execução (aba **Actions → execução → Artifacts**).
- **Neon, transferência de dados:** o plano gratuito tem uma cota mensal pequena de transferência. Em outubro de 2026 ela estourou num dia de várias cargas completas seguidas, e o banco ficou bloqueado até a cota renovar. Evite disparar recargas completas à mão.

## Travas contra consumo excessivo

Valem tanto no plano gratuito quanto no pago:

- **Cache na CDN** (`backend/app/main.py`): toda resposta GET 200 da API sai com `s-maxage=3600, stale-while-revalidate=86400`, então a mesma consulta chega ao banco no máximo uma vez por hora. `/saude` e os erros ficam sem cache.
- **Cache por instância da lista** (`backend/app/services/ranking.py`): em produção, a base da lista de parlamentares fica 10 minutos em memória. Buscas por nome diferentes, que escapam da CDN, não releem a tabela.
- **Firewall da Vercel no projeto `panoptico-api`:** limite de 120 requisições por minuto por IP; acima disso, a resposta é 429. O servidor do site se identifica com o `User-Agent: panoptico-site` (`frontend/lib/api.ts`) e fica de fora, porque as renderizações de muitos visitantes saem dos mesmos IPs da Vercel. Para ver ou mudar o limite, use **panoptico-api → Firewall**.

No plano pago do Neon, configure também no console:

- **Autoscaling:** mínimo e máximo de 0,25 CU, e scale to zero ligado. Isso põe um teto de cerca de US$ 19 por mês no processamento, mesmo com o banco ligado o mês inteiro.
- **Spending limit** baixo, por exemplo US$ 10. Hoje ele só manda e-mail aos 80% e aos 100% e não suspende o banco.
- **Um único branch:** cada compute ligado custa à parte.
- **`DATABASE_URL` nunca em código ou log:** o repositório é público.

## Filas no banco

Cada tipo de carga tem a sua fila (`concurrency` no workflow), e por isso cargas diferentes podem rodar ao mesmo tempo:
- `ingestao-federal`: a ingestão diária e a recarga do Publicar, que escrevem nas mesmas tabelas;
- `ingestao-tse`, `ingestao-mensal`, `ingestao-camaras` e `ingestao-justica`: cada uma com as suas tabelas. A de Justiça escreve em `pessoa`, `pessoa_vinculo`, `evento`, `processo`, `sancao_empresa` e `cpi*`, e só lê `candidatura`, `parlamentar` e `mandato_local`; por isso roda na terça, depois da ingestão diária e longe do domingo das câmaras.

As migrações usam uma trava no próprio Postgres (`pg_advisory_xact_lock` em `alembic/env.py`): se dois workflows migrarem ao mesmo tempo, o segundo espera e não encontra nada a fazer. Atenção: o GitHub mantém só **uma** execução pendente por fila; disparar outra na mesma fila cancela a que estava esperando.

## Fontes de Justiça e identidade na produção

Workflow `.github/workflows/ingestao-justica.yml`, toda terça às 10h (Brasília), fila `ingestao-justica`, um único job com os passos na ordem das dependências do `fontes.toml` (`pessoas` primeiro; `cnj_datajud` depois de `tse_cassacoes` e `cgu_sancoes`). Cada passo roda mesmo que o anterior falhe (`if: !cancelled()`): um órgão fora do ar não trava os outros, e o job fica vermelho no fim. Também dá para disparar à mão (**Actions → Justiça e identidade → Run workflow**).

`pessoas` não baixa nada: lê `candidatura`, `parlamentar` e `mandato_local` (as únicas tabelas de que depende, todas existentes na produção) e aplica os CSVs de revisão versionados em `data/` (`vinculos_revisados.csv`, `atos_revisados.csv`, `indiciamentos_revisados.csv`) quando existirem. Só grava o que mudou (pessoas novas ou alteradas; vínculos com `ON CONFLICT ... WHERE` diferente). Localmente, com 158 mil registros, leva ~30 s e grava 0 linhas quando nada mudou. Dry run local dos passos em sequência: segunda rodada sem mudança em ~3 s para cassações, CGU, Éticas, CPIs (~105 s de consultas) e cargos partidários; só o TCU (45 s) e a Ética da Câmara (35 s) refazem consultas. O DataJud estava lento (429 e 15 a 25 s por consulta), por isso o passo tem limite de 40 min.

**Como cada fonte evita transferir quando nada mudou**

| Fonte | Tabelas que preenche (MB no acervo local, com índices) | Baixa por execução | Recarga incremental |
|---|---|---|---|
| `pessoas` | `pessoa` 34, `pessoa_vinculo` 31 (156 mil de candidaturas) | nada (lê ~40 MB do banco: candidatura ~25, vínculos ~10, pessoas ~7) | grava só o que mudou |
| `tse_cassacoes` | `evento` (894 linhas, 0,3) | 6 zips do TSE, 2,6 MB no total | sonda ETag; contexto = pessoas e candidaturas do ano |
| `cgu_sancoes` | `evento` (49), `sancao_empresa` 0,6 (908 empresas) | 1 zip da CGU, 4,2 MB (CEIS + CEAF) | sha256 do zip + contexto de pessoas |
| `tcu_condenacoes` | `evento` (371, 0,2) | 2,7 MB (JSON do TCU) | sha256 + contexto de pessoas |
| `cnj_datajud` | `processo` (0,03; ~520 números consultados) | ~0,1 MB de respostas + 1 página da chave pública | upsert de ~520 linhas (centenas de KB) |
| `camara_etica` | `evento` (85) | ~0,1 MB (72 representações) | sha256 + contexto de pessoas |
| `senado_etica` | `evento` (3) | 2 KB | sha256 + contexto de pessoas |
| `cpis` | `cpi` 0,1, `cpi_participacao` 0,4, `evento` (655, 0,4) | ~330 consultas e páginas de comissões (poucos MB), ~2 min | sha256 + contexto de pessoas |
| `tse_orgaos_partidarios` | `evento` 5,2 de dados (18,9 mil cargos), `pessoa_vinculo` 1,4 | 1 zip de **219 MB** (lido em fluxo, não fica no disco) | sonda ETag; contexto = pessoas com título; grava só cargos novos, alterados ou encerrados |
| `curadoria` | `caso*`, `processo`, `evento` (CSVs do repositório) | nada (arquivos do repositório) | recria tudo, são poucas linhas |

Total na produção: cerca de 80 MB de dados e índices no Neon, quase todos de `pessoa` e `pessoa_vinculo` (a base de candidaturas), mais ~6 MB de cargos partidários. Estimativa por semana: **arquivos baixados** 10 a 15 MB nas semanas sem mudança (219 MB a mais só quando o TSE republicar os órgãos partidários, o que é grátis para o banco porque fica no GitHub); **transferência do Neon** ~40 MB lidos por `pessoas` e menos de 1 MB gravado; nas semanas com mudança, mais alguns MB. É cerca de 0,2 GB por mês, longe de preocupar o plano Launch.

**Ficam de fora**

- `cnj_cnia`, `stf_processos`, `stj_processos`: catalogadas (sem coleta), bloqueiam acesso automático ou dependem de pedido formal (`docs/pedidos/`).
- `cpi_indiciamentos`, `querido_diario_atos`, `dou_atos`: geram **fila de revisão humana** local (`ingestion.revisar`); só o resultado, os CSVs `data/*_revisados.csv` versionados, é aplicado pela carga de `pessoas` na produção.
- `tse_contas_partidarias`, `tse_fefc_fp`: já rodam no `ingestao-mensal.yml`.
- `cnpj_socios` e `pncp_contratos`: têm volume e cadência próprios; não fazem parte deste conjunto.

