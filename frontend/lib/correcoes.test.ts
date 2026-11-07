import { describe, expect, it } from "vitest";

import { correcoesParaCsv, destinoCorrecao, textoLinkCorrecao, type Correcao } from "./correcoes";

const c = (id: number, data: string, extra: Partial<Correcao> = {}): Correcao => ({
  id,
  data,
  dado: "Gastos em 2026",
  antes: "R$ 296,3 mil",
  depois: "R$ 288,4 mil",
  motivo: "Nota repetida",
  fonte: "Cota parlamentar",
  perfil_tipo: "parlamentar",
  perfil_id: "1",
  perfil_nome: "Fulano",
  ...extra,
});

describe("textoLinkCorrecao", () => {
  it("usa singular e plural", () => {
    expect(textoLinkCorrecao(1)).toBe("Este perfil teve 1 correção");
    expect(textoLinkCorrecao(3)).toBe("Este perfil teve 3 correções");
  });
});

describe("destinoCorrecao", () => {
  it("aponta para a linha mais recente", () => {
    expect(destinoCorrecao([c(1, "2026-09-28"), c(2, "2026-10-29")])).toBe("/sobre-as-fontes#correcao-2");
  });
  it("sem itens, a seção", () => {
    expect(destinoCorrecao([])).toBe("/sobre-as-fontes#correcoes");
  });
});

describe("correcoesParaCsv", () => {
  it("escreve cabeçalho e linhas", () => {
    const csv = correcoesParaCsv([c(1, "2026-10-29")]);
    expect(csv.split("\r\n")[0]).toBe("data,dado,antes,depois,fonte,motivo,perfil");
    expect(csv.split("\r\n")[1]).toBe("2026-10-29,Gastos em 2026,\"R$ 296,3 mil\",\"R$ 288,4 mil\",Cota parlamentar,Nota repetida,Fulano");
  });
  it("escapa aspas e neutraliza fórmulas", () => {
    const csv = correcoesParaCsv([c(1, "2026-10-29", { motivo: '=1+1 "x"', antes: "-5" })]);
    expect(csv).toContain("\"'=1+1 \"\"x\"\"\"");
    expect(csv).toContain(",'-5,");
  });
});
