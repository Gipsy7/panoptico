import { describe, expect, it } from "vitest";

import { consultaDosCampos, enderecoComConsulta, textoAtivos } from "@/lib/filtros";

describe("consultaDosCampos", () => {
  it("tira valores vazios e os que estão no padrão", () => {
    const campos: [string, string][] = [
      ["busca", "  "],
      ["uf", "SC"],
      ["ordenar", "nome"],
      ["ordem", "desc"],
      ["ano", "2026"],
    ];
    expect(consultaDosCampos(campos, { ordenar: "nome", ano: "2026" })).toBe("uf=SC&ordem=desc");
    expect(consultaDosCampos([])).toBe("");
  });
});

describe("enderecoComConsulta", () => {
  it("junta caminho, consulta e âncora", () => {
    expect(enderecoComConsulta("/eleito/1#ver-agenda", "a=1", "ver-agenda")).toBe("/eleito/1?a=1#ver-agenda");
    expect(enderecoComConsulta("/parlamentares", "")).toBe("/parlamentares");
  });
});

describe("textoAtivos", () => {
  it("conta no singular e no plural", () => {
    expect(textoAtivos(0)).toBeNull();
    expect(textoAtivos(1)).toBe("1 filtro ativo");
    expect(textoAtivos(3)).toBe("3 filtros ativos");
  });
});
