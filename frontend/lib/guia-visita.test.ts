import { describe, expect, it } from "vitest";

import {
  chegouAoFim,
  GUIA_GERAL,
  GUIA_PERFIL,
  guiaJaVisto,
  passoDoProgresso,
  passosDoGuia,
  progressoDeRolagem,
  tipoDeGuia,
} from "./guia-visita";

describe("tipoDeGuia", () => {
  it("geral na página inicial", () => {
    expect(tipoDeGuia("/")).toBe("geral");
  });
  it("perfil em página de pessoa, não no cartão", () => {
    expect(tipoDeGuia("/parlamentar/123")).toBe("perfil");
    expect(tipoDeGuia("/vereador/9/")).toBe("perfil");
    expect(tipoDeGuia("/deputado-estadual/5")).toBe("perfil");
    expect(tipoDeGuia("/eleito/7")).toBe("perfil");
    expect(tipoDeGuia("/parlamentar/123/cartao")).toBeNull();
  });
  it("nenhum nas outras páginas", () => {
    expect(tipoDeGuia("/projetos")).toBeNull();
    expect(tipoDeGuia("/parlamentar/")).toBeNull();
    expect(tipoDeGuia(null)).toBeNull();
  });
});

describe("rolagem", () => {
  it("progresso entre 0 e 1", () => {
    expect(progressoDeRolagem(0, 2000, 800)).toBe(0);
    expect(progressoDeRolagem(600, 2000, 800)).toBe(0.5);
    expect(progressoDeRolagem(5000, 2000, 800)).toBe(1);
    expect(progressoDeRolagem(10, 700, 800)).toBe(0);
  });
  it("cada terço acende um passo", () => {
    expect(passoDoProgresso(0)).toBe(0);
    expect(passoDoProgresso(0.34)).toBe(1);
    expect(passoDoProgresso(0.67)).toBe(2);
    expect(passoDoProgresso(1)).toBe(2);
  });
  it("fim da página", () => {
    expect(chegouAoFim(0.5)).toBe(false);
    expect(chegouAoFim(0.98)).toBe(true);
  });
});

describe("conteúdo", () => {
  it("três passos em cada guia", () => {
    expect(passosDoGuia("geral")).toBe(GUIA_GERAL);
    expect(passosDoGuia("perfil")).toBe(GUIA_PERFIL);
    expect(GUIA_GERAL).toHaveLength(3);
    expect(GUIA_PERFIL).toHaveLength(3);
  });
  it("lembrança", () => {
    expect(guiaJaVisto("1")).toBe(true);
    expect(guiaJaVisto(null)).toBe(false);
  });
});
