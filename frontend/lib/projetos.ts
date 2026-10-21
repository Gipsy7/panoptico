/**
 * Lógica pura das telas de projetos e votações (sem React): leitura de filtros e de `?uf=`,
 * situação em linguagem do dia a dia, ordem fixa dos grupos de voto e texto de compartilhamento.
 * Fica aqui para ser testada (Vitest) sem subir o site.
 */
import type { FiltrosProjetos, GrupoDiscursos, GrupoQuemVotou, PessoaQueVotou, VotacaoDoProjeto } from "@/lib/api";
import { UFS } from "@/lib/ufs";

const SEM_ACENTO = /[̀-ͯ]/g;

export function semAcento(texto: string): string {
  return texto.normalize("NFD").replace(SEM_ACENTO, "").toLowerCase();
}

/** `?uf=sp` -> "SP"; qualquer coisa que não seja um estado vira null. */
export function lerUf(valor: string | string[] | undefined | null): string | null {
  const v = (Array.isArray(valor) ? valor[0] : valor)?.trim().toUpperCase();
  return v && UFS.some((u) => u.sigla === v) ? v : null;
}

const CAMPOS_PROJETOS: (keyof FiltrosProjetos)[] = [
  "q",
  "esfera",
  "casa",
  "uf",
  "municipio",
  "tema",
  "ano",
  "votacao",
  "pagina",
];

/** Código IBGE de cada estado: os dois primeiros dígitos do código das cidades dele. */
export const CODIGO_IBGE_UF: Record<string, string> = {
  RO: "11", AC: "12", AM: "13", RR: "14", PA: "15", AP: "16", TO: "17",
  MA: "21", PI: "22", CE: "23", RN: "24", PB: "25", PE: "26", AL: "27", SE: "28", BA: "29",
  MG: "31", ES: "32", RJ: "33", SP: "35",
  PR: "41", SC: "42", RS: "43",
  MS: "50", MT: "51", GO: "52", DF: "53",
};

/** Lê os filtros da busca de /projetos a partir dos `searchParams`, descartando valores inválidos. */
export function lerFiltrosProjetos(sp: Record<string, string | string[] | undefined>): FiltrosProjetos {
  const f: FiltrosProjetos = {};
  for (const campo of CAMPOS_PROJETOS) {
    const bruto = sp[campo];
    const valor = (Array.isArray(bruto) ? bruto[0] : bruto)?.trim();
    if (valor) f[campo] = valor;
  }
  if (f.esfera && !["federal", "estadual", "municipal"].includes(f.esfera)) delete f.esfera;
  if (f.casa && !["camara", "senado", "assembleia", "camara_municipal"].includes(f.casa)) delete f.casa;
  if (f.votacao && !["com", "sem"].includes(f.votacao)) delete f.votacao;
  if (f.uf) {
    const uf = lerUf(f.uf);
    if (uf) f.uf = uf;
    else delete f.uf;
  }
  if (f.municipio && !/^\d{7}$/.test(f.municipio)) delete f.municipio;
  // Cidade de outro estado (ex.: trocou o estado no formulário sem JavaScript): a cidade sai.
  if (f.municipio && f.uf && f.municipio.slice(0, 2) !== CODIGO_IBGE_UF[f.uf]) delete f.municipio;
  if (f.ano && !/^\d{4}$/.test(f.ano)) delete f.ano;
  if (f.pagina && !/^[1-9]\d{0,3}$/.test(f.pagina)) delete f.pagina;
  if (f.q) f.q = f.q.slice(0, 200);
  return f;
}

/** Endereço de /projetos com uma mudança nos filtros; volta à página 1 (a menos que `pagina` venha na mudança). */
export function enderecoProjetos(filtros: FiltrosProjetos, mudanca: Partial<FiltrosProjetos> = {}): string {
  const params = new URLSearchParams();
  const todos: FiltrosProjetos = { ...filtros, ...mudanca };
  if (!("pagina" in mudanca)) todos.pagina = "";
  for (const campo of CAMPOS_PROJETOS) {
    const v = todos[campo];
    if (v) params.set(campo, v);
  }
  const texto = params.toString();
  return texto ? `/projetos?${texto}` : "/projetos";
}

