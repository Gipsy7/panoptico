/**
 * Defesa contra varreduras em massa (docs/DECISOES.md, 2026-11-19). Três peças, todas no firewall
 * do Cloudflare, gravadas pelo /configurar e pelo vigia do cron:
 *
 * 1. Brasil primeiro: no site, quem vem de fora do Brasil e não é robô conhecido (cf.client.bot;
 *    o campo verified_bot é só do plano pago) nem um dos
 *    robôs liberados recebe o desafio gerenciado (pessoa passa, coletor disfarçado não).
 * 2. Vigia: a cada 10 minutos o Worker lê a última hora de tráfego; um país (fora o Brasil) ou um
 *    User-Agent que passe de LIMITE_PEDIDOS_HORA e de FRACAO_MINIMA do total entra num desafio
 *    temporário de DURACAO_MS, e o dono recebe um e-mail.
 * 3. Países fixos (PAISES_COM_DESAFIO no index.ts) seguem valendo para site e API.
 *
 * Aqui ficam só funções puras (testadas em defesa.test.ts); quem lê e grava é o index.ts.
 */

export const LIMITE_PEDIDOS_HORA = 3000;
export const FRACAO_MINIMA = 0.3;
export const DURACAO_MS = 24 * 3600_000;
/** Renova a validade de um item ainda ativo só quando faltar menos que isso (poupa gravações no KV). */
export const RENOVAR_ANTES_MS = 6 * 3600_000;
export const MAX_ITENS = 20;

/** O vigia nunca põe estes no desafio: buscadores, prévias de link (o público chega pelo WhatsApp),
 * IAs que respondem com link e o próprio servidor do site ("node", chamando a API). */
export const ROBOS_SEMPRE_LIBERADOS = [
  "googlebot", "bingbot", "applebot", "duckduckbot", "yandex",
  "whatsapp", "facebookexternalhit", "facebookcatalog", "twitterbot", "telegrambot", "slackbot",
  "discordbot", "linkedinbot", "skypeuripreview",
  "oai-searchbot", "chatgpt-user", "claude-searchbot", "claude-user", "perplexity-user",
  "panoptico", "node",
];

/** Países que o vigia nunca põe no desafio. */
export const PAISES_SEMPRE_LIBERADOS = ["BR"];

export type TipoItem = "pais" | "robo";
export interface ItemDefesa {
  tipo: TipoItem;
  valor: string;
  pedidos: number;
  desde: string;
  expira: number;
}
export interface Defesa {
  itens: ItemDefesa[];
}

export interface Contagem {
  valor: string;
  pedidos: number;
}

export function defesaVazia(): Defesa {
  return { itens: [] };
}

export function roboLiberado(ua: string): boolean {
  const u = ua.toLowerCase();
  // "node" sozinho é o servidor do site; não casa com "node" dentro de outro nome.
  if (u.trim() === "node") return true;
  return ROBOS_SEMPRE_LIBERADOS.filter((r) => r !== "node").some((r) => u.includes(r));
}

export interface ResultadoVigia {
  defesa: Defesa;
  novos: ItemDefesa[];
  expirados: ItemDefesa[];
  /** Algo mudou e precisa ser gravado no KV. */
  mudou: boolean;
  /** As regras do firewall precisam ser regravadas (entrou ou saiu item). */
  regravarRegras: boolean;
}

/**
 * Decide o que entra, renova e sai do desafio temporário a partir da contagem da última hora.
 * `total` é o total de pedidos da zona na mesma janela.
 */
export function vigiar(
  atual: Defesa,
  total: number,
  porPais: Contagem[],
  porRobo: Contagem[],
  agora: number,
): ResultadoVigia {
  const expirados = atual.itens.filter((i) => i.expira <= agora);
  let itens = atual.itens.filter((i) => i.expira > agora);
  const novos: ItemDefesa[] = [];
  let renovou = false;

  const passa = (pedidos: number) =>
    pedidos >= LIMITE_PEDIDOS_HORA && total > 0 && pedidos / total >= FRACAO_MINIMA;

  const candidatos: { tipo: TipoItem; c: Contagem }[] = [
    ...porPais
      .filter((c) => c.valor && !PAISES_SEMPRE_LIBERADOS.includes(c.valor.toUpperCase()))
      .map((c) => ({ tipo: "pais" as const, c: { ...c, valor: c.valor.toUpperCase() } })),
    ...porRobo.filter((c) => c.valor && !roboLiberado(c.valor)).map((c) => ({ tipo: "robo" as const, c })),
  ];

  for (const { tipo, c } of candidatos) {
    if (!passa(c.pedidos)) continue;
    const existente = itens.find((i) => i.tipo === tipo && i.valor === c.valor);
    if (existente) {
      if (existente.expira - agora < RENOVAR_ANTES_MS) {
        itens = itens.map((i) => (i === existente ? { ...i, expira: agora + DURACAO_MS, pedidos: c.pedidos } : i));
        renovou = true;
      }
      continue;
    }
    if (itens.length >= MAX_ITENS) continue;
    const item: ItemDefesa = {
      tipo,
      valor: c.valor,
      pedidos: c.pedidos,
      desde: new Date(agora).toISOString(),
      expira: agora + DURACAO_MS,
    };
    itens = [...itens, item];
    novos.push(item);
  }

  const regravarRegras = novos.length > 0 || expirados.length > 0;
  return { defesa: { itens }, novos, expirados, mudou: regravarRegras || renovou, regravarRegras };
}

/** Texto seguro para dentro de aspas numa expressão do firewall. */
export function aspas(texto: string): string {
  return `"${texto.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}

/** Expressão "robôs liberados" (User-Agent), para excluir das regras de desafio. */
export function expressaoRobosLiberados(): string {
  return ROBOS_SEMPRE_LIBERADOS.filter((r) => r !== "node")
    .map((r) => `lower(http.user_agent) contains ${aspas(r)}`)
    .join(" or ");
}

/** Regra 1: Brasil primeiro, só no site (a API é chamada pelo servidor do site e pelo navegador). */
export function expressaoBrasilPrimeiro(site: string, ipServidor: string | undefined): string {
  const partes = [
    `http.host eq ${aspas(site)}`,
    `not ip.src.country in {${PAISES_SEMPRE_LIBERADOS.map(aspas).join(" ")}}`,
    "not cf.client.bot",
    `not (${expressaoRobosLiberados()})`,
  ];
  if (ipServidor) partes.push(`not ip.src eq ${ipServidor}`);
  return `(${partes.join(" and ")})`;
}

/** Regra de países (fixos e do vigia), em site e API; robôs verificados passam. */
export function expressaoPaises(paises: string[]): string | null {
  const lista = [...new Set(paises.map((p) => p.toUpperCase()))].filter(
    (p) => /^[A-Z]{2}$/.test(p) && !PAISES_SEMPRE_LIBERADOS.includes(p),
  );
  if (!lista.length) return null;
  return `(ip.src.country in {${lista.map(aspas).join(" ")}} and not cf.client.bot)`;
}

/** Regra dos User-Agents do vigia: desafio mesmo para robô verificado (o PerplexityBot era um). */
export function expressaoRobos(uas: string[]): string | null {
  const lista = [...new Set(uas)].filter((u) => u && !roboLiberado(u));
  if (!lista.length) return null;
  return lista.map((u) => `(http.user_agent eq ${aspas(u)})`).join(" or ");
}

export function descreverItem(i: ItemDefesa): string {
  const quem = i.tipo === "pais" ? `país ${i.valor}` : `robô "${i.valor.slice(0, 120)}"`;
  return `${quem}: ${i.pedidos} pedidos na última hora`;
}
