# Guia de design do Panóptico

Referência pedida pelo dono do projeto: https://12axes.vercel.app. Este guia copia a **disciplina** do 12axes
(ritmo, cartões, barras, mobile), não a paleta. O Panóptico continua "tinta e papel": marfim, tinta e bronze.
Auditoria feita em 17/10/2026 com Edge headless (360 e 390 px; 1280 px para home).

Nota de método: o Edge headless impõe janela mínima de ~500 px e recorta o screenshot, o que parece
"estouro" lateral mas não é. Os screenshots válidos usam um `<iframe>` de 360 px. As páginas que carregam
dados em streaming (perfil, comparador, partido) saíram no estado "Carregando" nesse método; os problemas
delas abaixo vêm da leitura do código e de um screenshot em 390 px anterior ao recorte. Reconferir em celular real.

## 1. O que o 12axes faz bem

- **Layout:** uma coluna única no celular, margem lateral constante (~16 px), cada bloco com um sobretítulo
  (`— CATÁLOGO`), título grande, subtítulo em cinza e só então o conteúdo. Nunca há dois níveis de caixa.
- **Ritmo vertical:** espaço grande e regular entre seções (~64 a 80 px) e pequeno dentro delas (8 a 16 px).
  A seção se separa por espaço e por um fio, não por fundo diferente. O olho sabe onde uma ideia termina.
- **Cartões:** poucos, todos iguais: borda fina, raio pequeno, número grande no alto, rótulo pequeno embaixo,
  uma ação ("Ver perfil") no canto inferior. O cartão de resumo (4 contadores 2x2) dá a dimensão do catálogo antes da lista.
- **Barras:** a faixa de 12 ícones por eixo e as barras de compatibilidade são finas, de altura única, com o valor
  escrito ao lado. A barra nunca vem sem número.
- **Tipografia:** uma família sans forte, títulos bem maiores que o texto (escala ~ 2,2x), texto corrido a 16 px
  com entrelinha ~1,6, legenda nunca abaixo de 13 px. Números em tamanho de título com `tabular-nums`.
- **Menu:** cabeçalho curto e fixo, logo à esquerda, **uma única ação primária** à direita ("Fazer o teste") em vez
  de menu hambúrguer escondendo tudo. Migalhas de pão (`Início / Partidos`) abaixo do cabeçalho.
- **Filtros:** busca + botão "Filtros" com contador + fileira de pílulas rolável na horizontal; o estado ativo é visível.
- **Animações:** curtas, de entrada (fade e subida), sem movimento contínuo. Carrossel com pontos indicando a posição.
- **Mobile:** alvos grandes (botões de 48 px, linhas de lista com 80 px), botões em largura total, grades 2x2 em vez
  de 4 colunas, textos cortados com reticências (`line-clamp`) em vez de crescerem.

## 2. O que adotar no Panóptico

Sem mudar a paleta. Nada de vermelho, azul ou verde-amarelo como cor principal (o 12axes usa verde, azul e vinho
para categorias; **não copiar**). Hierarquia só com:

1. **Tinta** (`--foreground`) para o que é mais importante, cinza quente (`--muted-foreground`) para apoio.
2. **Fio** (`figura`, `painel`, `lista-fios`): 1 px tinta para número em destaque, 1 px `--border` para separar.
3. **Peso e corpo:** Newsreader grande para números e títulos, Geist 500 para rótulos.
4. **Bronze** só em sobretítulo, marca, barra de dado, nota lateral e foco. Nunca como fundo de bloco.

Linguagem factual: sem adjetivo, sem "melhor/pior", sem semáforo. Comparar sempre com a média da Casa e dar a fonte.

Adotar do 12axes:
- Sobretítulo + título + subtítulo em toda página interna (já é o padrão; padronizar).
- Cartão-resumo 2x2 no alto de listas (ex.: /partidos: partidos, deputados, senadores, gasto médio).
- Migalhas de pão em páginas internas (partido, perfil, comparar).
- Filtros com contador e pílulas dos filtros ativos (ver "Filtros" na seção 4; as pílulas quebram linha, não rolam).
- Ação primária única no cabeçalho do celular ("Buscar pelo CEP" sempre visível) além do menu.
- Texto longo cortado com "ver mais" em vez de blocos de 10 linhas.
- Índice de seções no perfil (o 12axes tem âncoras `#como-funciona`, `#guia-eixos`).

