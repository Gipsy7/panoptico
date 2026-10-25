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
  const campo = page.getByLabel("Digite seu CEP");
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

test("representantes: prédio abre o painel e 'Ver a lista com os números' abre a gaveta com foco dentro", async ({ page }) => {
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

test("foco visível nos 15 primeiros elementos focáveis da home", async ({ page }) => {
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

test("busca de cidade: combobox por teclado (seta marca, Enter escolhe, Esc fecha, status anuncia)", async ({ page }, info) => {
  await page.goto("/impostos-e-repasses");
  const campo = page.getByRole("combobox", { name: "Buscar cidade pelo nome" });
  // No celular o campo fica atrás da lupa.
  const lupa = page.getByRole("button", { name: "Buscar cidade", exact: true });
  if (!(await campo.isVisible())) await lupa.click();
  await expect(campo).toBeVisible();
  const status = campo.locator("xpath=following-sibling::p[@role='status']");
  // Repete até a hidratação ligar o campo e a lista de cidades chegar.
  await expect(async () => {
    await campo.fill("");
    await campo.focus();
    await page.keyboard.type("Gasp", { delay: 30 });
    await expect(status).toHaveText(/^\d+ resultados?$/, { timeout: 2000 });
  }).toPass({ timeout: 20_000 });
  await page.keyboard.press("ArrowDown");
  const id = await campo.getAttribute("aria-activedescendant");
  expect(id, "aria-activedescendant depois de ↓").toBeTruthy();
  await expect(page.locator(`[id="${id}"]`)).toHaveAttribute("aria-selected", "true");
  // Esc fecha a lista sem apagar a escolha de foco.
  await page.keyboard.press("Escape");
  await expect(campo).toHaveAttribute("aria-expanded", "false");
  await expect(campo).toBeFocused();
  // ↓ reabre; Enter escolhe e navega/seleciona.
  await page.keyboard.press("ArrowDown");
  await expect(campo).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp("/impostos-e-repasses/[A-Z]{2}/[0-9]+"));
  // No celular a busca inteira fecha ao escolher; no desktop o campo é limpo.
  if (info.project.name === "desktop-1280") await expect(campo).toHaveValue("");
});

test("mapa do Brasil: Tab entra uma vez, setas e letras mudam o item, Enter abre, Esc volta", async ({ page }) => {
  await page.goto("/impostos-e-repasses");
  const mapa = page.getByRole("group", { name: /mapa/i }).first();
  const ufsTab = mapa.locator('path[data-nivel="uf"][tabindex="0"]');
  await expect(ufsTab).toHaveCount(1);
  // Antes de qualquer foco, a parada de Tab é o primeiro em ordem alfabética (Acre).
  await expect(ufsTab).toHaveAttribute("data-id", "AC");
  const status = mapa.locator("xpath=..").getByRole("status");
  const focado = () => page.evaluate(() => (document.activeElement as SVGElement | null)?.dataset?.id ?? null);

  // Repete até a hidratação ligar os manipuladores.
  await expect(async () => {
    await ufsTab.focus();
    await page.keyboard.press("ArrowRight");
    expect(await focado()).toBe("AL");
  }).toPass({ timeout: 20_000 });
  await expect(status).toContainText("Alagoas");
  await expect(mapa.locator('path[data-nivel="uf"][tabindex="0"]')).toHaveAttribute("data-id", "AL");
  await page.keyboard.press("ArrowLeft");
  expect(await focado()).toBe("AC");
  await page.keyboard.press("End");
  expect(await focado()).toBe("TO");
  // Letras: "sa" vai a Santa Catarina.
  await page.keyboard.type("sa");
  expect(await focado()).toBe("SC");
  await expect(status).toContainText("Santa Catarina");

  // Tab sai do mapa de uma vez (não passa pelos outros estados).
  await page.keyboard.press("Tab");
  expect(await page.evaluate(() => !!document.activeElement?.closest('svg[role="group"]'))).toBe(false);
  await page.keyboard.press("Shift+Tab");
  expect(await focado()).toBe("SC");

  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/impostos-e-repasses\/SC/);
  // Dentro do estado o foco vai para uma cidade, e só uma é parada de Tab.
  await expect.poll(focado).toMatch(/^42\d{5}$/);
  await expect(mapa.locator('path[data-nivel="mun"][tabindex="0"]')).toHaveCount(1);
  const antes = await focado();
  await page.keyboard.press("ArrowDown");
  await expect.poll(focado).not.toBe(antes);

  await page.keyboard.press("Escape");
  await expect(page).toHaveURL(/\/impostos-e-repasses\/?(\?.*)?$/);
  await expect.poll(focado).toBe("SC");

  // Abre de novo para conferir o que fica de fora dentro do estado.
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/impostos-e-repasses\/SC/);
  // Dentro do estado: nenhum path de UF é focável por Tab nem visível ao leitor.
  const ufs = page.locator('path[data-nivel="uf"]');
  await expect(ufs.first()).toHaveAttribute("aria-hidden", "true");
  const problemas = await ufs.evaluateAll((els) =>
    els
      .filter((e) => e.getAttribute("aria-hidden") !== "true" || e.getAttribute("tabindex") !== "-1")
      .map((e) => (e as SVGElement).dataset.id),
  );
  expect(problemas, "UFs ainda expostas dentro do estado").toEqual([]);
  // Uma cidade do estado segue como parada de Tab.
  await expect(page.locator('path[data-nivel="mun"][tabindex="0"]')).toHaveCount(1);
});

/** Quantos elementos focáveis fora de `seletor` (e fora dos `ate`) não estão sob um ancestral `inert`. */
async function focaveisAtivosFora(page: import("@playwright/test").Page, seletor: string, permitidos: string[] = []) {
  return page.evaluate(
    ([sel, ok]) => {
      const dentro = document.querySelector(sel);
      return [...document.querySelectorAll<HTMLElement>("a[href], button, input, select, textarea, [tabindex]")]
        .filter((e) => e.tabIndex >= 0 && !dentro?.contains(e) && !e.closest("[inert]") && !ok.some((s) => e.closest(s)))
        .map((e) => e.outerHTML.slice(0, 80));
    },
    [seletor, permitidos] as [string, string[]],
  );
}

test("diálogos deixam o fundo inerte: gaveta e menu do celular", async ({ page }, info) => {
  if (info.project.name === "celular-360") {
    await page.goto("/");
    const botao = page.getByRole("button", { name: /o menu$/i });
    await expect(async () => {
      await botao.click();
      await expect(botao).toHaveAttribute("aria-expanded", "true", { timeout: 1500 });
    }).toPass({ timeout: 15_000 });
    expect(await focaveisAtivosFora(page, "#menu-celular", ['button[aria-controls="menu-celular"]'])).toEqual([]);
    await page.keyboard.press("Escape");
    await expect(botao).toHaveAttribute("aria-expanded", "false");
    expect(await page.locator("[inert]").count()).toBe(0);
  }

  await page.goto("/representantes?municipio=4205902");
  const predios = page.locator('svg [role="button"]');
  await expect(predios.first()).toBeVisible();
  await predios.nth(1).focus();
  await page.keyboard.press("Enter");
  const ver = page.locator("#painel-predio").getByRole("link", { name: "Ver a lista com os números" });
  test.skip((await ver.count()) === 0, "o prédio escolhido não tem lista");
  await ver.focus();
  await page.keyboard.press("Enter");
  const gaveta = page.getByRole("dialog");
  await expect(gaveta).toBeVisible();
  expect(await focaveisAtivosFora(page, '[role="dialog"]')).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(gaveta).toBeHidden();
  expect(await page.locator("[inert]").count()).toBe(0);
});
