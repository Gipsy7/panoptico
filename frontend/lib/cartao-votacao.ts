// Lógica pura do cartão "Como votaram os deputados de [estado]" (imagem para Feed e Stories).
// Sem rede nem React: recebe os votos que a API já devolve e monta os grupos, os nomes e as frases.
// Decisão em docs/DECISOES.md, 2026-11-14 (protótipo A, com fotos em estado de até 20 pessoas).

export type VotoCartao = { parlamentar_id: number; nome: string; uf: string; voto: string };

export type ChaveGrupo = "sim" | "nao" | "outros";
export type GrupoCartao = { chave: ChaveGrupo; rotulo: string; pessoas: VotoCartao[] };

/** Até este total de pessoas do estado na votação, o cartão leva as fotos; acima, só os nomes. */
export const LIMITE_FOTOS = 20;

export function ufValida(valor: string | null | undefined): string | null {
  const uf = (valor ?? "").toUpperCase();
  return /^[A-Z]{2}$/.test(uf) ? uf : null;
}

/**
 * Sim, Não e o resto ("Outro registro": abstenção, obstrução, presidiu a sessão, ausência
 * publicada), cada grupo em ordem alfabética. Os três sempre voltam, mesmo vazios, para o placar.
 */
export function gruposDoEstado(parlamentares: VotoCartao[], uf: string): GrupoCartao[] {
  const doEstado = parlamentares
    .filter((p) => p.uf === uf)
    .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  return [
    { chave: "sim", rotulo: "Sim", pessoas: doEstado.filter((p) => p.voto === "Sim") },
    { chave: "nao", rotulo: "Não", pessoas: doEstado.filter((p) => p.voto === "Não") },
    {
      chave: "outros",
      rotulo: "Outro registro",
      pessoas: doEstado.filter((p) => p.voto !== "Sim" && p.voto !== "Não"),
    },
  ];
}

export function totalDosGrupos(grupos: GrupoCartao[]): number {
  return grupos.reduce((soma, g) => soma + g.pessoas.length, 0);
}

/** Nomes separados por vírgula até caber em `maximo` caracteres; o resto vira "e mais N". */
export function nomesCortados(nomes: string[], maximo: number): string {
  const dentro: string[] = [];
  let tamanho = 0;
  for (const nome of nomes) {
    const custo = nome.length + (dentro.length ? 2 : 0);
    // Reserva o espaço do "e mais N" enquanto ainda há nomes por vir.
    const reserva = dentro.length + 1 < nomes.length ? 12 : 0;
    if (dentro.length > 0 && tamanho + custo + reserva > maximo) break;
    dentro.push(nome);
    tamanho += custo;
  }
  const resto = nomes.length - dentro.length;
  if (resto === 0) return dentro.join(", ");
  return `${dentro.join(", ")} e mais ${resto}`;
}

const QUEM = { camara: "os deputados", senado: "os senadores" } as const;

/** "Como votaram os deputados de SC". */
export function tituloCartao(casa: "camara" | "senado", uf: string): string {
  return `Como votaram ${QUEM[casa]} de ${uf}`;
}

/** "14 Sim, 0 Não" e, se houver, "2 com outro registro". */
export function placarEmTexto(grupos: GrupoCartao[]): string {
  const n = (chave: ChaveGrupo) => grupos.find((g) => g.chave === chave)?.pessoas.length ?? 0;
  const base = `${n("sim")} Sim, ${n("nao")} Não`;
  return n("outros") > 0 ? `${base}, ${n("outros")} com outro registro` : base;
}

/** Frase que vai junto do link ao compartilhar. */
export function fraseCompartilhar(
  casa: "camara" | "senado",
  uf: string,
  proposicao: string | null,
  grupos: GrupoCartao[],
): string {
  const sobre = proposicao ? ` em ${proposicao}` : " nesta votação";
  return `${tituloCartao(casa, uf)}${sobre}: ${placarEmTexto(grupos)}. Veja o voto de cada um:`;
}

/** Caminho base da imagem (o formato entra depois, como nos outros cartões). */
export function caminhoCartaoVotacao(casa: string, id: string, uf: string): string {
  return `/votacao/${casa}/${encodeURIComponent(id)}/cartao/${uf}`;
}
