/**
 * Ligações entre os cargos: quem elege, fiscaliza, julga ou sanciona quem, no desenho
 * "De Brasília até a sua rua" (components/predios-representantes.tsx). Lógica pura e testável.
 *
 * Os artigos foram conferidos no texto oficial da Constituição Federal (planalto.gov.br). O que
 * depende da constituição do estado ou da lei orgânica do município diz isso na própria frase,
 * pois esse artigo não está na Constituição Federal.
 */
import type { PredioId } from "@/lib/predios";

export type NoLigacao = PredioId | "voce";
export type Verbo = "elege" | "fiscaliza" | "julga" | "sanciona";

export type Ligacao = {
  de: NoLigacao;
  para: NoLigacao;
  verbo: Verbo;
  /** Frase do dia a dia. */
  frase: string;
  /** Base legal, em letra menor. */
  artigo: string;
};

/** Ordem da linha "Ver:" e rótulo de cada verbo. */
export const VERBOS: { id: Verbo; rotulo: string; legenda: string }[] = [
  { id: "elege", rotulo: "Elege", legenda: "traço cheio" },
  { id: "fiscaliza", rotulo: "Fiscaliza", legenda: "traço tracejado" },
  { id: "julga", rotulo: "Julga", legenda: "traço pontilhado" },
  { id: "sanciona", rotulo: "Sanciona", legenda: "traço e ponto" },
];

/** Padrão do traço de cada verbo (não depende de cor). */
export const TRACO_VERBO: Record<Verbo, string | undefined> = {
  elege: undefined,
  fiscaliza: "8 5",
  julga: "1.5 6",
  sanciona: "10 4 2 4",
};

const ELEGE = (para: PredioId, frase: string, artigo: string): Ligacao => ({ de: "voce", para, verbo: "elege", frase, artigo });

export const LIGACOES: Ligacao[] = [
  ELEGE("planalto", "Você vota para escolher o presidente da República.", "Constituição Federal, art. 77"),
  ELEGE("senado", "Você vota para escolher os senadores do seu estado.", "Constituição Federal, art. 46"),
  ELEGE("camara", "Você vota para escolher os deputados federais do seu estado.", "Constituição Federal, art. 45"),
  ELEGE("governo", "Você vota para escolher o governador do seu estado.", "Constituição Federal, art. 28"),
  ELEGE("assembleia", "Você vota para escolher os deputados estaduais.", "Constituição Federal, art. 27, § 1º"),
  ELEGE("prefeitura", "Você vota para escolher o prefeito da sua cidade.", "Constituição Federal, art. 29, I e II"),
  ELEGE("camaramun", "Você vota para escolher os vereadores da sua cidade.", "Constituição Federal, art. 29, I"),

  {
    de: "camara",
    para: "planalto",
    verbo: "fiscaliza",
    frase: "A Câmara dos Deputados acompanha e controla os atos do presidente.",
    artigo: "Constituição Federal, art. 49, X (Congresso Nacional, por qualquer de suas Casas)",
  },
  {
    de: "senado",
    para: "planalto",
    verbo: "fiscaliza",
    frase: "O Senado acompanha e controla os atos do presidente.",
    artigo: "Constituição Federal, art. 49, X (Congresso Nacional, por qualquer de suas Casas)",
  },
  {
    de: "assembleia",
    para: "governo",
    verbo: "fiscaliza",
    frase: "A Assembleia Legislativa acompanha os atos do governador, nos termos da constituição do estado.",
    artigo: "Constituição Federal, art. 25, e constituição do estado",
  },
  {
    de: "camaramun",
    para: "prefeitura",
    verbo: "fiscaliza",
    frase: "A Câmara de Vereadores fiscaliza o prefeito, com o auxílio do Tribunal de Contas.",
    artigo: "Constituição Federal, art. 31, caput e § 1º",
  },

  {
    de: "camara",
    para: "planalto",
    verbo: "julga",
    frase: "A Câmara dos Deputados decide, por dois terços, se o processo de impeachment contra o presidente pode seguir.",
    artigo: "Constituição Federal, arts. 51, I, e 86",
  },
  {
    de: "senado",
    para: "planalto",
    verbo: "julga",
    frase: "O Senado julga o presidente nos crimes de responsabilidade (impeachment).",
    artigo: "Constituição Federal, arts. 52, I, e 86",
  },
  {
    de: "camaramun",
    para: "prefeitura",
    verbo: "julga",
    frase: "A Câmara de Vereadores julga as contas do prefeito, a partir do parecer do Tribunal de Contas.",
    artigo: "Constituição Federal, art. 31, §§ 1º e 2º",
  },

  {
    de: "planalto",
    para: "camara",
    verbo: "sanciona",
    frase: "O presidente sanciona (aprova) ou veta as leis votadas pelos deputados.",
    artigo: "Constituição Federal, art. 66",
  },
  {
    de: "planalto",
    para: "senado",
    verbo: "sanciona",
    frase: "O presidente sanciona (aprova) ou veta as leis votadas pelos senadores.",
    artigo: "Constituição Federal, art. 66",
  },
  {
    de: "governo",
    para: "assembleia",
    verbo: "sanciona",
    frase: "O governador sanciona ou veta as leis votadas pela Assembleia, conforme a constituição do estado.",
    artigo: "Constituição Federal, art. 25, e constituição do estado",
  },
  {
    de: "prefeitura",
    para: "camaramun",
    verbo: "sanciona",
    frase: "O prefeito sanciona ou veta as leis votadas pelos vereadores, conforme a lei orgânica do município.",
    artigo: "Constituição Federal, art. 29, caput, e lei orgânica do município",
  },
];

/** Ligações de um verbo cujas duas pontas existem no desenho ("voce" sempre existe). */
export function ligacoesVisiveis(verbo: Verbo | null, existentes: readonly PredioId[]): Ligacao[] {
  if (!verbo) return [];
  const tem = (n: NoLigacao) => n === "voce" || existentes.includes(n);
  return LIGACOES.filter((l) => l.verbo === verbo && tem(l.de) && tem(l.para));
}

export function chaveLigacao(l: Ligacao): string {
  return `${l.verbo}-${l.de}-${l.para}`;
}

/**
 * Curva entre dois pontos (quadrática, com o controle deslocado de lado) e o ponto final recuado
 * `recuo` unidades ao longo da tangente, para a seta não sumir atrás do prédio.
 */
export function caminhoCurvo(a: [number, number], b: [number, number], lado = 1, recuo = 24): string {
  const [x1, y1] = a;
  const [x2, y2] = b;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const d = Math.hypot(dx, dy) || 1;
  const desvio = Math.min(40, d * 0.2) * lado;
  const cx = (x1 + x2) / 2 + (-dy / d) * desvio;
  const cy = (y1 + y2) / 2 + (dx / d) * desvio;
  const tx = x2 - cx;
  const ty = y2 - cy;
  const t = Math.hypot(tx, ty) || 1;
  const r = Math.min(recuo, t * 0.5);
  const f = (n: number) => Math.round(n * 10) / 10;
  return `M${f(x1)} ${f(y1)} Q${f(cx)} ${f(cy)} ${f(x2 - (tx / t) * r)} ${f(y2 - (ty / t) * r)}`;
}
