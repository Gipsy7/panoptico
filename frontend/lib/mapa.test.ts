import { describe, expect, it } from "vitest";
import { classe, numeroOuSemDado, quantis, reaisOuSemDado, reaisPorHabitante } from "@/lib/mapa";

const n = (s: string) => s.replace(/[  ]/g, " ");

describe("quantis", () => {
  it("lista vazia dá lista vazia", () => expect(quantis([])).toEqual([]));
  it("só ausentes dá lista vazia", () => expect(quantis([null, undefined, NaN, Infinity])).toEqual([]));
  it("devolve n-1 cortes", () => {
    expect(quantis([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])).toEqual([3, 5, 7, 9]);
  });
  it("ordena antes de cortar", () => {
    expect(quantis([10, 1, 9, 2, 8, 3, 7, 4, 6, 5])).toEqual([3, 5, 7, 9]);
  });
  it("ignora null, undefined e não finitos", () => {
    expect(
      quantis([1, null, 2, undefined, 3, NaN, 4, Infinity, 5, -Infinity, 6, 7, 8, 9, 10]),
    ).toEqual([3, 5, 7, 9]);
  });
  it("zero conta como valor", () => {
    expect(quantis([0, 0, 0, 0, 0])).toEqual([0, 0, 0, 0]);
  });
  it("valores repetidos geram cortes repetidos", () => {
    expect(quantis([5, 5, 5, 5, 5, 5, 5, 5, 5, 5])).toEqual([5, 5, 5, 5]);
  });
  it("um único valor repete o corte", () => expect(quantis([7])).toEqual([7, 7, 7, 7]));
  it("n diferente de 5", () => {
    expect(quantis([1, 2, 3, 4, 5, 6], 3)).toEqual([3, 5]);
    expect(quantis([1, 2, 3, 4], 2)).toEqual([3]);
    expect(quantis([1, 2, 3], 1)).toEqual([]);
  });
  it("não altera a lista de entrada", () => {
    const entrada = [3, 1, 2];
    quantis(entrada);
    expect(entrada).toEqual([3, 1, 2]);
  });
});

describe("classe", () => {
  const cortes = [3, 5, 7, 9];
  it("null, undefined e não finitos são 0 (sem dado)", () => {
    expect(classe(null, cortes)).toBe(0);
    expect(classe(undefined, cortes)).toBe(0);
    expect(classe(NaN, cortes)).toBe(0);
    expect(classe(Infinity, cortes)).toBe(0);
  });
  it("zero é dado, não ausência", () => expect(classe(0, cortes)).toBe(1));
  it("abaixo do primeiro corte é 1", () => expect(classe(2.99, cortes)).toBe(1));
  it("o valor exatamente no corte sobe de classe", () => {
    expect(classe(3, cortes)).toBe(2);
    expect(classe(5, cortes)).toBe(3);
    expect(classe(7, cortes)).toBe(4);
    expect(classe(9, cortes)).toBe(5);
  });
  it("logo abaixo de cada corte fica na classe anterior", () => {
    expect(classe(4.99, cortes)).toBe(2);
    expect(classe(6.99, cortes)).toBe(3);
    expect(classe(8.99, cortes)).toBe(4);
  });
  it("acima do último corte fica em 5", () => expect(classe(1e9, cortes)).toBe(5));
  it("negativo cai na classe 1", () => expect(classe(-10, cortes)).toBe(1));
  it("sem cortes tudo é classe 1", () => expect(classe(42, [])).toBe(1));
  it("nunca passa de 5 mesmo com mais cortes", () => {
    expect(classe(100, [1, 2, 3, 4, 5, 6, 7])).toBe(5);
  });
  it("combina com quantis", () => {
    const c = quantis([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    expect(classe(1, c)).toBe(1);
    expect(classe(10, c)).toBe(5);
  });
});

describe("reaisOuSemDado", () => {
  it("ausente vira 'sem dado'", () => {
    expect(reaisOuSemDado(null)).toBe("sem dado");
    expect(reaisOuSemDado(undefined)).toBe("sem dado");
    expect(reaisOuSemDado(NaN)).toBe("sem dado");
  });
  it("zero é valor, não 'sem dado'", () => expect(n(reaisOuSemDado(0))).toBe("R$ 0"));
  it("formata compacto", () => expect(n(reaisOuSemDado(1_200_000_000))).toBe("R$ 1,2 bi"));
});

describe("reaisPorHabitante", () => {
  it("ausente vira 'sem dado'", () => {
    expect(reaisPorHabitante(null)).toBe("sem dado");
    expect(reaisPorHabitante(undefined)).toBe("sem dado");
    expect(reaisPorHabitante(Infinity)).toBe("sem dado");
  });
  it("arredonda e usa ponto de milhar", () => {
    expect(reaisPorHabitante(1234.6)).toBe("R$ 1.235");
    expect(reaisPorHabitante(999.4)).toBe("R$ 999");
  });
  it("zero é valor", () => expect(reaisPorHabitante(0)).toBe("R$ 0"));
});

describe("numeroOuSemDado", () => {
  it("ausente vira 'sem dado'", () => {
    expect(numeroOuSemDado(null)).toBe("sem dado");
    expect(numeroOuSemDado(undefined)).toBe("sem dado");
    expect(numeroOuSemDado(NaN)).toBe("sem dado");
  });
  it("arredonda e usa ponto de milhar", () => {
    expect(numeroOuSemDado(1234567.4)).toBe("1.234.567");
    expect(numeroOuSemDado(12.5)).toBe("13");
  });
  it("zero é valor", () => expect(numeroOuSemDado(0)).toBe("0"));
});
