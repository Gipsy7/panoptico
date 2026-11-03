/**
 * "O que mudou desde a sua última visita": compara os números dos cartões com os guardados no
 * aparelho (localStorage; nada vai ao servidor). Funções puras, testadas em novidades-perfil.test.ts.
 */

/** Valores numéricos por chave "<cartão>" ou "<cartão>.<detalhe>". O cartão é o `destino`. */
export type Valores = Record<string, number>;
export type Visita = { data: string; valores: Valores };

export const PREFIXO_CHAVE_VISITA = "panoptico:visita:";

export function chaveVisita(caminho: string): string {
  return PREFIXO_CHAVE_VISITA + caminho;
}

/** Lê o que o aparelho guardou; qualquer formato inesperado vira null (como primeira visita). */
export function lerVisita(bruto: string | null): Visita | null {
  if (!bruto) return null;
  try {
    const v = JSON.parse(bruto) as unknown;
    if (!v || typeof v !== "object") return null;
    const { data, valores } = v as { data?: unknown; valores?: unknown };
    if (typeof data !== "string" || !/^\d{4}-\d{2}-\d{2}/.test(data)) return null;
    if (!valores || typeof valores !== "object") return null;
    const limpos: Valores = {};
    for (const [k, x] of Object.entries(valores as Record<string, unknown>)) {
      if (typeof x === "number" && Number.isFinite(x)) limpos[k] = x;
    }
    return { data: data.slice(0, 10), valores: limpos };
  } catch {
    return null;
  }
}

/** "2026-10-12" -> "12/10". */
export function dataCurta(iso: string): string {
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
}

export type Novidades = {
  /** Cartões (`destino`) cujo valor mudou. */
  cartoes: string[];
  /** Ex.: "4 votações a mais, 1 projeto"; null se nada que se possa contar mudou. */
  linha: string | null;
  desde: string;
};

const plural = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;

/** Compara a visita anterior com os valores de agora. Sem visita anterior ou sem diferença: null. */
export function compararVisita(anterior: Visita | null, atual: Valores): Novidades | null {
  if (!anterior) return null;
  const cartoes = new Set<string>();
  for (const chave of Object.keys(atual)) {
    if (chave in anterior.valores && anterior.valores[chave] !== atual[chave]) cartoes.add(chave.split(".")[0]);
  }
  if (cartoes.size === 0) return null;

  const dif = (chave: string) =>
    chave in anterior.valores && chave in atual ? atual[chave] - anterior.valores[chave] : 0;
  const partes: string[] = [];
  const votacoes = dif("presenca.total");
  if (votacoes > 0) partes.push(`${plural(votacoes, "votação", "votações")} a mais`);
  const projetos = dif("projetos");
  if (projetos > 0) partes.push(plural(projetos, "projeto", "projetos"));
  const governo = dif("votos.total");
  if (governo > 0) partes.push(`${plural(governo, "voto", "votos")} com orientação do Governo`);
  if (dif("gastos") !== 0) partes.push("gastos do gabinete mudaram");
  if (dif("sancoes") !== 0) partes.push("registros na CGU e no TCU mudaram");
  if (dif("candidatura") !== 0) partes.push("bens declarados mudaram");

  return {
    cartoes: [...cartoes],
    linha: partes.length ? partes.join(", ") : null,
    desde: dataCurta(anterior.data),
  };
}

/** Dia de hoje no horário de Brasília, "AAAA-MM-DD". */
export function hojeISO(agora: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
  }).format(agora);
}
