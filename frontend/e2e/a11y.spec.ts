import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { ROTAS } from "./rotas";

// Impacto serious e critical reprovam; minor e moderate viram aviso no relatório.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

for (const tema of ["light", "dark"] as const) {
  test.describe(`axe, tema ${tema}`, () => {
    test.use({ colorScheme: tema });

    for (const rota of ROTAS) {
      test(`${rota}`, async ({ page }, info) => {
        const resp = await page.goto(rota, { waitUntil: "load" });
        expect(resp?.status(), `status de ${rota}`).toBeLessThan(400);
        await page.waitForLoadState("networkidle").catch(() => {});
        const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze();

        const linhas = (v: (typeof violations)[number]) =>
          `${v.id} [${v.impact}] ${v.help}\n` +
          v.nodes
            .slice(0, 5)
            .map((n) => `    alvo: ${n.target.join(" ")}  (rota ${rota}, ${tema}, ${info.project.name})`)
            .join("\n") +
          (v.nodes.length > 5 ? `\n    ... mais ${v.nodes.length - 5}` : "");

        const graves = violations.filter((v) => v.impact === "serious" || v.impact === "critical");
        const avisos = violations.filter((v) => !graves.includes(v));
        if (avisos.length) console.warn(`AVISO ${rota}\n` + avisos.map(linhas).join("\n"));
        expect(graves.map(linhas).join("\n"), `violações graves em ${rota}`).toBe("");
      });
    }
  });
}
