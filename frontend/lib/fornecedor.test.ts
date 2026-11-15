import { describe, expect, it } from "vitest";

import { type FichaFornecedor, digitosDoCnpj, fichaTemDado, formatarCnpj, frasesDaFicha, hrefFornecedor } from "./fornecedor";

const bloco = { recorte: "r", fonte_nome: "f", atualizado_em: null };

function ficha(parcial: Partial<FichaFornecedor> = {}): FichaFornecedor {
  return {
    cnpj: "02012862000160",
    nome: "EMPRESA SA",
    nome_omitido: false,
    nome_fantasia: null,
    uf: "SP",
    situacao: "ativa",
    cadastro_referencia: "2026-10",
    gabinetes: { ...bloco, por_ano: [], ano_da_lista: null, maiores: [], limite_da_lista: 20 },
    prefeituras: { ...bloco, por_ano: [], ano_da_lista: null, maiores: [], limite_da_lista: 20 },
    pncp: { ...bloco, por_ano: [] },
    emendas: { ...bloco, pagas_por_ano: [], convenios: { quantidade: 0, valor_repassado: 0 } },
    sancoes: { ...bloco, itens: [] },
    ...parcial,
  };
}

describe("endereço e CNPJ", () => {
  it("só CNPJ por inteiro vira link; CPF nunca", () => {
    expect(hrefFornecedor("02.012.862/0001-60")).toBe("/fornecedor/02012862000160");
    expect(hrefFornecedor("02012862000160")).toBe("/fornecedor/02012862000160");
    expect(hrefFornecedor("123.456.789-01")).toBeNull();
    expect(hrefFornecedor("")).toBeNull();
    expect(hrefFornecedor(null)).toBeNull();
    expect(digitosDoCnpj("abc")).toBeNull();
  });

  it("formata com pontos, barra e traço", () => {
    expect(formatarCnpj("02012862000160")).toBe("02.012.862/0001-60");
    expect(formatarCnpj("123")).toBe("123");
  });
});

describe("frasesDaFicha", () => {
  it("escreve o número em palavras, com singular e plural", () => {
    const f = ficha({
      gabinetes: {
        ...bloco,
        por_ano: [{ ano: 2025, valor: 15831356.9, gabinetes: 461, lancamentos: 23830 }],
        ano_da_lista: 2025,
        maiores: [],
        limite_da_lista: 20,
      },
      prefeituras: {
        ...bloco,
        por_ano: [{ ano: 2025, valor: 6444.9, municipios: 1 }],
        ano_da_lista: 2025,
        maiores: [],
        limite_da_lista: 20,
      },
      pncp: { ...bloco, por_ano: [{ ano: 2025, valor: 2141.91, contratos: 1, municipios: 1 }] },
    });
    expect(frasesDaFicha(f)).toEqual({
      gabinetes: "461 gabinetes pagaram, pela cota parlamentar",
      prefeituras: "1 cidade com pagamento de prefeitura ou câmara",
      pncp: "1 contrato em 1 cidade",
      emendas: null,
      sancoes: "Sem registro no CEIS nem no CNEP",
    });
    expect(fichaTemDado(f)).toBe(true);
  });

  it("emendas: pagas valem primeiro; sem elas, os convênios", () => {
    const pagas = ficha({
      emendas: { ...bloco, pagas_por_ano: [{ ano: 2026, valor: 400, autores: 2 }], convenios: { quantidade: 3, valor_repassado: 9 } },
    });
    expect(frasesDaFicha(pagas).emendas).toBe("Favorecida em emendas de 2 autores");
    const soConvenio = ficha({ emendas: { ...bloco, pagas_por_ano: [], convenios: { quantidade: 1, valor_repassado: 9 } } });
    expect(frasesDaFicha(soConvenio).emendas).toBe("1 convênio de emenda");
  });

  it("sanções: conta os registros, sem adjetivo", () => {
    const item = { cadastro: "CEIS", categoria: "Suspensão", abrangencia: null, orgao: null, inicio: null, fim: null, processo: null };
    expect(frasesDaFicha(ficha({ sancoes: { ...bloco, itens: [item, item] } })).sancoes).toBe("2 registros");
    expect(fichaTemDado(ficha())).toBe(false);
  });
});
