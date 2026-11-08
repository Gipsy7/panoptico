/** Textos das eleições (Frente 5) em linguagem do dia a dia; o termo do TSE vai em letra menor. */

const CARGOS: Record<string, string> = {
  PRESIDENTE: "Presidente",
  GOVERNADOR: "Governador",
  SENADOR: "Senador",
  "DEPUTADO FEDERAL": "Deputado federal",
  "DEPUTADO ESTADUAL": "Deputado estadual",
  "DEPUTADO DISTRITAL": "Deputado distrital",
  PREFEITO: "Prefeito",
  VEREADOR: "Vereador",
};

export function nomeCargo(cargo: string): string {
  return CARGOS[cargo.toUpperCase()] ?? cargo.charAt(0) + cargo.slice(1).toLowerCase();
}

/** Plural para "Deputados federais mais votados", "Vereadores"... */
export function nomeCargoPlural(cargo: string): string {
  const nome = nomeCargo(cargo);
  return nome
    .split(" ")
    .map((p) => (p.endsWith("l") ? `${p.slice(0, -1)}is` : p.endsWith("r") ? `${p}es` : `${p}s`))
    .join(" ");
}

/** Situação do TSE em palavras simples; `oficial` é o termo do TSE quando ele diz mais. */
export function situacaoSimples(situacao: string | null): { texto: string; oficial: string | null } {
  const s = (situacao ?? "").toUpperCase();
  if (!s) return { texto: "Sem resultado informado", oficial: null };
  if (s === "ELEITO") return { texto: "Eleito", oficial: null };
  if (s === "ELEITO POR QP") return { texto: "Eleito", oficial: "pelo quociente partidário" };
  if (s.startsWith("ELEITO POR M")) return { texto: "Eleito", oficial: "pela média (sobras)" };
  if (s === "SUPLENTE") return { texto: "Suplente", oficial: null };
  if (s.startsWith("N") && s.includes("ELEITO")) return { texto: "Não eleito", oficial: null };
  if (s.includes("2º TURNO") || s.includes("2O TURNO")) return { texto: "Foi ao 2º turno", oficial: null };
  return { texto: situacao ?? "", oficial: null };
}

export function formatarPct(pct: number | null | undefined, casas = 2): string {
  if (pct === null || pct === undefined) return "—";
  return `${pct.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas })}%`;
}

export function formatarVotos(votos: number): string {
  return votos.toLocaleString("pt-BR");
}

/** "Blumenau (SC)", "Santa Catarina", "Brasil": onde a disputa (ou o recorte) aconteceu. */
export function lugarDaDisputa(r: { uf: string | null; municipio: { nome: string; uf: string } | null }): string {
  if (r.municipio) return `${r.municipio.nome} (${r.municipio.uf})`;
  if (!r.uf || r.uf === "BR") return "Brasil";
  return r.uf;
}

/** Largura da barra em % (0–100), em relação ao mais votado da lista, para caber na tela. */
export function larguraBarra(votos: number, maior: number): number {
  if (maior <= 0) return 0;
  return Math.max(0.5, Math.round((1000 * votos) / maior) / 10);
}
