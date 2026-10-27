import { expect, test } from "@playwright/test";

// No computador, logo e menu cabem numa linha só (a quebra de linha é só para celular com
// letra grande). Folga pequena: um item novo no menu pode estourar; este teste avisa.
test("cabeçalho do computador em uma linha, sem estourar", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1280", "só no computador");
  await page.goto("/");
  const medida = await page.evaluate(() => {
    const d = document.getElementById("menu-principal")!;
    return { altura: d.getBoundingClientRect().height, scroll: d.scrollWidth, largura: d.clientWidth };
  });
  expect(medida.altura).toBeLessThanOrEqual(60);
  expect(medida.scroll).toBeLessThanOrEqual(medida.largura + 1);
});
