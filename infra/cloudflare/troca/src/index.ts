import {
  TIMEOUT_MS,
  decidir,
  estadoInicial,
  respostaSaudavel,
  type Destino,
  type EstadoServico,
} from "./decisao";

export interface Env {
  ESTADO: KVNamespace;
  CF_TOKEN: string;
  CHAVE_PAINEL: string;
  ZONE_ID: string;
  REGISTRO_SITE: string;
  REGISTRO_API: string;
  SITE_PRINCIPAL: string;
  SITE_RESERVA: string;
  API_PRINCIPAL: string;
  API_RESERVA: string;
  TESTE_SITE_PRINCIPAL: string;
  TESTE_SITE_RESERVA: string;
  TESTE_API_PRINCIPAL: string;
  TESTE_API_RESERVA: string;
}

type Servico = "site" | "api";
type Estados = Record<Servico, EstadoServico>;
const CHAVE_KV = "estado";

async function testar(url: string, ehApi: boolean): Promise<boolean> {
  try {
    const r = await fetch(url, {
      signal: AbortSignal.timeout(TIMEOUT_MS),
      redirect: "manual",
      headers: { "user-agent": "panoptico-troca/1" },
    });
    const corpo = await r.text();
    return respostaSaudavel({ status: r.status, corpo: corpo.slice(0, 4000) }, ehApi);
  } catch {
    return false;
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function cf(env: Env, caminho: string, init?: RequestInit): Promise<any> {
  const r = await fetch(`https://api.cloudflare.com/client/v4${caminho}`, {
    ...init,
    headers: {
      authorization: `Bearer ${env.CF_TOKEN}`,
      "content-type": "application/json",
    },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const j: any = await r.json();
  if (!j.success) throw new Error(`Cloudflare ${r.status}: ${JSON.stringify(j.errors)}`);
  return j;
}

async function trocarDns(env: Env, nome: string, destino: string): Promise<void> {
  const lista = await cf(env, `/zones/${env.ZONE_ID}/dns_records?name=${encodeURIComponent(nome)}&type=CNAME`);
  const registro = lista.result?.[0];
  if (!registro) throw new Error(`registro ${nome} nao encontrado`);
  if (registro.content === destino) return;
  await cf(env, `/zones/${env.ZONE_ID}/dns_records/${registro.id}`, {
    method: "PATCH",
    body: JSON.stringify({ content: destino, proxied: true }),
  });
}

async function lerEstado(env: Env): Promise<Estados> {
  const bruto = await env.ESTADO.get<Partial<Estados>>(CHAVE_KV, "json");
  return {
    site: { ...estadoInicial(), ...(bruto?.site ?? {}) },
    api: { ...estadoInicial(), ...(bruto?.api ?? {}) },
  };
}

export default {
  async scheduled(_evento: ScheduledController, env: Env): Promise<void> {
    const estados = await lerEstado(env);
    const [sP, sR, aP, aR] = await Promise.all([
      testar(env.TESTE_SITE_PRINCIPAL, false),
      testar(env.TESTE_SITE_RESERVA, false),
      testar(env.TESTE_API_PRINCIPAL, true),
      testar(env.TESTE_API_RESERVA, true),
    ]);
    const testes: Record<Servico, [boolean, boolean]> = { site: [sP, sR], api: [aP, aR] };
    const alvos: Record<Servico, { registro: string; destinos: Record<Destino, string> }> = {
      site: { registro: env.REGISTRO_SITE, destinos: { principal: env.SITE_PRINCIPAL, reserva: env.SITE_RESERVA } },
      api: { registro: env.REGISTRO_API, destinos: { principal: env.API_PRINCIPAL, reserva: env.API_RESERVA } },
    };

    for (const s of ["site", "api"] as Servico[]) {
      const [principalOk, reservaOk] = testes[s];
      const d = decidir(estados[s], principalOk, reservaOk);
      estados[s] = d.estado;
      if (d.observou) console.log(`${s}: [observar] trocaria para ${d.observou}`);
      if (d.trocarPara) {
        try {
          await trocarDns(env, alvos[s].registro, alvos[s].destinos[d.trocarPara]);
          console.log(`${s}: DNS trocado para ${d.trocarPara}`);
        } catch (e) {
          // Desfaz a troca no estado para tentar de novo no proximo minuto.
          estados[s].ativo = d.trocarPara === "reserva" ? "principal" : "reserva";
          console.log(`${s}: erro ao trocar DNS: ${(e as Error).message}`);
        }
      }
      const x = estados[s];
      console.log(`${s}: ativo=${x.ativo} modo=${x.modo} falhas=${x.falhas} sucessos=${x.sucessos} principal=${principalOk} reserva=${reservaOk}`);
    }
    await env.ESTADO.put(CHAVE_KV, JSON.stringify(estados));
  },

  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    if (req.method !== "GET" || url.pathname !== "/estado") return new Response("nao encontrado", { status: 404 });
    if (!env.CHAVE_PAINEL || url.searchParams.get("chave") !== env.CHAVE_PAINEL) {
      return new Response("nao autorizado", { status: 401 });
    }
    return Response.json(await lerEstado(env), { headers: { "cache-control": "no-store" } });
  },
};
