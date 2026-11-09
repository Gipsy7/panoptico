/**
 * Camadas do mapa da home (protótipo A): o dinheiro da União (que a home já tinha) e os
 * indicadores dos estados, todos no mesmo formato, com os anos de cada um. Funções puras: a
 * escolha do ano, a comparação entre duas camadas (andam juntos ou não, sem dizer causa) e a
 * lista em ordem do maior para o menor (a ordem fica escrita; não há posição nem selo).
 */
import type { IndicadoresUfs } from "@/lib/api";
import { formatarReaisCompacto } from "@/lib/formato";

export type UfDinheiro = {
  uf: string;
  nome: string;
  arrecadacao: number | null;
  repasse: number | null;
  obrasParadas?: number | null;
};

export type Camada = {
  id: string;
  grupo: string;
  tema: string;
  rotulo: string;
  titulo: string;
  unidade: string;
  anos: number[];
  fonte: string;
  nota: string | null;
  /** Valor do estado no ano (ou no último ano com dado, sem `ano`). */
  valor: (uf: string, ano?: number | null) => number | null;
  formatar: (v: number) => string;
};

const num = (d: number) => (v: number) =>
  v.toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const reaisInteiros = (v: number) => `R$ ${v.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;

export function montarCamadas(ufs: UfDinheiro[], ind: IndicadoresUfs | null, anoDinheiro: number, fonteDinheiro: string, fonteObras: string | null): Camada[] {
  const porUf = new Map(ufs.map((u) => [u.uf, u]));
  const fixo = (f: (u: UfDinheiro) => number | null | undefined) => (uf: string, ano?: number | null) => {
    if (ano != null && ano !== anoDinheiro) return null;
    const u = porUf.get(uf);
    const v = u ? f(u) : null;
    return v == null || !Number.isFinite(v) ? null : v;
  };
  const dinheiro: Camada[] = [
    {
      id: "retorno",
      grupo: "Dinheiro da União",
      tema: "dinheiro",
      rotulo: "Volta a cada R$ 100",
      titulo: `Quanto a União repassou a cada R$ 100 arrecadados no estado, ${anoDinheiro}`,
      unidade: "reais a cada R$ 100",
      anos: [anoDinheiro],
      fonte: fonteDinheiro,
      nota: "Repasse ao governo do estado e às prefeituras dividido pela arrecadação federal no estado.",
      valor: fixo((u) => (u.arrecadacao && u.arrecadacao > 0 && u.repasse != null ? (u.repasse / u.arrecadacao) * 100 : null)),
      formatar: reaisInteiros,
    },
    {
      id: "arrecadado",
      grupo: "Dinheiro da União",
      tema: "dinheiro",
      rotulo: "Arrecadado",
      titulo: `Quanto a União arrecadou em cada estado, ${anoDinheiro}`,
      unidade: "reais",
      anos: [anoDinheiro],
      fonte: fonteDinheiro,
      nota: null,
      valor: fixo((u) => u.arrecadacao),
      formatar: formatarReaisCompacto,
    },
    {
      id: "repassado",
      grupo: "Dinheiro da União",
      tema: "dinheiro",
      rotulo: "Repassado",
      titulo: `Quanto a União repassou ao estado e às cidades, ${anoDinheiro}`,
      unidade: "reais",
      anos: [anoDinheiro],
      fonte: fonteDinheiro,
      nota: null,
      valor: fixo((u) => u.repasse),
      formatar: formatarReaisCompacto,
    },
  ];
  if (fonteObras) {
    dinheiro.push({
      id: "obras",
      grupo: "Dinheiro da União",
      tema: "obras",
      rotulo: "Obras paradas",
      titulo: "Obras federais paradas a cada 100 começadas e não terminadas",
      unidade: "a cada 100",
      anos: [],
      fonte: fonteObras,
      nota: "Paradas = paralisadas ou inacabadas; começadas e não terminadas = essas mais as em execução.",
      valor: (uf) => porUf.get(uf)?.obrasParadas ?? null,
      formatar: num(0),
    });
  }
  // A média de 3 anos serve à comparação cidade × estado no Mapa; aqui seria uma opção repetida.
  const indicadores: Camada[] = (ind?.indicadores ?? []).filter((i) => !i.id.endsWith("_media3")).map((i) => {
    const porUfAno = new Map(Object.entries(i.valores).map(([uf, pts]) => [uf, new Map(pts.map((p) => [p.ano, p.valor]))]));
    const fmt = i.unidade.startsWith("R$") ? reaisInteiros : i.unidade.startsWith("%") ? (v: number) => `${num(i.decimais)(v)}%` : num(i.decimais);
    return {
      id: i.id,
      grupo: i.grupo,
      tema: i.tema,
      rotulo: i.rotulo,
      titulo: i.titulo,
      unidade: i.unidade,
      anos: i.anos,
      fonte: i.fonte_nome,
      nota: i.nota,
      valor: (uf: string, ano?: number | null) => {
        const m = porUfAno.get(uf);
        if (!m || m.size === 0) return null;
        if (ano == null) return m.get(Math.max(...m.keys())) ?? null;
        return m.get(ano) ?? null;
      },
      formatar: fmt,
    };
  });
  return [...indicadores, ...dinheiro];
}

/** Ano usado pela camada: o escolhido, se ela tem; senão o último dela (null = sem anos). */
export function anoDaCamada(c: Camada, escolhido: number | null): number | null {
  if (c.anos.length === 0) return null;
  return escolhido != null && c.anos.includes(escolhido) ? escolhido : c.anos[c.anos.length - 1];
}

function postos(v: number[]): number[] {
  const ordem = v.map((x, i) => [x, i] as const).sort((a, b) => a[0] - b[0]);
  const r = new Array<number>(v.length);
  let k = 0;
  while (k < ordem.length) {
    let j = k;
    while (j + 1 < ordem.length && ordem[j + 1][0] === ordem[k][0]) j++;
    for (let t = k; t <= j; t++) r[ordem[t][1]] = (k + j) / 2;
    k = j + 1;
  }
  return r;
}

/** Correlação de postos (Spearman) entre dois conjuntos pareados; null com menos de 5 pares. */
export function correlacao(x: (number | null)[], y: (number | null)[]): number | null {
  const pares = x.map((v, i) => [v, y[i]] as const).filter((p): p is readonly [number, number] => p[0] != null && p[1] != null);
  if (pares.length < 5) return null;
  const rx = postos(pares.map((p) => p[0]));
  const ry = postos(pares.map((p) => p[1]));
  const m = (pares.length - 1) / 2;
  let n = 0;
  let dx = 0;
  let dy = 0;
  for (let i = 0; i < pares.length; i++) {
    n += (rx[i] - m) * (ry[i] - m);
    dx += (rx[i] - m) ** 2;
    dy += (ry[i] - m) ** 2;
  }
  return dx && dy ? n / Math.sqrt(dx * dy) : null;
}

/** Frase literal sobre o padrão, sem causa: "tendem a andar juntos", "sem padrão claro"... */
export function frasePadrao(r: number | null): string {
  if (r == null) return "poucos estados com os dois números para comparar";
  const a = Math.abs(r);
  if (a < 0.3) return "sem padrão claro entre os estados";
  const forte = a >= 0.6;
  if (r > 0) return forte ? "onde um é maior, o outro costuma ser maior" : "onde um é maior, o outro tende a ser maior";
  return forte ? "onde um é maior, o outro costuma ser menor" : "onde um é maior, o outro tende a ser menor";
}

/** Estados com valor, do maior para o menor (empate: nome); os sem dado no fim, em ordem de nome. */
export function ordenarDoMaior<T extends { nome: string; valor: number | null }>(lista: T[]): T[] {
  return [...lista].sort((a, b) => {
    if (a.valor == null && b.valor == null) return a.nome.localeCompare(b.nome, "pt-BR");
    if (a.valor == null) return 1;
    if (b.valor == null) return -1;
    return b.valor - a.valor || a.nome.localeCompare(b.nome, "pt-BR");
  });
}
