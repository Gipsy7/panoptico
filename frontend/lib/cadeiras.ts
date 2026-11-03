/** Lógica pura das cadeiras do plenário (sem React): agrupar por partido e posicionar as bolinhas. */

export type ItemBancada = { partido: string; n: number };
export type Ponto = { x: number; y: number; fileira: number; angulo: number };
export type Voto = "sim" | "nao" | "outro";

/** Soma n de cada partido, ignora zeros e ordena por n decrescente e sigla. */
export function agrupar(itens: ItemBancada[]): ItemBancada[] {
  const soma = new Map<string, number>();
  for (const { partido, n } of itens) {
    if (n > 0) soma.set(partido, (soma.get(partido) ?? 0) + n);
  }
  return [...soma.entries()]
    .map(([partido, n]) => ({ partido, n }))
    .sort((a, b) => b.n - a.n || a.partido.localeCompare(b.partido, "pt-BR"));
}

export function totalDe(itens: ItemBancada[]): number {
  return itens.reduce((s, i) => s + i.n, 0);
}

/** Uma entrada por cadeira, partido a partido, na ordem dos itens. */
export function cadeirasPorPartido(itens: ItemBancada[]): string[] {
  return itens.flatMap(({ partido, n }) => Array.from({ length: n }, () => partido));
}

/** Uma entrada por cadeira: Sim, depois Não, depois outro. */
export function cadeirasPorVoto(sim: number, nao: number, outros: number): Voto[] {
  const fila = (v: Voto, n: number) => Array.from({ length: Math.max(0, n) }, () => v);
  return [...fila("sim", sim), ...fila("nao", nao), ...fila("outro", outros)];
}

/**
 * Posições das cadeiras num semicírculo em fileiras. Cada fileira recebe cadeiras em
 * proporção ao seu raio; os pontos saem ordenados da esquerda para a direita (pelo ângulo),
 * então cada partido ocupa uma fatia do semicírculo. Coordenadas em [0, largura] x [0, altura].
 */
export function layoutCadeiras(total: number, largura = 360): { pontos: Ponto[]; altura: number; raio: number } {
  if (total <= 0) return { pontos: [], altura: 0, raio: 0 };
  const fileiras = Math.max(1, Math.min(10, Math.round(Math.sqrt(total / 9))));
  const margem = largura * 0.03;
  const externo = largura / 2 - margem;
  const interno = externo * (fileiras === 1 ? 1 : 0.4);
  const passo = fileiras === 1 ? 0 : (externo - interno) / (fileiras - 1);
  const raios = Array.from({ length: fileiras }, (_, i) => interno + i * passo);
  const somaRaios = raios.reduce((a, b) => a + b, 0);

  // Maior resto: reparte `total` na proporção dos raios, sem perder nem sobrar cadeira.
  const exatas = raios.map((r) => (r / somaRaios) * total);
  const nas = exatas.map(Math.floor);
  let faltam = total - nas.reduce((a, b) => a + b, 0);
  const porResto = exatas.map((e, i) => ({ i, resto: e - nas[i] })).sort((a, b) => b.resto - a.resto);
  for (const { i } of porResto) {
    if (faltam <= 0) break;
    nas[i] += 1;
    faltam -= 1;
  }

  const pontos: Ponto[] = [];
  raios.forEach((r, fileira) => {
    const q = nas[fileira];
    for (let k = 0; k < q; k++) {
      const angulo = q === 1 ? Math.PI / 2 : Math.PI - (k * Math.PI) / (q - 1);
      pontos.push({
        x: largura / 2 + r * Math.cos(angulo),
        y: externo - r * Math.sin(angulo) + margem,
        fileira,
        angulo,
      });
    }
  });
  pontos.sort((a, b) => b.angulo - a.angulo || a.fileira - b.fileira);
  const raioBolinha = Math.max(1.6, Math.min(passo * 0.36, ((Math.PI * interno) / Math.max(1, nas[0])) * 0.36));
  return { pontos, altura: externo + margem * 2, raio: raioBolinha };
}

/** Texto para leitor de tela: "Câmara: 513 cadeiras. PL 90, PT 68 e outros 12 partidos." */
export function descricaoCadeiras(nome: string, itens: ItemBancada[], limite = 6): string {
  const lista = agrupar(itens);
  const total = totalDe(lista);
  if (total === 0) return `${nome}: sem dados de cadeiras.`;
  const mostrados = lista.slice(0, limite).map((i) => `${i.partido} ${i.n}`);
  const resto = lista.length - mostrados.length;
  const partes = resto > 0 ? `${mostrados.join(", ")} e mais ${resto} ${resto === 1 ? "partido" : "partidos"}` : mostrados.join(", ");
  return `${nome}: ${total} ${total === 1 ? "cadeira" : "cadeiras"}. ${partes}.`;
}

export function descricaoVotos(nome: string, sim: number, nao: number, outros: number): string {
  return `${nome}: ${sim} Sim, ${nao} Não e ${outros} com outro registro, em ${sim + nao + outros} cadeiras.`;
}
