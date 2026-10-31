// Gera o pack de redes sociais (PNG) com a logo oficial de frontend/lib/logo-caminhos.ts.
// Uso (na raiz): node scripts/gerar-pack-redes.mjs  →  marca/redes-sociais/*.png
// Usa o Playwright do frontend (Edge instalado ou Chromium do Playwright) e as fontes do Google Fonts.
import { createRequire } from "node:module";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(RAIZ, "frontend", "package.json"));
const { chromium } = require("playwright");
const SAIDA = join(RAIZ, "marca", "redes-sociais");
mkdirSync(SAIDA, { recursive: true });

// Caminhos da logo, lidos do TS para não duplicar a arte.
const ts = readFileSync(join(RAIZ, "frontend", "lib", "logo-caminhos.ts"), "utf8");
const caminho = (nome) => ts.match(new RegExp(`${nome}\\s*=\\s*"([^"]+)"`))[1];
const NOME = caminho("CAMINHO_NOME");
const SOCIAL = caminho("CAMINHO_SOCIAL");
const SOL = { cx: 65.5, cy: 62.5, escala: 2.17 };

const CLARO = { fundo: "#f4f1ea", tinta: "#141414", suave: "#6a665f", bronze: "#9c6a2a", bronzeTexto: "#7a5a32", nome: "#12263a", borda: "#e4ded1", cartao: "#f8f6f0" };
const ESCURO = { fundo: "#1c1a17", tinta: "#ece7dc", suave: "#a39d92", bronze: "#c9954a", bronzeTexto: "#d4a968", nome: "#ece7dc", borda: "#2e2a25", cartao: "#24211d" };

const r = (n) => Math.round(n * 100) / 100;
function raios(cx, cy, externo, interno, n = 12) {
  return Array.from({ length: n }, (_, i) => {
    const a = (i / n) * 2 * Math.PI - Math.PI / 2;
    return `<line x1="${r(cx + externo * Math.cos(a))}" y1="${r(cy + externo * Math.sin(a))}" x2="${r(cx + interno * Math.cos(a))}" y2="${r(cy + interno * Math.sin(a))}"/>`;
  }).join("");
}

/** Só o sol (marca), no desenho de 64×64. */
function marca(tamanho, cor, traco = 3.2) {
  return `<svg width="${tamanho}" height="${tamanho}" viewBox="0 0 64 64" fill="none" stroke="${cor}" stroke-linecap="round">
    <g stroke-width="${traco}">${raios(32, 32, 28, 15)}</g>
    <circle cx="32" cy="32" r="7.5" stroke-width="${traco * 0.8}"/></svg>`;
}

/** Logo completa: sol, "Panóptico" e ".social". `altura` em px. */
function logo(altura, p) {
  const largura = Math.round((786 * altura) / 127);
  return `<svg width="${largura}" height="${altura}" viewBox="0 0 786 127">
    <path d="${NOME}" fill="${p.nome}"/><path d="${SOCIAL}" fill="${p.bronze}"/>
    <g transform="translate(${SOL.cx} ${SOL.cy}) scale(${SOL.escala}) translate(-32 -32)" fill="none" stroke="${p.bronze}" stroke-linecap="round" stroke-width="2.6">
      ${raios(32, 32, 28, 15)}<circle cx="32" cy="32" r="7.5" stroke-width="2.1"/></g></svg>`;
}

/** Sol gigante de fundo, em traço quase da cor do papel (o panóptico invertido como textura). */
function solFundo(w, h, cx, cy, externo, interno, cor, traco, circulo = true) {
  return `<svg class="fundo" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" fill="none" stroke="${cor}" stroke-linecap="round">
    <g stroke-width="${traco}">${raios(cx, cy, externo, interno)}</g>
    ${circulo ? `<circle cx="${cx}" cy="${cy}" r="${interno * 0.5}" stroke-width="${traco * 0.8}"/>` : ""}</svg>`;
}