## 3. Tokens

Espaçamento (escala de 4 px; usar apenas estes):

| Token | Valor | Uso |
|---|---|---|
| `--esp-1` | 4 px | ícone e rótulo |
| `--esp-2` | 8 px | dentro de pílulas e linhas |
| `--esp-3` | 12 px | entre rótulo e número |
| `--esp-4` | 16 px | margem lateral no celular, padding de cartão |
| `--esp-6` | 24 px | entre blocos dentro de uma seção |
| `--esp-10` | 40 px | entre seções no celular |
| `--esp-16` | 64 px | entre seções no desktop |

Tipografia (mínimo de 14 px em qualquer conteúdo; 12 px só em metadado não essencial e nunca como único meio de ler um dado):

| Papel | Celular | Desktop | Fonte |
|---|---|---|---|
| h1 | 32 px / 1,1 (`text-[2rem]`) | 56 px | Newsreader 450 |
| h2 | 26 px / 1,2 | 36 px | Newsreader 450 |
| número grande | 32 px | 40 px | Newsreader 400, tabular |
| texto | 16 px / 1,6 | 17 px | Geist 400 |
| texto de apoio, tabela | 14 px / 1,5 | 14 px | Geist 400 |
| sobretítulo | 12 px, versalete, 0,14em (hoje 0,7rem = 11,2 px: subir) | 12 px | Geist 500 |
| legenda e fonte | 13 px | 13 px | Geist 400 |

Cores e modo escuro. A paleta escura deriva da "papel" (grafite quente, texto creme, bronze clareado) e vale quando o
sistema pede escuro (`prefers-color-scheme`) ou com `data-theme="dark"` na raiz; `data-theme="light"` força o claro. Por
padrão o site segue o sistema; não há opção "Automático" escrita. O botão de tema (`components/alternar-tema.tsx`) é um
ícone só, que alterna entre claro e escuro e mostra para onde vai (lua no claro, sol no escuro), com `aria-label` e `title`
"Usar tema escuro"/"Usar tema claro". A escolha fica em `localStorage` (chave `tema`) e o script do `<head>` a aplica antes
da pintura. Fica no cabeçalho a partir de 640 px; abaixo disso (o cabeçalho não tem espaço ao lado do logo, do "Buscar CEP"
e do menu), no topo do painel do menu. As imagens
Open Graph ficam sempre claras. Razões de contraste (WCAG):

| Par | Claro | Escuro |
|---|---|---|
| texto / fundo (`#141414` / `#f4f1ea`; `#ece7dc` / `#1c1a17`) | 16,3 | 14,1 |
| texto de apoio / fundo (`#6e6a63`; `#a39d92`) | 4,8 | 6,4 |
| texto de apoio / cartão | 5,0 | 5,9 |
| texto de apoio / `--muted` | 4,4 (só em pílulas, 13 px; a corrigir na onda 1 da acessibilidade, meta 4,5) | 5,5 |
| bronze-texto / fundo (`#7a5a32`; `#d4a968`) | 5,6 | 8,0 |
| primary-foreground / primary | 16,3 | 14,1 |
| destructive / fundo (`#8a2c1c`; `#e39a86`) | 7,6 | 7,6 |
| bronze dos gráficos / fundo (mín. 3:1) | 4,1 | 6,5 |

Valores escuros: `--background #1c1a17`, `--card/--popover #24211d`, `--secondary #2b2823`, `--muted #2a2723`,
`--accent #322e28`, `--border #3a362f`, `--input #5a554b`, `--ring/--bronze #c9954a`, `--chart-1..5` `#c9954a #8f7650 #a39d92 #5a554b #ece7dc`,
`--sidebar* ` na mesma família. A sombra do menu é o token `--sombra-menu`.

Raio: `--radius` atual (0,25 rem; 2 px em botões e pílulas). Manter retangular, nada de pílula arredondada.
Sombras: nenhuma em cartões (o fio basta). Única exceção: painel do menu móvel e o cartão flutuante da home,
`--sombra-menu` (`0 16px 24px -20px rgb(0 0 0 / .25)` no claro). Alvos: altura mínima 44 px (botão, link isolado, seletor, linha de lista).

