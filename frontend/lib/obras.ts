/** Conta das obras federais (Obrasgov.br), sem React, para o mapa e "Por dentro". */

export type Situacao = { situacao: string; obras: number };

/** Obras paradas (paralisadas ou inacabadas) a cada 100 começadas e não terminadas
 * (em execução + paradas). Sem nenhuma aberta, não há conta. */
export function paradasACada100(porSituacao: Situacao[]): number | null {
  const n = (s: string) => porSituacao.find((g) => g.situacao === s)?.obras ?? 0;
  const paradas = n("Paralisada") + n("Inacabada");
  const abertas = paradas + n("Em execução");
  return abertas > 0 ? (100 * paradas) / abertas : null;
}
