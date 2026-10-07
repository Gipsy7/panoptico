---
name: nova-secao-no-perfil
description: Como adicionar ou mudar um número, seção ou página no site do Panóptico (perfil do parlamentar, página de representantes/cidade), da rota na API ao componente Next.js, seguindo os princípios de linguagem factual, fonte visível e comparação com a média da Casa. Use sempre que a tarefa mexer no que o cidadão vê — nova métrica, gráfico, card, texto, página, compartilhamento — ou em rotas da API que alimentam o site, mesmo que o pedido fale só de "frontend" ou só de "API".
---

# Nova seção no perfil (ou em outra página)

O público é o grande público brasileiro, quase sempre no celular, vindo de um link de WhatsApp. O critério de pronto do projeto: alguém sem familiaridade com política digita o CEP, acha um representante e entende o número em menos de um minuto. Tudo abaixo serve a isso.

## Princípios que não se negociam (e por quê)

- **Factual, sem juízo.** Nada de notas, rankings, selos, cores de "bom/ruim" ou adjetivos. Mostre o número e, ao lado, a **média da Casa** (média entre parlamentares em exercício, quem não tem nada entra com zero). Um percentual solto pode soar como acusação; prefira o fato literal ("votou em 31 de 59") e mostre o contexto que a fonte dá (ausências justificadas).
- **Fonte e data em toda seção**, com `<FonteRodape fonte=... url=... atualizadoEm=...>`. A data vem de `fonte_ingestao` (última carga `ok`).
- **Linguagem do dia a dia**: "gastos do gabinete", "projetos de lei", "dinheiro enviado para a cidade". O termo oficial aparece em letra menor (ex.: "Cota para o Exercício da Atividade Parlamentar (CEAP)").
- **Perfil em camadas**: números-chave no topo (`ResumoPerfil`), detalhes abaixo, tabelas longas em `<details>`.
- **Diga o que ficou de fora** quando houver recorte (ex.: "não inclui emendas de bancada"). E atualize a explicação em `frontend/app/sobre-as-fontes/page.tsx` e `docs/DECISOES.md`.

## Backend

1. Regra de cálculo em `backend/app/services/<assunto>.py`, devolvendo um `dict` com o dado, a média da Casa, `fonte_nome`, `fonte_url` e `atualizado_em`. Veja `services/gastos.py` e `services/presenca.py`.
2. Schema Pydantic em `backend/app/schemas/__init__.py` (valores monetários como `float` na resposta).
3. Rota em `backend/app/api/parlamentares.py` (use `_buscar` para o 404) ou num router novo registrado em `app/main.py`. Parâmetro `ano` opcional com padrão "ano mais recente com dados" e 404 para ano sem dados.
4. Teste em `backend/tests/` com dados montados (helpers `_popular` e `_ingestao` de `tests/test_api.py`), incluindo o valor da média com um caso calculável à mão.

## Frontend (Next.js 16 — diferente do que você conhece)

Antes de usar qualquer API do Next, leia a doc local em `frontend/node_modules/next/dist/docs/`. Neste projeto, com `cacheComponents` ligado:

- `params` e `searchParams` são **Promises** e precisam ficar dentro de `<Suspense>`: `{params.then(({ id }) => <Perfil id={id} />)}` (veja `app/parlamentar/[id]/page.tsx`).
- Tipos de página: `PageProps<"/rota">`; se o `tsc` reclamar da rota, rode `npx next typegen`.
- `next/image`: use `preload` (o `priority` foi descontinuado); fotos externas precisam estar em `images.remotePatterns` no `next.config.ts`.
- Busca de dados em Server Components via `frontend/lib/api.ts` (`getJson` devolve `{ok, dados}` ou `{ok:false, status, mensagem}`); adicione o tipo e a função `getX` ali. No perfil, busque em paralelo no `Promise.all` de `Perfil`.

Crie o componente em `frontend/components/<assunto>-secao.tsx` seguindo `gastos-secao.tsx`/`presenca-secao.tsx`: `<section aria-labelledby>`, `<h2 id=...>` (as âncoras do resumo apontam para esses ids), cards `rounded-xl bg-card p-4 ring-1 ring-foreground/10`, números com `tabular-nums`, formatação por `lib/formato.ts` (`formatarReais`, `formatarData`, `MESES`, `CASA_CURTA`). Se for número-chave, inclua também em `components/resumo-perfil.tsx`.

**Cores**: use os tokens do tema (`bg-chart-1`, `text-muted-foreground`, `text-primary`), nunca cores fixas. A paleta evita vermelho, azul e verde-amarelo como cor principal (associação partidária). Se for desenhar gráfico ou barra, carregue a skill `dataviz` antes e valide qualquer cor nova com o `validate_palette.js` dela.

**Acessibilidade**: contraste AA, `alt` nas imagens, foco visível, `role="meter"` com `aria-valuenow` em medidores, tabelas com `<th scope>`.

## Verificar

```bash
cd backend && python -m uv run pytest -q && python -m uv run ruff check .
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```

Depois **olhe a tela**: siga a skill `rodar-e-verificar` para subir tudo e tirar um screenshot em largura de celular. Leia o texto da seção como um cidadão leria: algum número sem contexto? algum termo técnico sem tradução? alguma palavra que soe como julgamento?
