import { describe, expect, it } from "vitest";

import {
  GRADE_UFS,
  NOMES_UF,
  type PaginaContada,
  type Representante,
  baseDeComparacao,
  cargosPresentes,
  diaDeMaiorMedia,
  escalaDoEixo,
  faixaDoMapa,
  filtrarRepresentantes,
  nomeDaPagina,
  ordenarPaginas,
  sinal,
  textoDaDiferenca,
} from "@/lib/painel-acessos";

const pag = (chave: string, atual: number, anterior: number, conteudo = true): PaginaContada => ({
  chave,
  atual,
  anterior,
  conteudo,
});

describe("diferenças em texto", () => {
  it("diz a mais, a menos ou igual, sem juízo", () => {
    expect(textoDaDiferenca(52, 40, "que ontem")).toBe("12 a mais que ontem");
    expect(textoDaDiferenca(3, 10, "que ontem")).toBe("7 a menos que ontem");
    expect(textoDaDiferenca(5, 5, "que ontem")).toBe("igual que ontem");
    expect(sinal(12)).toBe("+12");
    expect(sinal(-3)).toBe("−3");
    expect(sinal(0)).toBe("0");
  });
  it("a base de comparação", () => {
    expect(baseDeComparacao(1)).toBe("que ontem");
    expect(baseDeComparacao(7)).toBe("que nos 7 dias anteriores");
  });
});

describe("ordenarPaginas", () => {
  const lista = [
    pag("/projetos", 9, 4),
    pag("/comparar", 2, 6),
    pag("/privacidade", 1, 0, false),
    pag("/segundo-turno", 0, 3),
  ];
  const fixas = ["/projetos", "/comparar", "/segundo-turno", "/perguntas"];
  it("mais vistas", () => {
    expect(ordenarPaginas("mais", lista, fixas).map((p) => p.chave)).toEqual(["/projetos", "/comparar", "/privacidade"]);
  });
  it("menos vistas só olha páginas de conteúdo", () => {
    expect(ordenarPaginas("menos", lista, fixas).map((p) => p.chave)).toEqual(["/comparar", "/projetos"]);
  });
  it("em alta: só quem subiu", () => {
    expect(ordenarPaginas("alta", lista, fixas).map((p) => p.chave)).toEqual(["/projetos", "/privacidade"]);
  });
  it("sem visita: rotas fixas sem vista no período, com o que tinham antes", () => {
    const z = ordenarPaginas("zero", lista, fixas);
    expect(z.map((p) => [p.chave, p.anterior])).toEqual([["/segundo-turno", 3], ["/perguntas", 0]]);
  });
  it("busca pelo nome em português", () => {
    expect(ordenarPaginas("mais", lista, fixas, "projetos de lei").map((p) => p.chave)).toEqual(["/projetos"]);
  });
  it("nome da página", () => {
    expect(nomeDaPagina("/eleito/[id]")).toBe("Perfil de eleito");
    expect(nomeDaPagina("/nova")).toBe("/nova");
  });
});

describe("representantes", () => {
  const r = (nome: string, cargo: string, uf: string, atual: number): Representante => ({
    chave: nome, nome, cargo, uf, partido: null, atual, anterior: 0,
  });
  const reps = [r("A", "Vereador", "SC", 3), r("B", "Senador", "SC", 9), r("C", "Vereador", "PR", 5)];
  it("cargos por abertura e filtros", () => {
    expect(cargosPresentes(reps)).toEqual(["Senador", "Vereador"]);
    expect(filtrarRepresentantes(reps, "todos", "todas").map((x) => x.nome)).toEqual(["B", "C", "A"]);
    expect(filtrarRepresentantes(reps, "Vereador", "SC").map((x) => x.nome)).toEqual(["A"]);
  });
});

describe("mapa e eixo", () => {
  it("as 27 UFs têm posição única e nome", () => {
    const ufs = Object.keys(GRADE_UFS);
    expect(ufs).toHaveLength(27);
    expect(new Set(ufs.map((u) => GRADE_UFS[u].join(","))).size).toBe(27);
    expect(ufs.every((u) => NOMES_UF[u])).toBe(true);
  });
  it("faixas em quartos do maior", () => {
    expect([0, 1, 30, 60, 100].map((t) => faixaDoMapa(t, 100))).toEqual([0, 1, 2, 3, 4]);
    expect(faixaDoMapa(5, 0)).toBe(0);
  });
  it("escala do eixo", () => {
    expect(escalaDoEixo(0)).toEqual({ topo: 4, passo: 1 });
    expect(escalaDoEixo(87)).toEqual({ topo: 100, passo: 25 });
    expect(escalaDoEixo(150).topo).toBeGreaterThanOrEqual(150);
  });
  it("dia da semana de maior média", () => {
    expect(diaDeMaiorMedia([{ dia: "segunda", dias: 1, media: 0 }])).toBeNull();
    expect(diaDeMaiorMedia([{ dia: "segunda", dias: 1, media: 3 }, { dia: "terça", dias: 2, media: 8 }])?.dia).toBe("terça");
  });
});
