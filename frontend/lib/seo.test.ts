import { describe, expect, it } from "vitest";

import { ROBOS_BLOQUEADOS, ROBOS_DE_IA_LIBERADOS, caminhoRepresentantes, temFiltro } from "@/lib/seo";

describe("caminhoRepresentantes", () => {
  it("cidade com estado, em ordem fixa", () => {
    expect(caminhoRepresentantes({ municipio: "4205902", uf: "sc" })).toBe("/representantes?uf=SC&municipio=4205902");
  });
  it("usa o estado da API quando a busca só tem a cidade ou o CEP", () => {
    expect(caminhoRepresentantes({ municipio: "4205902" }, "SC")).toBe("/representantes?uf=SC&municipio=4205902");
    expect(caminhoRepresentantes({ cep: "89110000" }, "SC")).toBe("/representantes?uf=SC");
  });
  it("só estado, sem nada e valores inválidos", () => {
    expect(caminhoRepresentantes({ uf: "DF" })).toBe("/representantes?uf=DF");
    expect(caminhoRepresentantes({})).toBe("/representantes");
    expect(caminhoRepresentantes({ uf: "XYZ", municipio: "abc" })).toBe("/representantes");
  });
});

describe("temFiltro", () => {
  it("detecta filtro e ignora parâmetros pedidos", () => {
    expect(temFiltro({})).toBe(false);
    expect(temFiltro({ uf: "SC" })).toBe(true);
    expect(temFiltro({ pagina: "1" }, ["pagina"])).toBe(false);
    expect(temFiltro({ uf: "" })).toBe(false);
  });
});

describe("robôs", () => {
  it("nenhum robô fica nas duas listas", () => {
    const bloqueados = new Set(ROBOS_BLOQUEADOS.map((r) => r.toLowerCase()));
    expect(ROBOS_DE_IA_LIBERADOS.filter((r) => bloqueados.has(r.toLowerCase()))).toEqual([]);
  });
});
