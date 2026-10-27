// Navegação do mapa pelo teclado (padrão "roving tabindex" do APG): uma parada de Tab, setas
// percorrem os itens em ordem alfabética pelo nome, Home/End vão às pontas e letras digitadas
// pulam para o próximo nome que começa com elas. Lógica pura, sem DOM.

export interface ItemMapa {
  id: string;
  nome: string;
}

export type TeclaMapa = "ArrowRight" | "ArrowDown" | "ArrowLeft" | "ArrowUp" | "Home" | "End";

export const TECLAS_MAPA: readonly string[] = ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"];

/** Minúsculas e sem acento, para comparar o que a pessoa digitou com o nome. */
export function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLocaleLowerCase("pt-BR");
}

const comparador = new Intl.Collator("pt-BR", { sensitivity: "base", numeric: true });

/** Ordem alfabética pelo nome (empate pelo id, para ser estável). Não altera a lista recebida. */
export function ordenarPorNome<T extends ItemMapa>(itens: readonly T[]): T[] {
  return [...itens].sort((a, b) => comparador.compare(a.nome, b.nome) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

/** Próximo índice para a tecla. Para nas pontas (sem dar a volta); `atual` = -1 quando nada tem foco. */
export function moverNoMapa(atual: number, total: number, tecla: TeclaMapa): number {
  if (total <= 0) return -1;
  switch (tecla) {
    case "Home":
      return 0;
    case "End":
      return total - 1;
    case "ArrowRight":
    case "ArrowDown":
      return atual < 0 ? 0 : Math.min(total - 1, atual + 1);
    case "ArrowLeft":
    case "ArrowUp":
      return atual < 0 ? 0 : Math.max(0, atual - 1);
  }
}

/**
 * Busca por digitação. `busca` é o que foi digitado nos últimos ~500 ms. Uma letra só (ou a mesma
 * letra repetida, "sss") percorre os nomes que começam com ela, a partir do item seguinte; mais de
 * uma letra procura a partir do item atual (assim "sa" e depois "san" ficam no mesmo nome).
 * Devolve -1 se nenhum nome combina.
 */
export function buscarNoMapa(nomes: readonly string[], atual: number, busca: string): number {
  const total = nomes.length;
  const alvo = normalizar(busca);
  if (!total || !alvo) return -1;
  const repetida = [...alvo].every((c) => c === alvo[0]);
  const tentar = (prefixo: string, deslocamento: number) => {
    const base = atual < 0 ? 0 : atual + deslocamento;
    for (let k = 0; k < total; k++) {
      const i = (base + k) % total;
      if (normalizar(nomes[i]).startsWith(prefixo)) return i;
    }
    return -1;
  };
  if (alvo.length > 1) {
    const i = tentar(alvo, 0);
    if (i >= 0 || !repetida) return i;
  }
  return tentar(alvo[0], 1);
}
