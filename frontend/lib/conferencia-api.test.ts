import { readFileSync } from "node:fs";
import { join } from "node:path";

import openapiTS, { astToString } from "openapi-typescript";
import { describe, expect, it } from "vitest";

import { arquivoConferencia, gerarConferencia, paresDoApi, rotaDoContrato, tiposUsados } from "./conferencia-api";

const lib = join(__dirname);
const ler = (nome: string) => readFileSync(join(lib, nome), "utf-8").replace(/\r\n/g, "\n");

describe("paresDoApi", () => {
  it("tira a rota de cada chamada, com parâmetros e sem a consulta", () => {
    const fonte = [
      "return getJson<Gastos>(\n    `/parlamentares/${encodeURIComponent(id)}/gastos${query}`,\n  );",
      "return getJson<Representantes>(`/representantes?${params}`);",
      'return getJson<{ status: string }>("/saude");',
      "return getJson<Agenda>(`/executivo/${id}/agenda${q ? `?${q}` : \"\"}`);",
      "return getJson<Foto[]>(`/fotos/${id}.webp`);",
    ].join("\n");
    expect(paresDoApi(fonte)).toEqual([
      { tipo: "Gastos", caminho: "/parlamentares/{}/gastos" },
      { tipo: "Representantes", caminho: "/representantes" },
      { tipo: "Agenda", caminho: "/executivo/{}/agenda" },
      { tipo: "Foto[]", caminho: "/fotos/{}.webp" },
    ]);
  });
});

describe("rotaDoContrato", () => {
  const rotas = ["/projetos/{casa}/{id_externo}", "/projetos/temas", "/projetos/local/{projeto_local_id}", "/fotos/{candidatura_id}.webp"];

  it("rota literal ganha da que tem parâmetro no mesmo lugar", () => {
    expect(rotaDoContrato("/projetos/temas", rotas)).toBe("/projetos/temas");
    expect(rotaDoContrato("/projetos/local/{}", rotas)).toBe("/projetos/local/{projeto_local_id}");
    expect(rotaDoContrato("/projetos/{}/{}", rotas)).toBe("/projetos/{casa}/{id_externo}");
  });

  it("parâmetro com extensão e rota que não existe", () => {
    expect(rotaDoContrato("/fotos/{}.webp", rotas)).toBe("/fotos/{candidatura_id}.webp");
    expect(rotaDoContrato("/nao/existe", rotas)).toBeNull();
  });
});

describe("arquivos gerados em dia (rode `npm run tipos-api` se falhar)", () => {
  const contrato = JSON.parse(ler("openapi.json"));

  it("lib/api-conferencia.ts confere todas as chamadas de lib/api.ts", () => {
    const c = gerarConferencia(ler("api.ts"), contrato);
    expect(c.semRota).toEqual([]);
    expect(c.semEsquema).toEqual([]);
    expect(ler("api-conferencia.ts")).toBe(arquivoConferencia(c, tiposUsados(c)));
  });

  it("lib/api-schema.ts é o que o openapi-typescript gera de lib/openapi.json", async () => {
    const gerado = astToString(await openapiTS(contrato));
    // O comando de linha acrescenta um cabeçalho; o resto tem de ser igual.
    expect(ler("api-schema.ts").endsWith(gerado.replace(/\r\n/g, "\n"))).toBe(true);
  });
});
