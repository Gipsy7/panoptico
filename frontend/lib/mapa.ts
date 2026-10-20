// Núcleo do mapa: tipos, escala por quantis, carga das malhas (public/mapa) e formatação.
// As malhas vêm do IBGE e são geradas por scripts/malhas_ibge.py; aqui só há geometria e nome.

import { formatarReaisCompacto } from "@/lib/formato";

export type Caixa = [number, number, number, number]; // x0, y0, x1, y1 no viewBox do Brasil
export type NivelMapa = "uf" | "mun";
/** Classe de cor: 0 = sem dado, 1..5 = escala em quantis. */
export type ClasseMapa = 0 | 1 | 2 | 3 | 4 | 5;
/** Ponto de rótulo [x, y, r]: interior mais distante da borda (polylabel) e essa distância. */
export type PontoRotulo = [number, number, number];

export interface UfGeo {
  cod: string;
  nome: string;
  regiao: string;
  d: string;
  bbox: Caixa;
  l?: PontoRotulo;
}
export type MalhaUf = Record<string, UfGeo>;

export interface MunGeo {
  n: string;
  d: string;
  b: Caixa;
  l?: PontoRotulo;
}
export type MalhaMun = Record<string, MunGeo>;

export interface Lugar {
  uf?: string;
  municipio?: string;
}

/** Viewbox do Brasil inteiro (o desenho vai até x = 874; a faixa à direita é mar para as siglas de fora). */
export const CAIXA_BRASIL: Caixa = [0, 0, 920, 894];

/** Onde vai a sigla dos estados pequenos quando ela não cabe dentro do desenho: no mar ou ao
 * lado, com uma linha fina até o estado. Coordenadas do viewBox do Brasil. */
export const SIGLA_FORA: Record<string, [number, number]> = {
  RN: [897, 246],
  PB: [897, 278],
  PE: [897, 310],
  AL: [897, 342],
  SE: [897, 374],
  ES: [796, 574],
  RJ: [748, 680],
  SC: [608, 768],
  DF: [608, 458],
};

/** Cortes de quantis (n-1 valores) ignorando ausentes e não finitos. */
export function quantis(valores: Array<number | null | undefined>, n = 5): number[] {
  const v = valores
    .filter((x): x is number => x != null && Number.isFinite(x))
    .sort((a, b) => a - b);
  if (!v.length) return [];
  const cortes: number[] = [];
  for (let i = 1; i < n; i++) cortes.push(v[Math.min(v.length - 1, Math.floor((i * v.length) / n))]);
  return cortes;
}

/** Classe 1..5 do valor conforme os cortes; 0 quando não há dado. */
export function classe(v: number | null | undefined, cortes: number[]): ClasseMapa {
  if (v == null || !Number.isFinite(v)) return 0;
  let i = 0;
  while (i < cortes.length && v >= cortes[i]) i++;
  return Math.min(5, i + 1) as ClasseMapa;
}

export function reaisOuSemDado(v: number | null | undefined): string {
  return v == null || !Number.isFinite(v) ? "sem dado" : formatarReaisCompacto(v);
}

export function reaisPorHabitante(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "sem dado";
  return `R$ ${Math.round(v).toLocaleString("pt-BR")}`;
}

export function numeroOuSemDado(v: number | null | undefined): string {
  return v == null || !Number.isFinite(v) ? "sem dado" : Math.round(v).toLocaleString("pt-BR");
}

// ---------- carga sob demanda, com cache em memória ----------
const BASE = "/mapa/";
const cache = new Map<string, Promise<unknown>>();

function buscar<T>(caminho: string): Promise<T> {
  let p = cache.get(caminho) as Promise<T> | undefined;
  if (!p) {
    p = fetch(BASE + caminho).then((r) => {
      if (!r.ok) throw new Error(`Não foi possível carregar ${caminho}`);
      return r.json() as Promise<T>;
    });
    p.catch(() => cache.delete(caminho)); // tenta de novo na próxima vez
    cache.set(caminho, p);
  }
  return p;
}

export const carregarUfs = () => buscar<MalhaUf>("ufs.json");
export const carregarMunicipios = (uf: string) => buscar<MalhaMun>(`mun/${uf}.json`);
/** Desenho detalhado das cidades de uma UF: {ibge: d}. */
export const carregarDetalhe = (uf: string) => buscar<Record<string, string>>(`det/${uf}.json`);
