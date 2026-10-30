/**
 * Interpreta a frase de quem escreve para o Argos: sem IA, só contagem de palavras-chave.
 * Funções puras (testadas no Vitest). O vocabulário fica em `vocabulario.ts`.
 *
 * Prioridade: opinião, CEP, assunto de dado ou dúvida sobre o site (vence quem tem mais
 * pontos; empate fica com o dado), saudação, e por fim só um nome.
 */
import type { AssuntoDado, Interpretacao } from "./tipos";
import {
  CONECTORES_DE_NOME,
  ORDEM_DADO,
  PALAVRAS_DADO,
  PALAVRAS_OPINIAO,
  PALAVRAS_SAUDACAO,
  PALAVRAS_SITE,
  PALAVRAS_VAZIAS,
} from "./vocabulario";

/** Minúsculas, sem acento, sem pontuação e com espaços simples. */
export function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/** CEP de 8 dígitos, com ou sem traço, devolvido como "88340-000". */
export function extrairCep(texto: string): string | undefined {
  const m = /(?<!\d)(\d{5})\s?-?\s?(\d{3})(?!\d)/.exec(texto);
  return m ? `${m[1]}-${m[2]}` : undefined;
}

function contem(normalizado: string, frase: string): boolean {
  return ` ${normalizado} `.includes(` ${frase} `);
}

/** Pontos de uma lista de frases: cada frase achada vale o número de palavras dela. */
function pontuar(normalizado: string, frases: string[]): number {
  let total = 0;
  for (const f of frases) {
    if (contem(normalizado, f)) total += f.split(" ").length;
  }
  return total;
}

function melhorDado(normalizado: string): { assunto: AssuntoDado; pontos: number } | null {
  let melhor: { assunto: AssuntoDado; pontos: number } | null = null;
  for (const assunto of ORDEM_DADO) {
    const pontos = pontuar(normalizado, PALAVRAS_DADO[assunto]);
    if (pontos > 0 && (!melhor || pontos > melhor.pontos)) melhor = { assunto, pontos };
  }
  return melhor;
}

function melhorSite(normalizado: string): { id: string; pontos: number } | null {
  let melhor: { id: string; pontos: number } | null = null;
  for (const { id, frases } of PALAVRAS_SITE) {
    const pontos = pontuar(normalizado, frases);
    if (pontos > 0 && (!melhor || pontos > melhor.pontos)) melhor = { id, pontos };
  }
  return melhor;
}

/** Toda palavra que aparece em alguma frase do vocabulário: não faz parte de um nome. */
const PALAVRAS_DO_VOCABULARIO = new Set<string>([
  ...PALAVRAS_VAZIAS,
  ...PALAVRAS_OPINIAO.flatMap((f) => f.split(" ")),
  ...PALAVRAS_SAUDACAO.flatMap((f) => f.split(" ")),
  ...Object.values(PALAVRAS_DADO).flatMap((l) => l.flatMap((f) => f.split(" "))),
  ...PALAVRAS_SITE.flatMap((s) => s.frases.flatMap((f) => f.split(" "))),
]);

/** Quantas palavras no máximo um nome tem; acima disso é frase solta, não nome. */
const MAX_PALAVRAS_NOME = 5;

/**
 * O que sobra da frase depois de tirar palavras-chave, palavras vazias e o CEP. Conectores
 * ("de", "da", "do"...) ficam só entre duas palavras do nome ("Maria do Rosário").
 */
export function extrairNome(texto: string): string | undefined {
  const semCep = texto.replace(/(?<!\d)\d{5}\s?-?\s?\d{3}(?!\d)/g, " ");
  const palavras = normalizar(semCep).split(" ").filter(Boolean);
  const eConector = (p: string) => CONECTORES_DE_NOME.includes(p);
  const chave = (p: string) => !PALAVRAS_DO_VOCABULARIO.has(p) && !eConector(p) && !/^\d+$/.test(p);

  let primeiro = -1;
  let ultimo = -1;
  palavras.forEach((p, i) => {
    if (chave(p)) {
      if (primeiro < 0) primeiro = i;
      ultimo = i;
    }
  });
  if (primeiro < 0) return undefined;
  // Entre a primeira e a última palavra do nome só ficam palavras de nome e conectores.
  const nome: string[] = [];
  for (let i = primeiro; i <= ultimo; i++) {
    const p = palavras[i];
    if (chave(p) || eConector(p)) nome.push(p);
  }
  const resultado = nome.join(" ");
  if (nome.filter(chave).length > MAX_PALAVRAS_NOME) return undefined;
  // A busca exige pelo menos 3 letras.
  if (resultado.replace(/[^a-z]/g, "").length < 3) return undefined;
  return resultado;
}

/** Opinião em qualquer ordem: "em quem votar", "votar em quem", "quem eu escolho". */
function pedeOpiniao(normalizado: string): boolean {
  if (pontuar(normalizado, PALAVRAS_OPINIAO) > 0) return true;
  const palavras = normalizado.split(" ");
  return palavras.includes("quem") && palavras.some((p) => ["votar", "voto", "votarei", "escolher", "escolho"].includes(p));
}

/** "quem gastou mais", "qual faltou menos": comparação entre pessoas, que o site não faz. */
function pedeRanking(normalizado: string): boolean {
  const palavras = normalizado.split(" ");
  const pergunta = palavras.some((p) => ["quem", "qual", "quais"].includes(p));
  const grau = palavras.some((p) => ["mais", "menos", "maior", "maiores", "menor", "menores"].includes(p));
  return pergunta && grau && melhorDado(normalizado) !== null;
}

export function interpretar(texto: string): Interpretacao {
  const normalizado = normalizar(texto);
  const cep = extrairCep(texto);
  if (!normalizado) return { assunto: "nenhum" };

  if (pedeOpiniao(normalizado)) return { assunto: "opiniao", cep };
  if (cep) return { assunto: "representantes", cep };
  if (pedeRanking(normalizado)) return { assunto: "ranking" };

  const dado = melhorDado(normalizado);
  const site = melhorSite(normalizado);
  const nome = extrairNome(texto);

  if (site && (!dado || site.pontos > dado.pontos)) {
    return { assunto: "site", perguntaId: site.id };
  }
  if (dado) return { assunto: dado.assunto, nome };
  if (pontuar(normalizado, PALAVRAS_SAUDACAO) > 0) {
    return nome ? { assunto: "pessoa", nome } : { assunto: "saudacao" };
  }
  if (nome) return { assunto: "pessoa", nome };
  return { assunto: "nenhum" };
}
