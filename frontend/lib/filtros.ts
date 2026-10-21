/**
 * Lógica pura dos filtros (sem React): monta o endereço a partir dos campos do formulário,
 * deixando de fora o que está vazio ou igual ao padrão, para o link compartilhado ficar curto
 * e igual ao que se chega pelas pílulas.
 */

export type Padroes = Record<string, string>;

/** Campos do formulário -> query string (sem "?"), sem valores vazios nem iguais ao padrão. */
export function consultaDosCampos(campos: Iterable<[string, FormDataEntryValue]>, padroes: Padroes = {}): string {
  const params = new URLSearchParams();
  for (const [chave, bruto] of campos) {
    if (typeof bruto !== "string") continue;
    const valor = bruto.trim();
    if (!valor || padroes[chave] === valor) continue;
    params.set(chave, valor);
  }
  return params.toString();
}

/** Junta caminho, consulta e âncora: "/lista", "a=1", "secao" -> "/lista?a=1#secao". */
export function enderecoComConsulta(caminho: string, consulta: string, ancora?: string): string {
  const base = caminho.split("#")[0];
  return `${base}${consulta ? `?${consulta}` : ""}${ancora ? `#${ancora}` : ""}`;
}

/** "1 filtro ativo", "2 filtros ativos" ou null. */
export function textoAtivos(n: number): string | null {
  if (n <= 0) return null;
  return n === 1 ? "1 filtro ativo" : `${n} filtros ativos`;
}
