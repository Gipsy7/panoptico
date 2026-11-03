import { describe, expect, it } from "vitest";
import { gerarFrases, montarTextoCompartilhar } from "@/lib/resumo-frases";

const n = (s: string) => s.replace(/[  ]/g, " ");

const completo = {
  presenca: { ano: 2026, votou: 31, total_votacoes: 59, media_casa_percentual: 78.8 },
  projetos: { desde: "2019-02-01", primeiro_autor: 9, media_casa_primeiro_autor: 6.2 },
  gastos: { ano: 2026, total: 312000, media_casa: 388000 },
  governo: { iguais: 71, total: 98, media_percentual: 69 },
};

describe("gerarFrases", () => {
  it("gera uma frase por cartão, com número literal e média da Casa", () => {
    const f = gerarFrases(completo).map(n);
    expect(f).toHaveLength(4);
    expect(f[0]).toBe("Votou em 31 de 59 votações do Plenário; em média, a Casa votou em 78,8% delas.");
    expect(f[1]).toBe("Apresentou 9 projetos como autor principal desde 2019; a média da Casa foi 6,2.");
    expect(f[2]).toContain("Gastou R$");
    expect(f[2]).toContain("a média da Casa foi R$");
    expect(f[3]).toBe("Votou como o Governo orientou em 71 de 98 votações; em média, a Casa votou assim em 69%.");
  });

  it("não inventa frase para cartão que não existe", () => {
    expect(gerarFrases({})).toEqual([]);
    expect(gerarFrases({ presenca: { ano: 2026, votou: 0, total_votacoes: 0, media_casa_percentual: null } })).toEqual(
      [],
    );
    expect(gerarFrases({ governo: { iguais: 0, total: 0, media_percentual: null } })).toEqual([]);
    expect(gerarFrases({ projetos: completo.projetos })).toHaveLength(1);
  });

  it("omite a média quando a fonte não a traz", () => {
    const f = gerarFrases({ presenca: { ano: 2026, votou: 5, total_votacoes: 10, media_casa_percentual: null } });
    expect(f).toEqual(["Votou em 5 de 10 votações do Plenário."]);
  });

  it("diz o que o zero significa nos gastos e usa singular", () => {
    const f = gerarFrases({
      gastos: { ano: 2026, total: 0, media_casa: 100000 },
      projetos: { desde: "2023-02-01", primeiro_autor: 1, media_casa_primeiro_autor: 3 },
    }).map(n);
    expect(f[0]).toContain("Apresentou 1 projeto como autor");
    expect(f[1]).toContain("Não tem reembolso da verba do gabinete em 2026");
  });
});

describe("montarTextoCompartilhar", () => {
  it("junta cabeçalho, frases, fonte com data e link", () => {
    const t = montarTextoCompartilhar({
      cabecalho: "Fulano, Câmara, em 2026:",
      frases: ["A.", "B."],
      fontes: ["Câmara dos Deputados"],
      atualizadoEm: "2026-11-02",
      url: "https://panoptico.social.br/parlamentar/1",
    });
    expect(t).toBe(
      "Fulano, Câmara, em 2026:\n• A.\n• B.\nFonte: Câmara dos Deputados · atualizado em 02/11/2026\nhttps://panoptico.social.br/parlamentar/1",
    );
  });

  it("sem data, não escreve data", () => {
    const t = montarTextoCompartilhar({ cabecalho: "X", frases: ["A."], fontes: ["F"], atualizadoEm: null, url: "u" });
    expect(t).toContain("Fonte: F\nu");
  });
});
