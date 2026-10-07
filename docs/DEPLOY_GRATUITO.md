# Publicação gratuita (Vercel + Neon + GitHub Actions)

| Parte | Onde | Endereço |
|---|---|---|
| Site (Next.js) | Vercel, projeto `panoptico` | https://panoptico.social.br |
| API (FastAPI) | Vercel, projeto `panoptico-api` | https://api.panoptico.social.br |
| Banco | Neon (plano gratuito, 0,5 GB) | — |
| Atualização diária dos dados | GitHub Actions (`.github/workflows/ingestao.yml`) | 6h de Brasília |

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
3. se alguma migração foi aplicada, recarrega todos os dados (leva cerca de 15 minutos);
4. avança o `main`, e a Vercel publica.

Assim o código novo nunca entra no ar antes de o banco estar pronto para ele, e o site não fica sem dados. Para forçar a recarga sem migração nova: **Actions → Publicar → Run workflow → recarregar**.

Regras:
- **Não envie direto para o `main`.** O Publicar só avança o `main` se for "fast-forward"; se o `main` tiver commits que o `dev` não tem, ele falha em vez de apagar trabalho.
- **Migrações só acrescentam** (tabelas e colunas opcionais). Remover ou renomear coluna exige duas publicações: primeiro o código para de usar, depois a migração remove.
- A ingestão diária e a recarga do Publicar não rodam ao mesmo tempo (mesmo grupo de concorrência), e cada fonte é trocada numa transação: durante a carga o site continua com os dados anteriores.

## Limites do plano gratuito

- **Neon:** 0,5 GB. O banco tem ~260 MB; os gastos do gabinete são a maior tabela e só guardamos o ano anterior e o atual.
- **Cold start:** depois de um tempo sem acesso, o banco e a API "acordam" e o primeiro acesso leva 1 a 3 segundos a mais.
- **Vercel Hobby:** uso não comercial.
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
