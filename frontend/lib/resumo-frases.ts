/**
 * "Em poucas palavras": frases do dia a dia geradas dos MESMOS números e médias dos cartões
 * do topo do perfil. Só há frase para o cartão que existe; número literal, sem adjetivo.
 * Função pura (sem rede nem DOM), testada em resumo-frases.test.ts.
 */
import { formatarData, formatarReaisCompacto } from "@/lib/formato";

const INTEIRO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const DECIMAL = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

export type EntradaFrases = {
  presenca?: {
    ano: number;
    votou: number;
    total_votacoes: number;
    media_casa_percentual: number | null;
  };
  gastos?: { ano: number; total: number; media_casa: number };
  projetos?: {
    desde: string;
    primeiro_autor: number;
    media_casa_primeiro_autor: number;
  };
  governo?: {
    iguais: number;
    total: number;
    media_percentual: number | null;
  } | null;
};

/** Até quatro frases, na ordem dos cartões. */
export function gerarFrases(e: EntradaFrases): string[] {
  const frases: string[] = [];
  const { presenca, gastos, projetos, governo } = e;
  if (presenca && presenca.total_votacoes > 0) {
    const media =
      presenca.media_casa_percentual !== null
        ? `; em média, a Casa votou em ${DECIMAL.format(presenca.media_casa_percentual)}% delas`
        : "";
    frases.push(
      `Votou em ${INTEIRO.format(presenca.votou)} de ${INTEIRO.format(presenca.total_votacoes)} votações do Plenário${media}.`,
    );
  }
  if (projetos) {
    frases.push(
      `Apresentou ${INTEIRO.format(projetos.primeiro_autor)} ${projetos.primeiro_autor === 1 ? "projeto" : "projetos"} como autor principal desde ${projetos.desde.slice(0, 4)}; a média da Casa foi ${DECIMAL.format(projetos.media_casa_primeiro_autor)}.`,
    );
  }
  if (gastos) {
    const media = `a média da Casa foi ${formatarReaisCompacto(gastos.media_casa)}`;
    frases.push(
      gastos.total === 0
        ? `Não tem reembolso da verba do gabinete em ${gastos.ano}; ${media}.`
        : `Gastou ${formatarReaisCompacto(gastos.total)} da verba do gabinete em ${gastos.ano}; ${media}.`,
    );
  }
  if (governo && governo.total > 0) {
    const media =
      governo.media_percentual !== null
        ? `; em média, a Casa votou assim em ${DECIMAL.format(governo.media_percentual)}%`
        : "";
    frases.push(
      `Votou como o Governo orientou em ${INTEIRO.format(governo.iguais)} de ${INTEIRO.format(governo.total)} votações${media}.`,
    );
  }
  return frases;
}

/** Texto para colar no WhatsApp: cabeçalho, frases, fonte com data e link absoluto do perfil. */
export function montarTextoCompartilhar(o: {
  cabecalho: string;
  frases: string[];
  fontes: string[];
  atualizadoEm: string | null;
  url: string;
}): string {
  const fonte = `Fonte: ${o.fontes.join(", ")}${o.atualizadoEm ? ` · atualizado em ${formatarData(o.atualizadoEm)}` : ""}`;
  return [o.cabecalho, ...o.frases.map((f) => `• ${f}`), fonte, o.url].join("\n");
}
