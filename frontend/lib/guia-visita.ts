// Guia da primeira visita: lógica pura (qual guia mostrar, qual passo acender, quando acabou).
// O componente components/guia-visita.tsx só liga isso à rolagem e ao localStorage.

export const CHAVE_GUIA_VISTO = "panoptico.guia";
/** Atributo em <html> enquanto o guia está na tela; a dica da página espera por ele. */
export const ATRIBUTO_GUIA_VISIVEL = "data-guia-visivel";

export type TipoGuia = "geral" | "perfil";

export type PassoGuia = { rotulo: string; frase: string };

const PREFIXOS_PERFIL = ["/parlamentar/", "/vereador/", "/deputado-estadual/", "/eleito/"];

/** Guia geral na página inicial; guia adaptado em perfil (chegada por link); nas outras páginas, nenhum. */
export function tipoDeGuia(caminho: string | null | undefined): TipoGuia | null {
  if (!caminho) return null;
  const limpo = caminho.split(/[?#]/)[0] ?? "";
  if (limpo === "/") return "geral";
  const sem = limpo.replace(/\/+$/, "");
  const perfil = PREFIXOS_PERFIL.find((p) => sem.startsWith(p));
  if (!perfil) return null;
  const resto = sem.slice(perfil.length);
  // Só o perfil em si (um segmento), não o cartão de compartilhar.
  return resto.length > 0 && !resto.includes("/") ? "perfil" : null;
}

export const GUIA_GERAL: PassoGuia[] = [
  { rotulo: "CEP", frase: "Digite o seu CEP para ver quem representa a sua cidade." },
  { rotulo: "Pessoas", frase: "Depois, toque num representante, do presidente ao vereador." },
  { rotulo: "Números", frase: "Cada número vem com a média da Casa, a fonte e a data." },
];

export const GUIA_PERFIL: PassoGuia[] = [
  { rotulo: "Quem é", frase: "Este é o perfil de uma pessoa eleita. Quer ver quem representa a sua cidade?" },
  { rotulo: "O que fez", frase: "Abaixo, o que ela fez: gastos, votos e projetos, com números do ano." },
  { rotulo: "Compare", frase: "Cada número tem a média da Casa ao lado. Toque para ver a fonte e a data." },
];

export const REGRA_GUIA = "Sem nota nem opinião: só dado oficial, com fonte e data.";

export function passosDoGuia(tipo: TipoGuia): PassoGuia[] {
  return tipo === "geral" ? GUIA_GERAL : GUIA_PERFIL;
}

/** Quanto da página já foi percorrido, de 0 a 1 (página que não rola devolve 0). */
export function progressoDeRolagem(rolado: number, alturaTotal: number, alturaJanela: number): number {
  const rolavel = alturaTotal - alturaJanela;
  if (!(rolavel > 0)) return 0;
  return Math.min(1, Math.max(0, rolado / rolavel));
}

/** Passo aceso (0, 1 ou 2): cada terço da página acende um passo. */
export function passoDoProgresso(progresso: number, total = 3): number {
  const p = Math.min(1, Math.max(0, progresso));
  return Math.min(total - 1, Math.floor(p * total));
}

/** Chegou ao fim da página: o guia cumpriu o papel e sai. */
export function chegouAoFim(progresso: number): boolean {
  return progresso >= 0.97;
}

export function guiaJaVisto(valor: string | null | undefined): boolean {
  return valor === "1";
}