## 4. Componentes

**Cartão.** `bg-card`, borda 1 px `--border`, padding 16 px, sem sombra. Estrutura: sobretítulo, número (Newsreader),
rótulo, ação opcional. No celular, largura total; no desktop, grade de 2 a 4 colunas.

**Número com média da Casa.** Linha 1: rótulo (14 px, cinza). Linha 2: número em serifa 32 px. Linha 3: "Média da Casa:
X" em 14 px cinza. Tudo dentro de `figura` (fio de tinta em cima). Dois números lado a lado só se couberem em 360 px
(grade 2 colunas, 164 px cada); senão, empilhar.

**Barra neutra.** Trilho `--muted` com 8 px de altura, preenchimento `--bronze`, marca vertical de tinta (2 px) na média
da Casa, valor escrito à direita (não dentro da barra). `role="img"` com `aria-label` descrevendo valor e média.

**Tabela rolável com coluna fixa.**
```tsx
<div className="-mx-4 overflow-x-auto px-4">
  <table className="w-full min-w-[40rem] text-left text-sm">
    <th className="sticky left-0 bg-background ..."> {/* 1ª coluna fixa, fio à direita */}
```
Regras: sempre dentro de `overflow-x-auto`; `min-width` definido; primeira coluna `sticky left-0` com fundo opaco;
sombra de borda (gradiente de 8 px) à direita indicando que há mais; linhas com 44 px. Extrair para `ui/tabela-rolavel.tsx`.

**Menu móvel.** Cabeçalho 56 px: logo, botão "Buscar pelo CEP" (44 px) e botão de menu (44x44). Painel em tela cheia
sob o cabeçalho, links de 48 px, fecha ao tocar num link, ao tocar fora, e com Esc; trava a rolagem do fundo.
Migrar de `<details>` para botão com `aria-expanded` + `useState`.

**Filtros (padrão único).** `components/ui/painel-filtros.tsx` + `ui/campos-filtro.tsx` (+ `ui/campos-filtro-cliente.tsx`
para campos que dependem um do outro). Regras:
- Celular (< 768 px): botão "Filtrar" de largura total com "N filtros ativos"; abre uma folha que sobe de baixo, com título,
  "×", campos de 48 px (texto de 16 px) e rodapé fixo com "Limpar" e "Aplicar". Fecha com Esc, "×" ou toque fora; trava o
  fundo e prende o Tab na folha. Computador: os mesmos campos à vista, em grade de 3 colunas. Filtros de 1 ou 2 campos dentro
  de uma seção (agenda, tema dos votos) usam `sempreVisivel`.
- Estado sempre na URL: aplicar navega para o endereço sem os campos vazios nem os de valor padrão (`padroes`), sem rolar a
  página. A página passa `key` com a consulta atual para os campos voltarem ao que está na URL (voltar do navegador).
- Sem JavaScript: é um formulário GET aberto (a folha só se esconde com `data-js` na raiz).
- Filtros ativos como pílulas removíveis (×) logo abaixo (`PilulasAtivas`), que quebram linha; com 2 ou mais, "Limpar tudo".
- Contagem de resultados no título da lista; lista vazia com `SemResultados` ("Nenhum ... com esses filtros." + "Limpar os filtros").
- Estado: select grande com os 27 nomes. Cidade: select que só aparece com estado escolhido, recarregado ao trocar o estado,
  com caixa "Procurar cidade" quando a lista passa de 40. Ordenação: trocar o critério põe a ordem natural (texto A-Z,
  números do maior para o menor).
- Filtros que rodam no navegador (quem votou, como votou cada parlamentar) usam as mesmas pílulas e o mesmo estado vazio.

**Índice de seções (perfil).** No celular: fileira horizontal fixa sob o cabeçalho, com pílulas de 44 px de altura
(Gastos, Presença, Votos, Projetos, Emendas...), `scroll-snap-type: x proximity`, destaca a seção visível (peso 600 e fio
de bronze embaixo). No desktop: lista vertical `sticky top-20` numa coluna lateral de 200 px. Links são âncoras `#id`
com `scroll-margin-top` igual à altura dos dois cabeçalhos.

## 5. Regras para celular

