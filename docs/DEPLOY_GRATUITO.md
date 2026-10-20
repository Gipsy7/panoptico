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

**Assembleias só do Brasil (11/10/2026):** ALMG, CLDF, ALEPE, ALRS, ALES, ALEMA, ALAP, ALBA e ALESE dão tempo esgotado (ALBA: 403) a IPs dos EUA, nas duas execuções do GitHub Actions. Os jobs delas estão desligados (`if: false` em `ingestao-camaras.yml`) e as fontes têm `acesso = "brasil"`: só atualizam pelo acervo local. Na produção ficam com a última carga feita (ALMG, ALEPE e CLDF têm dados de cargas anteriores; as outras seis ainda não chegaram à produção).

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
- `ingestao-tse`, `ingestao-mensal`, `ingestao-camaras`, `ingestao-pncp` e `ingestao-justica`: cada uma com as suas tabelas. A de Justiça escreve em `pessoa`, `pessoa_vinculo`, `evento`, `processo`, `sancao_empresa` e `cpi*`, e só lê `candidatura`, `parlamentar` e `mandato_local`; por isso roda na terça, depois da ingestão diária e longe do domingo das câmaras.

As migrações usam uma trava no próprio Postgres (`pg_advisory_xact_lock` em `alembic/env.py`): se dois workflows migrarem ao mesmo tempo, o segundo espera e não encontra nada a fazer. Atenção: o GitHub mantém só **uma** execução pendente por fila; disparar outra na mesma fila cancela a que estava esperando.

## Fontes de Justiça e identidade na produção

Workflow `.github/workflows/ingestao-justica.yml`, toda terça às 10h (Brasília), fila `ingestao-justica`, um único job com os passos na ordem das dependências do `fontes.toml` (`pessoas` primeiro; `cnj_datajud` depois de `tse_cassacoes` e `cgu_sancoes`). Cada passo roda mesmo que o anterior falhe (`if: !cancelled()`): um órgão fora do ar não trava os outros, e o job fica vermelho no fim. Também dá para disparar à mão (**Actions → Justiça e identidade → Run workflow**).

`pessoas` não baixa nada: lê `candidatura`, `parlamentar` e `mandato_local` (as únicas tabelas de que depende, todas existentes na produção) e aplica os CSVs de revisão versionados em `data/` (`vinculos_revisados.csv`, `atos_revisados.csv`, `indiciamentos_revisados.csv`) quando existirem. Só grava o que mudou (pessoas novas ou alteradas; vínculos com `ON CONFLICT ... WHERE` diferente). Localmente, com 158 mil registros, leva ~30 s e grava 0 linhas quando nada mudou. Dry run local dos passos em sequência: segunda rodada sem mudança em ~3 s para cassações, CGU, Éticas, CPIs (~105 s de consultas) e cargos partidários; só o TCU (45 s) e a Ética da Câmara (35 s) refazem consultas. O DataJud estava lento (429 e 15 a 25 s por consulta), por isso o passo tem limite de 40 min.

**Clicar em `socios_refazer` (Run workflow):** reconsulta também os CNPJs dos últimos 30 dias (`--refazer`); usar depois de carregar CPFs novos na produção (ex.: eleições 2016 e 2020), para que as ligações de sócios já consultadas sejam refeitas sem esperar o cache vencer.

**Como cada fonte evita transferir quando nada mudou**

