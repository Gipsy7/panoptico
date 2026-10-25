import { defineConfig } from "@playwright/test";

// Régua automática de acessibilidade. Roda contra um site já no ar (E2E_BASE_URL), nunca sobe o app.
// Local: usa o Edge instalado (EDGE_PATH muda o caminho). No CI (CI=true): o chromium do Playwright.
const edge = process.env.EDGE_PATH ?? "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const launchOptions = process.env.CI ? {} : { executablePath: edge };

export default defineConfig({
  testDir: "e2e",
  // Um worker só: o firewall da produção limita 120 req/min.
  workers: 1,
  fullyParallel: false,
  retries: 1,
  timeout: 60_000,
  reporter: [["list"], ["html", { outputFolder: "e2e-relatorio", open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3005",
    launchOptions,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "celular-360",
      use: { viewport: { width: 360, height: 740 }, hasTouch: true, deviceScaleFactor: 2 },
    },
    { name: "desktop-1280", use: { viewport: { width: 1280, height: 800 } } },
  ],
});