function pagina(w, h, p, corpo) {
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=block" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:${w}px;height:${h}px;overflow:hidden;background:${p.fundo};color:${p.tinta};font-family:Geist,sans-serif}
  .fundo{position:absolute;inset:0}
  .camada{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
  .serif{font-family:Newsreader,serif;letter-spacing:-0.01em}
  .suave{color:${p.suave}}
  .bronze{color:${p.bronzeTexto}}
  .sobre{font-weight:500;letter-spacing:0.14em;text-transform:uppercase;color:${p.bronzeTexto}}
</style></head><body>${corpo}</body></html>`;
}

const LEMA = "Quem te representa, às claras.";
const SITE = "panoptico.social.br";

const pecas = [
  // Foto de perfil: o sol cabe no corte circular (fica dentro de ~70% do diâmetro).
  { nome: "perfil-claro", w: 1080, h: 1080, p: CLARO, corpo: (p) => `<div class="camada">${marca(620, p.bronze, 3.4)}</div>` },
  { nome: "perfil-escuro", w: 1080, h: 1080, p: ESCURO, corpo: (p) => `<div class="camada">${marca(620, p.bronze, 3.4)}</div>` },

  // YouTube: 2560×1440; área segura (aparece em todo aparelho) é o centro de 1546×423.
  {
    nome: "youtube-banner", w: 2560, h: 1440, p: CLARO,
    corpo: (p) => `${solFundo(2560, 1440, 1280, 720, 1500, 880, p.borda, 26, false)}
      <div class="camada" style="gap:34px">
        ${logo(118, p)}
        <div class="serif" style="font-size:66px;font-weight:500">${LEMA}</div>
        <div class="suave" style="font-size:30px">Veja quem te representa, do presidente ao vereador, com dado oficial e fonte · ${SITE}</div>
      </div>`,
  },

  // X/Twitter: 1500×500; a foto de perfil cobre o canto inferior esquerdo.
  {
    nome: "x-capa", w: 1500, h: 500, p: CLARO,
    corpo: (p) => `${solFundo(1500, 500, 1290, 250, 160, 90, p.borda, 12)}
      <div class="camada" style="align-items:flex-start;padding-left:480px;gap:22px">
        ${logo(70, p)}
        <div class="serif" style="font-size:44px;font-weight:500">${LEMA}</div>
        <div class="suave" style="font-size:22px">Dado oficial, com fonte e data · ${SITE}</div>
      </div>`,
  },

  // Facebook: 1640×624; o celular corta as laterais, então tudo fica no centro.
  {
    nome: "facebook-capa", w: 1640, h: 624, p: CLARO,
    corpo: (p) => `${solFundo(1640, 624, 820, 312, 760, 440, p.borda, 16, false)}
      <div class="camada" style="gap:24px">
        ${logo(76, p)}
        <div class="serif" style="font-size:46px;font-weight:500">${LEMA}</div>
        <div class="suave" style="font-size:22px">Dado oficial, com fonte e data · ${SITE}</div>
      </div>`,
  },

  // LinkedIn: 1584×396; a foto cobre a esquerda.
  {
    nome: "linkedin-capa", w: 1584, h: 396, p: CLARO,
    corpo: (p) => `${solFundo(1584, 396, 1350, 198, 140, 80, p.borda, 11)}
      <div class="camada" style="align-items:flex-start;padding-left:440px;gap:18px">
        ${logo(62, p)}
        <div class="serif" style="font-size:38px;font-weight:500">${LEMA}</div>
        <div class="suave" style="font-size:20px">Dado oficial, com fonte e data · ${SITE}</div>
      </div>`,
  },

  // Post de apresentação (Instagram/Facebook, 4:5).
  {
    nome: "post-apresentacao", w: 1080, h: 1350, p: CLARO,
    corpo: (p) => `${solFundo(1080, 1350, 870, 250, 150, 85, p.borda, 11)}
      <div class="camada" style="align-items:flex-start;justify-content:space-between;padding:96px 88px">
        <div class="sobre" style="font-size:24px">— Dado oficial</div>
        <div>
          <div class="serif" style="font-size:96px;font-weight:500;line-height:1.02">Digite o CEP.<br>Veja quem te representa.</div>
          <div class="suave" style="font-size:34px;line-height:1.4;margin-top:40px;max-width:840px">Do presidente ao vereador: o que cada um faz, gasta, vota e recebe, com o link da fonte e a data.</div>
        </div>
        <div style="display:flex;width:100%;justify-content:space-between;align-items:center">
          ${logo(58, p)}<div class="bronze" style="font-size:26px;font-weight:500">${SITE}</div>
        </div>
      </div>`,
  },

  // Story (Instagram/WhatsApp status, 9:16): margens de 250 px em cima e embaixo ficam livres da interface.
  {
    nome: "story", w: 1080, h: 1920, p: CLARO,
    corpo: (p) => `<div class="camada" style="justify-content:space-between;padding:260px 88px">
        ${marca(300, p.bronze, 3.2)}
        <div style="text-align:center">
          <div class="serif" style="font-size:92px;font-weight:500;line-height:1.04">Quem te<br>representa,<br>às claras.</div>
          <div class="suave" style="font-size:36px;line-height:1.4;margin-top:44px">Veja quem te representa, do presidente ao vereador, com dado oficial e fonte.</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:22px">
          ${logo(64, p)}<div class="bronze" style="font-size:34px;font-weight:500">${SITE}</div>
        </div>
      </div>`,
  },

  // Miniatura de vídeo (YouTube, 1280×720): modelo com título trocável.
  {
    nome: "youtube-miniatura-modelo", w: 1280, h: 720, p: ESCURO,
    corpo: (p) => `${solFundo(1280, 720, 1090, 360, 150, 85, p.borda, 11)}
      <div class="camada" style="align-items:flex-start;justify-content:space-between;padding:72px 80px">
        <div class="sobre" style="font-size:26px">— Título da série</div>
        <div class="serif" style="font-size:88px;font-weight:500;line-height:1.04;max-width:820px">Título do vídeo em até duas linhas</div>
        ${logo(50, p)}
      </div>`,
  },
];

// Marca d'água do YouTube (aparece pequena no canto do vídeo, sobre qualquer cena): PNG quadrado com
// fundo transparente. "disco": sol bronze sobre disco creme; "vazada": sol creme com sombra, sem disco.
const MARCA_DAGUA = [
  {
    nome: "youtube-marca-dagua-disco", w: 300, h: 300,
    html: `<div class="camada"><div style="width:300px;height:300px;border-radius:50%;background:${CLARO.fundo};display:flex;align-items:center;justify-content:center">${marca(210, CLARO.bronze, 4.2)}</div></div>`,
  },
  {
    nome: "youtube-marca-dagua-vazada", w: 300, h: 300,
    html: `<div class="camada" style="filter:drop-shadow(0 0 6px rgba(0,0,0,.55))">${marca(270, CLARO.fundo, 4.6)}</div>`,
  },
];

let navegador;
try {
  navegador = await chromium.launch({ channel: "msedge" });
} catch {
  navegador = await chromium.launch();
}
for (const peca of pecas) {
  const pag = await navegador.newPage({ viewport: { width: peca.w, height: peca.h } });
  await pag.setContent(pagina(peca.w, peca.h, peca.p, peca.corpo(peca.p)), { waitUntil: "networkidle" });
  await pag.evaluate(() => document.fonts.ready);
  await pag.screenshot({ path: join(SAIDA, `${peca.nome}.png`) });
  await pag.close();
  console.log(`ok ${peca.nome} (${peca.w}×${peca.h})`);
}

for (const m of MARCA_DAGUA) {
  const pag = await navegador.newPage({ viewport: { width: m.w, height: m.h } });
  await pag.setContent(pagina(m.w, m.h, { ...CLARO, fundo: "transparent" }, m.html));
  await pag.screenshot({ path: join(SAIDA, `${m.nome}.png`), omitBackground: true });
  await pag.close();
  console.log(`ok ${m.nome} (${m.w}×${m.h}, transparente)`);
}

// Logo em SVG solto, para quem precisar de vetor (impressão, apresentações).
const { writeFileSync } = await import("node:fs");
writeFileSync(join(SAIDA, "logo-claro.svg"), logo(127, CLARO).replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" '));
writeFileSync(join(SAIDA, "logo-escuro.svg"), logo(127, ESCURO).replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" '));
writeFileSync(join(SAIDA, "marca-sol.svg"), marca(512, CLARO.bronze).replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" '));
await navegador.close();
