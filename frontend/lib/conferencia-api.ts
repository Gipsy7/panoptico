// Gera a conferência dos tipos escritos à mão em lib/api.ts contra o contrato da API
// (lib/openapi.json, de `python -m app.openapi_exportar`). Lógica pura: o teste
// lib/conferencia-api.test.ts compara o resultado com lib/api-conferencia.ts gravado, e o
// `tsc` (no build) acusa o tipo que não bate com a resposta da rota.
//
// Para gravar de novo: `npm run tipos-api` (gera lib/api-schema.ts e lib/api-conferencia.ts).

export type ParDeTipo = { tipo: string; caminho: string };

/** Cada `getJson<Tipo>(\`/rota\`)` de lib/api.ts, com a rota no formato do OpenAPI. */
export function paresDoApi(fonte: string): ParDeTipo[] {
  const pares: ParDeTipo[] = [];
  const padrao = /getJson<\s*([A-Za-z_][A-Za-z0-9_]*(?:\[\])?)\s*>\(\s*([`"])([\s\S]*?)\2/g;
  for (const m of fonte.matchAll(padrao)) {
    const caminho = m[3]
      // Consulta montada no fim (`${q ? `?${q}` : ""}`): a leitura para no acento grave de dentro e
      // sobra um `${` sem fechar. Some, assim como um `${...}` grudado no fim de um trecho, sem barra
      // antes (`/gastos${query}`): é consulta, não parte do caminho.
      .replace(/\$\{[^}]*$/, "")
      .replace(/([^/])\$\{[^}]*\}$/, "$1")
      .split("?")[0]
      .replace(/\$\{[^}]*\}/g, "{}");
    pares.push({ tipo: m[1], caminho });
  }
  return pares;
}

/** A rota do contrato que casa com o caminho (`{}` vale qualquer parâmetro), ou nulo. */
export function rotaDoContrato(caminho: string, rotas: string[]): string | null {
  const partes = caminho.split("/");
  const candidatas = rotas.filter((r) => {
    const rp = r.split("/");
    if (rp.length !== partes.length) return false;
    return rp.every((seg, i) => {
      const meu = partes[i];
      if (meu === "{}") return seg.startsWith("{");
      if (meu.includes("{}")) {
        // "{}.webp" e parecidos: o literal em volta precisa bater.
        const [antes, depois] = meu.split("{}");
        return seg.startsWith(antes) && seg.endsWith(depois) && seg.includes("{");
      }
      return seg === meu;
    });
  });
  // Rota literal ganha da que tem parâmetro no mesmo lugar (/projetos/temas x /projetos/{casa}).
  candidatas.sort((a, b) => (a.match(/\{/g)?.length ?? 0) - (b.match(/\{/g)?.length ?? 0));
  return candidatas[0] ?? null;
}

export type Conferencia = { linhas: string[]; semRota: ParDeTipo[]; semEsquema: ParDeTipo[] };

/** O conteúdo de lib/api-conferencia.ts. */
export function gerarConferencia(fonteApi: string, contrato: { paths: Record<string, Record<string, unknown>> }): Conferencia {
  const rotas = Object.keys(contrato.paths);
  const semRota: ParDeTipo[] = [];
  const semEsquema: ParDeTipo[] = [];
  const usados = new Set<string>();
  const linhas: string[] = [];
  for (const par of paresDoApi(fonteApi)) {
    // Tipo escrito na própria chamada ({ status: string }) não é conferido.
    if (!/^[A-Z][A-Za-z0-9_]+/.test(par.tipo)) continue; // nem genérico (T) nem tipo escrito na chamada
    const rota = rotaDoContrato(par.caminho, rotas);
    if (!rota) {
      semRota.push(par);
      continue;
    }
    const get = contrato.paths[rota].get as { responses?: Record<string, { content?: Record<string, { schema?: unknown }> }> } | undefined;
    const esquema = get?.responses?.["200"]?.content?.["application/json"]?.schema as Record<string, unknown> | undefined;
    if (!esquema || Object.keys(esquema).length === 0) {
      semEsquema.push(par);
      continue;
    }
    const chave = `${par.tipo}|${rota}`;
    if (usados.has(chave)) continue;
    usados.add(chave);
    const base = par.tipo.replace(/\[\]$/, "");
    // Rota que devolve um de dois formatos (o site escolhe pelo pedido): basta caber em um deles.
    const umDeVarios = Array.isArray(esquema.anyOf) || Array.isArray(esquema.oneOf);
    const nome = `_${base.replace(/\W/g, "")}_${linhas.length}`;
    linhas.push(
      umDeVarios
        ? `type ${nome} = Ok<CabeEmUm<${par.tipo}, Enviado<Resposta<"${rota}">>>>;`
        : `type ${nome} = Confere<${par.tipo}, Enviado<Resposta<"${rota}">>>;`,
    );
  }
  return { linhas, semRota, semEsquema };
}

/** O arquivo inteiro, pronto para gravar. */
export function arquivoConferencia(c: Conferencia, tipos: string[]): string {
  return [
    "// GERADO por `npm run tipos-api` (lib/conferencia-api.ts). Não edite à mão.",
    "// Cada linha diz: a resposta desta rota (lib/api-schema.ts, do contrato da API) cabe no tipo",
    "// que o site espera (lib/api.ts). Se o `tsc` acusar uma linha, a API e o site divergem.",
    "/* eslint-disable @typescript-eslint/no-unused-vars */",
    `import type { ${tipos.join(", ")} } from "@/lib/api";`,
    'import type { paths } from "@/lib/api-schema";',
    "",
    "type Resposta<R extends keyof paths> = paths[R] extends {",
    '  get: { responses: { 200: { content: { "application/json": infer T } } } };',
    "}",
    "  ? T",
    "  : never;",
    "// Duas folgas, de propósito:",
    "// - Solto: o site pode estreitar um texto (\"camara\" | \"senado\") onde a API declara só `str`.",
    "// - Enviado: campo com valor padrão sai sempre na resposta (o Pydantic serializa os padrões),",
    "//   mas o contrato o marca como opcional.",
    "type Solto<T> = T extends string",
    "  ? string",
    "  : T extends (infer U)[]",
    "    ? Solto<U>[]",
    "    : T extends object",
    "      ? { [K in keyof T]: Solto<T[K]> }",
    "      : T;",
    "type Enviado<T> = T extends (infer U)[]",
    "  ? Enviado<U>[]",
    "  : T extends object",
    "    ? { [K in keyof T]-?: Enviado<Exclude<T[K], undefined>> }",
    "    : T;",
    "/** Falha na compilação quando a resposta da rota não cabe no tipo que o site espera. */",
    "type Confere<Esperado, Real extends Solto<Esperado>> = Real;",
    "/** Para rota com mais de um formato de resposta: algum deles cabe no tipo do site. */",
    "type CabeEmUm<Esperado, Real> = [Extract<Real, Solto<Esperado>>] extends [never] ? false : true;",
    "type Ok<T extends true> = T;",
    "",
    ...c.linhas,
    "",
  ].join("\n");
}

/** Os nomes de tipo usados nas linhas, para o import. */
export function tiposUsados(c: Conferencia): string[] {
  return [...new Set(c.linhas.map((l) => /(?:Confere|CabeEmUm)<([A-Za-z0-9_]+)/.exec(l)![1]))].sort();
}
