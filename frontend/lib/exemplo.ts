// Sorteio da dupla do exemplo de comparação da home. Roda no navegador, depois da hidratação,
// para a dupla mudar a cada visita (o sorteio no servidor ficaria congelado no cache da CDN).
// O gerador aleatório é injetável para os testes.

export type Aleatorio = () => number;
export type CasaExemplo = "senado" | "camara";

/** Uma posição de 0 a n-1. */
export function sorteioIndice(n: number, aleatorio: Aleatorio = Math.random): number {
  return Math.min(n - 1, Math.floor(aleatorio() * n));
}

export function sortearItem<T>(itens: readonly T[], aleatorio: Aleatorio = Math.random): T | undefined {
  return itens.length ? itens[sorteioIndice(itens.length, aleatorio)] : undefined;
}

/** Dois itens distintos, ou null se houver menos de dois. */
export function sortearDupla<T>(itens: readonly T[], aleatorio: Aleatorio = Math.random): [T, T] | null {
  if (itens.length < 2) return null;
  const i = sorteioIndice(itens.length, aleatorio);
  const resto = itens.filter((_, k) => k !== i);
  return [itens[i], resto[sorteioIndice(resto.length, aleatorio)]];
}

export function sortearCasa(aleatorio: Aleatorio = Math.random): CasaExemplo {
  return aleatorio() < 0.5 ? "senado" : "camara";
}

export function rotuloCasaExemplo(casa: CasaExemplo): string {
  return casa === "senado" ? "senadores" : "deputados federais";
}
