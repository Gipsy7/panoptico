/**
 * Interpreta a frase de quem escreve para o Argos: sem IA, só contagem de palavras-chave e
 * extração de entidades (estado, partido, tempo, nomes). Funções puras (testadas no Vitest).
 * O vocabulário fica em `vocabulario.ts` e as entidades em `entidades.ts`.
 *
 * Prioridade: opinião, CEP, tema de projetos, ranking, assunto (ou dúvida sobre o site; vence
 * quem tem mais pontos e, em empate, o assunto), saudação, e por fim só um nome.
 */
import { extrairCasa, extrairPartido, extrairTempo, extrairUf } from "./entidades";
import { contem, normalizar, pontuar, tirar } from "./texto";
import type { Botao, CriterioLista, Interpretacao } from "./tipos";
import {
  CONECTORES_DE_NOME,
  EXEMPLOS,
  ORDEM_ASSUNTO,
  PALAVRAS_ASSUNTO,
  PALAVRAS_OPINIAO,
  PALAVRAS_SAUDACAO,
  PALAVRAS_SITE,
  PALAVRAS_VAZIAS,
  SUGESTOES_POR_PALAVRA,
} from "./vocabulario";

export { normalizar } from "./texto";

const REGEX_CEP = /(?<!\d)(\d{5})\s?-?\s?(\d{3})(?!\d)/;

/** CEP de 8 dígitos, com ou sem traço, devolvido como "88340-000". */
export function extrairCep(texto: string): string | undefined {
  const m = REGEX_CEP.exec(texto);
  return m ? `${m[1]}-${m[2]}` : undefined;
}

/** Toda palavra que aparece em alguma frase do vocabulário: não faz parte de um nome. */
export const PALAVRAS_DO_VOCABULARIO = new Set<string>([
  ...PALAVRAS_VAZIAS,
  ...PALAVRAS_OPINIAO.flatMap((f) => f.split(" ")),
  ...PALAVRAS_SAUDACAO.flatMap((f) => f.split(" ")),
  ...Object.values(PALAVRAS_ASSUNTO).flatMap((l) => l.flatMap((f) => f.split(" "))),
  ...PALAVRAS_SITE.flatMap((s) => s.frases.flatMap((f) => f.split(" "))),
]);

/** Quantas palavras no máximo um nome tem; acima disso é frase solta, não nome. */
const MAX_PALAVRAS_NOME = 5;

/**
 * O que sobra da frase depois de tirar palavras-chave, palavras vazias, o CEP e as entidades
 * já reconhecidas (`remover`). Conectores ("de", "da", "do"...) ficam só entre duas palavras
 * do nome ("Maria do Rosário").
 */
