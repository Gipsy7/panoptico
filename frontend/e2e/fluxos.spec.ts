import { type Page, expect, test } from "@playwright/test";

// Fumaça dos caminhos que definem o produto: cidade → representante → número com fonte; projeto →
// votação; comparação. Não confere valores (isso é dos testes da API): confere que cada tela abre,
// tem o que promete e não estoura a largura do celular. Só leitura, contra um site no ar.

const GASPAR = "4205902";

/** Erros de JavaScript da página (não os de rede de terceiros). */
function vigiarErros(page: Page): string[] {
  const erros: string[] = [];
  page.on("pageerror", (e) => erros.push(e.message));
  return erros;
}

async function semTelaDeErro(page: Page) {
  await expect(page.getByText(/Application error|Esta página não abriu|O site não abriu/)).toHaveCount(0);
}

async function cabeNaLargura(page: Page) {
  const sobra = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(sobra, "a página rola para o lado").toBeLessThanOrEqual(1);
}

test("da cidade ao perfil: representantes de Gaspar e o gasto do gabinete com fonte", async ({ page }) => {
  const erros = vigiarErros(page);
  await page.goto(`/representantes?municipio=${GASPAR}`);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await semTelaDeErro(page);
  await cabeNaLargura(page);

  // O primeiro perfil de parlamentar federal que a página oferece (senador ou deputado do estado).
  const perfil = page.locator('a[href^="/parlamentar/"]').first();
  await expect(perfil).toHaveCount(1);
  const href = await perfil.getAttribute("href");
  await page.goto(href!);

  await expect(page.getByRole("heading", { level: 1 })).not.toBeEmpty();
  // O resumo do topo: o gasto do gabinete em número literal, com a média da Casa ao lado.
  await expect(page.getByRole("heading", { name: /Em poucas palavras/ })).toBeVisible();
  // \s: o valor em reais vem com espaço que não quebra a linha.
  await expect(page.getByText(/Gastou R\$\s.+média da Casa/).first()).toBeVisible();
  // Fonte e data visíveis: regra fixa do projeto. Só os que estão à vista (há rodapés de fonte
  // dentro de blocos recolhidos).
  const fonte = page.getByText(/Fonte:[\s\S]*atualizado em \d{2}\/\d{2}\/\d{4}/i).filter({ visible: true });
  await expect(fonte.first()).toBeVisible();
  await semTelaDeErro(page);
  await cabeNaLargura(page);
  expect(erros).toEqual([]);
});

test("a cidade por dentro abre com o nome e sem estourar", async ({ page }) => {
  const erros = vigiarErros(page);
  await page.goto(`/cidade/${GASPAR}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Gaspar/);
  await semTelaDeErro(page);
  await cabeNaLargura(page);
  expect(erros).toEqual([]);
});

test("do projeto à votação: busca pelo número, abre o projeto e uma votação", async ({ page }) => {
  const erros = vigiarErros(page);
  await page.goto("/projetos?q=PL+2338%2F2023");
  const projeto = page.locator('a[href^="/projeto/"]').first();
  await expect(projeto).toBeVisible();
  await projeto.click();
  await expect(page).toHaveURL(/\/projeto\//);
  await expect(page.getByRole("heading", { level: 1 })).not.toBeEmpty();
  await semTelaDeErro(page);
  await cabeNaLargura(page);

  // Nem todo projeto tem votação nominal; quando tem, a página da votação precisa abrir.
  const votacao = page.locator('a[href^="/votacao/"]').first();
  if ((await votacao.count()) > 0) {
    await page.goto((await votacao.getAttribute("href"))!);
    await expect(page.getByRole("heading", { level: 1 })).not.toBeEmpty();
    await semTelaDeErro(page);
    await cabeNaLargura(page);
  }
  expect(erros).toEqual([]);
});

test("comparar dois senadores do estado mostra os números lado a lado", async ({ page }) => {
  const erros = vigiarErros(page);
  await page.goto("/representantes?uf=SC");
  const ids = await page.evaluate(() => {
    const vistos = new Set<string>();
    for (const a of document.querySelectorAll<HTMLAnchorElement>('a[href^="/parlamentar/"]')) {
      const id = a.getAttribute("href")!.split("/")[2].split(/[?#]/)[0];
      if (/^\d+$/.test(id)) vistos.add(id);
      if (vistos.size === 2) break;
    }
    return [...vistos];
  });
  expect(ids).toHaveLength(2);

  await page.goto(`/comparar?ids=${ids.join(",")}`);
  await expect(page.getByText("Gastos do gabinete").first()).toBeVisible();
  await expect(page.getByText(/média (Câmara|Senado)/).first()).toBeVisible();
  await semTelaDeErro(page);
  await cabeNaLargura(page);
  expect(erros).toEqual([]);
});

test("endereço que não existe responde 404 com caminho de volta", async ({ page }) => {
  const resposta = await page.goto("/pagina-que-nao-existe");
  expect(resposta?.status()).toBe(404);
  await expect(page.getByText("Página não encontrada").first()).toBeVisible();
  await expect(page.locator("main a").first()).toBeVisible();
});
