/** Funções de texto do Argos (puras). */

/** Minúsculas, sem acento, sem pontuação e com espaços simples. */
export function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/** A frase (já normalizada) tem esta palavra ou sequência de palavras inteira? */
export function contem(normalizado: string, frase: string): boolean {
  return ` ${normalizado} `.includes(` ${frase} `);
}

/** Tira uma sequência de palavras inteira do texto normalizado. */
export function tirar(normalizado: string, frase: string): string {
  return ` ${normalizado} `.split(` ${frase} `).join(" ").replace(/\s+/g, " ").trim();
}

/** Pontos de uma lista de frases: cada frase achada vale o número de palavras dela. */
export function pontuar(normalizado: string, frases: string[]): number {
  let total = 0;
  for (const f of frases) {
    if (contem(normalizado, f)) total += f.split(" ").length;
  }
  return total;
}
