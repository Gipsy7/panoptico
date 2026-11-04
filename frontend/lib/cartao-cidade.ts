// Lógica pura do cartão "Quem decide por [cidade]" (imagem para Feed e Stories).
// Sem rede nem React: recebe o que a API já devolve e monta contagens, mosaico e rodapé.

export type FormatoCartao = "feed" | "stories";

export const FORMATOS: Record<FormatoCartao, { width: number; height: number; fotos: number }> = {
  feed: { width: 1080, height: 1080, fotos: 6 },
  stories: { width: 1080, height: 1920, fotos: 9 },
};

export function formatoDe(valor: string | null | undefined): FormatoCartao {
  return valor === "stories" ? "stories" : "feed";
}

export type Esfera = "presidente" | "governador" | "prefeito" | "senado" | "federal" | "estadual";

export type PessoaMosaico = {
  chave: string;
  esfera: Esfera;
  /** Endereço da foto oficial; nulo vira silhueta. */
  foto: string | null;
};

export type Contagem = { esfera: Esfera | "vereadores"; n: number; rotulo: string };

/** Rótulo curto no canto da foto. Sem gênero: a API não diz se é senador ou senadora. */
export const ROTULO_FOTO: Record<Esfera, string> = {
  presidente: "Presidência",
  governador: "Governo",
  prefeito: "Prefeitura",
  senado: "Senado",
  federal: "Dep. federal",
  estadual: "Dep. estadual",
};

const ORDEM: Esfera[] = ["presidente", "governador", "prefeito", "senado", "federal", "estadual"];

/** Pluraliza em português: 1 presidente, 3 senadores. */
export function rotuloContagem(n: number, um: string, varios: string): string {
  return `${n.toLocaleString("pt-BR")} ${n === 1 ? um : varios}`;
}

export type Entrada = {
  presidente: number | null;
  governador: number | null;
  prefeito: number | null;
  /** Quantidade de cada cargo; nulo quando o dado não está publicado. */
  nSenadores: number | null;
  nFederais: number | null;
  nEstaduais: number | null;
  nVereadores: number | null;
  /** Distrito Federal: câmara legislativa no lugar da assembleia; não tem prefeitura nem vereadores. */
  distrito?: boolean;
};

/** Contagens por cargo, na ordem do país para a cidade. Cargo sem dado fica de fora. */
export function contagens(e: Entrada): { itens: Contagem[]; total: number; fora: string[] } {
  const itens: Contagem[] = [];
  const fora: string[] = [];
  const add = (esfera: Contagem["esfera"], n: number | null, um: string, varios: string, nome: string) => {
    if (n == null || n <= 0) {
      fora.push(nome);
      return;
    }
    itens.push({ esfera, n, rotulo: rotuloContagem(n, um, varios) });
  };
  add("presidente", e.presidente, "presidente", "presidentes", "presidente");
  add("senado", e.nSenadores, "senador", "senadores", "senadores");
  add("federal", e.nFederais, "deputado federal", "deputados federais", "deputados federais");
  add("governador", e.governador, "governador", "governadores", "governador");
  add(
    "estadual",
    e.nEstaduais,
    e.distrito ? "deputado distrital" : "deputado estadual",
    e.distrito ? "deputados distritais" : "deputados estaduais",
    e.distrito ? "deputados distritais" : "deputados estaduais",
  );
  if (!e.distrito) {
    add("prefeito", e.prefeito, "prefeito", "prefeitos", "prefeito");
    add("vereadores", e.nVereadores, "vereador", "vereadores", "vereadores");
  }
  return { itens, total: itens.reduce((s, c) => s + c.n, 0), fora };
}

/** "Dado não publicado: vereadores e prefeito." */
export function textoFora(fora: string[]): string | null {
  if (fora.length === 0) return null;
  const lista = fora.length === 1 ? fora[0] : `${fora.slice(0, -1).join(", ")} e ${fora[fora.length - 1]}`;
  return `Dado não publicado: ${lista}.`;
}

/** Número estável a partir de um texto (para sortear sem favorecer a ordem alfabética). */
function semente(texto: string): number {
  let h = 2166136261;
  for (let i = 0; i < texto.length; i++) {
    h ^= texto.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function embaralhar<T>(lista: T[], chave: string): T[] {
  let s = semente(chave) || 1;
  const a = [...lista];
  for (let i = a.length - 1; i > 0; i--) {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    const j = s % (i + 1);
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/**
 * Escolhe quem aparece no mosaico: primeiro cada cargo único (presidente, governador,
 * prefeito), depois os senadores, depois deputados federais e estaduais. Quem tem foto
 * vem antes de quem não tem. Entre deputados, a ordem é sorteada pela cidade (sempre a mesma
 * para a mesma cidade), sem favorecer ninguém. O mosaico sai em ordem fixa de cargo.
 */
export function escolherMosaico(pessoas: PessoaMosaico[], quantas: number, chave: string): PessoaMosaico[] {
  const porEsfera = (e: Esfera) => pessoas.filter((p) => p.esfera === e);
  const fila: PessoaMosaico[] = [];
  for (const e of ["presidente", "governador", "prefeito", "senado"] as Esfera[]) fila.push(...porEsfera(e));
  for (const e of ["federal", "estadual"] as Esfera[]) fila.push(...embaralhar(porEsfera(e), `${chave}-${e}`));
  const escolhidos = [...fila.filter((p) => p.foto), ...fila.filter((p) => !p.foto)].slice(0, quantas);
  // Só linhas inteiras de 3: sobra de 1 ou 2 fotos deixaria buraco no mosaico.
  const cabem = Math.floor(escolhidos.length / 3) * 3;
  return escolhidos.slice(0, cabem).sort((a, b) => ORDEM.indexOf(a.esfera) - ORDEM.indexOf(b.esfera));
}

/** "Câmara, Senado e TSE" a partir das fontes usadas, sem repetir. */
export function listaDeFontes(fontes: string[]): string {
  const unicas = [...new Set(fontes.filter(Boolean))];
  if (unicas.length <= 1) return unicas[0] ?? "";
  return `${unicas.slice(0, -1).join(", ")} e ${unicas[unicas.length - 1]}`;
}

/** Maior data (ISO) entre as informadas. */
export function dataMaisRecente(datas: (string | null | undefined)[]): string | null {
  const ok = datas.filter((d): d is string => Boolean(d)).sort();
  return ok.at(-1) ?? null;
}
