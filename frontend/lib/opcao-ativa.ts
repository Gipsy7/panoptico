// Movimento da opção ativa numa lista de resultados (padrão combobox do APG).
// `atual` = -1 quando nenhuma opção está ativa. Setas dão a volta nas pontas.

export type TeclaLista = "ArrowDown" | "ArrowUp" | "Home" | "End";

export function moverOpcao(atual: number, total: number, tecla: TeclaLista): number {
  if (total <= 0) return -1;
  switch (tecla) {
    case "Home":
      return 0;
    case "End":
      return total - 1;
    case "ArrowDown":
      return atual < 0 || atual >= total - 1 ? 0 : atual + 1;
    case "ArrowUp":
      return atual <= 0 ? total - 1 : atual - 1;
  }
}

export function textoResultados(n: number, nenhum: string): string {
  if (n === 0) return nenhum;
  return n === 1 ? "1 resultado" : `${n} resultados`;
}