| Fonte | Tabelas que preenche (MB no acervo local, com índices) | Baixa por execução | Recarga incremental |
|---|---|---|---|
| `pessoas` | `pessoa` 34, `pessoa_vinculo` 31 (156 mil de candidaturas) | nada (lê ~40 MB do banco: candidatura ~25, vínculos ~10, pessoas ~7) | grava só o que mudou |
| `tse_cassacoes` | `evento` (894 linhas, 0,3) | 6 zips do TSE, 2,6 MB no total | sonda ETag; contexto = pessoas e candidaturas do ano |
| `cgu_sancoes` | `evento` (49), `sancao_empresa` 0,6 (908 empresas) | 1 zip da CGU, 4,2 MB (CEIS + CEAF) | sha256 do zip + contexto de pessoas |
| `cgu_servidores` | `servidor_federal` 0,06, `evento` (15) | ZIP de **83 MB** do mês (lido em fluxo, 450 MB descompactado; ~10 s) | sonda Last-Modified + tamanho; contexto = pessoas |
| `cgu_viagens` | `viagem_federal_ano` 0,1, `servidor_federal` (55 cargos de natureza especial), `evento` (174 + 55) | ZIP de **156 MB** por ano (anterior e atual), só o `Viagem.csv` (~10 s) | sonda Last-Modified + tamanho; contexto = pessoas |
| `cgu_cpgf` | `cpgf_portador_mes` 0,04, `evento` (3) | ZIP mensal de **~300 KB**, só os 3 últimos meses publicados | sonda Last-Modified + tamanho; contexto = pessoas; `sleep 300` antes (WAF) |
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
- `pncp_contratos`: tem workflow próprio e diário (seção seguinte). `cnpj_socios` entra neste workflow, depois das sanções, com 250 consultas e no máximo 40 minutos por execução (`--minutos 40`; cache de 30 dias). Medido em 10/10/2026: a partir do Actions cada consulta leva 7 a 13 s (não os 2 s da pausa) e duas execuções (600 e 400 consultas) estouraram o limite de 60 min. **Ligações: 0 em ~600 consultas.** Causa: a ligação exige `Pessoa.cpf`, e a produção carrega só as eleições 2018, 2022 e 2024; o TSE mascara o CPF em 2024, então só ~3 mil pessoas (deputados e candidatos de 2018/2022) têm CPF, contra 53,7 mil no acervo local, onde 2016 e 2020 (`SO_CONHECIDOS`, CPF completo) dão CPF a 50,7 mil pessoas (4 das 5 ligações do acervo vêm só delas). Para a produção ligar sócios, será preciso carregar 2016 e 2020 no Neon (~82 mil candidaturas, ordem 30 a 40 MB, a medir) com o workflow do TSE; até lá a consulta só enche o cache e avisa na saída.

## PNCP na produção

Workflow `.github/workflows/ingestao-pncp.yml`, todo dia às 2h30 (Brasília), fila própria `ingestao-pncp` (escreve em `pncp_contrato`, `pncp_dia`, `pncp_janela`, `pncp_anual`; só lê `socio_pessoa` e `sancao_empresa`). Roda `python -m ingestion.pncp.contratos --producao --releitura 3`.

**Recorte da produção** (o acervo local continua com a soma diária `pncp_soma`, ~800 MB, que NÃO vai para o Neon):

| O que | Tabela | Recorte | Tamanho estimado |
|---|---|---|---|
| Contratos inteiros do alvo | `pncp_contrato` | fornecedor CNPJ em `socio_pessoa` ou `sancao_empresa`, sem alienações, do ano anterior em diante | medido: 896 contratos em 4 dias só das 908 empresas sancionadas (224/dia, ~0,58 KB cada com índices); 650 dias dão ~90 a 100 MB; cresce ~45 MB por ano |
| Soma anual | `pncp_anual` | ano atual e anterior, órgãos municipais, por município × fornecedor (CNPJ), só os 30 maiores de cada município e ano | medido: ~215 bytes por linha; teto de 5,5 mil municípios x 30 x 2 anos = 330 mil linhas = ~65 MB |
| Janela | `pncp_janela` | últimos 10 dias, por dia × município × fornecedor, para reler um dia sem somar duas vezes | ~4,4 mil linhas por dia (~1 MB no total) |
| Cursor | `pncp_dia` | um registro por dia lido (`compactado` diz se o dia já foi somado em `pncp_anual`) | ~650 linhas |

Total: ~160 MB no Neon (armazenamento ~US$ 0,06 por mês). Não entram: pessoa física, fornecedor estrangeiro, empenhos de órgãos federais e estaduais na soma anual, tipo de contrato e órgão (a soma é por município).

