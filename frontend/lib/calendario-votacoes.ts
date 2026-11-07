/**
 * Lógica pura do calendário de votações em /projetos (mapa de calor C, Frente 4): degraus de cor,
 * grade do mês, textos de cada dia e endereços. A cor só repete o número escrito em cada dia.
 */
import type { RecorteVotacoes } from "@/lib/api";
import { PARAM_RECORTE } from "@/lib/recorte-votacoes";

export const MESES_NOME = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];
export const DIAS_SEMANA = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];
export const DIAS_SEMANA_CURTO = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

/** Faixas da legenda, na ordem dos degraus 0 a 4. */
export const FAIXAS = ["0", "1–3", "4–6", "7–9", "10+"] as const;

/** Degrau de cor (0 a 4) para o número de votações do dia. */
export function degrau(n: number): 0 | 1 | 2 | 3 | 4 {
  if (n <= 0) return 0;
  if (n <= 3) return 1;
  if (n <= 6) return 2;
  if (n <= 9) return 3;
  return 4;
}

/** Casas da grade: `null` antes do dia 1 (a semana começa no domingo), depois 1..último dia. */
export function gradeDoMes(ano: number, mes: number): (number | null)[] {
  const primeiro = new Date(Date.UTC(ano, mes - 1, 1)).getUTCDay();
  const dias = new Date(Date.UTC(ano, mes, 0)).getUTCDate();
  return [...Array<null>(primeiro).fill(null), ...Array.from({ length: dias }, (_, i) => i + 1)];
}

export function diaDaSemana(ano: number, mes: number, dia: number): string {
  return DIAS_SEMANA[new Date(Date.UTC(ano, mes - 1, dia)).getUTCDay()];
}

export function dataIso(ano: number, mes: number, dia: number): string {
  return `${ano}-${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
}

const contagemTexto = (n: number, tipo: RecorteVotacoes) => {
  const sufixo = tipo === "merito" ? " sobre o texto" : tipo === "procedimento" ? " de procedimento" : "";
  return `${n} ${n === 1 ? "votação" : "votações"}${sufixo}`;
};

/** Nome acessível do dia: "terça, 9 de setembro: 11 votações sobre o texto (de 14)". */
export function rotuloDia(
  ano: number,
  mes: number,
  dia: number,
  n: number,
  todas: number,
  tipo: RecorteVotacoes,
): string {
  const quando = `${diaDaSemana(ano, mes, dia)}, ${dia} de ${MESES_NOME[mes - 1]}`;
  if (todas === 0) return `${quando}: nenhuma votação nominal`;
  const de = tipo !== "todas" && n !== todas ? ` (de ${todas} no dia)` : "";
  return `${quando}: ${contagemTexto(n, tipo)}${de}`;
}

export { contagemTexto };

export type EstadoCalendario = {
  casa?: string;
  /** "AAAA-MM" */
  mes?: string;
  /** "AAAA-MM-DD" */
  dia?: string;
  tipo: RecorteVotacoes;
  pagina?: string;
};

/** Lê o estado do calendário do endereço de /projetos (parâmetros com prefixo `cal_`). */
export function lerCalendario(sp: Record<string, string | string[] | undefined>): EstadoCalendario {
  const um = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) || undefined;
  const casa = um(sp.cal_casa);
  const mes = um(sp.cal_mes);
  const dia = um(sp.cal_dia);
  const pagina = um(sp.cal_pagina);
  return {
    casa: casa === "senado" || casa === "camara" ? casa : undefined,
    mes: mes && /^\d{4}-(0[1-9]|1[0-2])$/.test(mes) ? mes : undefined,
    dia: dia && /^\d{4}-\d{2}-\d{2}$/.test(dia) ? dia : undefined,
    tipo: um(sp[PARAM_RECORTE]) === "todas" ? "todas" : "merito",
    pagina: pagina && /^\d+$/.test(pagina) ? pagina : undefined,
  };
}

/** Endereço de /projetos com o estado do calendário trocado (âncora na seção). */
export function enderecoCalendario(atual: EstadoCalendario, muda: Partial<EstadoCalendario>): string {
  const e = { ...atual, ...muda };
  const p = new URLSearchParams();
  if (e.casa && e.casa !== "camara") p.set("cal_casa", e.casa);
  if (e.mes) p.set("cal_mes", e.mes);
  if (e.dia) p.set("cal_dia", e.dia);
  if (e.tipo === "todas") p.set(PARAM_RECORTE, "todas");
  if (e.pagina && e.pagina !== "1") p.set("cal_pagina", e.pagina);
  const q = p.toString();
  return `/projetos${q ? `?${q}` : ""}#calendario-votacoes`;
}
