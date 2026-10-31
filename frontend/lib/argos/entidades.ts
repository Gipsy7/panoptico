/**
 * Extração de entidades da frase: estado (UF), partido, ano e mês, e a Casa. Funções puras.
 * Cada função devolve o que achou e as palavras que usou, para não virarem "nome de pessoa".
 */
import { UFS } from "@/lib/ufs";

import { contem, normalizar, tirar } from "./texto";

// ---------- Estado ----------

/** Siglas que não confundem com palavra: valem em minúsculas ("sc", "sp"). */
const SIGLAS_SEGURAS = new Set([
  "ac", "ap", "ba", "ce", "df", "mg", "ms", "mt", "pb", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc", "sp",
]);

export function nomeDaUf(sigla: string): string {
  return UFS.find((u) => u.sigla === sigla)?.nome ?? sigla;
}

export type AchadoUf = { uf: string; usadas: string[] };

/**
 * Estado por nome ("santa catarina") ou sigla ("SC"). Siglas que são palavras comuns (SE, TO,
 * PA, AM, MA, PE, AL, ES, GO) só valem em maiúsculas; "Pará" também precisa de "do" ou "no" antes.
 */
export function extrairUf(texto: string): AchadoUf | undefined {
  let norm = normalizar(texto);
  const porTamanho = [...UFS].sort((a, b) => b.nome.length - a.nome.length);
  for (const u of porTamanho) {
    const nome = normalizar(u.nome);
    if (nome === "para") {
      if (/\b(do|no|pelo|estado do|estado de) para\b/.test(norm)) return { uf: u.sigla, usadas: [nome] };
      continue;
    }
    if (contem(norm, nome)) return { uf: u.sigla, usadas: [nome] };
    norm = tirar(norm, nome);
  }
  for (const token of texto.split(/[^\p{L}\d]+/u)) {
    if (token.length !== 2) continue;
    const sigla = token.toUpperCase();
    if (!UFS.some((u) => u.sigla === sigla)) continue;
    const maiuscula = token === sigla;
    if (maiuscula || SIGLAS_SEGURAS.has(token.toLowerCase())) return { uf: sigla, usadas: [token.toLowerCase()] };
  }
  return undefined;
}

// ---------- Partido ----------

type PartidoConhecido = {
  sigla: string;
  /** Nomes por extenso, sem acento. */
  nomes: string[];
  /** Sigla que é palavra comum ou sigla de outra coisa: só vale com "partido" ou em maiúsculas. */
  precisaContexto?: boolean;
};

export const PARTIDOS: PartidoConhecido[] = [
  { sigla: "PT", nomes: ["partido dos trabalhadores"] },
  { sigla: "PL", nomes: ["partido liberal"], precisaContexto: true },
  { sigla: "MDB", nomes: ["movimento democratico brasileiro"] },
  { sigla: "PSDB", nomes: ["social democracia brasileira"] },
  { sigla: "PP", nomes: ["progressistas", "partido progressista"], precisaContexto: true },
  { sigla: "PSD", nomes: ["partido social democratico"] },
  { sigla: "UNIÃO", nomes: ["uniao brasil"], precisaContexto: true },
  { sigla: "REPUBLICANOS", nomes: ["republicanos"] },
  { sigla: "PDT", nomes: ["partido democratico trabalhista"] },
  { sigla: "PSB", nomes: ["partido socialista brasileiro"] },
  { sigla: "PSOL", nomes: ["socialismo e liberdade"] },
  { sigla: "PCdoB", nomes: ["pc do b", "pcdob", "comunista do brasil"] },
  { sigla: "PV", nomes: ["partido verde"], precisaContexto: true },
  { sigla: "NOVO", nomes: ["partido novo"], precisaContexto: true },
  { sigla: "PODE", nomes: ["partido podemos"], precisaContexto: true },
  { sigla: "AVANTE", nomes: ["partido avante"], precisaContexto: true },
  { sigla: "SOLIDARIEDADE", nomes: ["partido solidariedade"], precisaContexto: true },
  { sigla: "CIDADANIA", nomes: ["partido cidadania"], precisaContexto: true },
  { sigla: "REDE", nomes: ["rede sustentabilidade", "partido rede"], precisaContexto: true },
  { sigla: "PRD", nomes: [] },
  { sigla: "PMB", nomes: [] },
  { sigla: "DC", nomes: ["democracia crista"], precisaContexto: true },
  { sigla: "AGIR", nomes: ["partido agir"], precisaContexto: true },
  { sigla: "MOBILIZA", nomes: ["partido mobiliza"], precisaContexto: true },
  { sigla: "PRTB", nomes: [] },
  { sigla: "PCO", nomes: [] },
  { sigla: "PSTU", nomes: [] },
  { sigla: "PCB", nomes: [] },
  { sigla: "UP", nomes: ["unidade popular"], precisaContexto: true },
];