**Como evita somar duas vezes:** cada dia lido entra em `pncp_janela` (trocado inteiro se relido). Quando sai da janela (10 dias) ele é somado em `pncp_anual` uma única vez e marcado `compactado`; reler um dia já compactado só atualiza os contratos do alvo. Aproximação assumida: aditivo em contrato de dia já compactado não muda a soma anual; fornecedor fora dos 30 maiores do município recomeça do zero se voltar (erro pequeno, longe do topo que o site mostra).

**Custo por dia (medido no acervo, com a API do PNCP lenta):** ~9 mil contratos e ~3,6 min por dia de publicação (35.816 contratos em 14 min 21 s); a rota de alterações leva ~80 s por dia. A releitura de 3 dias custa ~15 a 20 min de Actions por dia (grátis em repositório público). Dados que vão ao Neon: ~4 a 5 MB por dia (janela, alvo, soma), ~0,15 GB por mês; leituras do banco, só os CNPJs do alvo (~3 mil) e os dias do cursor. Estimativa de acréscimo na conta do Neon: menos de R$ 5 por mês (computação de ~20 min por dia a 0,25 CU).

**Primeira carga: pacote em release (decisão de 10/10/2026).** Reler a API leva ~39 h (~650 dias a ~3,6 min). O acervo local já tem os 4.988.640 contratos de 01/01/2023 a 09/10/2026, conferidos dia a dia contra o total da API, então a carga histórica sai dele:

1. Na máquina do acervo (só SELECT): `cd backend && python -m ingestion.pncp.pacote gerar --destino pncp-pacote.zip --url postgresql+psycopg://panoptico:panoptico@localhost:5432/panoptico_acervo` (~20 s). Gera `pncp-pacote.zip` (~7,2 MB; versão 3 inclui `pncp_ente_publico`, CNPJs de órgãos, para a etiqueta "órgão público") e `pncp-pacote.manifesto.json` (sha256 do arquivo; o zip leva o sha256 de cada tabela). Medido em 10/10/2026: `pncp_anual` 190.146 linhas, `pncp_dia` 647, `pncp_janela` 32.707, `pncp_contrato` 46.028.
2. Crie a release com os dois arquivos: `gh release create pncp-pacote-AAAA-MM-DD pncp-pacote.zip pncp-pacote.manifesto.json --title "Pacote PNCP AAAA-MM-DD" --notes "Carga histórica do PNCP"`.
3. **Actions → PNCP (carga histórica por pacote) → Run workflow**, `tag` = a da release. O workflow baixa os anexos, confere o sha256 e roda `python -m ingestion.pncp.pacote carregar` com o `DATABASE_URL` do repositório, na fila `ingestao-pncp` (30 min no máximo; leva cerca de 1 min).
4. Depois o diário das 2h30 continua dali (cursor `pncp_dia`), sem reler o histórico.

O pacote traz o que `--producao` teria gravado: soma anual dos 30 maiores por município e ano (ano anterior e atual), só dos dias já compactados (anteriores a hoje − 10); a janela dos 10 últimos dias; o cursor `pncp_dia` (com `compactado`) e os contratos inteiros do conjunto-alvo (`sancao_empresa` e `socio_pessoa`; hoje só as sancionadas) publicados desde 1º de janeiro do ano anterior. Sem pessoa física (só fornecedor com CNPJ; texto livre passa por `sem_cpf` e a geração para se achar padrão de CPF). `carregar` troca o período numa transação (`pncp_anual` dos anos do pacote, `pncp_dia` e `pncp_janela` dos dias dele; contratos por upsert), então rodar duas vezes dá o mesmo resultado, e como a divisão compactado/janela é a do modo `--producao`, o diário não soma duas vezes. Recusa carregar se o diário já somou em `pncp_anual` um dia posterior ao pacote (apagaria essa soma); `--forcar` ignora. Se o diário já leu dias antes da carga, o pacote os substitui.

Diferenças em relação a ler a API: o acervo guarda somas, não contratos, então "valor global > 0" vale para o total do grupo e não para cada contrato; o nome do fornecedor vem do alvo, das sancionadas e dos pagamentos dos TCEs (12,5% das linhas de `pncp_anual`; os demais ficam sem nome até o diário vê-los de novo e o site mostra o CNPJ com link para a consulta da Receita); `pncp_orgao` não vai (a produção não o grava). O alvo do pacote é o do acervo (`sancao_empresa` de lá), não o da produção.

