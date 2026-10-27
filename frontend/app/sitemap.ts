import type { MetadataRoute } from "next";
import { cacheLife } from "next/cache";

import { getAssembleia, getEleitos2026, getFontes, getIdsProjetos, getMunicipios, getParlamentares } from "@/lib/api";
import { caminhoRepresentantes } from "@/lib/seo";
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
  "/acessibilidade",
  "/apoie",
  "/apoiadores",
  "/o-panoptico",
  "/perguntas",
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
        cidades: municipios.ok ? municipios.dados.map((m) => ({ ibge: m.ibge, uf: sigla })) : [],
      };
    }),
  );
  // Projetos do Congresso com votação nominal (rota barata: só casa e id).
  const projetosIds = await getIdsProjetos();
  const projetos = projetosIds.ok ? projetosIds.dados.itens.map((p) => `${p.casa}/${encodeURIComponent(p.id_externo)}`) : [];
  // Data da carga mais recente (fonte_ingestao): é a data real em que os dados dos perfis mudaram.
  const fontes = await getFontes();
  const datas = fontes.ok ? fontes.dados.map((f) => f.atualizado_em).filter((d): d is string => Boolean(d)) : [];
  const atualizado = datas.length ? datas.reduce((a, b) => (a > b ? a : b)) : undefined;
  return {
    atualizado,
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
      ...UFS.map(({ sigla }) => caminhoRepresentantes({ uf: sigla })),
      // "Quem me representa em <cidade>": a porta de entrada de quem busca pelo nome da cidade.
      ...p.cidades.map((c) => caminhoRepresentantes({ uf: c.uf, municipio: c.ibge })),
      ...p.parlamentares.map((id) => `/parlamentar/${id}`),
      ...p.estaduais.map((id) => `/deputado-estadual/${id}`),
      ...p.eleitos.map((id) => `/eleito/${id}`),
      ...p.cidades.map((c) => `/cidade/${c.ibge}`),
      ...p.projetos.map((c) => `/projeto/${c}`),
    ];
    // Limite do protocolo: 50.000 URLs ou 50 MB por arquivo. Hoje são ~13 mil (~1 MB); se passar de 40 mil, vira
    // generateSitemaps (e o robots.txt passa a listar cada /sitemap/N.xml).
    const todas = [...fixas, ...dinamicas.map((c) => ({ url: url(c), lastModified: p.atualizado }))];
    if (todas.length > 40000) console.warn(`sitemap com ${todas.length} URLs: dividir com generateSitemaps`);
    return todas.slice(0, 50000);
  } catch {
    return fixas;
  }
}
