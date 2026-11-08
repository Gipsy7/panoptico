// Dica curta por página: uma linha, uma vez só por página e por aparelho (localStorage).

export const PREFIXO_CHAVE_DICA = "panoptico.dica.";

export const DICAS = {
  projetos: "Procure pelo número do projeto (PL 2338/2023) ou por uma palavra do assunto.",
  representantes: "Toque numa pessoa para ver o que ela faz, gasta e vota, com a fonte e a data.",
  perfil: "Toque num número para ver de onde ele vem. A média da Casa fica ao lado.",
  cidade: "Toque num tema para ver os números. Tudo sobre a cidade fica no fim da página.",
} as const;

export type ChaveDica = keyof typeof DICAS;

export function textoDaDica(chave: string): string | null {
  return Object.prototype.hasOwnProperty.call(DICAS, chave) ? DICAS[chave as ChaveDica] : null;
}

export function chaveArmazenamentoDica(chave: ChaveDica): string {
  return `${PREFIXO_CHAVE_DICA}${chave}`;
}

export function dicaJaVista(valor: string | null | undefined): boolean {
  return valor === "1";
}
