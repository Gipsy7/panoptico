import { describe, expect, it } from "vitest";
import { MOTIVO_PADRAO, montarChecklist } from "@/lib/checklist-perfil";

describe("montarChecklist", () => {
  it("conta o que tem e o total", () => {
    const c = montarChecklist([
      { id: "a", rotulo: "A", tem: true, fonte: "Fonte A" },
      { id: "b", rotulo: "B", tem: false },
      { id: "c", rotulo: "C", tem: true, fonte: "Fonte C" },
    ]);
    expect(c.tem).toBe(2);
    expect(c.total).toBe(3);
    expect(c.resumo).toBe("2 de 3");
  });

  it("quem falta ganha o motivo padrão, ou o dado", () => {
    const c = montarChecklist([
      { id: "a", rotulo: "A", tem: false },
      { id: "b", rotulo: "B", tem: false, motivo: "A câmara não publica." },
    ]);
    expect(c.itens[0].motivo).toBe(MOTIVO_PADRAO);
    expect(c.itens[1].motivo).toBe("A câmara não publica.");
    expect(c.itens[0].fonte).toBeNull();
  });

  it("quem tem fica sem motivo e mantém a fonte e o destino", () => {
    const c = montarChecklist([{ id: "g", rotulo: "G", destino: "gastos", tem: true, fonte: "Câmara", motivo: "x" }]);
    expect(c.itens[0]).toMatchObject({ motivo: null, fonte: "Câmara", destino: "gastos" });
  });

  it("dado que não se aplica ao perfil fica fora da conta", () => {
    const c = montarChecklist([
      { id: "a", rotulo: "A", tem: true, fonte: "F" },
      { id: "b", rotulo: "B", tem: false, aplica: false },
    ]);
    expect(c.itens.map((i) => i.id)).toEqual(["a"]);
    expect(c.resumo).toBe("1 de 1");
  });

  it("lista vazia dá 0 de 0", () => {
    expect(montarChecklist([]).resumo).toBe("0 de 0");
  });
});
