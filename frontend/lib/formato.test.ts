import { describe, expect, it } from "vitest";
import {
  MESES,
  formatarCep,
  formatarData,
  formatarGastos,
  formatarPosse,
  formatarReais,
  formatarReaisCompacto,
} from "@/lib/formato";

// O Intl separa "R$" do número com espaço não separável ( ); a versão do ICU pode variar
// entre Windows e Ubuntu, então o teste compara com o espaço normalizado.
const n = (s: string) => s.replace(/[  ]/g, " ");

describe("formatarCep", () => {
  it("devolve vazio para vazio", () => expect(formatarCep("")).toBe(""));
  it("entrada parcial não ganha hífen", () => {
    expect(formatarCep("123")).toBe("123");
    expect(formatarCep("12345")).toBe("12345");
  });
  it("seis dígitos já ganham hífen", () => expect(formatarCep("123456")).toBe("12345-6"));
  it("aplica a máscara em 8 dígitos", () => expect(formatarCep("01310100")).toBe("01310-100"));
  it("aceita entrada já mascarada", () => expect(formatarCep("01310-100")).toBe("01310-100"));
  it("descarta o que não é dígito", () => expect(formatarCep("a1b2.3-4 5/6")).toBe("12345-6"));
  it("corta além de 8 dígitos", () => expect(formatarCep("013101009999")).toBe("01310-100"));
});

describe("formatarData", () => {
  it("data sem hora não recua um dia por causa do fuso", () => {
    expect(formatarData("2022-10-02")).toBe("02/10/2022");
    expect(formatarData("2027-01-01")).toBe("01/01/2027");
  });
  it("ISO com hora usa America/Sao_Paulo", () => {
    // 01h UTC ainda é o dia anterior em Brasília (UTC-3)
    expect(formatarData("2022-10-02T01:00:00Z")).toBe("01/10/2022");
    expect(formatarData("2022-10-02T12:00:00Z")).toBe("02/10/2022");
  });
  it("limite da meia-noite de Brasília", () => {
    expect(formatarData("2022-10-02T03:00:00Z")).toBe("02/10/2022");
    expect(formatarData("2022-10-02T02:59:59Z")).toBe("01/10/2022");
  });
});

describe("formatarPosse", () => {
  it("dia 1 vira 1º", () => expect(formatarPosse("2027-02-01")).toBe("1º/2/2027"));
  it("outros dias não têm zero à esquerda nem ordinal", () => {
    expect(formatarPosse("2027-02-15")).toBe("15/2/2027");
    expect(formatarPosse("2027-12-05")).toBe("5/12/2027");
  });
  it("dia 11 não é confundido com dia 1", () => expect(formatarPosse("2027-02-11")).toBe("11/2/2027"));
});

describe("formatarReais", () => {
  it("duas casas decimais por padrão", () => {
    expect(n(formatarReais(1234.5))).toBe("R$ 1.234,50");
    expect(n(formatarReais(0))).toBe("R$ 0,00");
  });
  it("curto tira os centavos", () => {
    expect(n(formatarReais(1234.5, true))).toBe("R$ 1.235");
    expect(n(formatarReais(0, true))).toBe("R$ 0");
  });
  it("negativo leva o sinal antes do R$", () => expect(n(formatarReais(-1234.5))).toBe("-R$ 1.234,50"));
  it("milhão e bilhão com separador de milhar", () => {
    expect(n(formatarReais(1234567.891))).toBe("R$ 1.234.567,89");
    expect(n(formatarReais(2_500_000_000))).toBe("R$ 2.500.000.000,00");
  });
  it("usa espaço não separável entre R$ e o número", () => {
    expect(formatarReais(10)).toMatch(/^R\$[  ]10,00$/);
  });
});

describe("formatarReaisCompacto", () => {
  it("abrevia mil, milhão e bilhão", () => {
    expect(n(formatarReaisCompacto(1500))).toBe("R$ 1,5 mil");
    expect(n(formatarReaisCompacto(1_234_567))).toBe("R$ 1,2 mi");
    expect(n(formatarReaisCompacto(1_200_000_000))).toBe("R$ 1,2 bi");
  });
  it("valores pequenos e zero ficam por extenso", () => {
    expect(n(formatarReaisCompacto(0))).toBe("R$ 0");
    expect(n(formatarReaisCompacto(999))).toBe("R$ 999");
  });
  it("negativo mantém o sinal", () => expect(n(formatarReaisCompacto(-2_500_000))).toBe("-R$ 2,5 mi"));
});

describe("formatarGastos", () => {
  it("zero vira texto, não R$ 0", () => {
    expect(formatarGastos(0)).toBe("Nenhum reembolso");
    expect(formatarGastos(0, true)).toBe("Nenhum reembolso");
  });
  it("valor positivo segue formatarReais", () => {
    expect(formatarGastos(1234.5)).toBe(formatarReais(1234.5));
    expect(formatarGastos(1234.5, true)).toBe(formatarReais(1234.5, true));
  });
  it("um centavo ainda é valor", () => {
    expect(n(formatarGastos(0.01))).toBe("R$ 0,01");
  });
});

describe("MESES", () => {
  it("tem 12 itens, de jan a dez", () => {
    expect(MESES).toHaveLength(12);
    expect(MESES[0]).toBe("jan");
    expect(MESES[11]).toBe("dez");
    expect(new Set(MESES).size).toBe(12);
  });
});
