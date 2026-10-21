import type { MetadataRoute } from "next";
import { cacheLife } from "next/cache";

import { getAssembleia, getEleitos2026, getIdsProjetos, getMunicipios, getParlamentares } from "@/lib/api";
import { SITE_URL } from "@/lib/site";
import { UFS } from "@/lib/ufs";

type Entrada = MetadataRoute.Sitemap[number];

const FIXAS = [
  "/",
  "/parlamentares",
  "/projetos",
  "/partidos",
  "/impostos-e-repasses",
  "/segundo-turno",
  "/comparar",
  "/sobre-as-fontes",
  "/sobre-as-fontes/cobertura",
  "/status",
  "/privacidade",
  "/apoie",
];

const url = (caminho: string) => `${SITE_URL}${caminho === "/" ? "" : caminho}`;

/** Listas de perfis vindas da API. Se a API não responder, lança erro para o resultado não ficar em cache. */
async function perfis() {
  "use cache";
  cacheLife("days");

  const primeira = await getParlamentares({ pagina: "1" });
  if (!primeira.ok) throw new Error("API sem lista de parlamentares");
  const paginas = Math.ceil(primeira.dados.total / primeira.dados.por_pagina);
  const outras = await Promise.all(
    Array.from({ length: Math.max(paginas - 1, 0) }, (_, i) => getParlamentares({ pagina: String(i + 2) })),
  );
  const parlamentares = [primeira, ...outras].flatMap((r) => (r.ok ? r.dados.itens.map((p) => p.id) : []));

  const porUf = await Promise.all(
    UFS.map(async ({ sigla }) => {
      const [assembleia, eleitos, municipios] = await Promise.all([
        getAssembleia(sigla),
        getEleitos2026(sigla),
        getMunicipios(sigla),
      ]);
      const futuros = eleitos.ok
        ? [...eleitos.dados.presidente, ...eleitos.dados.governador, ...eleitos.dados.senadores]
        : [];
      return {
        estaduais: assembleia.ok ? assembleia.dados.itens.map((v) => v.id) : [],
        eleitos: futuros.filter((e) => !e.parlamentar_id).map((e) => e.id),
        cidades: municipios.ok ? municipios.dados.map((m) => m.ibge) : [],
      };
    }),
  );
  // Projetos do Congresso com votação nominal (rota barata: só casa e id).
  const projetosIds = await getIdsProjetos();
  const projetos = projetosIds.ok ? projetosIds.dados.itens.map((p) => `${p.casa}/${encodeURIComponent(p.id_externo)}`) : [];
  return {
    projetos,
    parlamentares,
    estaduais: porUf.flatMap((u) => u.estaduais),
    eleitos: [...new Set(porUf.flatMap((u) => u.eleitos))],
    cidades: porUf.flatMap((u) => u.cidades),
  };
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const fixas: Entrada[] = FIXAS.map((c) => ({ url: url(c) }));
  try {
    const p = await perfis();
    const dinamicas = [
      ...p.parlamentares.map((id) => `/parlamentar/${id}`),
      ...p.estaduais.map((id) => `/deputado-estadual/${id}`),
      ...p.eleitos.map((id) => `/eleito/${id}`),
      ...p.cidades.map((ibge) => `/cidade/${ibge}`),
      ...p.projetos.map((c) => `/projeto/${c}`),
    ];
    // Limite do protocolo: 50.000 URLs por arquivo. Hoje são bem menos; se passar, vira generateSitemaps.
    return [...fixas, ...dinamicas.map((c) => ({ url: url(c) }))].slice(0, 50000);
  } catch {
    return fixas;
  }
}
