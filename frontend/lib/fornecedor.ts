// Lógica pura da ficha do fornecedor (docs/DECISOES.md, 2026-11-14, protótipo 1B).
// Sem rede nem React: endereço da ficha, CNPJ formatado e as frases dos cartões.

export type FichaFornecedor = {
  cnpj: string;
  nome: string | null;
  nome_omitido: boolean;
  nome_fantasia: string | null;
  uf: string | null;
  situacao: string | null;
  cadastro_referencia: string | null;
  gabinetes: BlocoFicha & {
    por_ano: { ano: number; valor: number; gabinetes: number; lancamentos: number }[];
    ano_da_lista: number | null;
    maiores: {
      parlamentar_id: number;
      nome: string;
      casa: "camara" | "senado";
      partido: string | null;
      uf: string;
      valor: number;
    }[];
    limite_da_lista: number;
  };
  prefeituras: BlocoFicha & {
    por_ano: { ano: number; valor: number; municipios: number }[];
    ano_da_lista: number | null;
    maiores: { ibge: string; municipio: string; uf: string; orgao: string; valor: number }[];
    limite_da_lista: number;
  };
  pncp: BlocoFicha & { por_ano: { ano: number; valor: number; contratos: number; municipios: number }[] };
  emendas: BlocoFicha & {
    pagas_por_ano: { ano: number; valor: number; autores: number }[];
    convenios: { quantidade: number; valor_repassado: number };
  };
  sancoes: BlocoFicha & {
    itens: {
      cadastro: string;
      categoria: string;
      abrangencia: string | null;
      orgao: string | null;
      inicio: string | null;
      fim: string | null;
      processo: string | null;
    }[];
    fonte_url?: string;
  };
};

type BlocoFicha = { recorte: string; fonte_nome: string; atualizado_em: string | null };

/** Os 14 dígitos, ou nulo se não for um CNPJ escrito por inteiro. Não confere dígito verificador. */
export function digitosDoCnpj(valor: string | null | undefined): string | null {
  const d = (valor ?? "").replace(/\D/g, "");
  return d.length === 14 ? d : null;
}

/** Endereço da ficha; nulo quando o documento não é CNPJ (CPF nunca vira link). */
export function hrefFornecedor(documento: string | null | undefined): string | null {
  const d = digitosDoCnpj(documento);
  return d ? `/fornecedor/${d}` : null;
}

export function formatarCnpj(valor: string): string {
  const d = digitosDoCnpj(valor);
  return d ? `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}` : valor;
}

const plural = (n: number, um: string, varios: string) => `${n.toLocaleString("pt-BR")} ${n === 1 ? um : varios}`;

/** Frase de apoio de cada cartão: o número em palavras, sem adjetivo. */
export function frasesDaFicha(f: FichaFornecedor) {
  const g = f.gabinetes.por_ano[0];
  const p = f.prefeituras.por_ano[0];
  const c = f.pncp.por_ano[0];
  const e = f.emendas.pagas_por_ano[0];
  const s = f.sancoes.itens.length;
  return {
    gabinetes: g ? `${plural(g.gabinetes, "gabinete pagou", "gabinetes pagaram")}, pela cota parlamentar` : null,
    prefeituras: p ? `${plural(p.municipios, "cidade", "cidades")} com pagamento de prefeitura ou câmara` : null,
    pncp: c ? `${plural(c.contratos, "contrato", "contratos")} em ${plural(c.municipios, "cidade", "cidades")}` : null,
    emendas: e
      ? `Favorecida em emendas de ${plural(e.autores, "autor", "autores")}`
      : f.emendas.convenios.quantidade > 0
        ? plural(f.emendas.convenios.quantidade, "convênio de emenda", "convênios de emendas")
        : null,
    sancoes: s === 0 ? "Sem registro no CEIS nem no CNEP" : plural(s, "registro", "registros"),
  };
}

/** A ficha tem alguma coisa além do cadastro? */
export function fichaTemDado(f: FichaFornecedor): boolean {
  return (
    f.gabinetes.por_ano.length > 0 ||
    f.prefeituras.por_ano.length > 0 ||
    f.pncp.por_ano.length > 0 ||
    f.emendas.pagas_por_ano.length > 0 ||
    f.emendas.convenios.quantidade > 0 ||
    f.sancoes.itens.length > 0
  );
}
