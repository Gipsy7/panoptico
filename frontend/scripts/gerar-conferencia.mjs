// Grava lib/api-conferencia.ts a partir de lib/api.ts e de lib/openapi.json.
// Uso: `npm run tipos-api` (depois de `python -m app.openapi_exportar` no backend).
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { arquivoConferencia, gerarConferencia, tiposUsados } from "../lib/conferencia-api.ts";

const raiz = join(import.meta.dirname, "..");
const api = readFileSync(join(raiz, "lib", "api.ts"), "utf-8");
const contrato = JSON.parse(readFileSync(join(raiz, "lib", "openapi.json"), "utf-8"));
const c = gerarConferencia(api, contrato);
writeFileSync(join(raiz, "lib", "api-conferencia.ts"), arquivoConferencia(c, tiposUsados(c)));
console.log(`conferidos: ${c.linhas.length}; sem rota no contrato: ${c.semRota.length}; rota sem esquema: ${c.semEsquema.length}`);
for (const p of c.semRota) console.log(`  sem rota: ${p.tipo} ${p.caminho}`);
for (const p of c.semEsquema) console.log(`  sem esquema: ${p.tipo} ${p.caminho}`);
