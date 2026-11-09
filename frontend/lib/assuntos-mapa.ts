/**
 * Assuntos do Mapa (protótipo A): cada um tem ícone, cor de tema e o indicador que pinta os estados
 * (`/estados/indicadores`) e as cidades (`/estados/{uf}/cidades/indicadores`). "Dinheiro" é o que a
 * página já mostrava (impostos e repasses da União) e continua sendo o padrão.
 */
import type { Assunto } from "@/components/icone-assunto";
import type { IndicadorUf, PontoAno } from "@/lib/api";

export type AssuntoMapa = {
  id: "dinheiro" | "seguranca" | "saude" | "saneamento" | "escolas" | "economia";
  nome: string;
  icone: Assunto;
  tema: string;
  /** Indicador dos estados e das cidades (o mesmo id nas duas rotas). */
  indicador: string | null;
  /** Série da linha do tempo do lugar mostrada em "aprofundar". */
  serie: string | null;
};

export const ASSUNTOS_MAPA: AssuntoMapa[] = [
  { id: "dinheiro", nome: "Dinheiro", icone: "dinheiro", tema: "dinheiro", indicador: null, serie: null },
  { id: "seguranca", nome: "Segurança", icone: "seguranca", tema: "seguranca", indicador: "homicidios", serie: "homicidios_taxa" },
  { id: "saude", nome: "Saúde", icone: "saude", tema: "saude", indicador: "leitos", serie: null },
  { id: "saneamento", nome: "Saneamento", icone: "saneamento", tema: "obras", indicador: "esgoto", serie: null },
  { id: "escolas", nome: "Escolas", icone: "escolas", tema: "escolas", indicador: "ideb", serie: "ideb" },
  { id: "economia", nome: "Economia", icone: "economia", tema: "economia", indicador: "pib", serie: "pib" },
];

export const assuntoPorId = (id: string | null | undefined) =>
  ASSUNTOS_MAPA.find((a) => a.id === id) ?? ASSUNTOS_MAPA[0];

/** Último ponto de um lugar num indicador. */
export function ultimoPonto(ind: IndicadorUf | undefined, codigo: string): PontoAno | null {
  const pts = ind?.valores[codigo];
  return pts && pts.length ? pts[pts.length - 1] : null;
}

export function formatarIndicadorAssunto(ind: Pick<IndicadorUf, "unidade" | "decimais">, v: number): string {
  if (ind.unidade.startsWith("R$")) return `R$ ${v.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
  const n = v.toLocaleString("pt-BR", { minimumFractionDigits: ind.decimais, maximumFractionDigits: ind.decimais });
  return ind.unidade.startsWith("%") ? `${n}%` : n;
}
