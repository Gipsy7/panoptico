import {
  TIMEOUT_MS,
  decidir,
  enderecosDeRelease,
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

/** Registros, destinos e testes que a troca usa (nenhum pode ser de release). */
function enderecosDaTroca(env: Env): string[] {
  return [
    env.REGISTRO_SITE, env.REGISTRO_API, env.SITE_PRINCIPAL, env.SITE_RESERVA, env.API_PRINCIPAL, env.API_RESERVA,
    env.TESTE_SITE_PRINCIPAL, env.TESTE_SITE_RESERVA, env.TESTE_API_PRINCIPAL, env.TESTE_API_RESERVA,
  ];
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
    // O release (homologação) não tem reserva e nunca entra na troca: configuração com endereço de
    // release é erro, e o Worker não testa nem troca nada até ser corrigida.
    const proibidos = enderecosDeRelease(enderecosDaTroca(env));
    if (proibidos.length) {
      console.log(`configuracao invalida: endereco de release na troca (${proibidos.join(", ")}); nada feito`);
      return;
    }
    const estados = await lerEstado(env);
    const antes = JSON.stringify(estados);
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
    // Só grava quando algo mudou (limite diário de gravações do KV no plano grátis).
    const depois = JSON.stringify(estados);
    if (depois !== antes) await env.ESTADO.put(CHAVE_KV, depois);
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
    if (req.method === "POST" && url.pathname === "/configurar") {
      return Response.json(await configurar(env), semCache);
    }
    if (req.method === "GET" && url.pathname === "/trafego") {
      const horas = Math.min(Number(url.searchParams.get("horas") ?? "1") || 1, 24);
      return Response.json(await trafego(env, horas), semCache);
    }
    return new Response("nao encontrado", { status: 404 });
  },
};

