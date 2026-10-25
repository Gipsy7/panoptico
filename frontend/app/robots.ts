import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// Robôs que coletam páginas para treinar IA (não são buscadores nem prévias de link). Em out/2026
// o meta-externalagent visitou todos os perfis sem parar e esgotou a CPU do plano; o firewall da
// Vercel também os bloqueia (regra "Bloquear robos de coleta para IA").
const ROBOS_DE_IA = [
  "meta-externalagent",
  "GPTBot",
  "ClaudeBot",
  "anthropic-ai",
  "Bytespider",
  "CCBot",
  "Amazonbot",
  "PerplexityBot",
  "Google-Extended",
  "Applebot-Extended",
  "cohere-ai",
  "Diffbot",
];

// Tudo liberado, menos as rotas que geram imagem para compartilhamento (não são páginas para gente
// ler) e a lista de resultados de busca por CEP, que depende do que a pessoa digitou.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: ROBOS_DE_IA, disallow: "/" },
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/segundo-turno/imagem", "/comparar/imagem", "/*/opengraph-image"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