1. **360 px sem rolagem horizontal da página.** Teste: `document.documentElement.scrollWidth <= 360` em cada rota.
   O que for mais largo rola dentro do próprio contêiner (`overflow-x-auto`), nunca no `body`.
2. **Alvos de 44 px ou mais** (altura e largura), com 8 px de espaço entre alvos. Link só de texto em corpo de frase é exceção;
   links soltos (ex.: "trocar") ganham `min-h-11 inline-flex items-center`.
3. Conteúdo a 14 px no mínimo; `text-xs` só em metadado repetido (UF, casa) e nunca em número ou texto de explicação.
4. Margem lateral de 16 px; nada de `fixed` com largura em px.
5. Títulos com `text-balance` e `break-words`; nomes longos de partido e de projeto quebram, não estouram.
6. Uma ação primária por tela; botões de formulário em largura total.
7. Imagens e fotos com `aspect-ratio` fixo para não pular o layout (CLS).
8. Respeitar `prefers-reduced-motion` (já feito). Animação só de entrada, no máximo 420 ms.
9. Conferir em 360 e em 390, e com zoom de texto a 200%.

## 6. Problemas atuais priorizados

Referências conferidas no código de `frontend/` em 17/10/2026.

**P1 (quebra a leitura ou o uso no celular)**
- Tabelas sem `overflow-x-auto` (estouram a página em 360 px): `components/destino-emendas-secao.tsx:107`,
  `components/emendas-relator-secao.tsx:24`, `components/projetos-secao.tsx:35`, `components/partido-secao.tsx:140`,
  `app/comparar/local/page.tsx:145`. Já corretas e a copiar: `components/gastos-secao.tsx:105` e `app/partidos/page.tsx:86`.
- Menu móvel `<details>` com botão de 40 px (`components/menu-principal.tsx:41`), painel que não fecha ao tocar fora nem com Esc
  (`menu-principal.tsx:50`), sem trava de rolagem do fundo.
- Perfil do parlamentar com 12 seções empilhadas e sem índice nem "voltar ao topo" (`app/parlamentar/[id]/page.tsx:138-180`);
  no celular são ~5 000 px de rolagem. A lista de votos (`votos-secao.tsx`) é a mais longa.
- "trocar" no comparador é `text-xs` sem área de toque (`app/comparar/page.tsx:343`), alvo de ~16 px.
- Comparador só aceita 2 pessoas e no celular espreme dois cartões em 164 px cada (`app/comparar/page.tsx:164-165`).

**P2 (legibilidade e consistência)**
- Excesso de texto pequeno: 116 usos de `text-xs`/`text-[0.7rem]` em 37 arquivos (os maiores: `candidatura-secao.tsx`,
  `atividade-local.tsx`, `fornecedores-pncp-secao.tsx`, `comparar/page.tsx`, `partido-secao.tsx`, `linha-do-tempo-secao.tsx`).
  Utilitário `sobretitulo` em 0,7 rem (`app/globals.css:200`) e `pilula` em 0,75 rem (`globals.css:185`): subir para 0,75 e 0,8125 rem.
- Home com `text-5xl` (48 px) em 360 px (`app/page.tsx:23`): quebra o título em 4 linhas e "às claras" fica no limite.
  Usar `text-[2rem] sm:text-5xl lg:text-6xl`.
- Botão `botao-linha` do cabeçalho com `h-9` (36 px) no desktop (`menu-principal.tsx:33`) e `seletor` de 44 px sem espaço entre alvos.
- Faixa de votos em `votos-secao.tsx` com três colunas ("Votou / Governo orientou / Maioria") cortadas em 360 px (screenshot do perfil).
- Falta migalha de pão e botão "voltar" nas páginas internas (partido, perfil, comparar).

**P3 (polimento)**
- Padronizar espaçamento entre seções (`gap-*` varia entre 8 e 14 nas páginas).
- Skeleton de carregamento mostra só uma foto cinza; mostrar a estrutura da seção (título, 3 linhas).
- Tabela `/partidos` (`min-w-[44rem]`) sem indicação visual de que rola.
- Cartão flutuante da home com sombra e ponta de segundo cartão: remover a sombra (fora da regra "sem sombra").
- Adicionar cartão-resumo 2x2 e pílulas de filtro roláveis em `/parlamentares` e `/partidos`.

