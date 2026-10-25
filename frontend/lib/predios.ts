/**
 * Lógica pura do desenho "De Brasília até a sua rua" (components/predios-representantes.tsx):
 * faixas, contagens, roteiro da mão e medidas do desenho.
 */

export type PredioId = "planalto" | "senado" | "camara" | "governo" | "assembleia" | "prefeitura" | "camaramun";

export const CAPITAIS: Record<string, string> = {
  AC: "Rio Branco",
  AL: "Maceió",
  AP: "Macapá",
  AM: "Manaus",
  BA: "Salvador",
  CE: "Fortaleza",
  DF: "Brasília",
  ES: "Vitória",
  GO: "Goiânia",
  MA: "São Luís",
  MT: "Cuiabá",
  MS: "Campo Grande",
  MG: "Belo Horizonte",
  PA: "Belém",
  PB: "João Pessoa",
  PR: "Curitiba",
  PE: "Recife",
  PI: "Teresina",
  RJ: "Rio de Janeiro",
  RN: "Natal",
  RS: "Porto Alegre",
  RO: "Porto Velho",
  RR: "Boa Vista",
  SC: "Florianópolis",
  SP: "São Paulo",
  SE: "Aracaju",
  TO: "Palmas",
};

/** "SANTA CATARINA · FLORIANÓPOLIS"; sem capital conhecida, só o nome do estado. */
export function faixaEstado(uf: string, nomeEstado: string): string {
  const capital = CAPITAIS[uf.toUpperCase()];
  const base = nomeEstado.toUpperCase();
  return capital && capital.toUpperCase() !== base ? `${base} · ${capital.toUpperCase()}` : base;
}

/** Largura da pílula de uma faixa no desenho (viewBox de 360), a partir do texto. */
export function larguraFaixa(texto: string): number {
  return Math.min(340, Math.round(texto.length * 7.8 + 24));
}

export function contagem(n: number, um: string, varios: string): string {
  return `${n.toLocaleString("pt-BR")} ${n === 1 ? um : varios}`;
}

/** Ordem em que a mão passeia; só visita prédios que existem no desenho. */
const ROTEIRO: PredioId[] = ["senado", "assembleia", "camaramun", "planalto", "governo", "camara"];

export function roteiroDaMao(existentes: readonly PredioId[]): PredioId[] {
  const lista = ROTEIRO.filter((id) => existentes.includes(id));
  return lista.length > 0 ? lista : [...existentes].slice(0, 1);
}

/** Medidas do desenho: com cidade ele desce até a prefeitura; sem, termina no estado. */
export function medidasDoDesenho(temCidade: boolean) {
  const yVoce = temCidade ? 660 : 466;
  return {
    yVoce,
    altura: yVoce + 56,
    // O caminho tracejado desce reto e faz uma curva curta antes do ponto "Você".
    caminho: `M180 36 V${yVoce - 100} C180 ${yVoce - 60} 180 ${yVoce - 48} 180 ${yVoce - 28}`,
  };
}

/** Prédio já selecionado ao abrir: o mais perto de quem busca. */
export function predioInicial(existentes: readonly PredioId[]): PredioId {
  for (const id of ["prefeitura", "governo", "planalto"] as const) if (existentes.includes(id)) return id;
  return existentes[0];
}
