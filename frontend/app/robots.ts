import type { MetadataRoute } from "next";

import { CAMINHOS_FORA_DO_ROBOTS, ROBOS_BLOQUEADOS, ROBOS_DE_IA_LIBERADOS } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// Robôs de IA de pesquisa e de treino das grandes IAs ficam liberados: é assim que o Panóptico pode
// ser citado nas respostas. Ficam bloqueados só os coletores que gastam CPU ou revendem dados (em
// out/2026 o meta-externalagent visitou todos os perfis sem parar). O Cloudflare (Worker
// panoptico-troca, rota /configurar) aplica a mesma política no firewall, antes de o pedido chegar.
// Tudo mais é liberado, menos as rotas de imagem para compartilhamento (não são páginas para ler).
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: ROBOS_BLOQUEADOS, disallow: "/" },
      { userAgent: ROBOS_DE_IA_LIBERADOS, allow: "/", disallow: CAMINHOS_FORA_DO_ROBOTS },
      { userAgent: "*", allow: "/", disallow: CAMINHOS_FORA_DO_ROBOTS },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
