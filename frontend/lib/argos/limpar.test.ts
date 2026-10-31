import { describe, expect, it } from "vitest";

import { MAX_FRASE, MAX_MENSAGEM, limpar, prepararConversa, soMarca } from "./limpar";

describe("limpar", () => {
  it.each([
    ["meu cep é 88340-000 e moro aqui", "meu cep é [removido] e moro aqui"],
    ["88340000", "[removido]"],
    ["cpf 123.456.789-09", "cpf [removido]"],
    ["cpf 12345678909", "cpf [removido]"],
    ["me liga (48) 99999-1234", "me liga [removido]"],
    ["fone 48999991234", "fone [removido]"],
    ["escreva para fulano@exemplo.com.br", "escreva para [removido]"],
    ["veja https://site.com/a?b=1 e www.x.com", "veja [removido] e [removido]"],
    ["protocolo 1234567", "protocolo [removido]"],
    ["deputados de SC em 2025", "deputados de SC em 2025"],
    ["  muitos    espaços  ", "muitos espaços"],
  ])("%s", (entrada, esperado) => {
    expect(limpar(entrada)).toBe(esperado);
  });

  it("corta no limite", () => {
    expect(limpar("a".repeat(900))).toHaveLength(MAX_FRASE);
    expect(limpar("b".repeat(900), MAX_MENSAGEM)).toHaveLength(MAX_MENSAGEM);
  });
});

describe("soMarca", () => {
  it("só dado pessoal não vale", () => {
    expect(soMarca(limpar("88340-000"))).toBe(true);
    expect(soMarca(limpar("cep: 88340-000?"))).toBe(false);
    expect(soMarca("gato")).toBe(false);
  });
});

describe("prepararConversa", () => {
  it("limpa, descarta vazias e fica com as últimas 30", () => {
    const msgs = Array.from({ length: 35 }, (_, i) => ({ autor: "cidadao" as const, texto: `fala ${i} 88340-000` }));
    const r = prepararConversa([{ autor: "argos", texto: "   " }, ...msgs]);
    expect(r).toHaveLength(30);
    expect(r[29].texto).toBe("fala 34 [removido]");
    expect(r.every((m) => m.texto.length <= MAX_MENSAGEM)).toBe(true);
  });
});
