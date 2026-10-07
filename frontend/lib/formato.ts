import type { Casa } from "@/lib/api";

export function formatarCep(valor: string): string {
  const digitos = valor.replace(/\D/g, "").slice(0, 8);
  return digitos.length > 5 ? `${digitos.slice(0, 5)}-${digitos.slice(5)}` : digitos;
}

export function formatarData(iso: string): string {
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