/**
 * A API devolve `/votacoes/local/{id}` para votação de câmara municipal ou assembleia; a tela
 * mora em `/votacao/local/{id}` (mesmo prefixo do explicador federal).
 */
export function caminhoInterno(link: string): string {
  return link.replace(/^\/votacoes\/local\//, "/votacao/local/");
}

export const ORDEM_GRUPOS_VOTO = ["sim", "nao", "outros"] as const;
export const ORDEM_GRUPOS_DISCURSO = ["sim", "nao", "outro", "sem_voto"] as const;

function ordenarPorChave<T extends { chave: string }>(grupos: T[], ordem: readonly string[]): T[] {
  const posicao = (c: string) => {
    const i = ordem.indexOf(c);
    return i < 0 ? ordem.length : i;
  };
  return [...grupos].sort((a, b) => posicao(a.chave) - posicao(b.chave));
}

/** Grupos de quem votou, sempre Sim, Não e depois os outros registros. */
export function ordenarGruposVoto<T extends { chave: string }>(grupos: T[]): T[] {
  return ordenarPorChave(grupos, ORDEM_GRUPOS_VOTO);
}

/** Grupos de discursos: Votou Sim, Votou Não, Outro registro, Falou e não registrou voto. */
export function ordenarGruposDiscurso<T extends { chave: string }>(grupos: T[]): T[] {
  return ordenarPorChave(grupos, ORDEM_GRUPOS_DISCURSO);
}

export const ROTULO_GRUPO_DISCURSO: Record<string, string> = {
  sim: "Votou Sim",
  nao: "Votou Não",
  outro: "Outro registro",
  sem_voto: "Falou e não registrou voto",
};

export function rotuloGrupoDiscurso(g: Pick<GrupoDiscursos, "chave" | "rotulo">): string {
  return ROTULO_GRUPO_DISCURSO[g.chave] ?? g.rotulo;
}

/** Recorta cada grupo de votantes para um estado; as quantidades passam a ser as do estado. */
export function filtrarGruposPorUf(grupos: GrupoQuemVotou[], uf: string | null): GrupoQuemVotou[] {
  const ordenados = ordenarGruposVoto(grupos);
  if (!uf) return ordenados;
  return ordenados.map((g) => {
    const pessoas: PessoaQueVotou[] = g.pessoas.filter((p) => p.uf === uf);
    const porPartido = new Map<string, number>();
    for (const p of pessoas) porPartido.set(p.partido, (porPartido.get(p.partido) ?? 0) + 1);
    const partidos = [...porPartido.entries()]
      .map(([partido, quantidade]) => ({ partido, quantidade }))
      .sort((a, b) => b.quantidade - a.quantidade || a.partido.localeCompare(b.partido, "pt-BR"));
    return { ...g, pessoas, partidos, quantidade: pessoas.length };
  });
}

export type Situacao = { rotulo: string | null; oficial: string | null };

/**
 * Situação em linguagem do dia a dia, com o texto oficial guardado para a letra menor. Só traduz
 * o que se reconhece com segurança; o resto fica sem tradução (rotulo null) e mostra o texto oficial.
 */
export function situacaoSimples(situacao: string | null | undefined, virouLei: boolean | null | undefined): Situacao {
  const oficial = situacao?.trim() || null;
  if (virouLei) return { rotulo: "Virou lei", oficial };
  if (!oficial) return { rotulo: null, oficial: null };
  const t = semAcento(oficial);
  const regras: [RegExp, string][] = [
    [/arquiva/, "Arquivado"],
    [/norma juridica|promulga/, "Virou lei"],
    [/vetad/, "Vetado"],
    [/sancao/, "Aguarda sanção da Presidência"],
    [/pronta para pauta|pauta no plenario/, "Pronto para ir ao Plenário"],
    [/designacao de relator/, "Esperando um relator ser escolhido"],
    [/parecer.*relator|relator/, "Em análise numa comissão"],
    [/comissao|tramitando/, "Em tramitação"],
  ];
  for (const [re, rotulo] of regras) if (re.test(t)) return { rotulo, oficial };
  return { rotulo: null, oficial };
}

const INTEIRO = new Intl.NumberFormat("pt-BR");

export function recortar(texto: string, limite: number): string {
  const t = texto.replace(/\s+/g, " ").trim();
  return t.length <= limite ? t : `${t.slice(0, limite - 1).trimEnd()}…`;
}

/** Texto factual para o WhatsApp, a partir do último placar. */
export function textoCompartilharProjeto(args: {
  rotulo: string;
  ementa?: string | null;
  casaCurta: string;
  placar?: { sim: number; nao: number; data: string } | null;
}): string {
  const { rotulo, ementa, casaCurta, placar } = args;
  const resumo = ementa ? ` ${recortar(ementa, 140)}` : "";
  const voto = placar
    ? ` Última votação nominal no Plenário (${placar.data}): Sim ${INTEIRO.format(placar.sim)} x Não ${INTEIRO.format(placar.nao)}.`
    : " Ainda sem votação nominal no Plenário.";
  return `${rotulo} (${casaCurta}).${resumo}${voto} Veja quem votou e o que disseram:`;
}

/** Anos do filtro, do atual para trás. */
export function anosParaFiltro(atual: number, quantos = 12): number[] {
  return Array.from({ length: quantos }, (_, i) => atual - i);
}

export const CHAVE_UF_LEMBRADA = "panoptico.uf";

/**
 * A resposta do explicador traz só o endereço oficial da proposição, que carrega o id na Casa
 * (`idProposicao=123` na Câmara, `/materia/123` no Senado). Devolve o id, ou null.
 */
export function idDaProposicao(url: string | null | undefined): string | null {
  if (!url) return null;
  return /[?&]idProposicao=(\d+)/.exec(url)?.[1] ?? /\/materia\/(\d+)(?:[/?#]|$)/.exec(url)?.[1] ?? null;
}

/** Placar de uma votação do projeto: o publicado pela Casa quando existe, senão a contagem da lista. */
export function placarDaVotacao(v: VotacaoDoProjeto): { sim: number; nao: number; daFonte: boolean } {
  const o = v.placar_publicado;
  const daFonte = o?.sim != null || o?.nao != null;
  return { sim: o?.sim ?? v.placar_contado.sim, nao: o?.nao ?? v.placar_contado.nao, daFonte };
}

/**
 * Quando o placar publicado pela Casa é maior que a soma do grupo correspondente da lista
 * (votos de quem já deixou o cargo contam no placar, mas não estão no nosso cadastro),
 * devolve os números de Sim e Não; senão null.
 */
export function placarMaiorQueALista(
  publicado: { sim: number | null; nao: number | null } | null | undefined,
  grupos: Pick<GrupoQuemVotou, "chave" | "quantidade">[],
): { sim: number; nao: number; listaSim: number; listaNao: number } | null {
  if (!publicado) return null;
  const listaSim = grupos.find((g) => g.chave === "sim")?.quantidade ?? 0;
  const listaNao = grupos.find((g) => g.chave === "nao")?.quantidade ?? 0;
  const sim = publicado.sim ?? 0;
  const nao = publicado.nao ?? 0;
  if (sim <= listaSim && nao <= listaNao) return null;
  return { sim, nao, listaSim, listaNao };
}

export type VotoLocal = { mandato_id: number; nome: string; partido: string | null; voto: string };

/**
 * Votos de uma casa local em três grupos fixos (Sim, Não, outros registros), com o nome em ordem
 * alfabética. O texto do voto é o que a casa publica ("Abstenção", "Ausente"...).
 */
export function agruparVotosLocais(votos: VotoLocal[]): { chave: "sim" | "nao" | "outros"; rotulo: string; votos: VotoLocal[] }[] {
  const grupos = {
    sim: [] as VotoLocal[],
    nao: [] as VotoLocal[],
    outros: [] as VotoLocal[],
  };
  for (const v of votos) {
    const t = semAcento(v.voto).trim();
    if (t === "sim") grupos.sim.push(v);
    else if (t === "nao") grupos.nao.push(v);
    else grupos.outros.push(v);
  }
  const ordenar = (l: VotoLocal[]) => [...l].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  return [
    { chave: "sim", rotulo: "Sim", votos: ordenar(grupos.sim) },
    { chave: "nao", rotulo: "Não", votos: ordenar(grupos.nao) },
    { chave: "outros", rotulo: "Outros registros", votos: ordenar(grupos.outros) },
  ];
}
