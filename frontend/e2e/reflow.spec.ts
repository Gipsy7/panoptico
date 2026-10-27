import { expect, test, type Page } from "@playwright/test";
import { ROTAS } from "./rotas";

// Elementos mais largos que a janela, ignorando o que está dentro de um container com rolagem horizontal própria.
async function largos(page: Page) {
  return page.evaluate(() => {
    const larg = document.documentElement.clientWidth;
    const rolagemPropria = (el: Element) => {
      for (let p = el.parentElement; p && p !== document.documentElement; p = p.parentElement) {
        const ox = getComputedStyle(p).overflowX;
        if (ox === "auto" || ox === "scroll") return true;
      }
      return false;
    };
    const lista: string[] = [];
    for (const el of Array.from(document.body.querySelectorAll("*"))) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      if (r.right <= larg + 1 && r.left >= -1) continue;
      const cs = getComputedStyle(el);
      if (cs.position === "fixed" && r.right <= larg + 1) continue;
      if (rolagemPropria(el)) continue;
      lista.push(`<${el.tagName.toLowerCase()} class="${String(el.getAttribute("class") ?? "").slice(0, 80)}"> largura ${Math.round(r.width)} (esq ${Math.round(r.left)}, dir ${Math.round(r.right)})`);
    }
    return { scrollWidth: document.documentElement.scrollWidth, larg, culpados: lista.slice(0, 8), total: lista.length };
  });
}

async function carregar(page: Page, rota: string) {
  const resp = await page.goto(rota, { waitUntil: "load" });
  expect(resp?.status(), `status de ${rota}`).toBeLessThan(400);
  await page.waitForLoadState("networkidle").catch(() => {});
}

function msg(rota: string, r: Awaited<ReturnType<typeof largos>>) {
  return `${rota}: scrollWidth ${r.scrollWidth} > ${r.larg}\n` + r.culpados.map((c) => "    " + c).join("\n") + (r.total > 8 ? `\n    ... mais ${r.total - 8}` : "");
}

test.describe("reflow 320 px", () => {
  test.use({ viewport: { width: 320, height: 640 } });
  for (const rota of ROTAS) {
    test(rota, async ({ page }) => {
      await carregar(page, rota);
      const r = await largos(page);
      expect(r.scrollWidth <= 320 + 1 ? "" : msg(rota, r), `rolagem horizontal em ${rota}`).toBe("");
    });
  }
});

test.describe("texto a 200%", () => {
  test.use({ viewport: { width: 360, height: 740 } });
  for (const rota of ROTAS) {
    test(rota, async ({ page }) => {
      await carregar(page, rota);
      await page.evaluate(() => {
        document.documentElement.style.fontSize = "200%";
      });
      await page.waitForTimeout(300);

      const cortados = await page.evaluate(() => {
        const lista: string[] = [];
        for (const el of Array.from(document.body.querySelectorAll<HTMLElement>("*"))) {
          if (!el.textContent?.trim() || el.children.length > 0 && !Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent?.trim())) continue;
          const cs = getComputedStyle(el);
          if (cs.display === "none" || cs.visibility === "hidden") continue;
          if (cs.overflowX !== "hidden" || cs.textOverflow === "ellipsis" || el.clientWidth <= 1) continue;
          if (el.scrollWidth > el.clientWidth + 1)
            lista.push(`<${el.tagName.toLowerCase()} class="${String(el.getAttribute("class") ?? "").slice(0, 80)}"> scroll ${el.scrollWidth} > ${el.clientWidth}`);
        }
        return lista.slice(0, 8);
      });
      if (cortados.length) console.warn(`AVISO texto possivelmente cortado a 200% em ${rota}\n` + cortados.map((c) => "    " + c).join("\n"));

      const r = await largos(page);
      expect(r.scrollWidth <= 360 + 1 ? "" : msg(rota, r), `rolagem horizontal a 200% em ${rota}`).toBe("");
    });
  }
});
