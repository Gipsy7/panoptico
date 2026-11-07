import { describe, expect, it } from "vitest";

import { comArtigo, composicaoDoAno, contagemLeis, larguraBarra, origensDaLei } from "@/lib/normas";

describe("comArtigo", () => {
  it("usa 'da' para PEC e medida provisória e 'do' para projeto de lei", () => {
    expect(comArtigo("PEC 45/2019")).toBe("da PEC 45/2019");
    expect(comArtigo("MPV 1300/2025")).toBe("da MPV 1300/2025");
    expect(comArtigo("PLP 68/2024")).toBe("do PLP 68/2024");
    expect(comArtigo("PLS 559/2013")).toBe("do PLS 559/2013");
  });
});

describe("origensDaLei", () => {
  it("junta a mesma identificação das duas Casas e fica com a que tem página", () => {
    expect(
      origensDaLei([
        { casa: "senado", id_externo: "164914", identificacao: "PLP 68/2024", link: null },
        { casa: "camara", id_externo: "2430143", identificacao: "PLP 68/2024", link: "/projeto/camara/2430143" },
        { casa: "senado", id_externo: "1", identificacao: null, link: null },
      ]),
    ).toEqual([{ identificacao: "PLP 68/2024", link: "/projeto/camara/2430143" }]);
  });
});

describe("contagens", () => {
  it("escreve a contagem e a composição do ano só com o que existe", () => {
    expect(contagemLeis(1)).toBe("1 lei");
    expect(contagemLeis(1255)).toBe("1.255 leis");
    expect(composicaoDoAno({ leis: 239, leis_complementares: 13, emendas_constitucionais: 3 })).toBe(
      "239 leis ordinárias, 13 leis complementares e 3 emendas à Constituição",
    );
    expect(composicaoDoAno({ leis: 0, leis_complementares: 1, emendas_constitucionais: 0 })).toBe("1 lei complementar");
  });

  it("barra proporcional ao maior ano, sem sumir", () => {
    expect(larguraBarra(301, 301)).toBe(100);
    expect(larguraBarra(1, 301)).toBe(2);
    expect(larguraBarra(0, 301)).toBe(0);
  });
});
