/**
 * "O que mudou": frases literais tiradas das séries da linha do tempo (de quanto para quanto, em
 * que anos, ao lado do estado e do Brasil). Sem adjetivo nem juízo; a janela é fixa por série
 * (5 anos; 10 no IDEB, que é a cada 2 anos), nunca o ano que deixaria a frase mais forte.
 */
import type { TempoDoLugar, PontoAno, SerieTempo } from "@/lib/api";

export type Descoberta = {
  /** Série que a pergunta completa mostra. */
  serie: string;
  tema: string;
  titulo: string;
  pergunta: string;
  frase: string;
  detalhe: string;
};

type Regra = {
  serie: string;
  titulo: string;
  pergunta: (lugar: string) => string;
  janela: number;
  /** Texto curto depois dos números ("homicídios de moradores por ano"). */
  oque: (s: SerieTempo, linha: TempoDoLugar) => string;
  comparar?: string;
};

const REGRAS: Regra[] = [
  {
    serie: "homicidios",
    titulo: "Segurança",
    pergunta: (l) => `Como a violência mudou em ${l}?`,
    janela: 5,
    oque: () => "homicídios de moradores por ano",
    comparar: "homicidios_taxa",
  },
  {
    serie: "ideb",
    titulo: "Escolas",
    pergunta: (l) => `As escolas de ${l} melhoraram no IDEB?`,
    janela: 10,
    oque: (s) => s.rotulo.replace("IDEB, ", "IDEB ").toLowerCase().replace("ideb", "IDEB"),
    comparar: "ideb",
  },
  {
    serie: "gasto_seguranca_estado",
    titulo: "Segurança",
    pergunta: () => "O governo do estado gasta mais ou menos com segurança?",
    janela: 5,
    oque: (_s, l) => `gasto do governo do estado com segurança por morador, em reais de ${l.reais_de}`,
  },
  {
    serie: "gasto_saude_prefeitura",
    titulo: "Saúde",
    pergunta: () => "A prefeitura gasta mais ou menos com saúde?",
    janela: 5,
    oque: (_s, l) => `gasto da prefeitura com saúde por morador, em reais de ${l.reais_de}`,
  },
  {
    serie: "gasto_saude_estado",
    titulo: "Saúde",
    pergunta: () => "O governo do estado gasta mais ou menos com saúde?",
    janela: 5,
    oque: (_s, l) => `gasto do governo do estado com saúde por morador, em reais de ${l.reais_de}`,
  },
  {
    serie: "gasto_educacao_prefeitura",
    titulo: "Escolas",
    pergunta: () => "A prefeitura gasta mais ou menos com educação?",
    janela: 5,
    oque: (_s, l) => `gasto da prefeitura com educação por morador, em reais de ${l.reais_de}`,
  },
  {
    serie: "pib",
    titulo: "Economia",
    pergunta: (l) => `A economia de ${l} cresceu?`,
    janela: 5,
    oque: (_s, l) => `PIB em reais de ${l.reais_de}, descontada a inflação`,
  },
];

export function formatarValor(s: Pick<SerieTempo, "id" | "unidade" | "decimais">, v: number): string {
  if (s.unidade.startsWith("R$")) {
    if (Math.abs(v) >= 1e9) return `R$ ${(v / 1e9).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} bi`;
    if (Math.abs(v) >= 1e6) return `R$ ${(v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
    return `R$ ${v.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
  }
  return v.toLocaleString("pt-BR", { minimumFractionDigits: s.decimais, maximumFractionDigits: s.decimais });
}

/** O ponto do começo da janela: o ano exato, ou o primeiro depois dele. */
export function inicioDaJanela(pontos: PontoAno[], janela: number): PontoAno | null {
  if (pontos.length < 2) return null;
  const fim = pontos[pontos.length - 1];
  const ini = pontos.find((p) => p.ano >= fim.ano - janela);
  return ini && ini.ano < fim.ano ? ini : null;
}

const ultimo = (p: PontoAno[]) => p[p.length - 1];

export function gerarDescobertas(linha: TempoDoLugar, lugar: string, nomeEstado = "estado"): Descoberta[] {
  const porId = new Map(linha.series.map((s) => [s.id, s]));
  const saida: Descoberta[] = [];
  for (const r of REGRAS) {
    const s = porId.get(r.serie);
    if (!s) continue;
    const ini = inicioDaJanela(s.pontos, r.janela);
    if (!ini) continue;
    const fim = ultimo(s.pontos);
    const frase = `${formatarValor(s, ini.valor)} em ${ini.ano}, ${formatarValor(s, fim.valor)} em ${fim.ano}`;
    let detalhe = r.oque(s, linha);
    const c = r.comparar ? porId.get(r.comparar) : undefined;
    if (c) {
      const comps = c.comparacoes
        .map((cmp) => {
          const p = cmp.pontos.find((x) => x.ano === fim.ano);
          return p ? `${cmp.rotulo === "estado" ? nomeEstado : cmp.rotulo}: ${formatarValor(c, p.valor)}` : null;
        })
        .filter(Boolean);
      const proprio = c !== s ? c.pontos.find((x) => x.ano === fim.ano) : null;
      const base = proprio ? `${formatarValor(c, proprio.valor)} ${c.unidade} em ${fim.ano}` : null;
      const juntos = [base, ...comps].filter(Boolean).join("; ");
      if (juntos) detalhe += `. ${juntos}`;
    }
    saida.push({ serie: s.id, tema: s.tema, titulo: r.titulo, pergunta: r.pergunta(lugar), frase, detalhe: `${detalhe}.` });
  }
  return saida;
}
