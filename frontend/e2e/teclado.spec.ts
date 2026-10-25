import { expect, test } from "@playwright/test";

// Fluxos só por teclado (sem mouse e sem toque).

test("Tab inicial mostra 'Pular para o conteúdo' e Enter leva o foco a #conteudo", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const pular = page.getByRole("link", { name: "Pular para o conteúdo" });
  await expect(pular).toBeFocused();
  await expect(pular).toBeVisible();
  await page.keyboard.press("Enter");
  // O resultado que importa: o próximo Tab cai dentro do conteúdo, não de volta no cabeçalho.
  await page.keyboard.press("Tab");
  await expect
    .poll(() => page.evaluate(() => !!document.activeElement?.closest("#conteudo")))
    .toBe(true);
});

test("menu do celular: Enter abre, Esc fecha e o foco volta ao botão", async ({ page }, info) => {
  test.skip(info.project.name !== "celular-360", "o menu em painel só existe no celular");
  await page.goto("/");
  const botao = page.getByRole("button", { name: /o menu$/i });
  await botao.focus();
  await page.keyboard.press("Enter");
  await expect(botao).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Escape");
  await expect(botao).toHaveAttribute("aria-expanded", "false");
  await expect(botao).toBeFocused();
});

test("CEP: inválido não sai da página; válido leva a /representantes", async ({ page }) => {
  await page.goto("/");
  // Com localização disponível o CEP fica atrás de "Prefiro digitar o CEP".
  const prefiro = page.getByRole("button", { name: "Prefiro digitar o CEP" });
  const campo = page.locator("input#cep");
  if (await prefiro.isVisible().catch(() => false)) {
    // Repete até a hidratação ligar o botão.
    await expect(async () => {
      if (await campo.isVisible()) return;
      await prefiro.focus({ timeout: 1000 });
      await page.keyboard.press("Enter");
      await expect(campo).toBeVisible({ timeout: 1000 });
    }).toPass({ timeout: 15_000 });
  }
  await expect(campo).toBeVisible();
  await campo.focus();
  await page.keyboard.type("123");
  await page.keyboard.press("Enter");
  await expect(page).not.toHaveURL(/\/representantes/);
  await campo.fill("");
  await campo.focus();
  await page.keyboard.type("89110000"); // Gaspar (SC)
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/representantes/);
});

// Achado do primeiro retrato: a gaveta abre, mas o foco continua no link (fora do dialog).
// A onda de foco/gavetas corrige; ao corrigir, trocar test.fixme por test.
test.fixme("representantes: prédio abre o painel e 'Ver a lista com os números' abre a gaveta com foco dentro", async ({ page }) => {
  await page.goto("/representantes?municipio=4205902");
  const predios = page.locator('svg [role="button"]');
  await expect(predios.first()).toBeVisible();
  await predios.nth(1).focus();
  await page.keyboard.press("Enter");
  const painel = page.locator("#painel-predio");
  await expect(painel).toBeVisible();
  const ver = painel.getByRole("link", { name: "Ver a lista com os números" });
  test.skip((await ver.count()) === 0, "o prédio escolhido não tem lista");
  await ver.focus();
  await page.keyboard.press("Enter");
  const gaveta = page.getByRole("dialog");
  await expect(gaveta).toBeVisible();
  await expect.poll(() => page.evaluate(() => !!document.activeElement?.closest('[role="dialog"]'))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(gaveta).toBeHidden();
  // O foco volta a algo útil (o link que abriu), não ao corpo da página.
  await expect(ver).toBeFocused();
});

test("abas do perfil: setas mudam aria-selected", async ({ page }) => {
  await page.goto("/parlamentar/538");
  const abas = page.getByRole("tab");
  await abas.first().focus();
  await expect(abas.first()).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("ArrowRight");
  await expect(abas.nth(1)).toHaveAttribute("aria-selected", "true");
  await expect(abas.first()).toHaveAttribute("aria-selected", "false");
  await page.keyboard.press("ArrowLeft");
  await expect(abas.first()).toHaveAttribute("aria-selected", "true");
});

// Achado do primeiro retrato: um link sem texto e um campo da home ficam com outline "none" ao
// receber foco. A onda 1 (contorno global) corrige; ao corrigir, trocar test.fixme por test.
test.fixme("foco visível nos 15 primeiros elementos focáveis da home", async ({ page }) => {
  await page.goto("/");
  const falhas: string[] = [];
  for (let i = 0; i < 15; i++) {
    await page.keyboard.press("Tab");
    const info = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el || el === document.body) return null;
      const s = getComputedStyle(el);
      const nome = `${el.tagName.toLowerCase()}${el.id ? "#" + el.id : ""} "${(el.textContent ?? "").trim().slice(0, 30)}"`;
      return { nome, largura: parseFloat(s.outlineWidth), estilo: s.outlineStyle };
    });
    if (info && !(info.largura > 0 && info.estilo !== "none")) {
      falhas.push(`${info.nome}: outline ${info.largura}px ${info.estilo}`);
    }
  }
  expect(falhas, "elementos sem contorno de foco").toEqual([]);
});

test.fixme("busca de cidade: combobox por teclado (onda 1: padrão APG, lista não fecha no blur)", async ({ page }) => {
  await page.goto("/impostos-e-repasses");
  await expect(page.getByRole("combobox").first()).toBeVisible();
});

test.fixme("mapa do Brasil: estado por teclado e leitor de tela (onda 1: aria-hidden nos itens fora de uso e onClick)", async ({
  page,
}) => {
  await page.goto("/impostos-e-repasses");
  await expect(page.locator('[role="button"][aria-label*="SC"]').first()).toBeVisible();
});
