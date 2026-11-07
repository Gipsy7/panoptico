/** Correções públicas (Frente 7): texto do link no perfil e CSV da tabela de /sobre-as-fontes. */

export type Correcao = {
  id: number;
  data: string;
  dado: string;
  antes: string;
  depois: string;
  motivo: string;
  fonte: string;
  perfil_tipo: string | null;
  perfil_id: string | null;
  perfil_nome: string | null;
};

export type Correcoes = { itens: Correcao[]; total: number };

export function idLinhaCorrecao(c: Pick<Correcao, "id">): string {
  return `correcao-${c.id}`;
}

/** "Este perfil teve 1 correção" / "Este perfil teve 3 correções". */
export function textoLinkCorrecao(total: number): string {
  return `Este perfil teve ${total} ${total === 1 ? "correção" : "correções"}`;
}

/** Endereço do link no perfil: a linha mais recente, ou a seção toda. */
export function destinoCorrecao(itens: Correcao[]): string {
  const maisRecente = [...itens].sort((a, b) => b.data.localeCompare(a.data))[0];
  return maisRecente ? `/sobre-as-fontes#${idLinhaCorrecao(maisRecente)}` : "/sobre-as-fontes#correcoes";
}

function celulaCsv(v: string | number | null | undefined): string {
  let s = v == null ? "" : String(v);
  // Evita que o programa de planilha leia o texto como fórmula.
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\n\r;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

const COLUNAS_CSV = ["data", "dado", "antes", "depois", "fonte", "motivo", "perfil"] as const;

/** CSV (vírgula, UTF-8, com cabeçalho) das correções, na ordem recebida. */
export function correcoesParaCsv(itens: Correcao[]): string {
  const linhas = itens.map((c) =>
    [c.data, c.dado, c.antes, c.depois, c.fonte, c.motivo, c.perfil_nome ?? ""].map(celulaCsv).join(","),
  );
  return [COLUNAS_CSV.join(","), ...linhas].join("\r\n") + "\r\n";
}