/** De onde vêm os acessos à zona (Analytics do Cloudflare; o token precisa de Analytics Read). */
async function trafego(env: Env, horas: number): Promise<unknown> {
  const desde = new Date(Date.now() - horas * 3600_000).toISOString();
  const grupo = (nome: string, dims: string) =>
    `${nome}: httpRequestsAdaptiveGroups(limit: 15, filter: {datetime_geq: "${desde}"}, orderBy: [count_DESC]) { count dimensions { ${dims} } }`;
  const query = `{ viewer { zones(filter: {zoneTag: "${env.ZONE_ID}"}) {
    ${grupo("porRobo", "userAgent")}
    ${grupo("porDesfecho", "securityAction cacheStatus edgeResponseStatus")}
    ${grupo("porHost", "clientRequestHTTPHost")}
    ${grupo("porCaminho", "clientRequestPath")}
    ${grupo("porPais", "clientCountryName")}
    ${grupo("porIp", "clientIP")}
  } } }`;
  // O GraphQL não traz `success`: lê direto, sem passar por cf().
  const r = await fetch("https://api.cloudflare.com/client/v4/graphql", {
    method: "POST",
    headers: { authorization: `Bearer ${env.CF_TOKEN.trim()}`, "content-type": "application/json" },
    body: JSON.stringify({ query }),
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const j: any = await r.json().catch(() => ({ erro: `HTTP ${r.status}` }));
  if (j?.errors?.length) return { erro: j.errors.map((e: { message: string }) => e.message) };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const z = (j as any)?.data?.viewer?.zones?.[0];
  return z ? { desde, ...z } : j;
}

// Robôs que varrem o site inteiro sem critério (o da Meta derrubou a CPU da Vercel em out/2026) e
// robôs de ferramentas de SEO, que não trazem público. Ficam LIBERADOS os buscadores e os robôs de
// pesquisa e resposta das IAs (OAI-SearchBot, ChatGPT-User, PerplexityBot, Perplexity-User,
// Claude-SearchBot, Claude-User) e os de treino das grandes IAs que o público usa (GPTBot,
// ClaudeBot, Applebot, Google-Extended): aparecer nas respostas delas é parte do objetivo do site.
const ROBOS_BLOQUEADOS = [
  "meta-externalagent", "bytespider", "ccbot", "amazonbot", "cohere-ai", "diffbot", "imagesiftbot",
  "omgilibot", "petalbot", "timpibot", "ahrefsbot", "semrushbot", "mj12bot", "dataforseobot",
];

/** Regras da zona: cada fase é gravada inteira (PUT do entrypoint), então rodar de novo não duplica.
 * Sem limite por IP: no plano Free a regra não pode excluir o User-Agent do servidor do site. */
async function configurar(env: Env): Promise<Record<string, string>> {
  const zona = `/zones/${env.ZONE_ID}`;
  const api = env.REGISTRO_API;
  const fase = (nome: string, rules: unknown[]) =>
    cf(env, `${zona}/rulesets/phases/${nome}/entrypoint`, { method: "PUT", body: JSON.stringify({ rules }) });
  const passos: [string, () => Promise<unknown>][] = [
    [
      "cache da API (respeita o s-maxage da origem; /saude fica de fora)",
      () =>
        fase("http_request_cache_settings", [
          {
            description: "API: cache na borda",
            expression: `(http.host eq "${api}" and not starts_with(http.request.uri.path, "/saude"))`,
            action: "set_cache_settings",
            action_parameters: { cache: true, edge_ttl: { mode: "respect_origin" } },
          },
          {
            // O Next manda `no-store` em toda página (PPR), então cada visita rodava a função da
            // origem (foi o que esgotou a CPU da Vercel e os créditos da Netlify). O site não tem
            // login nem conteúdo por pessoa: a mesma página serve a todos por 30 min. A navegação
            // do Next usa `?_rsc=`, que entra na chave do cache e não se mistura com o HTML.
            description: "Site: páginas na borda por 30 min",
            expression: `(http.host eq "${env.REGISTRO_SITE}" and http.request.method eq "GET" and not starts_with(http.request.uri.path, "/cdn-cgi"))`,
            action: "set_cache_settings",
            action_parameters: {
              cache: true,
              edge_ttl: { mode: "override_origin", default: 1800 },
              browser_ttl: { mode: "respect_origin" },
            },
          },
        ]),
    ],
    [
      "bloqueio de robôs de coleta em massa (firewall)",
      () =>
        fase("http_request_firewall_custom", [
          {
            description: "Bloquear robôs de coleta em massa",
            expression: ROBOS_BLOQUEADOS.map((r) => `(lower(http.user_agent) contains "${r}")`).join(" or "),
            action: "block",
          },
        ]),
    ],
    [
      "www leva ao endereço sem www",
      () =>
        fase("http_request_dynamic_redirect", [
          {
            description: "www para o domínio",
            expression: `(http.host eq "www.${env.REGISTRO_SITE}")`,
            action: "redirect",
            action_parameters: {
              from_value: {
                status_code: 301,
                preserve_query_string: true,
                target_url: { expression: `concat("https://${env.REGISTRO_SITE}", http.request.uri.path)` },
              },
            },
          },
        ]),
    ],
    [
      // Desligado: o bloqueio gerenciado pega também os robôs de pesquisa das IAs.
      "Block AI bots gerenciado: desligado (a lista própria acima decide)",
      () => cf(env, `${zona}/bot_management`, { method: "PUT", body: JSON.stringify({ ai_bots_protection: "disabled" }) }),
    ],
    [
      "SSL Full",
      () => cf(env, `${zona}/settings/ssl`, { method: "PATCH", body: JSON.stringify({ value: "full" }) }),
    ],
    [
      // As cidades do Cloudflare consultam um cache central antes de ir à origem (mais acertos).
      "cache em camadas (Smart Tiered Cache)",
      () => cf(env, `${zona}/cache/tiered_cache_smart_topology_enable`, { method: "PATCH", body: JSON.stringify({ value: "on" }) }),
    ],
  ];
  const resultado: Record<string, string> = {};
  for (const [nome, passo] of passos) {
    try {
      await passo();
      resultado[nome] = "ok";
    } catch (e) {
      resultado[nome] = (e as Error).message.slice(0, 300);
    }
  }
  return resultado;
}

/** Deixa a zona no formato que a troca espera: raiz, www e api como CNAME com proxy, apontando
 * para o destino ativo segundo o estado (a reserva, enquanto a Vercel estiver pausada). */
async function preparar(env: Env): Promise<{ feito: string[]; dns: Awaited<ReturnType<typeof listarDns>> }> {
  const proibidos = enderecosDeRelease(enderecosDaTroca(env));
  if (proibidos.length) throw new Error(`endereco de release na troca: ${proibidos.join(", ")}`);
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
