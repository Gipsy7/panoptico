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

export type Traco = {
  d: string;
  /** Ponta da seta e o ângulo (graus) com que a linha chega nela. */
  fim: [number, number];
  ang: number;
  /** Comprimento aproximado, só para a duração do desenho. */
  comprimento: number;
};

type Pt = [number, number];
const f1 = (n: number) => Math.round(n * 10) / 10;
const dist = (a: Pt, b: Pt) => Math.hypot(b[0] - a[0], b[1] - a[1]);

/**
 * Pares fiscaliza, julga e sanciona: curva suave entre a lateral de um prédio da direita e a de um
 * da esquerda (chave "direita|esquerda"), em coordenadas do desenho final, passando por trás dos prédios.
 */
const PARES: Record<string, [Pt, Pt, Pt, Pt]> = {
  "camara|planalto": [[307, 95], [290, 28], [205, 34], [142, 80]],
  "senado|planalto": [[198, 126], [183, 126], [177, 104], [162, 104]],
  "assembleia|governo": [[204, 332], [186, 332], [176, 318], [162, 318]],
  "camaramun|prefeitura": [[200, 548], [184, 548], [172, 560], [152, 560]],
};
const DIREITA: NoLigacao[] = ["camara", "senado", "assembleia", "camaramun"];

/**
 * Elege: um fio por prédio saindo de "Você", contornando pelas margens e entrando pela base de
 * cada prédio, sem passar por cima do desenho de nenhum. Valores: margem x, altura de entrada, ponta x.
 */
const FLANCO: Partial<Record<PredioId, [number, number, number]>> = {
  prefeitura: [21, 574, 35],
  camaramun: [343, 564, 334],
  governo: [13, 352, 27],
  assembleia: [349, 352, 333],
  planalto: [6, 134, 29],
  senado: [172, 140, 195],
  camara: [354, 140, 339],
};

function traco(d: string, fim: Pt, ang: number, pts: Pt[]): Traco {
  let c = 0;
  for (let i = 1; i < pts.length; i++) c += dist(pts[i - 1], pts[i]);
  return { d, fim: [f1(fim[0]), f1(fim[1])], ang: f1(ang), comprimento: Math.round(c * 0.9) };
}

/** Traço da ligação no desenho (curva fina por trás dos prédios), ou null sem geometria. */
export function tracoLigacao(l: Ligacao, yVoce: number): Traco | null {
  if (l.de === "voce" && l.para !== "voce") {
    const f = FLANCO[l.para];
    if (!f) return null;
    const [mx, ey, tip] = f;
    const y0 = yVoce - 20;
    const cx = mx < 100 ? 120 : mx < 180 ? 160 : 240;
    const s = tip > mx ? 1 : -1;
    const r = 14;
    const d = `M180 ${y0} C${cx} ${y0 + 10} ${mx} ${y0 + 18} ${mx} ${y0 - 14} L${mx} ${ey + r} Q${mx} ${ey} ${mx + s * r} ${ey} L${tip} ${ey}`;
    return traco(d, [tip, ey], s > 0 ? 0 : 180, [[180, y0], [mx, y0 + 6], [mx, ey], [tip, ey]]);
  }
  const dir = DIREITA.includes(l.de);
  const par = PARES[`${dir ? l.de : l.para}|${dir ? l.para : l.de}`];
  if (!par) return null;
  const p = dir ? par : ([par[3], par[2], par[1], par[0]] as [Pt, Pt, Pt, Pt]);
  const d = `M${p[0][0]} ${p[0][1]} C${p[1][0]} ${p[1][1]} ${p[2][0]} ${p[2][1]} ${p[3][0]} ${p[3][1]}`;
  const ang = (Math.atan2(p[3][1] - p[2][1], p[3][0] - p[2][0]) * 180) / Math.PI;
  return traco(d, p[3], ang, p);
}