export function extrairNome(texto: string, remover: string[] = []): string | undefined {
  const semCep = texto.replace(new RegExp(REGEX_CEP.source, "g"), " ");
  let norm = normalizar(semCep);
  for (const r of remover) norm = tirar(norm, r);
  const palavras = norm.split(" ").filter((p) => p.length > 1 || p === "e");
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

/** "Fulano e Beltrano", "Fulano x Beltrano", "Fulano, Beltrano": um nome por pessoa. */
export function extrairNomes(texto: string, remover: string[] = []): string[] {
  const nomes: string[] = [];
  for (const parte of texto.split(/[,;]/)) {
    const norm = normalizar(parte.replace(new RegExp(REGEX_CEP.source, "g"), " "));
    const segmentos = norm.split(/ (?:x|vs|versus|contra|com|ou|e|e o|e a|com o|com a) /);
    for (const seg of segmentos) {
      const nome = extrairNome(seg, remover);
      if (nome && !nomes.includes(nome)) nomes.push(nome);
    }
  }
  return nomes;
}

/** Opinião em qualquer ordem: "em quem votar", "votar em quem", "quem eu escolho". */
function pedeOpiniao(normalizado: string): boolean {
  if (pontuar(normalizado, PALAVRAS_OPINIAO) > 0) return true;
  const palavras = normalizado.split(" ");
  return palavras.includes("quem") && palavras.some((p) => ["votar", "voto", "votarei", "escolher", "escolho"].includes(p));
}

const CRITERIOS: CriterioLista[] = ["gastos", "presenca", "projetos", "emendas"];

/** "quem gastou mais", "qual faltou menos": comparação entre pessoas; o site tem a lista ordenável. */
function pedeRanking(normalizado: string): Interpretacao | null {
  const palavras = normalizado.split(" ");
  const pergunta = palavras.some((p) => ["quem", "qual", "quais"].includes(p));
  const mais = palavras.some((p) => ["mais", "maior", "maiores"].includes(p));
  const menos = palavras.some((p) => ["menos", "menor", "menores"].includes(p));
  if (!pergunta || (!mais && !menos)) return null;
  let melhor: { criterio: CriterioLista; pontos: number } | null = null;
  for (const criterio of CRITERIOS) {
    const pontos = pontuar(normalizado, PALAVRAS_ASSUNTO[criterio]);
    if (pontos > 0 && (!melhor || pontos > melhor.pontos)) melhor = { criterio, pontos };
  }
  if (!melhor) return null;
  // "faltou mais" quer dizer presença menor.
  const faltas = melhor.criterio === "presenca" && palavras.some((p) => ["faltou", "faltas", "falta", "ausente", "ausencia"].includes(p));
  const desc = faltas ? !mais : mais;
  return { assunto: "ranking", ordem: { criterio: melhor.criterio, desc } };
}

function melhorAssunto(normalizado: string): { chave: string; pontos: number } | null {
  let melhor: { chave: string; pontos: number } | null = null;
  const ordem = (c: string) => {
    const i = ORDEM_ASSUNTO.indexOf(c);
    return i < 0 ? 999 : i;
  };
  for (const chave of Object.keys(PALAVRAS_ASSUNTO)) {
    const pontos = pontuar(normalizado, PALAVRAS_ASSUNTO[chave]);
    if (pontos <= 0) continue;
    if (!melhor || pontos > melhor.pontos || (pontos === melhor.pontos && ordem(chave) < ordem(melhor.chave))) {
      melhor = { chave, pontos };
    }
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

function instituicaoDe(norm: string): Interpretacao["instituicao"] {
  if (/\b(prefeitura|prefeito|prefeita)\b/.test(norm)) return "municipal";
  if (/\b(governador|governadora)\b/.test(norm) || /\bgoverno (do|de) estado\b/.test(norm)) return "estadual";
  if (/\b(governo|uniao|planalto|ministerio|ministerios|presidente|presidenta)\b/.test(norm)) return "federal";
  return undefined;
}

function cargoDe(norm: string): Interpretacao["cargo"] {
  if (/\b(presidente|presidenta)\b/.test(norm)) return "presidente";
  if (/\b(governador|governadora)\b/.test(norm)) return "governador";
  if (/\b(prefeito|prefeita)\b/.test(norm)) return "prefeito";
  return undefined;
}

/** Tema depois de "projetos sobre ...": tira as entidades e as palavras vazias do começo e do fim. */
function extrairTema(norm: string, usadas: string[]): string | undefined {
  const m = /\b(?:projetos?|leis?|projeto de lei|propostas?|votacoes?|votacao)\s+(?:de lei\s+)?(?:sobre|a respeito de|do tema|(?:que )?(?:tratam|falam) de|relacionados a)\s+(.+)$/.exec(norm);
  if (!m) return undefined;
  let resto = m[1];
  for (const u of usadas) resto = tirar(resto, u);
  const palavras = resto.split(" ").filter(Boolean);
  const tira = new Set(["o", "a", "os", "as", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "pra", "para", "por", "ao", "um", "uma"]);
  while (palavras.length && tira.has(palavras[0])) palavras.shift();
  while (palavras.length && tira.has(palavras[palavras.length - 1])) palavras.pop();
  const tema = palavras.join(" ");
  return tema.length >= 3 ? tema : undefined;
}

function sugestoes(norm: string): Botao[] {
  const palavras = new Set(norm.split(" "));
  const achadas: Botao[] = [];
  for (const { palavras: ws, botao } of SUGESTOES_POR_PALAVRA) {
    if (ws.some((w) => palavras.has(w)) && !achadas.some((b) => b.rotulo === botao.rotulo)) achadas.push(botao);
  }
  for (const e of EXEMPLOS) {
    if (achadas.length >= 3) break;
    if (!achadas.some((b) => b.rotulo === e)) achadas.push({ rotulo: e, frase: e });
  }
  return achadas.slice(0, 3);
}

export function interpretar(texto: string, agora: Date = new Date()): Interpretacao {
  const normalizado = normalizar(texto);
  const cep = extrairCep(texto);
  if (!normalizado) return { assunto: "nenhum", sugestoes: sugestoes("") };

  if (pedeOpiniao(normalizado)) return { assunto: "opiniao", cep };
  if (cep) return { assunto: "representantes", cep };

  // Entidades: o que for reconhecido aqui não vira nome de pessoa.
  const uf = extrairUf(texto);
  const partido = extrairPartido(texto);
  const tempo = extrairTempo(texto, agora);
  const casa = extrairCasa(texto);
  const usadas = [...(uf?.usadas ?? []), ...(partido?.usadas ?? []), ...tempo.usadas];
  const base: Interpretacao = {
    assunto: "nenhum",
    uf: uf?.uf,
    partido: partido?.sigla,
    ano: tempo.ano,
    mes: tempo.mes,
    relativo: tempo.relativo || undefined,
    casa,
  };

  const tema = extrairTema(normalizado, usadas);
  if (tema) return { ...base, assunto: "projetos_busca", tema };

  const ranking = pedeRanking(normalizado);
  if (ranking) return { ...base, ...ranking };

  const nome = extrairNome(texto, usadas);
  const nomes = extrairNomes(texto, usadas);
  let assunto = melhorAssunto(normalizado);
  // "como o Fulano votou na reforma": votos, mesmo com palavras no meio.
  if ((!assunto || assunto.chave === "presenca") && /\bcomo\b.*\b(votou|votaram|vota|votam)\b/.test(normalizado)) {
    assunto = { chave: "secao:votos", pontos: 2 };
  }
  const site = melhorSite(normalizado);
  const separador = / (x|vs|versus|contra) /.test(` ${normalizado} `);
  const chave = assunto?.chave;

  // Dúvida sobre o site vence quando tem mais pontos que qualquer assunto.
  if (site && (!assunto || site.pontos > assunto.pontos)) {
    return { ...base, assunto: "site", perguntaId: site.id };
  }

  // Duas ou mais pessoas: comparar.
  const dePessoa = !chave || ["comparar", "gastos", "presenca", "projetos", "emendas", "salario"].includes(chave);
  if (nomes.length >= 2 && dePessoa) return { ...base, assunto: "comparar", nomes };
  if (chave === "comparar") return { ...base, assunto: "comparar", nomes };
  if (separador && nomes.length >= 2) return { ...base, assunto: "comparar", nomes };

  if (chave === "sobre_argos") return { ...base, assunto: "sobre_argos" };

  if (chave) {
    const [tipo, id] = chave.split(":");
    if (tipo === "secao") return { ...base, assunto: "secao", secao: id, nome };
    if (tipo === "pagina") return { ...base, assunto: "pagina", secao: id, nome };
    const inst = instituicaoDe(normalizado);
    // "Quanto o PT gastou": as contas do partido, não de uma pessoa.
    if (partido && !nome && ["gastos", "emendas", "dinheiro_federal"].includes(chave)) {
      return { ...base, assunto: "partidos" };
    }
    // "Quanto o governo gastou": instituição, não pessoa. Na prefeitura o nome é a cidade.
    if ((chave === "gastos" || chave === "emendas") && inst && (!nome || inst === "municipal")) {
      return { ...base, assunto: "governo_gasto", instituicao: inst, nome };
    }
    // "Quanto gastam os deputados de SC": vários, não uma pessoa; vale a lista ordenável.
    const coletivo = /\b(deputados|deputadas|senadores|senadoras|parlamentares)\b/.test(normalizado);
    if (coletivo && !nome && (chave === "gastos" || chave === "presenca" || chave === "projetos" || chave === "emendas")) {
      return { ...base, assunto: "ranking", ordem: { criterio: chave, desc: true } };
    }
    if (chave === "executivo") {
      return { ...base, assunto: "executivo", cargo: cargoDe(normalizado), instituicao: inst, nome };
    }
    if (chave === "lista" && nome) return { ...base, assunto: "pessoa", nome };
    return { ...base, assunto: chave as Interpretacao["assunto"], nome };
  }

  if (pontuar(normalizado, PALAVRAS_SAUDACAO) > 0) {
    return nome ? { ...base, assunto: "pessoa", nome } : { ...base, assunto: "saudacao" };
  }
  if (partido) return { ...base, assunto: "partidos" };
  if (uf && !nome) return { ...base, assunto: "lista", casa };
  if (nome) return { ...base, assunto: "pessoa", nome };
  return { ...base, assunto: "nenhum", sugestoes: sugestoes(normalizado) };
}

export { contem };
