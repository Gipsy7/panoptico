/**
 * Checklist "O que está e o que não está neste perfil". Função pura: a página diz, para cada
 * dado, se ele veio (`tem`) e de qual fonte; aqui só se conta e se completa o motivo de quem falta.
 * Dado que não se aplica ao tipo de perfil (`aplica: false`) não entra na conta.
 */
export type ItemChecklistEntrada = {
  id: string;
  /** Nome do dado em linguagem do dia a dia (ex.: "Gastos do gabinete"). */
  rotulo: string;
  /** Seção que abre na gaveta (`#ver-<destino>`), quando o dado tem seção própria. */
  destino?: string;
  tem: boolean;
  /** Nome da fonte (quando `tem`). */
  fonte?: string | null;
  /** Por que não há o dado (quando não `tem`); sem isto vale o texto padrão. */
  motivo?: string;
  aplica?: boolean;
};

export type ItemChecklist = {
  id: string;
  rotulo: string;
  destino: string | null;
  tem: boolean;
  fonte: string | null;
  motivo: string | null;
};

export type Checklist = { itens: ItemChecklist[]; tem: number; total: number; resumo: string };

export const MOTIVO_PADRAO = "A fonte oficial não publica este dado para este perfil.";

export function montarChecklist(entradas: ItemChecklistEntrada[]): Checklist {
  const itens = entradas
    .filter((e) => e.aplica !== false)
    .map<ItemChecklist>((e) => ({
      id: e.id,
      rotulo: e.rotulo,
      destino: e.destino ?? null,
      tem: e.tem,
      fonte: e.tem ? (e.fonte ?? null) : null,
      motivo: e.tem ? null : (e.motivo ?? MOTIVO_PADRAO),
    }));
  const tem = itens.filter((i) => i.tem).length;
  return { itens, tem, total: itens.length, resumo: `${tem} de ${itens.length}` };
}
