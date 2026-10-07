import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // O Dockerfile define NEXT_OUTPUT=standalone para gerar um servidor enxuto.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  cacheComponents: true,
  partialPrefetching: true,
  images: {
    remotePatterns: [
      new URL("https://www.camara.leg.br/internet/deputado/bandep/**"),
      new URL("https://www.senado.leg.br/senadores/img/fotos-oficiais/**"),
    ],
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
