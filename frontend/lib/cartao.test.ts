import { describe, expect, it } from "vitest";
import {
  escolherNumeros,
  lerFormato,
  mediaEmContagem,
  montarEleito,
  montarFederal,
  montarLocal,
  quebrarNome,
} from "@/lib/cartao";

const base = { nome: "Fulana", casa: "camara" as const, cargo: "Deputada federal", partido: "XYZ", uf: "SC", foto: null, fonte: "Fonte: Câmara" };

describe("cartão do perfil", () => {
  it("formato desconhecido cai no Feed", () => {
    expect(lerFormato("stories")).toBe("stories");
    expect(lerFormato("x")).toBe("feed");
    expect(lerFormato(null)).toBe("feed");
  });

  it("converte a média em percentual para contagem", () => {
    expect(mediaEmContagem(88.1, 118)).toBe(104);
    expect(mediaEmContagem(0, 50)).toBe(0);
  });

  it("federal: presença é o número grande, com a média ao lado", () => {
    const d = montarFederal({
      ...base,
      presenca: { ano: 2026, votou: 112, total_votacoes: 118, media_casa_percentual: 88.1 },
      gastos: { ano: 2026, total: 312000, media_casa: 388000 },
      projetos: { desde: "2019-02-01", primeiro_autor: 9, media_casa_primeiro_autor: 6.2 },
      governo: { iguais: 71, total: 98, media_percentual: 65.3 },
    });
    expect(d.principal?.valor).toBe("112");
    expect(d.principal?.complemento).toBe("das 118 votações de 2026");
    expect(d.principal?.media).toBe("Média da Câmara: 104 de 118");
    expect(d.outros).toHaveLength(3);
    expect(d.outros.every((o) => o.media !== undefined)).toBe(true);
    expect(d.outros[2].media).toBe("Média da Câmara: 64 de 98");
    expect(d.contexto).toBe("Deputada federal · XYZ · SC");
    expect(d.frase).toBeNull();
  });

  it("federal sem votações: o primeiro número com média assume, sem inventar", () => {
    const d = montarFederal({ ...base, gastos: { ano: 2026, total: 0, media_casa: 1000 } });
    expect(d.principal?.valor).toBe("Nenhum reembolso");
    expect(d.principal?.media).toContain("Média da Câmara");
    expect(d.outros).toHaveLength(0);
  });

  it("federal sem nenhum número: só uma frase factual", () => {
    const d = montarFederal(base);
    expect(d.principal).toBeNull();
    expect(d.frase).toBe("Deputada federal por SC.");
  });

  it("local: presença com média; projetos ficam sem média", () => {
    const d = montarLocal({
      ...base,
      casa: "assembleia",
      cargo: "Deputado estadual",
      presenca: { sessoes: 236, presencas: 126, media_casa: 70.2 },
      projetos: 45,
      proposicoes: 206,
    });
    expect(d.principal?.valor).toBe("126");
    expect(d.principal?.media).toBe("Média da Assembleia: 166 de 236");
    const proj = d.outros.find((o) => o.rotulo.startsWith("Projetos"));
    expect(proj?.media).toBeUndefined();
    expect(proj?.nota).toBe("206 proposições no total");
  });

  it("local sem número com média: o primeiro vira principal", () => {
    const d = montarLocal({ ...base, casa: "camara", projetos: 3, proposicoes: 4 });
    expect(d.principal?.valor).toBe("3");
    expect(d.principal?.media).toBeUndefined();
  });

  it("eleito: votos sem média e frase quando não há número", () => {
    const d = montarEleito({
      nome: "Beltrano",
      cargo: "Vereador",
      unidade: "Gaspar",
      partido: "ABC",
      uf: "SC",
      situacao: "Eleito por QP",
      anoEleicao: 2024,
      foto: null,
      fonte: "Fonte: TSE",
      votos: 4641,
    });
    expect(d.principal?.valor).toBe("4.641");
    expect(d.principal?.media).toBeUndefined();
    const v = montarEleito({ ...{ nome: "B", cargo: "Prefeito", unidade: null, partido: null, uf: "SC", situacao: "Eleito", anoEleicao: 2024, foto: null, fonte: "x" } });
    expect(v.principal).toBeNull();
    expect(v.frase).toBe("Eleito em 2024 para prefeito.");
  });

  it("escolherNumeros sem candidatos", () => {
    expect(escolherNumeros([])).toEqual({ principal: null, outros: [] });
  });

  it("quebra o nome em duas linhas", () => {
    expect(quebrarNome("Adail")).toEqual(["Adail"]);
    expect(quebrarNome("Altair Silva")).toEqual(["Altair Silva"]);
    expect(quebrarNome("Carlos Chiodini")).toEqual(["Carlos", "Chiodini"]);
    expect(quebrarNome("Maria da Silva Souza")).toEqual(["Maria da", "Silva Souza"]);
  });
});

describe("escolherNumeros sem média", () => {
  it("não põe zero como número principal", () => {
    const r = escolherNumeros([
      { rotulo: "Projetos", valor: "0" },
      { rotulo: "Salário", valor: "R$ 12 mil" },
    ]);
    expect(r.principal?.rotulo).toBe("Salário");
  });
  it("só zeros: sem principal", () => {
    expect(escolherNumeros([{ rotulo: "Projetos", valor: "0" }]).principal).toBeNull();
  });
});
