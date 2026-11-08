/**
 * "Seu lugar": a cidade que a pessoa escolheu, guardada só neste aparelho (localStorage), para o
 * cabeçalho mostrar "Blumenau, SC" e o menu abrir as telas já nela. Nada vai ao servidor.
 */

export const CHAVE_LUGAR = "panoptico:lugar";
export const EVENTO_LUGAR = "panoptico:lugar";

export type Lugar = { ibge: string; nome: string; uf: string };

export function lerLugar(bruto: string | null): Lugar | null {
  if (!bruto) return null;
  try {
    const v = JSON.parse(bruto) as Partial<Lugar>;
    if (typeof v.ibge === "string" && /^\d{7}$/.test(v.ibge) && typeof v.nome === "string" && v.nome && typeof v.uf === "string" && /^[A-Z]{2}$/.test(v.uf)) {
      return { ibge: v.ibge, nome: v.nome, uf: v.uf };
    }
  } catch {
    // Valor corrompido: como se não houvesse lugar.
  }
  return null;
}

export function gravarLugar(l: Lugar): string {
  return JSON.stringify({ ibge: l.ibge, nome: l.nome, uf: l.uf });
}

/** Destinos do menu: com lugar, as telas já abrem nele; sem, levam à escolha da cidade na home. */
export function hrefDoMenu(rotulo: "Seu lugar" | "Representantes", lugar: Lugar | null): string {
  if (rotulo === "Seu lugar") return lugar ? `/cidade/${lugar.ibge}` : "/#cep";
  return lugar ? `/representantes?municipio=${lugar.ibge}` : "/#cep";
}
