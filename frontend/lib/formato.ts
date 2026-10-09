import type { Casa } from "@/lib/api";

export function formatarCep(valor: string): string {
  const digitos = valor.replace(/\D/g, "").slice(0, 8);
  return digitos.length > 5 ? `${digitos.slice(0, 5)}-${digitos.slice(5)}` : digitos;
}

export function formatarData(iso: string): string {
  // Data sem hora ("2022-10-02"): o Date a leria como meia-noite UTC, que no horário de
  // Brasília ainda é o dia anterior. Formata direto, sem fuso.
  const dia = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (dia) return `${dia[3]}/${dia[2]}/${dia[1]}`;
  return new Date(iso).toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

export const NOME_CASA: Record<Casa, string> = {
  camara: "Câmara dos Deputados",
  senado: "Senado Federal",
};

export const FONTE_CASA: Record<Casa, string> = {
  camara: "Dados Abertos da Câmara dos Deputados",
  senado: "Dados Abertos do Senado Federal",
};

const REAIS = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const REAIS_CURTO = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

export function formatarReais(valor: number, curto = false): string {
  return (curto ? REAIS_CURTO : REAIS).format(valor);
}

/**
 * Gastos do gabinete: zero quer dizer que a fonte oficial não tem nenhum reembolso no período
 * (abriu mão da cota, estava licenciado ou como ministro, ou assumiu depois). Conferido na
 * fonte: não é falha de carga. Mostrar "R$ 0" sugeriria um valor medido; o texto diz o que é.
 */
export function formatarGastos(valor: number, curto = false): string {
  return valor === 0 ? "Nenhum reembolso" : formatarReais(valor, curto);
}

export const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export const CASA_CURTA: Record<Casa, string> = { camara: "Câmara", senado: "Senado" };