## 7. Comparador de até 4 pessoas (estilo TudoCelular)

Rota única `/comparar?ids=1,10,57,88` (mesmo parâmetro da API; `a` e `b` continuam valendo). Mínimo 2, máximo 4.

**Celular, 360 px.** Colunas de 140 px de largura; a coluna de rótulos fica fixa à esquerda (96 px) e as pessoas rolam com
`scroll-snap-type: x mandatory`; cada coluna é um ponto de parada. Cabeçalho (fotos) fixo no topo com `sticky top-14`.
```
+--------------------------------------+ 360
| Panóptico.social     [CEP]  [menu]   |
+--------------------------------------+
| Comparar parlamentares     2 de 4    |
+--------+-----------------------------+  <- cabeçalho fixo (sticky)
|        | [foto]    [foto]  [ + ]     |
|        | Esperidião Ivete   Adicionar|
|        | PP·SC     MDB·SC           |
|        | [Remover] [Remover]        |
+--------+-----------------------------+
|Gastos  | R$ 269.307 | R$ 279.347 ->  |  <- rola de lado, encaixa (snap)
|2026    | média: ... | média: ...     |
|Presença| 58 de 62   | 53 de 62       |
|Projetos| 27         | 13             |
|Votos   | [ver matriz abaixo]         |
+--------+-----------------------------+
| Votos em comum (matriz)              |
|        Esp   Ive   Jor   Ana         |
|  Esp    -    95%   71%   60%         |
|  Ive   95%    -    74%   62%         |
|  Jor   71%   74%    -    80%         |
|  Ana   60%   62%   80%    -          |
|  "votaram igual em X de Y votações"  |
+--------------------------------------+
```
- Colunas de rótulo e de pessoa alinhadas por linha (cada linha tem altura única, 64 px) para não desencontrar ao rolar.
- Dica de rolagem: ponta da próxima coluna sempre visível (140 px x 2 + 96 = 376 > 360).
- Adicionar: botão "+" (44 px) abre uma folha de baixo com a busca por nome; remover: botão "Remover" de 44 px no cabeçalho.
- Matriz em tabela rolável com primeira coluna fixa; célula mostra o percentual e, abaixo em 13 px, "19 de 20".
  Intensidade só em cinza e bronze (fundo `--muted` a `--bronze` com 20% a 60% de opacidade); nunca verde/vermelho.

**Desktop, 1280 px.**
```
| Comparar parlamentares                              [Só diferenças] [Compartilhar] |
+-----------------+--------------+--------------+--------------+--------------+
| (rótulos fixos) | [foto]  X    | [foto]  X    | [foto]  X    |   [ + ]      |  <- sticky
|  200 px         | Nome         | Nome         | Nome         | Adicionar    |
+-----------------+--------------+--------------+--------------+--------------+
| Gastos 2026     | R$ 269.307   | R$ 279.347   | R$ 188.020   |              |
|   média da Casa | R$ 250.100   | ...          |              |              |
| Presença        | 58 de 62     | ...          |              |              |
| Projetos        | 27           | ...          |              |              |
+-----------------+--------------+--------------+--------------+--------------+
| Votos em comum: matriz par a par (4x4), clique na célula lista as votações |
```
- Colunas de 220 px até 4; com 2 ou 3 pessoas, distribuem a largura (`grid-template-columns: 200px repeat(n, 1fr)`).
- Cabeçalho `sticky top-0` e coluna de rótulos `sticky left-0`; filtro "Só diferenças" mantém só as linhas em que há valores distintos.
- Casas diferentes (Câmara × Senado): a matriz de votos em comum só compara pares da mesma Casa; os demais pares mostram "Casas diferentes".
- URL compartilhável e imagem Open Graph (já existe `app/comparar/imagem`) estendida para 3 e 4 pessoas.

Critérios de aceite: sem rolagem horizontal da página em 360 px; todos os alvos >= 44 px; teclado percorre colunas;
leitor de tela lê "Linha Gastos, Esperidião R$ 269.307, Ivete R$ 279.347".

## 7. Marca (logo)