**Plano B (sem pacote):** disparar **Actions → PNCP → Run workflow** com `de` e `ate` em blocos de até 80 dias (8 a 9 disparos, em fila; ordem livre, e o agendamento diário completa o que faltar, 120 min por dia), ou rodar a primeira carga da máquina local contra o Neon com `DATABASE_URL`. Com `socio_pessoa` vazia o comando roda só com as sancionadas e avisa; contrato de sócio descoberto depois não é recuperado sem reler os dias (`--de/--ate`; o que já foi somado não soma de novo).

**Salto de valor (10/10/2026):** o pacote passa a aceitar `--saltos saltos.json` (gerado por `python -m ingestion.pncp.salto varrer --url URL_DO_ACERVO --minimo 50000000 --saida saltos.json`, ~1 h, retomável, só leitura no acervo e consultas à API do PNCP): contrato com valor global acima de 100× o inicial sai das somas e vai para `pncp_suspeito`. Sem o arquivo o pacote sai como antes. A migração `0037_pncp_salto_de_valor` reavalia `pncp_contrato.valor_suspeito` (rode `alembic upgrade head` na produção antes de carregar o pacote novo). Formato do pacote inalterado (versão 3).

**Valor suspeito (migração `0035_pncp_suspeito`):** contrato municipal com valor acima do menor entre a despesa paga anual do município (`contas_municipio`, SICONFI) e R$ 50 bi não entra em `pncp_janela`/`pncp_anual`: vai para `pncp_suspeito` (poucas linhas; 217 no pacote; podada com os anos antigos) e, no alvo, `pncp_contrato.valor_suspeito`. A produção lê `contas_municipio` no começo de cada execução (sem contas, vale só o teto). Regra e números em `docs/DECISOES.md`. O pacote passa a ser versão 2 (tabela `pncp_suspeito`; pacote antigo não carrega). Medido em 10/10/2026: `pncp_anual` 190.113 linhas (R$ 415 bi) e `pncp_janela` 32.700 (R$ 9,9 bi), contra ~R$ 10,6 tri sem a regra; `pncp_suspeito` 217 linhas (R$ 10,2 tri).

**Fica de fora:** contratos de antes do ano anterior; órgãos que não publicam no PNCP; valores pagos (a seção de TCE continua sendo a de pagamentos).

## TransfereGov (convênios e transferências especiais das emendas) na produção

Medido no banco local: `emenda_transferencia` 60 mil linhas, ~30 MB (mais ~3 MB de `emenda_convenio`). A carga baixa o zip de convênios da CGU (67 MB, só da internet para o runner; ~12 s e o CSV é lido em fluxo, sem disco além do temporário) e pagina a API do TransfereGov (~170 requisições, ~30 s, sem chave). Como o arquivo só muda em dia útil e o servidor informa o validador (HEAD), a segunda execução do dia não baixa nada. Por ser pequena em banco e em tempo, as duas cargas (`transferegov_convenios`, `transferegov_especiais`) estão no `run_all` diário, depois das emendas. Migração `0040_transferegov` (aditiva).


## Indicações de emendas de relator (RP9) na produção

Medido no banco local: `emenda_relator_indicacao` 7,9 mil linhas, ~4,7 MB (índices incluídos). A carga baixa uma planilha de 3 MB da CMO e, como o servidor informa ETag/Last-Modified e o arquivo é de 2022, a partir da segunda execução não baixa nada. Está no `run_all` (depois das emendas); pequena demais para exigir carga inicial separada. Migração `0041_emenda_relator` (aditiva).

## Runner no Brasil

Algumas fontes só respondem a IP brasileiro (geobloqueio): `acesso = "brasil"` em `backend/ingestion/fontes.toml`. Os runners hospedados do GitHub ficam nos EUA, então elas rodam num **self-hosted runner no PC do dono (Windows 11, no Brasil)**, com o label `brasil`. Não é proxy nem truque: é uma máquina no Brasil fazendo a coleta pública normal. Decisão e motivos em `docs/DECISOES.md` (2026-10-19).

