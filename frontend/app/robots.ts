import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// Tudo liberado, menos as rotas que geram imagem para compartilhamento (não são páginas para gente
// ler) e a lista de resultados de busca por CEP, que depende do que a pessoa digitou.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/segundo-turno/imagem", "/comparar/imagem", "/*/opengraph-image"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
