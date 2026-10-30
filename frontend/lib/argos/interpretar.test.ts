import { describe, expect, it } from "vitest";

import { extrairCep, extrairNome, interpretar, normalizar } from "./interpretar";

describe("normalizar", () => {
  it("tira acento, pontuação e caixa", () => {
    expect(normalizar("  Quanto o João GASTOU?! ")).toBe("quanto o joao gastou");
    expect(normalizar("Presença, votações e ação")).toBe("presenca votacoes e acao");
  });
});

describe("extrairCep", () => {
  it.each([
    ["88340-000", "88340-000"],
    ["88340000", "88340-000"],
    ["moro no 01310-100, e agora?", "01310-100"],
    ["meu cep é 01310 100", "01310-100"],
  ])("acha o CEP em %s", (frase, esperado) => {
    expect(extrairCep(frase)).toBe(esperado);
  });

  it("não confunde com número maior nem menor", () => {
    expect(extrairCep("123456789")).toBeUndefined();
    expect(extrairCep("1234-567")).toBeUndefined();
    expect(extrairCep("sem número")).toBeUndefined();
  });
});

describe("extrairNome", () => {
  it.each([
    ["quanto o Fulano gastou", "fulano"],
    ["gastos do deputado Tabata Amaral", "tabata amaral"],
    ["presença da Maria do Rosário", "maria do rosario"],
    ["Fulano", "fulano"],
    ["e a presença dele?", undefined],
    ["quanto gastou", undefined],
    ["oi", undefined],
    ["ab", undefined],
  ])("%s -> %s", (frase, esperado) => {
    expect(extrairNome(frase)).toBe(esperado);
  });

  it("ignora o CEP", () => {
    expect(extrairNome("88340-000")).toBeUndefined();
  });

  it("frase longa demais não é nome", () => {
    expect(extrairNome("zeta alfa beta gama delta epsilon omega")).toBeUndefined();
  });
});

describe("interpretar", () => {
  it("gastos com nome", () => {
    expect(interpretar("quanto o fulano gastou")).toEqual({ assunto: "gastos", nome: "fulano" });
    expect(interpretar("Gastos de Tabata Amaral")).toEqual({ assunto: "gastos", nome: "tabata amaral" });
    expect(interpretar("a cota de Fulano")).toEqual({ assunto: "gastos", nome: "fulano" });
  });

  it("gastos sem nome (usa a pessoa lembrada)", () => {
    expect(interpretar("quanto gastou?")).toEqual({ assunto: "gastos", nome: undefined });
  });

  it("presença", () => {
    expect(interpretar("e a presença dele?")).toEqual({ assunto: "presenca", nome: undefined });
    expect(interpretar("quantas votações o Fulano faltou")).toEqual({ assunto: "presenca", nome: "fulano" });
    expect(interpretar("compareceu")).toEqual({ assunto: "presenca", nome: undefined });
  });

  it("projetos", () => {
    expect(interpretar("projetos de lei do Fulano")).toEqual({ assunto: "projetos", nome: "fulano" });
    expect(interpretar("o que ele propôs?")).toEqual({ assunto: "projetos", nome: undefined });
  });

  it("emendas vencem 'dinheiro' solto", () => {
    expect(interpretar("quanto dinheiro o Fulano mandou dinheiro para a cidade")).toMatchObject({ assunto: "emendas" });
    expect(interpretar("emendas da Fulana")).toEqual({ assunto: "emendas", nome: "fulana" });
    expect(interpretar("verba")).toMatchObject({ assunto: "emendas" });
  });

  it("CEP", () => {
    expect(interpretar("88340-000")).toEqual({ assunto: "representantes", cep: "88340-000" });
    expect(interpretar("moro no cep 01310100")).toEqual({ assunto: "representantes", cep: "01310-100" });
  });

  it("representantes sem CEP", () => {
    expect(interpretar("quem me representa?")).toMatchObject({ assunto: "representantes" });
    expect(interpretar("quem são meus deputados")).toMatchObject({ assunto: "representantes" });
    expect(interpretar("moro em Gaspar")).toMatchObject({ assunto: "representantes" });
  });

  it("opinião vem antes de tudo, até do CEP", () => {
    expect(interpretar("em quem votar?")).toMatchObject({ assunto: "opiniao" });
    expect(interpretar("em quem eu voto")).toMatchObject({ assunto: "opiniao" });
    expect(interpretar("o Fulano é corrupto?")).toMatchObject({ assunto: "opiniao" });
    expect(interpretar("qual o melhor deputado")).toMatchObject({ assunto: "opiniao" });
    expect(interpretar("em quem votar no cep 88340-000")).toMatchObject({ assunto: "opiniao" });
    expect(interpretar("esse cara presta?")).toMatchObject({ assunto: "opiniao" });
  });

  it("dúvidas sobre o site", () => {
    expect(interpretar("o que é a média da casa")).toEqual({ assunto: "site", perguntaId: "media-casa" });
    expect(interpretar("de onde vêm os dados?")).toEqual({ assunto: "site", perguntaId: "fonte" });
    expect(interpretar("o site guarda meu CEP?")).toEqual({ assunto: "site", perguntaId: "cep" });
    expect(interpretar("vocês dão nota ou ranking?")).toEqual({ assunto: "site", perguntaId: "nota" });
    expect(interpretar("quem paga o site")).toEqual({ assunto: "site", perguntaId: "quem-paga" });
    expect(interpretar("posso baixar os dados?")).toEqual({ assunto: "site", perguntaId: "dados" });
    expect(interpretar("como funciona")).toEqual({ assunto: "site", perguntaId: "sobre" });
  });

  it("saudação e ajuda", () => {
    expect(interpretar("oi")).toEqual({ assunto: "saudacao" });
    expect(interpretar("Olá, bom dia!")).toEqual({ assunto: "saudacao" });
    expect(interpretar("ajuda")).toEqual({ assunto: "saudacao" });
    expect(interpretar("o que você faz?")).toEqual({ assunto: "saudacao" });
  });

  it("só o nome vira 'pessoa'", () => {
    expect(interpretar("Tabata Amaral")).toEqual({ assunto: "pessoa", nome: "tabata amaral" });
    expect(interpretar("oi, Fulano")).toEqual({ assunto: "pessoa", nome: "fulano" });
  });

  it("vazio ou só pontuação não é entendido", () => {
    expect(interpretar("")).toMatchObject({ assunto: "nenhum" });
    expect(interpretar("???")).toMatchObject({ assunto: "nenhum" });
    expect(interpretar("a o e")).toMatchObject({ assunto: "nenhum" });
  });

  it("opinião em qualquer ordem de palavras", () => {
    expect(interpretar("votar em quem?")).toMatchObject({ assunto: "opiniao" });
    expect(interpretar("quem eu escolho para votar")).toMatchObject({ assunto: "opiniao" });
    expect(interpretar("quem votou contra a reforma")).not.toMatchObject({ assunto: "opiniao" });
  });

  it("ranking não usa pessoa", () => {
    for (const f of ["quem gastou mais", "quem faltou menos", "qual gastou mais?", "quem mais gastou", "quais propuseram mais projetos"]) {
      expect(interpretar(f).assunto).toBe("ranking");
    }
    expect(interpretar("quanto o Fulano gastou").assunto).toBe("gastos");
  });
});
