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

## Limites do plano gratuito

- **Neon:** 0,5 GB. O banco tem ~260 MB; os gastos do gabinete são a maior tabela e só guardamos o ano anterior e o atual.
- **Cold start:** depois de um tempo sem acesso, o banco e a API "acordam" e o primeiro acesso leva 1 a 3 segundos a mais.
- **Vercel Hobby:** uso não comercial.
- **GitHub Actions:** em repositório público, os workflows agendados são **desativados depois de 60 dias sem commits**. O GitHub avisa por e-mail; basta reativar em **Actions** ou fazer um commit.
- **Arquivos brutos:** ficam 7 dias como artefato de cada execução (aba **Actions → execução → Artifacts**).