export type AchadoPartido = { sigla: string; usadas: string[] };

export function extrairPartido(texto: string): AchadoPartido | undefined {
  const norm = normalizar(texto);
  const falouPartido = contem(norm, "partido") || contem(norm, "partidos") || contem(norm, "legenda");
  for (const p of PARTIDOS) {
    for (const nome of p.nomes) {
      if (contem(norm, nome)) return { sigla: p.sigla, usadas: [nome] };
    }
  }
  const tokens = texto.split(/[^\p{L}\d]+/u).filter(Boolean);
  for (const token of tokens) {
    const sigla = token.toUpperCase();
    const maiuscula = token === sigla && token.length >= 2;
    for (const p of PARTIDOS) {
      if (normalizar(p.sigla) !== normalizar(token)) continue;
      if (!p.precisaContexto || falouPartido || maiuscula) return { sigla: p.sigla, usadas: [normalizar(token)] };
    }
  }
  return undefined;
}

// ---------- Tempo ----------

const MESES_NOMES = [
  "janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
  "novembro", "dezembro",
];

export type AchadoTempo = {
  ano?: number;
  mes?: number;
  /** Disse "esse mês", "este ano" ou "hoje" (o período vem da data de agora). */
  relativo?: boolean;
  usadas: string[];
};

export function extrairTempo(texto: string, agora: Date = new Date()): AchadoTempo {
  const norm = normalizar(texto);
  const out: AchadoTempo = { usadas: [] };
  const anoAtual = agora.getFullYear();
  const mesAtual = agora.getMonth() + 1;

  const a = /(?:^| )(20[12]\d)(?: |$)/.exec(norm);
  if (a) {
    out.ano = Number(a[1]);
    out.usadas.push(a[1]);
  }
  if (/\b(esse|este|neste|nesse) mes\b|\bmes atual\b/.test(norm)) {
    out.mes = mesAtual;
    out.ano ??= anoAtual;
    out.relativo = true;
    out.usadas.push("mes");
  } else if (/\bmes passado\b|\bultimo mes\b/.test(norm)) {
    out.mes = mesAtual === 1 ? 12 : mesAtual - 1;
    out.ano ??= mesAtual === 1 ? anoAtual - 1 : anoAtual;
    out.relativo = true;
    out.usadas.push("mes");
  } else if (/\bano passado\b/.test(norm)) {
    out.ano ??= anoAtual - 1;
    out.relativo = true;
    out.usadas.push("ano");
  } else if (/\b(esse|este|neste|nesse) ano\b|\bano atual\b|\bhoje\b/.test(norm)) {
    out.ano ??= anoAtual;
    out.relativo = true;
    out.usadas.push("ano");
  }
  if (out.mes === undefined) {
    MESES_NOMES.forEach((m, i) => {
      if (out.mes !== undefined || !contem(norm, m)) return;
      // "março" também é nome de gente: só vale depois de "em", "de", "no" ou "ate".
      const contexto = /\b(em|de|no|ate|desde) marco\b/.exec(norm);
      if (m === "marco" && !contexto) return;
      out.mes = i + 1;
      // Só a expressão ("em março"), para não apagar um "Marco" que seja nome de pessoa.
      out.usadas.push(m === "marco" && contexto ? contexto[0] : m);
    });
  }
  return out;
}

// ---------- Casa ----------

export function extrairCasa(texto: string): "camara" | "senado" | undefined {
  const norm = normalizar(texto);
  const camara = /\b(deputado|deputada|deputados|deputadas|camara dos deputados)\b/.test(norm);
  const senado = /\b(senador|senadora|senadores|senadoras|senado)\b/.test(norm);
  if (camara && !senado) return "camara";
  if (senado && !camara) return "senado";
  return undefined;
}
