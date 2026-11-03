import { describe, expect, it } from "vitest";
import { compararVisita, dataCurta, hojeISO, lerVisita } from "@/lib/novidades-perfil";

const antes = {
  data: "2026-10-12",
  valores: { "presenca.total": 55, "presenca.votou": 30, projetos: 8, gastos: 1000, "votos.total": 90 },
};

describe("compararVisita", () => {
  it("na primeira visita não mostra nada", () => {
    expect(compararVisita(null, antes.valores)).toBeNull();
  });

  it("sem diferença, não mostra nada", () => {
    expect(compararVisita(antes, { ...antes.valores })).toBeNull();
  });

  it("marca os cartões que mudaram e resume o que dá para contar", () => {
    const r = compararVisita(antes, {
      "presenca.total": 59,
      "presenca.votou": 31,
      projetos: 9,
      gastos: 1000,
      "votos.total": 90,
    });
    expect(r?.cartoes.sort()).toEqual(["presenca", "projetos"]);
    expect(r?.linha).toBe("4 votações a mais, 1 projeto");
    expect(r?.desde).toBe("12/10");
  });

  it("ignora cartão que não existia na visita anterior", () => {
    expect(compararVisita(antes, { ...antes.valores, sancoes: 2 })).toBeNull();
  });

  it("gasto que mudou marca o cartão e entra na linha", () => {
    const r = compararVisita(antes, { ...antes.valores, gastos: 1500 });
    expect(r?.cartoes).toEqual(["gastos"]);
    expect(r?.linha).toBe("gastos do gabinete mudaram");
  });

  it("queda de valor marca o cartão sem inventar contagem", () => {
    const r = compararVisita(antes, { ...antes.valores, projetos: 7 });
    expect(r?.cartoes).toEqual(["projetos"]);
    expect(r?.linha).toBeNull();
  });
});

describe("lerVisita", () => {
  it("lê o que foi guardado", () => {
    expect(lerVisita(JSON.stringify(antes))).toEqual(antes);
  });
  it("lixo vira null", () => {
    expect(lerVisita(null)).toBeNull();
    expect(lerVisita("{")).toBeNull();
    expect(lerVisita('{"data":"ontem","valores":{}}')).toBeNull();
    expect(lerVisita('{"data":"2026-10-12","valores":3}')).toBeNull();
  });
  it("descarta valores que não são número", () => {
    const v = lerVisita('{"data":"2026-10-12","valores":{"a":1,"b":"x"}}');
    expect(v?.valores).toEqual({ a: 1 });
  });
});

describe("datas", () => {
  it("dataCurta", () => expect(dataCurta("2026-10-12")).toBe("12/10"));
  it("hojeISO usa o horário de Brasília", () => {
    expect(hojeISO(new Date("2026-11-03T01:00:00Z"))).toBe("2026-11-02");
  });
});