Arte oficial: sol de 12 raios com círculo vazado, "Panóptico" em serifa própria (o "P" em caligrafia, laço longo à
esquerda) e ".social" em serifa menor na linha de base. O nome e o ".social" são caminhos SVG vetorizados da arte
(potrace, a partir da versão preto sobre branco) em `frontend/lib/logo-caminhos.ts`; não há fonte equivalente.
`components/logo.tsx` (`Logo`) usa o token `--marca-nome` (`text-marca-nome`) no nome e os tokens `bronze-texto` (".social") e
`bronze` (sol), então funciona em claro e escuro. `Marca` (só o sol) segue para rodapé e ícones. Imagens de
compartilhamento usam `LogoCompleta` em `lib/og.tsx`, com as cores fixas da paleta clara. O nome usa o azul-marinho da
arte (`--marca-nome`, #12263a; creme no escuro) por decisão do dono (2026-10-19), só na logo: nunca em texto, fundo ou dado. No cabeçalho de 56 px a logo tem 28 px de altura
(173 px de largura); acima disso o botão de menu estoura 360 px.

## 8. Acessibilidade

Meta: **WCAG 2.2 nível AA** e **eMAG 3.1** (Modelo de Acessibilidade em Governo Eletrônico). O plano e as ondas
estão em `C:\Users\samir\.claude\plans\tem-duas-coias-que-wild-hoare.md`; a decisão, em `docs/DECISOES.md` (2026-10-25).

### Checklist para toda tela nova

1. **Foco visível:** contorno de 2 px na cor `bronze-texto`, com afastamento, e pelo menos 3:1 contra o fundo nos dois temas.
   Nunca `focus-visible:outline-none` sem outro contorno no lugar.
2. **Teclado:** tudo operável com Tab, Enter e Espaço; Esc fecha o que abriu; abas, listas e combobox usam setas.
3. **Nome acessível:** botões e links com texto que diz o destino ("Ver gastos de Fulano", não "Ver mais"). Ícone sem texto tem `aria-label`.
4. **Imagens:** `alt` descritivo. `alt=""` quando o nome já está escrito ao lado da foto.
5. **Gráficos:** o valor aparece em texto ou tabela equivalente; nada transmite informação só por cor, forma ou posição.
6. **Tabelas:** `<caption>` (ou `rotulo` no `TabelaRolavel`), `th scope="col"` ou `"row"`.
7. **Formulários:** todo campo com `<label>`. Texto de ajuda ligado por `aria-describedby`. Erro na página, com `aria-invalid="true"` e `aria-describedby` apontando para a mensagem.
8. **Anúncios:** `role="status"` com frase curta ("Senado: 3 senadores"). Nunca um bloco inteiro dentro de `aria-live`.
9. **Diálogos (gavetas, folhas, menu):** foco preso dentro, Esc fecha, foco volta ao botão que abriu, e o resto da página fica `inert`.
10. **Links que abrem nova aba:** avisam no texto (componente `LinkExterno`, "(abre em nova aba)").
11. **Texto:** 14 px no mínimo para texto corrido; contraste AA: 4,5:1 texto, 3:1 componentes de interface e foco.
12. **Zoom e tamanho:** zoom de texto a 200% sem perda; reflow em 320 px sem rolagem horizontal da página.
13. **Movimento:** respeitar `prefers-reduced-motion`. Animação que repete tem botão para pausar (ou para sozinha após poucos ciclos).
14. **Idioma:** `lang="pt-BR"` na página; trecho em outro idioma com `lang` próprio.

### Como verificar

- `npm run lint` (com `jsx-a11y` no conjunto `strict`): roda no CI.
- `npm run e2e` (Playwright + axe): aponta para o site com `E2E_BASE_URL` (padrão: o acervo local). Falha com violações `serious` ou `critical`
  nas rotas principais, em 360 e 1280 px, tema claro e escuro, e roda os fluxos só por teclado de `e2e/teclado.spec.ts`.
- Workflow `acessibilidade.yml`: roda todo dia e sob demanda contra `https://panoptico.social.br`, só leitura.
- Teste manual: navegar a tela só com Tab, Enter e Esc, a 200% de zoom e em 360 px. Verificar o `scrollWidth` em 320 px.
- Testes automáticos pegam de 30% a 40% dos problemas de leitor de tela. Teste com pessoas reais fica para depois.
