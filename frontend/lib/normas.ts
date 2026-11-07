/**
 * Projetos que viraram lei: textos e contas puras para o filtro "Virou lei" de /projetos, o
 * "Viraram lei" do perfil e o "Resultado" do Caminho do projeto (dados de app/services/normas.py).
 */
import type { NormaItem } from "@/lib/api";

type ProjetoDaNorma = NormaItem["projetos"][number];

/** "do PL 1087/2025", "da PEC 45/2019", "da MPV 1300/2025": o artigo certo para a sigla. */
export function comArtigo(identificacao: string): string {
  return /^(PEC|MPV|MP)\b/i.test(identificacao.trim()) ? `da ${identificacao}` : `do ${identificacao}`;
}

/**
 * Projetos de origem sem repetir a mesma identificação (o mesmo PLP na Câmara e no Senado vira um
 * só), preferindo o que tem página no site.
 */
export function origensDaLei(projetos: ProjetoDaNorma[]): { identificacao: string; link: string | null }[] {
  const porIdent = new Map<string, string | null>();
  for (const p of projetos) {
    if (!p.identificacao) continue;
    const atual = porIdent.get(p.identificacao);
    if (atual === undefined || (!atual && p.link)) porIdent.set(p.identificacao, p.link);
  }
  return [...porIdent].map(([identificacao, link]) => ({ identificacao, link }));
}

/** Largura da barra de um ano, em %, proporcional ao maior ano da lista (mínimo visível de 2%). */
export function larguraBarra(total: number, maior: number): number {
  if (maior <= 0 || total <= 0) return 0;
  return Math.max(2, Math.round((total / maior) * 100));
}

/** "255 leis", "1 lei" (lei ordinária, complementar e emenda contam juntas). */
export function contagemLeis(n: number): string {
  return `${n.toLocaleString("pt-BR")} ${n === 1 ? "lei" : "leis"}`;
}

/** Composição do ano em palavras, só com o que existe: "239 leis, 13 leis complementares e 3 emendas à Constituição". */
export function composicaoDoAno(a: { leis: number; leis_complementares: number; emendas_constitucionais: number }): string {
  const partes = [
    a.leis ? `${a.leis.toLocaleString("pt-BR")} ${a.leis === 1 ? "lei ordinária" : "leis ordinárias"}` : null,
    a.leis_complementares
      ? `${a.leis_complementares} ${a.leis_complementares === 1 ? "lei complementar" : "leis complementares"}`
      : null,
    a.emendas_constitucionais
      ? `${a.emendas_constitucionais} ${a.emendas_constitucionais === 1 ? "emenda à Constituição" : "emendas à Constituição"}`
      : null,
  ].filter((p): p is string => p !== null);
  if (partes.length <= 1) return partes[0] ?? "";
  return `${partes.slice(0, -1).join(", ")} e ${partes.at(-1)}`;
}