**Jobs que usam `runs-on: [self-hosted, windows, brasil]`:**
- `ingestao-camaras.yml`: `almg`, `alepe`, `cldf`, `alrs`, `alba`, `ales`, `alema`, `alese`, `alap`, `alerr` (Assembleia de Roraima, SAPL) e `camaras-brasil` (SAPL de RO e RJ, que cobre Porto Velho e Armação dos Búzios). Os comentários no fim do arquivo marcam onde entram `alep` e `eagendas`.
- `ingestao-mensal.yml`: `tce-rs` (despesas por fornecedor do TCE-RS).
- Fora do runner: `querido_diario_atos` (acesso "espelho") e `dou_atos` (acesso "aberto") não são geobloqueio; não têm workflow porque alimentam filas de revisão humana, que ficam no acervo local.

**Instalar** (o dono, uma vez; o script não é executado por agentes):
1. Pré-requisitos no PC: Git para Windows em `C:\Program Files\Git` e `gh` autenticado (`gh auth login`). O serviço roda com um usuário próprio, que não enxerga o Python nem o PATH do dono: cada job põe `C:\Program Files\Gitin` no PATH (passo "Bash do Git no PATH") e instala o uv pela ação oficial, que baixa um Python gerenciado no primeiro `uv sync` (primeira execução de 20/10/2026 falhou com `bash: command not found` antes disso).
2. PowerShell **como administrador**, na raiz do repositório: `powershell -ExecutionPolicy Bypass -File scripts\instalar-runner-brasil.ps1` (use `-SoConferir` para só checar os pré-requisitos). O script baixa o runner na versão fixa, confere o SHA-256, cria o usuário local `runner-panoptico` sem admin, extrai em `C:\actions-runner-panoptico` (fora do repositório), pede o token de registro ao GitHub com a sua conta e instala o serviço.
3. No GitHub: **Settings > Actions > General > Fork pull request workflows from outside collaborators: Require approval for all outside collaborators.** Faça manualmente.
4. Teste: Actions > Câmaras e assembleias (SAPL) > Run workflow com `ufs` = `["RR"]`; o job `alerr` deve rodar no seu PC.

**Pausar e remover:**
- Pausar: `Stop-Service "actions.runner.*"` (como administrador); `Start-Service` para voltar. Os jobs do runner ficam na fila.
- Remover: `gh api -X POST repos/Gipsy7/panoptico/actions/runners/remove-token --jq .token` e, na pasta do runner, `.\config.cmd remove --token <token>`; depois apague a pasta e o usuário `runner-panoptico`.

**PC desligado ou sem rede:** o job espera um runner livre e é cancelado pelo GitHub depois de 24 horas na fila (`timeout-minutes` só conta depois que o job começa). Nada quebra: a produção mantém a última carga, e cada seção mostra a data dela (vem de `fonte_ingestao`). O `concurrency` do workflow mantém uma só execução pendente por fila, então cargas atrasadas não se empilham.

**Riscos e mitigação** (repositório público, AGPL):
- Quem consegue rodar workflow no runner executa código na sua máquina. Mitigação: os workflows do runner só têm gatilho `schedule` e `workflow_dispatch` (nunca `pull_request`, `pull_request_target` nem `issue_comment`); cada job tem `if: github.repository == 'Gipsy7/panoptico'` e só roda nos branches `main` e `dev`; `permissions: contents: read`; `timeout-minutes` em todos. Não crie workflow novo para o runner com outro gatilho.
- Pull requests de fora: a opção do passo 3 exige aprovação antes de qualquer workflow de fork rodar.
- O serviço roda com usuário comum, numa pasta com acesso restrito. O `DATABASE_URL` só existe nos Secrets do GitHub e chega ao job em memória; não grave segredo no PC.
- Um runner persistente guarda o `_work` de cada job. Não deixe ali nada que não possa ser lido pelos jobs.
- Mantenha o Windows e o runner em dia (o serviço se atualiza sozinho; o script fixa a versão só da instalação).
