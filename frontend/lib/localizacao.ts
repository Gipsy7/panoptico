// Acha a cidade a partir de latitude e longitude, inteiramente no aparelho: as coordenadas nunca
// saem daqui (nem para nosso servidor, nem para terceiros). Usa as malhas do IBGE em public/mapa.

import type { Caixa, MalhaMun, MalhaUf } from "@/lib/mapa";

// Mesma projeção de scripts/malhas_ibge.py (lon/lat -> viewBox do Brasil).
const LON0 = -74.1;
const LAT_MAX = 5.35;
const LAT0 = -14.0;
const K = 22.8;
const COS = Math.cos((LAT0 * Math.PI) / 180);

export function projetar(lat: number, lon: number): [number, number] {
  return [(lon - LON0) * K * COS, (LAT_MAX - lat) * K];
}

type Anel = Array<[number, number]>;

/** Lê o path gerado pelo script: M absoluto, l relativo e z (aceita também L/m/h/v/H/V). */
export function lerAneis(d: string): Anel[] {
  const aneis: Anel[] = [];
  let atual: Anel = [];
  let x = 0;
  let y = 0;
  const partes = d.match(/[A-Za-z]|-?\d*\.?\d+(?:e[-+]?\d+)?/gi) ?? [];
  let i = 0;
  let cmd = "";
  const num = () => Number(partes[i++]);
  while (i < partes.length) {
    if (/[A-Za-z]/.test(partes[i])) cmd = partes[i++];
    if (cmd === "z" || cmd === "Z") {
      if (atual.length) aneis.push(atual);
      atual = [];
      continue;
    }
    if (cmd === "M" || cmd === "m") {
      if (atual.length) aneis.push(atual);
      atual = [];
      const px = num();
      const py = num();
      x = cmd === "M" ? px : x + px;
      y = cmd === "M" ? py : y + py;
      cmd = cmd === "M" ? "L" : "l"; // pares seguintes são linhas
    } else if (cmd === "L" || cmd === "l") {
      const px = num();
      const py = num();
      x = cmd === "L" ? px : x + px;
      y = cmd === "L" ? py : y + py;
    } else if (cmd === "H" || cmd === "h") {
      const px = num();
      x = cmd === "H" ? px : x + px;
    } else if (cmd === "V" || cmd === "v") {
      const py = num();
      y = cmd === "V" ? py : y + py;
    } else {
      i++; // comando desconhecido: ignora
      continue;
    }
    atual.push([x, y]);
  }
  if (atual.length) aneis.push(atual);
  return aneis;
}

/** Ponto dentro do desenho (regra par-ímpar: buracos contam como fora). */
export function pontoNoDesenho(x: number, y: number, d: string): boolean {
  let dentro = false;
  for (const a of lerAneis(d)) {
    for (let i = 0, j = a.length - 1; i < a.length; j = i++) {
      const [xi, yi] = a[i];
      const [xj, yj] = a[j];
      if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) dentro = !dentro;
    }
  }
  return dentro;
}

const naCaixa = (x: number, y: number, b: Caixa) => x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3];

export function acharUf(x: number, y: number, ufs: MalhaUf): string | null {
  for (const [sigla, u] of Object.entries(ufs)) {
    if (naCaixa(x, y, u.bbox) && pontoNoDesenho(x, y, u.d)) return sigla;
  }
  return null;
}

/** Código IBGE do município; usa o desenho detalhado (`det`) quando houver. */
export function acharMunicipio(
  x: number,
  y: number,
  mun: MalhaMun,
  det?: Record<string, string>,
): string | null {
  for (const [ibge, m] of Object.entries(mun)) {
    if (naCaixa(x, y, m.b) && pontoNoDesenho(x, y, det?.[ibge] ?? m.d)) return ibge;
  }
  return null;
}

export interface CidadeAchada {
  uf: string;
  ibge: string;
  nome: string;
}

export interface Malhas {
  ufs: () => Promise<MalhaUf>;
  municipios: (uf: string) => Promise<MalhaMun>;
  detalhe: (uf: string) => Promise<Record<string, string>>;
}

/** Cidade que contém o ponto, ou null (fora do Brasil ou fora das malhas). */
export async function acharCidade(lat: number, lon: number, malhas: Malhas): Promise<CidadeAchada | null> {
  const [x, y] = projetar(lat, lon);
  const uf = acharUf(x, y, await malhas.ufs());
  if (!uf) return null;
  const mun = await malhas.municipios(uf);
  const det = await malhas.detalhe(uf).catch(() => undefined);
  const ibge = acharMunicipio(x, y, mun, det);
  return ibge ? { uf, ibge, nome: mun[ibge].n } : null;
}
