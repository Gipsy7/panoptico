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
      authorization: `Bearer ${env.CF_TOKEN.trim()}`,
      "content-type": "application/json",
    },
  });
  const texto = await r.text();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let j: any;
  try {
    j = JSON.parse(texto);
  } catch {
    throw new Error(`Cloudflare ${r.status}: resposta nao JSON (${texto.slice(0, 120)})`);
  }
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

/** Cria ou corrige um CNAME com proxy. */
async function garantirCname(env: Env, nome: string, destino: string): Promise<string> {
  const l = await cf(env, `/zones/${env.ZONE_ID}/dns_records?name=${encodeURIComponent(nome)}&type=CNAME`);
  const r = l.result?.[0];
  if (!r) {
    await cf(env, `/zones/${env.ZONE_ID}/dns_records`, {
      method: "POST",
      body: JSON.stringify({ type: "CNAME", name: nome, content: destino, proxied: true, ttl: 1 }),
    });
    return `criado CNAME ${nome} -> ${destino}`;
  }
  if (r.content === destino && r.proxied) return `ok CNAME ${nome} -> ${destino}`;
  await cf(env, `/zones/${env.ZONE_ID}/dns_records/${r.id}`, {
    method: "PATCH",
    body: JSON.stringify({ content: destino, proxied: true }),
  });
  return `corrigido CNAME ${nome} -> ${destino}`;
}

async function listarDns(env: Env): Promise<{ nome: string; tipo: string; destino: string; proxy: boolean }[]> {
  const l = await cf(env, `/zones/${env.ZONE_ID}/dns_records?per_page=100`);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (l.result ?? []).map((r: any) => ({
    nome: r.name,
    tipo: r.type,
    destino: r.type === "TXT" ? "(texto)" : r.content,
    proxy: r.proxied,
  }));
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
    if (!env.CHAVE_PAINEL || url.searchParams.get("chave") !== env.CHAVE_PAINEL) {
      return new Response("nao autorizado", { status: 401 });
    }
    const semCache = { headers: { "cache-control": "no-store" } };
    if (req.method === "GET" && url.pathname === "/estado") return Response.json(await lerEstado(env), semCache);
    if (req.method === "GET" && url.pathname === "/diagnostico") {
      const t = env.CF_TOKEN ?? "";
      const verificar = async (caminho: string) => {
        const r = await fetch(`https://api.cloudflare.com/client/v4${caminho}`, {
          headers: { authorization: `Bearer ${t.trim()}` },
        });
        return { status: r.status, corpo: (await r.text()).slice(0, 300) };
      };
      return Response.json(
        {
          tamanho: t.length,
          tamanho_sem_espacos: t.trim().length,
          so_caracteres_validos: /^[A-Za-z0-9_-]+$/.test(t.trim()),
          usuario: await verificar("/user/tokens/verify"),
          conta: await verificar("/accounts/c0968ba678687384cefd9fb3d8d0253b/tokens/verify"),
        },
        semCache,
      );
    }
    if (req.method === "GET" && url.pathname === "/dns") return Response.json(await listarDns(env), semCache);
    // Deixa a zona no formato que a troca espera: raiz, www e api como CNAME com proxy,
    // apontando para o destino ativo segundo o estado (a reserva, enquanto a Vercel estiver pausada).
    if (req.method === "POST" && url.pathname === "/preparar") {
      try {
        return Response.json(await preparar(env), semCache);
      } catch (e) {
        return Response.json({ erro: (e as Error).message }, { status: 500 });
      }
    }
    return new Response("nao encontrado", { status: 404 });
  },
};

/** Deixa a zona no formato que a troca espera: raiz, www e api como CNAME com proxy, apontando
 * para o destino ativo segundo o estado (a reserva, enquanto a Vercel estiver pausada). */
async function preparar(env: Env): Promise<{ feito: string[]; dns: Awaited<ReturnType<typeof listarDns>> }> {
  const estados = await lerEstado(env);
  const site = estados.site.ativo === "reserva" ? env.SITE_RESERVA : env.SITE_PRINCIPAL;
  const api = estados.api.ativo === "reserva" ? env.API_RESERVA : env.API_PRINCIPAL;
  const feito: string[] = [];
  for (const tipo of ["A", "AAAA"]) {
    const l = await cf(env, `/zones/${env.ZONE_ID}/dns_records?name=${env.REGISTRO_SITE}&type=${tipo}`);
    for (const r of l.result ?? []) {
      await cf(env, `/zones/${env.ZONE_ID}/dns_records/${r.id}`, { method: "DELETE" });
      feito.push(`apagado ${tipo} ${r.name} ${r.content}`);
    }
  }
  feito.push(await garantirCname(env, env.REGISTRO_SITE, site));
  feito.push(await garantirCname(env, `www.${env.REGISTRO_SITE}`, env.REGISTRO_SITE));
  feito.push(await garantirCname(env, env.REGISTRO_API, api));
  feito.push(await garantirCname(env, new URL(env.TESTE_API_RESERVA).hostname, env.API_RESERVA));
  return { feito, dns: await listarDns(env) };
}
