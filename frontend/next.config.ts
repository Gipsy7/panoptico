import type { NextConfig } from "next";

// Release (homologação em release.panoptico.social.br): build com NEXT_PUBLIC_AMBIENTE=release.
const EH_RELEASE = process.env.NEXT_PUBLIC_AMBIENTE?.trim().toLowerCase() === "release";

const nextConfig: NextConfig = {
  // O Dockerfile define NEXT_OUTPUT=standalone para gerar um servidor enxuto.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  cacheComponents: true,
  async redirects() {
    return [
      { source: "/dinheiro-federal", destination: "/impostos-e-repasses", permanent: true },
      { source: "/dinheiro-federal/:path*", destination: "/impostos-e-repasses/:path*", permanent: true },
    ];
  },
  async headers() {
    return [
      // O mesmo site responde em outros endereços (teste, reserva, api-*): só o principal vai ao Google.
      // O build de release não entra em índice nenhum, seja qual for o endereço.
      EH_RELEASE
        ? { source: "/:path*", headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] }
        : {
            source: "/:path*",
            has: [{ type: "host" as const, value: "(?!panoptico\\.social\\.br$).*" }],
            headers: [{ key: "X-Robots-Tag", value: "noindex" }],
          },
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
          { key: "Permissions-Policy", value: "geolocation=(self), camera=(), microphone=(), payment=()" },
        ],
      },
    ];
  },
  partialPrefetching: true,
  images: {
    remotePatterns: [
      new URL("https://www.camara.leg.br/internet/deputado/bandep/**"),
      new URL("https://www.senado.leg.br/senadores/img/fotos-oficiais/**"),
    ],
  },
  turbopack: {
    rules: {
      "globals.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
