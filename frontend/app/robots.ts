import type { MetadataRoute } from "next";

import { CAMINHOS_FORA_DO_ROBOTS, ROBOS_BLOQUEADOS, ROBOS_DE_IA_LIBERADOS } from "@/lib/seo";
import { EH_RELEASE, SITE_URL } from "@/lib/site";

// Robôs de IA que respondem com link (pesquisa e pedido do usuário) ficam liberados: é assim que o Panóptico pode
// ser citado nas respostas. Ficam bloqueados os coletores que gastam CPU ou revendem dados e, desde 13/11/2026, os de treino (em
// out/2026 o meta-externalagent visitou todos os perfis sem parar). O Cloudflare (Worker
// panoptico-troca, rota /configurar) aplica a mesma política no firewall, antes de o pedido chegar.
// Tudo mais é liberado, menos as rotas de imagem para compartilhamento (não são páginas para ler).
export default function robots(): MetadataRoute.Robots {
  // Release (homologação): o link é aberto, mas nenhum robô entra, e não há mapa do site.
  if (EH_RELEASE) return { rules: { userAgent: "*", disallow: "/" } };
  return {
    rules: [
      { userAgent: ROBOS_BLOQUEADOS, disallow: "/" },
      { userAgent: ROBOS_DE_IA_LIBERADOS, allow: "/", disallow: CAMINHOS_FORA_DO_ROBOTS },
      { userAgent: "*", allow: "/", disallow: CAMINHOS_FORA_DO_ROBOTS },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
