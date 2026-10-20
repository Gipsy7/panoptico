import type { DinheiroFederalTotais } from "@/lib/api";
import { formatarReais, formatarReaisCompacto } from "@/lib/formato";

export const ANO_PADRAO = 2025;

/** Blocos de repasse: nome do dia a dia e termo oficial em letra menor. */
export const BLOCOS: { chave: string; nome: string; oficial: string; nomeCidade?: string; oficialCidade?: string }[] = [
  { chave: "FPE", nome: "Fundo dos estados", oficial: "FPE, Fundo de Participação dos Estados" },
  {
    chave: "FPM",
    nome: "Fundo das prefeituras",
    oficial: "FPM, Fundo de Participação dos Municípios",
  },
  {
    chave: "FUNDEB_UNIAO",
    nome: "Escolas (parte da União)",
    oficial: "Complementação da União ao Fundeb",
  },
  {
    chave: "LEGAIS_VOLUNTARIAS",
    nome: "Saúde, convênios e outros repasses",
    oficial: "Transferências legais, voluntárias e específicas",
  },
  { chave: "ROYALTIES", nome: "Royalties e compensações", oficial: "Petróleo, gás, minérios e energia" },
  { chave: "IPI_EXP", nome: "Exportações", oficial: "IPI-Exportação" },
  { chave: "OUTRAS_OBRIG", nome: "Outros repasses obrigatórios", oficial: "CIDE, IOF-Ouro, ITR, LC 176" },
];

export const NOME_INDICADOR = {
  repHab: "Repasse por habitante",
  por100: "Repasse a cada R$ 100",
  arrHab: "Arrecadação por habitante",
} as const;
export type Indicador = keyof typeof NOME_INDICADOR;

export const reais = (v: number | null | undefined) => (v == null ? "sem dado" : formatarReaisCompacto(v));
export const reaisInteiro = (v: number | null | undefined) => (v == null ? "sem dado" : formatarReais(v, true));
export const porHab = (v: number | null | undefined) => (v == null ? "sem dado" : formatarReais(v, true));
const DECIMAL = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const reaisA100 = (v: number | null | undefined) => (v == null ? "sem dado" : `R$ ${DECIMAL.format(v)}`);
export const numero = (v: number | null | undefined) =>
  v == null ? "sem dado" : Math.round(v).toLocaleString("pt-BR");
export const percentual = (v: number | null | undefined) =>
  v == null ? "sem dado" : `${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;

export const rotuloAno = (ano: number, emCurso: boolean) => (emCurso ? `${ano} (em curso)` : String(ano));

const dividir = (a: number | null, b: number | null) => (a == null || b == null || !b ? null : a / b);

export function repHab(t: DinheiroFederalTotais) {
  return dividir(t.repasse, t.populacao);
}
export function arrHab(t: DinheiroFederalTotais) {
  return dividir(t.arrecadacao, t.populacao);
}
export function por100(t: DinheiroFederalTotais) {
  return t.arrecadacao && t.repasse != null ? (t.repasse / t.arrecadacao) * 100 : null;
}
export function valorIndicador(t: DinheiroFederalTotais, i: Indicador) {
  return i === "repHab" ? repHab(t) : i === "por100" ? por100(t) : arrHab(t);
}
export function formatarIndicador(i: Indicador, v: number | null) {
  return i === "por100" ? reaisA100(v) : porHab(v);
}

/** "população de 2022, Censo" quando a população não é do ano mostrado; vazio caso contrário. */
export function notaPopulacao(t: { populacao_ano: number | null; populacao_origem: string | null }, ano: number) {
  if (t.populacao_ano == null || t.populacao_ano === ano) return "";
  return `população de ${t.populacao_ano}${t.populacao_origem === "censo" ? ", Censo" : ", estimativa do IBGE"}`;
}
