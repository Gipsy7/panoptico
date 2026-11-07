/**
 * Contas e frases da seção "Quanto custa o mandato" (components/remuneracao-secao.tsx). Funções
 * puras, testadas no Vitest.
 */
import type { CustoMandato, ItemCustoMandato } from "@/lib/api";

const MESES_LONGOS = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

/** "de janeiro a outubro de 2026" (ou "janeiro de 2026", com um mês só). */
export function periodoDoUso(ano: number, ultimoMes: number): string {
  const fim = MESES_LONGOS[Math.min(Math.max(ultimoMes, 1), 12) - 1];
  return ultimoMes <= 1 ? `${fim} de ${ano}` : `de janeiro a ${fim} de ${ano}`;
}

export type Segmento = { item: ItemCustoMandato["item"]; nome: string; valor: number; largura: number };

/**
 * Pedaços de uma barra empilhada, em % da escala comum (o maior dos três totais), para as três
 * barras ficarem comparáveis. Itens sem número ficam de fora da barra (não viram zero).
 */
export function segmentos(
  itens: ItemCustoMandato[],
  campo: "valor" | "usou" | "media_casa",
  escala: number,
): Segmento[] {
  if (escala <= 0) return [];
  return itens
    .filter((i) => i[campo] !== null && (i[campo] as number) > 0)
    .map((i) => ({ item: i.item, nome: i.nome, valor: i[campo] as number, largura: ((i[campo] as number) / escala) * 100 }));
}

/** Escala comum das barras: o maior total. */
export function escalaDasBarras(c: CustoMandato): number {
  return Math.max(c.total_se_usar_tudo, c.usou_total, c.media_total, 0);
}

/** Junta nomes em português: "a", "a e b", "a, b e c" (só a primeira letra vira minúscula). */
export function listaNomes(nomes: string[]): string {
  const n = nomes.map((s) => s.charAt(0).toLowerCase() + s.slice(1));
  if (n.length <= 1) return n.join("");
  return `${n.slice(0, -1).join(", ")} e ${n[n.length - 1]}`;
}
