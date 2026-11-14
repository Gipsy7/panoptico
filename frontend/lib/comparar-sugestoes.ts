/**
 * Atalhos do comparador a partir do lugar guardado no aparelho (docs/DECISOES.md, 2026-11-14).
 * Lógica pura, sem rede: recebe o que a API devolveu e monta os endereços.
 *
 * Nenhuma escolha editorial: os senadores são todos os do estado, em ordem alfabética; os
 * deputados são os dois eleitos mais votados na cidade, na ordem dos votos, e o atalho só existe
 * quando os dois primeiros da lista oficial estão em exercício. Quem diz isso é a API
 * (`parlamentar_id`, a ligação do cadastro do TSE com o da Casa). Numa API antiga, sem esse
 * campo, vale o nome idêntico. Se um dos dois não está no cargo, o atalho some em vez de
 * mostrar "os mais votados" com alguém faltando.
 */

/** Eleição que escolheu os deputados federais em exercício. Trocar para 2026 na posse (fev/2027). */
export const ANO_ELEICAO_FEDERAL = 2022;

export type PessoaAtalho = { id: number; nome_parlamentar: string };
export type VotadoNaCidade = { nome_urna: string; eleito: boolean; parlamentar_id?: number | null };

export function chaveDoNome(nome: string): string {
  return nome
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toUpperCase()
    .replace(/\s+/g, " ")
    .trim();
}

export function enderecoComparar(ids: number[]): string {
  return `/comparar?ids=${ids.join(",")}`;
}

/** Todos os senadores do estado, em ordem alfabética (até 4). Menos de 2: sem atalho. */
export function senadoresDoEstado<T extends PessoaAtalho>(senadores: T[]): T[] | null {
  if (senadores.length < 2) return null;
  return [...senadores]
    .sort((a, b) => a.nome_parlamentar.localeCompare(b.nome_parlamentar, "pt-BR"))
    .slice(0, 4);
}

/**
 * Os dois deputados federais eleitos mais votados na cidade, se os dois estão em exercício.
 * `votados` vem na ordem dos votos (como a API devolve).
 */
export function maisVotadosEmExercicio<T extends PessoaAtalho>(
  votados: VotadoNaCidade[],
  deputados: T[],
): [T, T] | null {
  const porNome = new Map<string, T[]>();
  for (const d of deputados) {
    const chave = chaveDoNome(d.nome_parlamentar);
    porNome.set(chave, [...(porNome.get(chave) ?? []), d]);
  }
  const eleitos = votados.filter((v) => v.eleito).slice(0, 2);
  if (eleitos.length < 2) return null;
  const achados: T[] = [];
  for (const e of eleitos) {
    if (e.parlamentar_id !== undefined) {
      // A API disse quem é (ou que não está em exercício): não se tenta pelo nome.
      const pelaLigacao = deputados.find((d) => d.id === e.parlamentar_id);
      if (!pelaLigacao) return null;
      achados.push(pelaLigacao);
      continue;
    }
    const iguais = porNome.get(chaveDoNome(e.nome_urna)) ?? [];
    // Nome que não bate, ou dois deputados com o mesmo nome: não dá para afirmar quem é.
    if (iguais.length !== 1) return null;
    achados.push(iguais[0]);
  }
  return achados[0].id === achados[1].id ? null : [achados[0], achados[1]];
}

/** Os mesmos ids, em qualquer ordem. */
export function mesmoGrupo(a: number[], b: number[]): boolean {
  return a.length === b.length && [...a].sort().join(",") === [...b].sort().join(",");
}

/** "Amin, Seif e Ivete" a partir dos nomes completos. */
export function listaDeNomes(nomes: string[]): string {
  if (nomes.length <= 1) return nomes.join("");
  return `${nomes.slice(0, -1).join(", ")} e ${nomes[nomes.length - 1]}`;
}
