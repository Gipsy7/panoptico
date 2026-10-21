import type { Casa, CasaProjeto } from "@/lib/api";

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

/** "2027-02-01" -> "1º/2/2027". */
export function formatarPosse(iso: string): string {
  const [ano, mes, dia] = iso.split("-").map(Number);
  return `${dia === 1 ? "1º" : dia}/${mes}/${ano}`;
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

const REAIS_COMPACTO = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  notation: "compact",
  compactDisplay: "short",
  maximumFractionDigits: 1,
});

/** Reais abreviados ("R$ 1,2 bi"), para números grandes em espaço apertado. */
export function formatarReaisCompacto(valor: number): string {
  return REAIS_COMPACTO.format(valor);
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

/** Com artigo e preposição: "da Câmara", "do Senado". */
export const CASA_DA: Record<Casa, string> = { camara: "da Câmara", senado: "do Senado" };
export const CASA_CURTA: Record<Casa, string> = { camara: "Câmara", senado: "Senado" };

/** Casas que aparecem em projetos e votações (Congresso, assembleia estadual e câmara municipal). */
export const CASA_PROJETO_NOME: Record<CasaProjeto, string> = {
  camara: "Câmara dos Deputados",
  senado: "Senado Federal",
  assembleia: "Assembleia Legislativa",
  camara_municipal: "Câmara Municipal",
};

export const CASA_PROJETO_CURTA: Record<CasaProjeto, string> = {
  camara: "Câmara",
  senado: "Senado",
  assembleia: "Assembleia",
  camara_municipal: "Câmara Municipal",
};

/** "Câmara Municipal de Gaspar/SC", "Assembleia Legislativa de SC", "Senado Federal". */
export function lugarDoProjeto(casa: CasaProjeto, uf: string | null, municipio: string | null): string {
  const nome = CASA_PROJETO_NOME[casa];
  if (casa === "camara_municipal") return municipio ? `${nome} de ${municipio}${uf ? `/${uf}` : ""}` : nome;
  if (casa === "assembleia") return uf ? `${nome} de ${uf}` : nome;
  return nome;
}

export const RESULTADO_VOTACAO: Record<string, string> = { aprovada: "Aprovada", rejeitada: "Rejeitada" };

/** Resultado como a fonte publica; Câmara e Senado usam "aprovada"/"rejeitada", as câmaras locais, texto livre. */
export function textoResultado(resultado: string | null | undefined): string | null {
  if (!resultado) return null;
  return RESULTADO_VOTACAO[resultado.toLowerCase()] ?? resultado;
}
