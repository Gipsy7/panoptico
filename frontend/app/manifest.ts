import type { MetadataRoute } from "next";

import { COR_PAPEL } from "@/lib/marca-svg";

// Necessário para o iPhone: os avisos só existem para o site adicionado à tela inicial.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Panóptico",
    short_name: "Panóptico",
    description: "Quem te representa, às claras.",
    lang: "pt-BR",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: COR_PAPEL,
    theme_color: COR_PAPEL,
    icons: [
      { src: "/icone-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icone-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
